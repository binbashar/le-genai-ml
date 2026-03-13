# AgentCore + LiveKit Bidirectional Voice Agent

**Date:** 2026-03-13
**Status:** Draft
**Branch:** `feat/nova-sonic-livekit-poc`

## Problem Statement

A client running voice agents on EKS wants to migrate their AI logic to AWS Bedrock AgentCore Runtime while preserving low-latency WebRTC communication to the browser. They currently use a cascade pipeline (STT→LLM→TTS) and OpenAI Realtime API, and want an architecture that supports their existing stack while enabling a future migration to Nova Sonic 2. They require LiveKit self-hosted (not cloud) for media transport.

## Solution Overview

**Approach A: LiveKit as WebRTC media gateway + AgentCore as bidirectional voice backend.**

LiveKit Server handles WebRTC transport. A lightweight Bridge Worker translates between LiveKit audio frames and AgentCore's WebSocket bidirectional protocol. AgentCore Runtime hosts the voice agent with a pluggable backend (Nova Sonic 2 by default, extensible to cascade pipelines).

## Architecture

```
┌─────────────┐    WebRTC     ┌──────────────┐    Room     ┌──────────────┐   WebSocket    ┌─────────────────┐
│   Browser   │◄════════════►│ LiveKit Server│◄══════════►│ Bridge Worker│◄══════════════►│ AgentCore       │
│ (vanilla JS)│  audio/signal │ (self-hosted) │ audio frames│ (stateless)  │  audio/control │ Runtime (managed)│
└─────────────┘               └──────────────┘             └──────────────┘                └─────────────────┘
                                    │                                                            │
                               Helm chart                                                   @app.websocket
                               STUN/TURN                                                    port 8080 /ws
                               Room mgmt                                                    Auto-scaling
                                                                                            Sessions
                                                                                            Versioning
```

### Components

1. **Browser (frontend)** — Vanilla JS + LiveKit Client SDK. Connects to a LiveKit room via WebRTC. Captures microphone, plays agent audio. Status indicators for connection state.

2. **LiveKit Server (self-hosted)** — Deployed via Helm chart on EKS (or locally for dev). Handles WebRTC signaling, STUN/TURN, room management, media routing. No AI logic.

3. **Bridge Worker (stateless)** — LiveKit Agent Worker (~80 lines). Registers with LiveKit Server, receives job dispatch when a user joins a room. Captures audio frames from the human participant, forwards them via WebSocket to AgentCore. Receives audio from AgentCore and publishes it back to the room. Does not know what AI model runs behind AgentCore.

4. **AgentCore Runtime (AWS managed)** — Runs the voice agent. Exposes `@app.websocket` on `/ws`. Receives audio, delegates to a pluggable `VoiceBackend`, returns audio. AWS handles scaling, versioning, sessions, observability.

### Conversation Flow

1. User opens browser → connects to a LiveKit room
2. LiveKit Server detects the room → dispatches a job to the Bridge Worker
3. Bridge Worker accepts the job, joins the room as a participant
4. Bridge Worker opens WebSocket to AgentCore Runtime
5. User speaks → WebRTC carries audio to LiveKit Server → LiveKit delivers it to Bridge Worker as `AudioFrame`
6. Bridge Worker packages frames → sends them over WebSocket to AgentCore
7. AgentCore processes (Nova Sonic / cascade) → returns audio over WebSocket
8. Bridge Worker receives audio → publishes it to the room → WebRTC carries it to browser
9. User hears the response

## Extensibility: VoiceBackend Strategy Pattern

The AgentCore voice agent uses a strategy pattern to decouple the WebSocket protocol from the voice processing backend.

### Interface

```python
class VoiceBackend(ABC):
    """Interface for bidirectional voice processing backends."""

    @abstractmethod
    async def start_session(self, config: dict) -> None:
        """Initialize the voice session (model connection, etc.)."""

    @abstractmethod
    async def send_audio(self, audio_bytes: bytes) -> None:
        """Send audio chunk from user to the backend."""

    @abstractmethod
    async def receive_audio(self) -> AsyncIterator[bytes]:
        """Yield audio chunks from the backend to send back to user."""

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources."""
```

### Implementations

- **`NovaSonicBackend`** (default, fully functional): Opens bidirectional stream to Bedrock Nova Sonic 2. `send_audio()` feeds the input stream, `receive_audio()` yields from the output stream. Native barge-in support.

- **`CascadeBackend`** (stub with documented extension points): Shows where to plug STT (Transcribe/Whisper), LLM (Claude/Nova), and TTS (Polly/ElevenLabs). Implemented as a stub with comments, not functional code.

### Factory

The `session_start` message from the Bridge Worker includes a `backend` field. A factory function instantiates the correct implementation:

```python
def create_backend(config: dict) -> VoiceBackend:
    backend_type = config.get("backend", "nova_sonic")
    if backend_type == "nova_sonic":
        return NovaSonicBackend(config)
    elif backend_type == "cascade":
        return CascadeBackend(config)
    raise ValueError(f"Unknown backend: {backend_type}")
```

## WebSocket Protocol (Bridge ↔ AgentCore)

### Message Types

**JSON messages** for control:

```json
// Bridge → AgentCore: Start session
{"type": "session_start", "config": {"backend": "nova_sonic", "sample_rate": 24000, "voice_id": "tiffany"}}

// AgentCore → Bridge: Session ready
{"type": "session_ready"}

// Bridge → AgentCore: User interrupted (barge-in)
{"type": "interrupt"}

// Bridge → AgentCore: End session
{"type": "session_end"}
```

**Binary frames** for audio:
- Raw PCM 16-bit mono, 24kHz
- No base64 encoding (binary WebSocket frames, ~33% more efficient)
- 24kHz is the native format for both LiveKit and Nova Sonic — zero re-encoding needed

### AgentCore WebSocket Frame Size

AgentCore has a 32KB maximum message frame size. At 24kHz 16-bit mono, that's ~682ms of audio per frame — well within normal streaming chunk sizes (typically 20-60ms frames).

## Separation of Responsibilities

| Component | Knows about | Does NOT know about |
|---|---|---|
| **Frontend** | LiveKit SDK, WebRTC, UI | AgentCore, AI models |
| **LiveKit Server** | WebRTC, rooms, signaling | AI, AgentCore, audio processing |
| **Bridge Worker** | LiveKit AudioFrame, WebSocket protocol | What model runs, AI logic |
| **AgentCore voice_agent** | WebSocket protocol, backend factory | LiveKit, WebRTC |
| **VoiceBackend impl** | Its specific model (Nova Sonic, cascade) | WebSocket, LiveKit, frontend |

## Error Handling

### AgentCore WebSocket disconnects mid-conversation
- Bridge Worker detects `ConnectionClosed`
- Reconnects with exponential backoff (3 attempts: 1s, 2s, 4s)
- Buffers up to 2s of user audio during reconnection
- If reconnection fails → closes session cleanly, publishes silence to room

### Bridge Worker crashes
- LiveKit Server detects participant left the room
- Dispatches a new job to another available worker (native LiveKit pool model)
- New AgentCore session starts — user experiences ~2-3s interruption
- Stateless by design: nothing to recover

### User loses WebRTC connection
- LiveKit handles automatic reconnection (ICE restart)
- Bridge Worker detects audio track disconnected
- Keeps AgentCore session open for configurable timeout (default: 30s)
- If user returns, conversation continues without restart

### Barge-in (interruptions)
- LiveKit detects VAD from user while agent is speaking
- Bridge Worker sends `{"type": "interrupt"}` to AgentCore
- Nova Sonic backend: handles barge-in natively (stops generating)
- Cascade backend: cancels TTS in progress, restarts pipeline with new audio

## Security

```
Browser ──DTLS/SRTP──► LiveKit ──internal──► Bridge ──WSS+SigV4──► AgentCore ──IAM──► Bedrock
          (WebRTC)                           (EKS pod)              (managed)
```

| Segment | Protocol | Auth |
|---|---|---|
| Browser ↔ LiveKit | WebRTC (DTLS-SRTP) | LiveKit JWT tokens (short TTL, room-scoped) |
| Bridge ↔ AgentCore | WSS | SigV4 via IRSA (EKS pod IAM role) |
| AgentCore ↔ Bedrock | Internal AWS | Execution role (`bedrock:InvokeModelWithResponseStream`) |

Bridge Worker requires only one IAM permission: `bedrock-agentcore:InvokeAgentRuntimeWithWebSocketStream`.

## Deployment & Testing Strategy

### Level 1: Full local (development)

Everything on local machine. Validates code correctness, not real AWS integration.

```bash
just start
```

- LiveKit Server: `livekit-server --dev` (no TLS, devkey/secret)
- Bridge Worker: connects to `ws://localhost:8080/ws`
- AgentCore voice_agent: runs as plain Starlette/Uvicorn server on port 8080
- Frontend: static server on port 3000
- Token: generated LiveKit JWT for the frontend

The `voice_agent.py` runs locally because `BedrockAgentCoreApp` is internally a Starlette app. The `@app.websocket` decorator works identically in both local and deployed environments.

### Level 2: Hybrid local + AgentCore on AWS (recommended for demos)

Validates real WebSocket bidi integration, SigV4 auth, Nova Sonic on Bedrock, real latency.

```bash
just deploy-agentcore    # Deploy voice agent to AgentCore Runtime
just start-hybrid        # Local LiveKit + Bridge connecting to AWS
```

- AgentCore: deployed via `agentcore launch` (managed AWS)
- LiveKit Server + Bridge Worker: local
- Bridge Worker connects to AgentCore ARN via WSS+SigV4
- Frontend: local, connects to local LiveKit

### Level 3: All on AWS without EKS (client validation)

Single EC2 (t3.medium) running Docker Compose with LiveKit Server + Bridge Worker. AgentCore on AWS. Validates the full architecture without EKS complexity.

```bash
# On EC2
docker compose up -d
```

The client can then migrate the Docker Compose services to their EKS using the provided `k8s/` manifests.

### Connection routing logic in Bridge Worker

```python
# If AGENTCORE_WS_URL is set → direct WebSocket (local dev)
# If AGENTCORE_RUNTIME_ARN is set → WSS+SigV4 via SDK (AWS)
```

## Project Structure

```
genai-agentcore-voice-livekit/
├── agent.py                          # Bridge Worker (LiveKit ↔ AgentCore)
├── web/
│   └── index.html                    # Frontend (LiveKit Client SDK)
├── justfile                          # Task runner (start, start-hybrid, deploy, etc.)
├── pyproject.toml                    # Bridge Worker dependencies
├── docker-compose.yml                # LiveKit Server + Bridge Worker
├── docker-compose.override.yml       # Dev local overrides
├── Dockerfile.bridge                 # Bridge Worker container
├── .env.example                      # Documented environment variables
│
├── agentcore/                        # Voice agent for AgentCore Runtime
│   ├── voice_agent.py                # @app.websocket entrypoint
│   ├── backends/
│   │   ├── base.py                   # VoiceBackend ABC
│   │   ├── nova_sonic.py             # Nova Sonic 2 bidi (functional)
│   │   └── cascade.py                # Cascade pipeline (stub)
│   ├── Dockerfile                    # AgentCore container
│   └── pyproject.toml                # Agent dependencies
│
├── k8s/                              # Kubernetes manifests (reference)
│   ├── bridge-deployment.yaml        # Bridge Worker Deployment
│   └── livekit-values.yaml           # Helm values for LiveKit Server
│
├── CLAUDE.md
└── README.md
```

## Environment Variables

```bash
# Bridge Worker
LIVEKIT_URL=ws://localhost:7880           # LiveKit server URL
LIVEKIT_API_KEY=devkey                    # LiveKit API key
LIVEKIT_API_SECRET=secret                 # LiveKit API secret
AGENTCORE_RUNTIME_ARN=                    # AgentCore Runtime ARN (prod, mutually exclusive with WS_URL)
AGENTCORE_WS_URL=ws://localhost:8080/ws   # Direct WebSocket URL (dev, mutually exclusive with ARN)
VOICE_BACKEND=nova_sonic                  # Backend selection (nova_sonic | cascade)
VOICE_ID=tiffany                          # Voice ID for Nova Sonic

# AgentCore voice agent (set by AgentCore Runtime or manually for local)
AWS_REGION=us-east-1                      # Bedrock region
```

## Deliverables

### Code (functional)

1. **`agentcore/voice_agent.py`** (~100 lines) — WebSocket handler with backend factory
2. **`agentcore/backends/base.py`** (~30 lines) — `VoiceBackend` ABC
3. **`agentcore/backends/nova_sonic.py`** (~120 lines) — Nova Sonic 2 bidi implementation
4. **`agentcore/backends/cascade.py`** (~60 lines) — Documented stub
5. **`agent.py`** (~80 lines) — Bridge Worker (evolution of existing POC)
6. **`web/index.html`** — Frontend with connection status indicators

### Configuration

7. **`justfile`** — Recipes for all testing levels
8. **`docker-compose.yml`** + **`docker-compose.override.yml`** — LiveKit + Bridge
9. **`Dockerfile.bridge`** — Bridge Worker container
10. **`agentcore/Dockerfile`** — Voice agent container
11. **`k8s/bridge-deployment.yaml`** — Reference Kubernetes manifest
12. **`k8s/livekit-values.yaml`** — Reference Helm values
13. **`.env.example`** — Documented variables

### Not in scope

- Complete LiveKit Helm chart (official chart exists)
- CDK/Terraform for client's EKS
- Functional cascade backend implementation (stub only)
- Auth/Cognito integration (reference exists in `genai-agentcore-demos/`)
- Production TLS certificate management

## References

- [AgentCore WebSocket Bidirectional Streaming](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-websocket.html)
- [sample-nova-sonic-websocket-agentcore](https://github.com/aws-samples/sample-nova-sonic-websocket-agentcore)
- [AgentCore Bidirectional Streaming Tutorial](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/01-AgentCore-runtime/06-bi-directional-streaming)
- [LiveKit Self-Hosting on Kubernetes](https://docs.livekit.io/transport/self-hosting/kubernetes/)
- [LiveKit Agents Framework](https://docs.livekit.io/agents/)
- [LiveKit Agent Server Overview](https://docs.livekit.io/agents/server/)
- [LiveKit Realtime Models](https://docs.livekit.io/agents/models/realtime/)
