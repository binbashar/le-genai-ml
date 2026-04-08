# Nova 2 Sonic WebSocket POC

Bidirectional voice agent POC using **Amazon Nova 2 Sonic** via pure WebSocket (no LiveKit/WebRTC).

**Stack**: AgentCore Runtime + Strands BidiAgent + vanilla JS frontend.

## Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (package manager)
- AWS CLI v2 with an SSO profile that has access to **Bedrock** in `us-east-1`
- Chrome (or any modern browser with AudioWorklet support)

## Quick start

```bash
# 1. Install dependencies
cd nova-sonic-ws-poc
uv sync

# 2. Log in to AWS SSO (replace YOUR_PROFILE with your AWS profile)
aws sso login --profile YOUR_PROFILE

# 3. Start the server
AWS_PROFILE=YOUR_PROFILE uv run python agent.py

# 4. Open in Chrome
open http://localhost:8080
```

The server starts at `http://localhost:8080` with:
- `/` — Web frontend
- `/ws` — WebSocket for bidirectional audio
- `/ping` — Health check

## Usage

1. Open `http://localhost:8080` in Chrome
2. Click **Connect** (~2s while it validates credentials and connects to Nova 2 Sonic)
3. **Push-to-talk**: hold the button and speak
4. **Continuous mode**: enable the checkbox to speak without holding
5. Transcriptions appear in real time
6. Sessions have an 8-minute limit (Nova 2 Sonic restriction)

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_PROFILE` | None | AWS SSO profile |
| `AWS_REGION` | `us-east-1` | Nova 2 Sonic regions: us-east-1, us-west-2, ap-northeast-1 |

All other settings are constants at the top of `agent.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `VOICE` | `"lupe"` | Voice ID — `"lupe"` (es), `"carlos"` (es), `"tiffany"` (en, polyglot), `"matthew"` (en, polyglot) |
| `SYSTEM_PROMPT` | *"You are a friendly..."* | Instructions for the voice agent |
| `OUTPUT_SAMPLE_RATE` | `24000` | Audio output rate in Hz (16000 or 24000) |
| `ENDPOINTING_SENSITIVITY` | `None` | Turn detection: `"HIGH"`, `"MEDIUM"`, `"LOW"`, or `None` for model default |
| `SESSION_TIMEOUT_SECONDS` | `480` | Session limit in seconds (Nova 2 Sonic ~8 min max) |

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

## Troubleshooting

**"AWS credentials error"**: Run `aws sso login --profile YOUR_PROFILE` and restart the server.

**No audio heard**: Verify Chrome has microphone permission for `localhost:8080`. Must be opened from `http://localhost:8080`, NOT from `file://`.

**"Timed out waiting for input events"**: Nova 2 Sonic received no audio. Verify you are speaking (push-to-talk or continuous mode active).

**Session expires at 8 min**: Nova 2 Sonic limitation. Click "Reconnect".
