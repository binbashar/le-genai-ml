# AgentCore Voice + LiveKit

Bidirectional voice agent that combines [LiveKit](https://livekit.io/) (WebRTC) with [AWS Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/) and [Amazon Nova 2 Sonic](https://docs.aws.amazon.com/nova/latest/nova2-userguide/sonic-getting-started.html) for real-time speech-to-speech conversations.

```
Browser  ◄──WebRTC──►  LiveKit Server  ◄──Room──►  Bridge Worker  ◄──WebSocket──►  AgentCore  ◄──Bedrock──►  Nova 2 Sonic
 :3000                    :7880                      agent.py                       :8080/ws                   us-east-1
```

The user speaks into the browser, audio flows through LiveKit to the Bridge Worker, which forwards it over WebSocket to an AgentCore voice agent. Nova 2 Sonic processes the audio and responds — full-duplex with barge-in support.

## Quick Start

### Prerequisites

- [just](https://github.com/casey/just) — `brew install just`
- [uv](https://docs.astral.sh/uv/) — `brew install uv`
- [LiveKit Server + CLI](https://docs.livekit.io/home/cli/cli-setup/) — `just install-livekit`

### Run locally (echo mode — no AWS needed)

```bash
just install    # Install Python dependencies
just start      # Start all components + open browser
```

This starts LiveKit, the voice agent (echo backend), the bridge worker, and opens Chrome with the mic enabled. You'll hear your own voice echoed back, confirming the full pipeline works.

### Run with Nova 2 Sonic (requires AWS credentials)

```bash
VOICE_BACKEND=nova_sonic just start
```

The voice agent connects to Amazon Nova 2 Sonic via Bedrock. Speak naturally and get AI voice responses in real time.

> **Note:** Requires valid AWS credentials with `bedrock:InvokeModel` permissions in `us-east-1`. Run `just whoami` to verify.

### Stop

```bash
just stop
```

## How It Works

Each component has a single responsibility:

| Component | File | Role |
|-----------|------|------|
| **Frontend** | `web/index.html` | Captures mic audio via WebRTC, plays agent audio |
| **LiveKit Server** | `livekit-server --dev` | WebRTC media gateway (SFU) |
| **Bridge Worker** | `agent.py` | Translates LiveKit audio frames ↔ AgentCore WebSocket |
| **Voice Agent** | `agentcore/voice_agent.py` | WebSocket server that delegates to a voice backend |
| **Voice Backend** | `agentcore/backends/` | Pluggable audio processing (Nova Sonic, echo, etc.) |

The frontend knows nothing about AI models. The bridge knows nothing about which model runs behind AgentCore. Each layer can be swapped independently.

## Deployment Levels

| Level | What's local | What's on AWS | Command |
|-------|-------------|---------------|---------|
| **1 — All local** | Everything | Bedrock API only | `just start` |
| **2 — Hybrid** | LiveKit + Bridge + Frontend | AgentCore Runtime + Bedrock | `just start-hybrid ARN` |
| **3 — Docker** | Containers on EC2 | AgentCore Runtime + Bedrock | `docker compose up -d` |

### Level 2: Hybrid

Deploy the voice agent to AgentCore Runtime, keep LiveKit local:

```bash
just deploy-agentcore
# Copy the ARN from the output, then:
just start-hybrid arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/...
```

### Level 3: Docker Compose

```bash
export AGENTCORE_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:...
docker compose up -d
```

## Voice Backends

The voice agent uses a strategy pattern — swap backends without changing anything else.

| Backend | Status | Description |
|---------|--------|-------------|
| `echo` | Working | Echoes user audio back. No AWS needed. Default for local dev. |
| `nova_sonic` | Working | Bidirectional streaming with Nova 2 Sonic. 16 kHz in, 24 kHz out. Barge-in support. |
| `cascade` | Stub | Extension point for STT → LLM → TTS pipelines. |

### Add a custom backend

1. Create `agentcore/backends/my_backend.py` implementing `VoiceBackend`:

```python
from backends.base import VoiceBackend

class MyBackend(VoiceBackend):
    async def start_session(self, config: dict) -> None: ...
    async def send_audio(self, audio_bytes: bytes) -> None: ...
    async def receive_audio(self) -> AsyncIterator[bytes]: ...
    async def close(self) -> None: ...
```

2. Register in `agentcore/backends/__init__.py`:

```python
BACKENDS["my_backend"] = MyBackend
```

3. Select it: `VOICE_BACKEND=my_backend just start`

## Project Structure

```
├── agent.py                    # Bridge Worker (LiveKit ↔ AgentCore)
├── web/index.html              # Browser frontend (vanilla JS + LiveKit SDK)
├── justfile                    # Task runner recipes
├── pyproject.toml              # Bridge Worker dependencies
│
├── agentcore/
│   ├── voice_agent.py          # AgentCore WebSocket voice agent
│   ├── pyproject.toml          # Voice agent dependencies
│   ├── Dockerfile              # Voice agent container
│   └── backends/
│       ├── base.py             # VoiceBackend ABC
│       ├── echo.py             # Echo backend (testing)
│       ├── nova_sonic.py       # Nova 2 Sonic backend
│       └── cascade.py          # STT→LLM→TTS stub
│
├── docker-compose.yml          # LiveKit + Bridge containers
├── docker-compose.override.yml # Dev override (local voice agent)
├── Dockerfile.bridge           # Bridge Worker container
└── k8s/                        # Reference K8s manifests for EKS
```

> Two separate `pyproject.toml` files: root for bridge worker, `agentcore/` for voice agent. Run `just install` to sync both.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VOICE_BACKEND` | `echo` | Backend: `echo`, `nova_sonic`, or `cascade` |
| `VOICE_ID` | `tiffany` | Nova Sonic voice ID |
| `AGENTCORE_WS_URL` | — | Direct WebSocket URL (local dev) |
| `AGENTCORE_RUNTIME_ARN` | — | AgentCore Runtime ARN (AWS, mutually exclusive with above) |
| `AWS_REGION` | `us-east-1` | AWS region for Bedrock |
| `LIVEKIT_URL` | `ws://localhost:7880` | LiveKit server URL |
| `LIVEKIT_API_KEY` | `devkey` | LiveKit API key |
| `LIVEKIT_API_SECRET` | `secret` | LiveKit API secret |

See [`.env.example`](.env.example) for a copyable template.

## Troubleshooting

**No audio from the agent** — Check AWS credentials (`just whoami`) and voice agent logs (`tail -f /tmp/voice-agent.log`). The Smithy SDK hangs silently without valid credentials.

**Bridge connects but no job dispatched** — LiveKit doesn't retry jobs for the same room. Use a fresh room name or restart LiveKit (`just stop && just start`).

**Port 8080 already in use** — Kill the previous voice agent: `lsof -ti :8080 | xargs kill -9`

**Token expired** — Regenerate: `just token`

**Docker bridge can't reach local voice agent** — The override uses `host.docker.internal` (macOS/Windows). On Linux, use `--network=host`.

## Useful Commands

```bash
just --list          # Show all available recipes
just check           # Verify prerequisites are installed
just voice-agent     # Run voice agent standalone
just bridge          # Run bridge worker standalone
just livekit-server  # Run LiveKit standalone
just frontend        # Serve frontend standalone
just token           # Generate a LiveKit access token
just whoami          # Check AWS identity
just sso-login       # AWS SSO login
just clean           # Remove .venv and caches
```

## Links

- [AWS Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Amazon Nova 2 Sonic](https://docs.aws.amazon.com/nova/latest/nova2-userguide/sonic-getting-started.html)
- [LiveKit Self-Hosting](https://docs.livekit.io/home/self-hosting/local/)
- [LiveKit Agents Framework](https://docs.livekit.io/agents/)
- [Reference: Nova Sonic WebSocket AgentCore Sample](https://github.com/aws-samples/sample-nova-sonic-websocket-agentcore)
