# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bidirectional voice agent POC using **Amazon Nova 2 Sonic** via pure WebSocket (no LiveKit/WebRTC). Stack: AgentCore Runtime + Strands BidiAgent + vanilla JS frontend. Two files: `agent.py` (server) and `web/index.html` (client).

## Commands

```bash
# Install dependencies
uv sync

# Run the server (starts on http://localhost:8080)
AWS_PROFILE=YOUR_PROFILE uv run python agent.py

# Health check
curl http://localhost:8080/ping
```

## Linting

CI runs **Black** (`--check`) on all Python files. Format before committing:
```bash
uvx black agent.py
```
Note: `uvx black@23.3.0` fails on Python 3.12+ (`ast.Str` removed). Use `uvx black` (latest) — CI accepts it.

## Architecture

```
Browser (Chrome)                    Server (AgentCore + Strands)
+------------------+               +---------------------------+
| AudioWorklet     |  PCM 16kHz    | WebSocketBidiInput        |
| (48kHz -> 16kHz) | ------------> | (Queue -> BidiAudioInput) |
|                  |   WebSocket   |                           |
| AudioContext     |  PCM 24kHz    | WebSocketBidiOutput       |
| (24kHz playback) | <------------ | (BidiAudioStream -> Queue)|
|                  |               |                           |
| Transcripts      |    JSON       | BidiTranscriptStream      |
| (DOM updates)    | <------------ | (role, text, is_final)    |
+------------------+               +---------------------------+
                                           |
                                           | Strands BidiAgent
                                           v
                                  +------------------+
                                  | BidiNovaSonicModel|
                                  | (Bedrock bidi    |
                                  |  stream, Smithy) |
                                  +------------------+
```

**Server (`agent.py`):**
- `BedrockAgentCoreApp` (Starlette-based ASGI) provides HTTP routing + WebSocket handler
- `BidiNovaSonicModel` from `strands.experimental.bidi.models.nova_sonic` — Bedrock Smithy event stream
- `BidiAgent` from `strands.experimental.bidi` — experimental bidirectional agent (no tools)
- Custom I/O bridge classes: `WebSocketBidiInput` (PCM → base64 → BidiAudioInputEvent) and `WebSocketBidiOutput` (BidiOutputEvent → Queue → WebSocket)
- Four concurrent tasks via `asyncio.TaskGroup`: ws_reader, ws_writer, agent.run(), session_timeout
- Session handshake: client sends `session_start` JSON → server validates AWS creds via STS → responds `session_ready`

**Client (`web/index.html`):**
- Single HTML file (~493 lines), inline CSS/JS, no build step, no dependencies
- AudioWorklet captures at 48kHz, downsamples 3:1 to 16kHz PCM (16-bit mono)
- Playback via AudioContext at 24kHz with gapless scheduling (`nextPlayTime`)
- Two modes: push-to-talk (default) and continuous
- Barge-in support: clears playback buffer on `barge_in` control message

**WebSocket protocol:**
- Browser → Server: binary (PCM audio) or JSON (`session_start`, `session_end`)
- Server → Browser: binary (PCM audio) or JSON (`session_ready`, `transcript`, `barge_in`, `session_timeout`, `error`)

## Configuration

| Variable | Default | Notes |
|----------|---------|-------|
| `AWS_PROFILE` | **required** | AWS SSO profile with Bedrock access |
| `AWS_REGION` | `us-east-1` | Nova 2 Sonic regions: us-east-1, us-west-2, ap-northeast-1 |

Configurable constants at the top of `agent.py`: voice (`lupe`), model (`amazon.nova-2-sonic-v1:0`), output sample rate (24kHz), system prompt, endpointing sensitivity, session timeout (8 min).

## Strands Library Notes

- `strands.experimental.bidi.models.nova_sonic` exports `NOVA_SONIC_V2_MODEL_ID` and `NOVA_SONIC_V1_MODEL_ID` constants — use these instead of hardcoding model IDs
- `provider_config["turn_detection"]` (endpointing sensitivity) is Nova 2 Sonic only — strands raises `ValueError` if used with v1 model ID

## Gotchas

- Nova 2 Sonic has an **8-minute connection limit** — the server enforces this and sends `session_timeout`
- WebSocket URL is hardcoded to `ws://localhost:8080/ws` in the frontend
- `AWS_PROFILE` env var is **required** — `os.environ["AWS_PROFILE"]` raises `KeyError` if unset
- `strands.experimental.bidi` is experimental API — may change across strands-agents versions
- `OUTPUT_SAMPLE_RATE` in `agent.py` must match `OUTPUT_RATE` in `web/index.html` — mismatch causes audio to play at wrong speed
- `handleDisconnect()` in frontend must check for existing error state before overwriting status — `ws.onclose` fires after server sends error JSON
- The AudioWorklet inline processor runs at browser's native 48kHz and downsamples; changing sample rates requires updating both client and server
