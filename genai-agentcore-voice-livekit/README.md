# AgentCore Voice Agent + LiveKit

Bidirectional voice agent architecture combining **LiveKit** (self-hosted WebRTC media gateway) with **AWS Bedrock AgentCore Runtime** (managed voice backend) and **Amazon Nova Sonic 2** (speech-to-speech foundation model).

## Architecture

```
┌─────────┐     WebRTC      ┌─────────────┐    Room     ┌──────────────┐    WebSocket    ┌───────────────────┐    Bedrock API    ┌──────────────┐
│ Browser  │◄──────────────►│ LiveKit      │◄──────────►│ Bridge       │◄──────────────►│ AgentCore Voice   │◄───────────────►│ Nova Sonic 2 │
│ (WebRTC) │                │ Server       │            │ Worker       │                │ Agent             │                  │ (Bedrock)    │
└─────────┘                 └─────────────┘             └──────────────┘                └───────────────────┘                  └──────────────┘
  web/index.html             livekit-server               agent.py                       agentcore/                             amazon.nova-
  port 3000                  port 7880                    (LiveKit SDK)                   voice_agent.py                         sonic-v1:0
                                                                                          port 8080 /ws
```

**How it works:**

1. User opens the browser frontend and connects to a LiveKit room via WebRTC
2. LiveKit Server dispatches a job to the Bridge Worker when a participant joins
3. Bridge Worker opens a WebSocket connection to the AgentCore voice agent
4. User speaks -- audio flows: Browser -> LiveKit -> Bridge Worker -> AgentCore -> Nova Sonic 2
5. Nova Sonic 2 responds -- audio flows back the same path to the browser speaker
6. Full-duplex: the user can interrupt (barge-in) at any time

Each component is isolated by responsibility. The frontend knows nothing about AI models. The Bridge Worker knows nothing about what model runs behind AgentCore. The AgentCore voice agent knows nothing about LiveKit or WebRTC.

## Quick Start

### Prerequisites

| Tool | Install | Purpose |
|------|---------|---------|
| [just](https://github.com/casey/just) | `brew install just` | Task runner |
| [uv](https://docs.astral.sh/uv/) | `brew install uv` | Python package manager |
| Python 3.13 | via uv | Runtime |
| [LiveKit CLI + Server](https://docs.livekit.io/home/cli/cli-setup/) | `just install-livekit` | WebRTC infrastructure |
| AWS CLI | `brew install awscli` | AWS credentials |
| AWS credentials | `aws configure` or SSO | Bedrock API access (Nova Sonic 2) |

### Level 1: All Local

Everything runs on your machine. Validates code correctness and end-to-end audio flow.

```bash
# 1. Install dependencies
just install

# 2. Start everything (LiveKit + voice agent + bridge + frontend)
just start
```

This will:
- Start LiveKit Server in dev mode (port 7880)
- Start the AgentCore voice agent locally (port 8080)
- Start the Bridge Worker connecting to both
- Generate a LiveKit token and open the browser at http://localhost:3000
- Your microphone will be enabled -- speak and the agent responds

To stop all processes:

```bash
just stop
```

### Level 2: Hybrid (Local LiveKit + AWS AgentCore)

The voice agent runs on AWS Bedrock AgentCore Runtime. LiveKit and the Bridge Worker remain local. This validates real SigV4 WebSocket auth, Nova Sonic on Bedrock, and production-like latency.

```bash
# 1. Deploy voice agent to AgentCore Runtime
just deploy-agentcore

# 2. Copy the ARN from the deploy output, then:
just start-hybrid arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/voice-agent-xyz
```

The Bridge Worker detects `AGENTCORE_RUNTIME_ARN` and uses the AgentCore SDK to open a SigV4-signed WSS connection instead of a direct WebSocket.

### Level 3: Docker Compose (EC2 / CI)

All infrastructure in containers. AgentCore voice agent runs on AWS. Suitable for single-EC2 deployment or CI validation.

```bash
# Set the AgentCore Runtime ARN
export AGENTCORE_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/...

# Start LiveKit Server + Bridge Worker
docker compose up -d
```

The `docker-compose.yml` runs LiveKit Server and the Bridge Worker. The Bridge Worker connects to the AgentCore Runtime ARN via environment variable.

For local development with a local voice agent, Docker Compose automatically applies the override file:

```bash
# Starts with docker-compose.override.yml (bridge -> ws://host.docker.internal:8080/ws)
docker compose up -d

# Run voice agent on host
cd agentcore && uv run python voice_agent.py
```

## Project Structure

```
genai-agentcore-voice-livekit/
├── agent.py                          # Bridge Worker (LiveKit <-> AgentCore)
├── web/
│   └── index.html                    # Frontend (LiveKit Client SDK, vanilla JS)
├── justfile                          # Task runner (start, start-hybrid, deploy, etc.)
├── pyproject.toml                    # Bridge Worker dependencies
├── docker-compose.yml                # LiveKit Server + Bridge Worker
├── docker-compose.override.yml       # Dev override (local voice agent)
├── Dockerfile.bridge                 # Bridge Worker container
├── .env.example                      # Documented environment variables
│
├── agentcore/                        # Voice agent for AgentCore Runtime
│   ├── voice_agent.py                # @app.websocket entrypoint
│   ├── backends/
│   │   ├── base.py                   # VoiceBackend abstract base class
│   │   ├── nova_sonic.py             # Nova Sonic 2 bidirectional (functional)
│   │   ├── cascade.py                # STT->LLM->TTS pipeline (stub)
│   │   └── __init__.py               # Backend factory
│   ├── Dockerfile                    # AgentCore container
│   └── pyproject.toml                # Agent dependencies
│
├── k8s/                              # Kubernetes manifests (reference)
│   ├── bridge-deployment.yaml        # Bridge Worker Deployment + ConfigMap + Secret
│   └── livekit-values.yaml           # Helm values for LiveKit Server on EKS
│
├── CLAUDE.md                         # Claude Code guidance
└── README.md                         # This file
```

## Backend Extensibility

The voice agent uses a **strategy pattern** to decouple the WebSocket protocol from the voice processing backend. The Bridge Worker sends a `backend` field in the `session_start` message, and the factory instantiates the correct implementation.

### VoiceBackend interface

```python
class VoiceBackend(ABC):
    async def start_session(self, config: dict) -> None: ...
    async def send_audio(self, audio_bytes: bytes) -> None: ...
    async def receive_audio(self) -> AsyncIterator[bytes]: ...
    async def close(self) -> None: ...
```

### Built-in backends

| Backend | Status | Description |
|---------|--------|-------------|
| `nova_sonic` | Functional | Bidirectional streaming with Amazon Nova Sonic 2 via the Smithy Bedrock SDK. Input: 16 kHz PCM. Output: 24 kHz PCM. Native barge-in support. |
| `cascade` | Stub | Documented extension point for traditional STT -> LLM -> TTS pipelines (Transcribe/Whisper + Claude/Nova + Polly/ElevenLabs). |

### Adding a new backend

1. Create `agentcore/backends/my_backend.py` implementing `VoiceBackend`
2. Register in `agentcore/backends/__init__.py`:
   ```python
   from backends.my_backend import MyBackend
   BACKENDS["my_backend"] = MyBackend
   ```
3. Clients select it by sending `{"backend": "my_backend"}` in the session config

No changes needed in the Bridge Worker, voice agent, or frontend.

## Environment Variables

| Variable | Component | Default | Description |
|----------|-----------|---------|-------------|
| `LIVEKIT_URL` | Bridge Worker | `ws://localhost:7880` | LiveKit server WebSocket URL |
| `LIVEKIT_API_KEY` | Bridge Worker | `devkey` | LiveKit API key |
| `LIVEKIT_API_SECRET` | Bridge Worker | `secret` | LiveKit API secret |
| `AGENTCORE_WS_URL` | Bridge Worker | -- | Direct WebSocket URL for local dev (`ws://localhost:8080/ws`) |
| `AGENTCORE_RUNTIME_ARN` | Bridge Worker | -- | AgentCore Runtime ARN for AWS (mutually exclusive with `AGENTCORE_WS_URL`) |
| `VOICE_BACKEND` | Bridge Worker | `nova_sonic` | Backend to request: `nova_sonic` or `cascade` |
| `VOICE_ID` | Bridge/Agent | `tiffany` | Nova Sonic voice identifier |
| `AWS_REGION` | Voice Agent | `us-east-1` | AWS region for Bedrock API |
| `AWS_PROFILE` | justfile | `default` | AWS profile for SSO / credential export |

See `.env.example` for a complete template.

## Kubernetes Deployment

Reference manifests are provided in `k8s/` for deploying to Amazon EKS:

- **`bridge-deployment.yaml`**: Deployment, ConfigMap, Secret, and ServiceAccount for the Bridge Worker. Uses IRSA for Bedrock/AgentCore IAM access.
- **`livekit-values.yaml`**: Helm values for the [official LiveKit chart](https://github.com/livekit/livekit-helm) with ALB ingress and WebSocket support.

```bash
# Install LiveKit via Helm
helm repo add livekit https://helm.livekit.io
helm install livekit livekit/livekit-server -f k8s/livekit-values.yaml

# Deploy Bridge Worker
kubectl apply -f k8s/bridge-deployment.yaml
```

The AgentCore voice agent is deployed and managed by AWS (`just deploy-agentcore`). It does not run in your Kubernetes cluster.

## Testing Levels

| Level | Local components | AWS components | Validates | Command |
|-------|-----------------|----------------|-----------|---------|
| **1: All local** | LiveKit + Bridge + Voice Agent + Frontend | Bedrock API only | Code correctness, audio pipeline, WebSocket protocol | `just start` |
| **2: Hybrid** | LiveKit + Bridge + Frontend | AgentCore Runtime + Bedrock | SigV4 auth, real latency, production agent lifecycle | `just start-hybrid ARN` |
| **3: Docker/EC2** | -- | EC2 (Docker Compose) + AgentCore + Bedrock | Full architecture without EKS, container networking | `docker compose up -d` |

## Troubleshooting

### No audio from agent

- Check that your AWS credentials are valid: `just whoami`
- Verify Nova Sonic access in your region (us-east-1 recommended)
- Check voice agent logs: `tail -f /tmp/voice-agent.log`
- Ensure the Bridge Worker connected: `tail -f /tmp/bridge-worker.log`

### "Either AGENTCORE_WS_URL or AGENTCORE_RUNTIME_ARN must be set"

The Bridge Worker requires exactly one connection method. For local dev, `just start` sets `AGENTCORE_WS_URL` automatically. For hybrid mode, pass the ARN to `just start-hybrid`.

### WebSocket handshake fails

- Verify the voice agent is running: `curl http://localhost:8080/ping`
- Check that port 8080 is not in use by another process
- The handshake expects `session_start` as the first message; custom WebSocket clients must follow the protocol

### LiveKit token expired

Generate a new token:

```bash
just token
```

Tokens are valid for 24 hours by default.

### Browser microphone not working

- Use Chrome for best WebRTC audio quality
- Grant microphone permission when prompted
- Check that `localhost:3000` is served over HTTP (not HTTPS) for local dev

### Docker Compose: bridge can't reach local voice agent

The override file uses `host.docker.internal` which works on macOS/Windows Docker Desktop. On Linux, add `--network=host` or configure the host IP manually.

### AWS SSO credentials expired

```bash
just sso-login
# Then re-run your command
```

## Links

- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AgentCore WebSocket Bidirectional Streaming](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-websocket.html)
- [Amazon Nova Sonic 2](https://docs.aws.amazon.com/nova/latest/userguide/speech.html)
- [LiveKit Self-Hosting](https://docs.livekit.io/home/self-hosting/local/)
- [LiveKit Self-Hosting on Kubernetes](https://docs.livekit.io/transport/self-hosting/kubernetes/)
- [LiveKit Agents Framework](https://docs.livekit.io/agents/)
- [sample-nova-sonic-websocket-agentcore](https://github.com/aws-samples/sample-nova-sonic-websocket-agentcore)
