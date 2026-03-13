# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this project.

## Project Overview

Bidirectional voice agent combining **LiveKit** (WebRTC media gateway) with **AWS Bedrock AgentCore Runtime** (managed voice backend). LiveKit handles browser-to-server WebRTC transport, a lightweight Bridge Worker translates between LiveKit audio frames and AgentCore's WebSocket protocol, and AgentCore hosts a voice agent with pluggable backends (Nova Sonic 2 by default).

## Architecture

```
┌───────────┐   WebRTC    ┌──────────────┐   Room    ┌──────────────┐  WebSocket   ┌─────────────────┐  Bedrock API  ┌──────────────┐
│  Browser   │◄══════════►│ LiveKit      │◄════════►│ Bridge       │◄════════════►│ AgentCore Voice │◄════════════►│ Nova Sonic 2 │
│  (Web UI)  │   audio    │ Server       │  frames  │ Worker       │  audio/ctrl  │ Agent           │  bidi stream │ (Bedrock)    │
└───────────┘             └──────────────┘           └──────────────┘              └─────────────────┘              └──────────────┘
   port 3000               port 7880                  agent.py                      agentcore/                       us-east-1
   web/index.html          livekit-server --dev        (LiveKit SDK)                voice_agent.py                   amazon.nova-sonic-v1:0
                                                                                    port 8080 /ws
```

**Audio flows bidirectionally:** user speaks into browser microphone, WebRTC carries audio to LiveKit, Bridge Worker forwards raw PCM over WebSocket to AgentCore, Nova Sonic 2 processes and responds, audio flows back the same path.

## Build & Run Commands

All commands use the `just` task runner. Run from the project root (`genai-agentcore-voice-livekit/`).

| Task | Command | Description |
|------|---------|-------------|
| **Install deps** | `just install` | `uv sync` for both bridge worker and agentcore voice agent |
| **Install LiveKit** | `just install-livekit` | Install LiveKit server and CLI via Homebrew |
| **Check prereqs** | `just check` | Verify aws, livekit-server, lk, uv, python3, just |
| **Start (Level 1)** | `just start` | All local: LiveKit + voice agent + bridge + frontend |
| **Start hybrid (Level 2)** | `just start-hybrid ARN` | Local LiveKit + bridge, AgentCore on AWS |
| **Deploy to AWS** | `just deploy-agentcore` | `agentcore configure` + `agentcore launch` |
| **Stop all** | `just stop` | Kill all background processes |
| **Generate token** | `just token` | Create LiveKit JWT for frontend |
| **AWS SSO login** | `just sso-login` | `aws sso login` with configured profile |
| **Clean** | `just clean` | Remove .venv and __pycache__ |

### Typical workflows

```bash
# Level 1: All local development
just install && just start

# Level 2: Hybrid (AgentCore on AWS)
just deploy-agentcore
# Copy the ARN from the output, then:
just start-hybrid arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/...

# Level 3: Docker Compose (EC2 or CI)
docker compose up -d
```

### Running components individually

```bash
just voice-agent    # AgentCore voice agent on ws://localhost:8080/ws
just bridge         # Bridge worker connecting to local voice agent
just livekit-server # LiveKit server in dev mode (port 7880)
just frontend       # Static file server on port 3000
```

## Key Files

| File | Responsibility |
|------|----------------|
| `agentcore/voice_agent.py` | AgentCore WebSocket voice agent. `@app.websocket` handler that accepts sessions, delegates to a VoiceBackend, and bridges bidirectional audio. Runs on port 8080 at `/ws`. |
| `agentcore/backends/base.py` | `VoiceBackend` abstract base class: `start_session()`, `send_audio()`, `receive_audio()`, `close()`. |
| `agentcore/backends/nova_sonic.py` | `NovaSonicBackend` — fully functional bidirectional streaming with Amazon Nova Sonic 2 via the Smithy Bedrock SDK. Input: 16 kHz PCM. Output: 24 kHz PCM. Handles barge-in. |
| `agentcore/backends/cascade.py` | `CascadeBackend` — documented stub showing where to plug STT/LLM/TTS services. Not functional. |
| `agentcore/backends/__init__.py` | Backend factory: `create_backend(config)` maps `"nova_sonic"` / `"cascade"` to their implementations. |
| `agent.py` | LiveKit Bridge Worker. Joins a LiveKit room, subscribes to user audio, forwards PCM to AgentCore over WebSocket, publishes agent audio back to the room. Supports both direct WS (`AGENTCORE_WS_URL`) and SigV4 ARN-based (`AGENTCORE_RUNTIME_ARN`) connections. |
| `web/index.html` | Browser frontend. LiveKit Client SDK for WebRTC connection, microphone capture, agent audio playback. Auto-connects if `?token=` is in URL. |
| `justfile` | Task runner with recipes for all three deployment levels. |
| `docker-compose.yml` | LiveKit Server + Bridge Worker containers. Bridge connects to AgentCore Runtime ARN. |
| `docker-compose.override.yml` | Dev override: bridge connects to `ws://host.docker.internal:8080/ws` (local voice agent). |
| `Dockerfile.bridge` | Bridge Worker container (uv + python3.13). |
| `agentcore/Dockerfile` | Voice agent container with OpenTelemetry instrumentation. |
| `k8s/bridge-deployment.yaml` | Reference Kubernetes Deployment, ConfigMap, Secret, ServiceAccount for bridge worker. |
| `k8s/livekit-values.yaml` | Reference Helm values for LiveKit Server on EKS with ALB ingress. |

## WebSocket Protocol (Bridge <-> AgentCore)

1. Bridge sends `{"type": "session_start", "config": {"backend": "nova_sonic", "voice_id": "tiffany", "sample_rate": 24000}}`
2. AgentCore responds `{"type": "session_ready"}`
3. Bidirectional binary PCM frames flow (int16 mono)
4. Bridge sends `{"type": "session_end"}` to close

## Environment Variables

| Variable | Used By | Default | Description |
|----------|---------|---------|-------------|
| `LIVEKIT_URL` | Bridge | `ws://localhost:7880` | LiveKit server WebSocket URL |
| `LIVEKIT_API_KEY` | Bridge | `devkey` | LiveKit API key |
| `LIVEKIT_API_SECRET` | Bridge | `secret` | LiveKit API secret |
| `AGENTCORE_WS_URL` | Bridge | (none) | Direct WebSocket URL for local dev |
| `AGENTCORE_RUNTIME_ARN` | Bridge | (none) | AgentCore Runtime ARN for AWS (mutually exclusive with WS_URL) |
| `VOICE_BACKEND` | Bridge | `nova_sonic` | Backend to request (`nova_sonic` or `cascade`) |
| `VOICE_ID` | Bridge/Agent | `tiffany` | Nova Sonic voice ID |
| `AWS_REGION` | Agent | `us-east-1` | AWS region for Bedrock API calls |
| `AWS_PROFILE` | justfile | `default` | AWS profile for SSO/credentials |

## Code Quality

- **Formatter**: Black 23.3.0. Run `black .` before committing.
- **Pre-commit**: The repository root has `.pre-commit-config.yaml` with Black configured.
- **Python version**: 3.13 (see `.python-version`).
- **Two separate pyproject.toml files**: root for bridge worker deps, `agentcore/` for voice agent deps.

## Adding a New VoiceBackend

1. Create `agentcore/backends/my_backend.py` implementing `VoiceBackend` from `base.py`
2. Register it in `agentcore/backends/__init__.py` by adding to the `BACKENDS` dict
3. Clients select it via `{"backend": "my_backend"}` in the `session_start` config

## Deployment Levels

| Level | What runs locally | What runs on AWS | Command |
|-------|-------------------|------------------|---------|
| **1 (all local)** | LiveKit + Bridge + Voice Agent + Frontend | Bedrock API only | `just start` |
| **2 (hybrid)** | LiveKit + Bridge + Frontend | AgentCore Runtime + Bedrock | `just start-hybrid ARN` |
| **3 (Docker/EC2)** | Nothing | EC2 Docker Compose + AgentCore + Bedrock | `docker compose up -d` |

## AWS Permissions

- **Bridge Worker (Level 2+)**: `bedrock-agentcore:InvokeAgentRuntimeWithWebSocketStream`
- **Voice Agent (local)**: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` (for Nova Sonic)
- **Deploy**: `BedrockAgentCoreFullAccess` or equivalent (ECR, CodeBuild, IAM, SSM)

## Monitoring

```bash
# CloudWatch logs for deployed voice agent
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow

# Local logs
tail -f /tmp/voice-agent.log    # Voice agent
tail -f /tmp/bridge-worker.log  # Bridge worker
tail -f /tmp/livekit-server.log # LiveKit server
```

## Gotchas

- **Smithy SDK credentials**: `aws-sdk-bedrock-runtime` only reads env vars (`AWS_ACCESS_KEY_ID`), NOT profiles/SSO. The `NovaSonicBackend._build_client()` pre-resolves via boto3. If it hangs silently, check credentials.
- **LiveKit job dispatch**: LiveKit does NOT re-dispatch jobs after a failed attempt. Use a fresh room name or restart LiveKit server when iterating.
- **Process management**: Never use `pkill -f "agent.py"` — it matches hundreds of unrelated processes. Use explicit PIDs or `pkill -x` for exact matches. The `just stop` recipe uses `pkill -f` patterns that may need refinement.
- **Two separate .venv**: Root `.venv/` (bridge worker deps) and `agentcore/.venv/` (voice agent deps). Run `just install` to sync both.
- **Default backend**: Level 1 local defaults to `echo` backend (no AWS). Set `VOICE_BACKEND=nova_sonic` for real AI voice.
