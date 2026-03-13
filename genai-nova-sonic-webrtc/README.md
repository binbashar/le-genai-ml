# Nova Sonic 2 POC - WebRTC (LiveKit)

Minimal proof-of-concept for real-time voice interaction with **Amazon Nova Sonic 2** using WebRTC via LiveKit. Demonstrates bidirectional speech-to-speech streaming with sub-second latency.

**Default language:** Brazilian Portuguese (pt-BR) using the `leo` native voice.

> **Part of the [le-genai-ml](https://github.com/binbashar/le-genai-ml) monorepo** — a collection of GenAI and ML demonstrations on AWS Bedrock.

## Architecture

```mermaid
flowchart LR
    subgraph Browser["Browser (Chrome)"]
        UI[Web UI]
        MIC[Microphone]
        SPK[Speaker]
    end

    subgraph Local["Local Environment"]
        LK[LiveKit Server<br/>ws://localhost:7880]
        AG[Python Agent<br/>livekit-agents]
    end

    subgraph AWS["AWS Cloud"]
        BR[Amazon Bedrock]
        NS[Nova Sonic 2<br/>Speech-to-Speech]
    end

    MIC -->|Audio| UI
    UI <-->|WebRTC| LK
    SPK <--|Audio| UI
    LK <-->|Room| AG
    AG <-->|Bidirectional<br/>Stream| BR
    BR <--> NS
```

### How It Works

1. **User speaks** → Browser captures audio via WebRTC and sends it to the LiveKit server
2. **LiveKit Server** → Routes audio frames to the Python Agent connected to the same room
3. **Python Agent** → Streams audio to Amazon Bedrock using the `livekit-plugins-aws` SDK
4. **Nova Sonic 2** → Processes speech in real-time and generates a spoken response
5. **Response audio** → Flows back through the same path to the browser speaker

The entire pipeline runs in real-time with bidirectional streaming — the model can begin responding before the user finishes speaking (barge-in support).

### Key Components

| Component | File | Description |
|-----------|------|-------------|
| **Python Agent** | `agent.py` | LiveKit agent that bridges audio between the room and Nova Sonic 2 via `livekit-plugins-aws` |
| **Web Frontend** | `web/index.html` | Vanilla JS client using LiveKit's browser SDK — no build step required |
| **Task Runner** | `justfile` | Automation recipes for setup, credentials, server management, and one-command startup |

### Model Details

| Property | Value |
|----------|-------|
| Model | Amazon Nova Sonic 2 |
| Model ID | `amazon.nova-2-sonic-v1:0` |
| Type | Speech-to-Speech (S2S) |
| Region | `us-east-1` (required) |
| Latency | Sub-second (real-time bidirectional streaming) |
| Features | Barge-in, native multilingual voices, configurable system prompt |

## Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager
- **AWS credentials** with Bedrock access (SSO supported)
- **Homebrew** (macOS/Linux) — for installing LiveKit
- **[just](https://github.com/casey/just)** command runner (`brew install just`)
- **Chrome browser** — Firefox/Safari have WebAudio compatibility issues with LiveKit

## Quick Start

```bash
cd genai-nova-sonic-webrtc

# One-time setup
just install-livekit   # Install LiveKit server + CLI via Homebrew
just install           # Install Python dependencies with uv
just patch-voices      # Enable native pt-BR voices (leo, carolina)

# Run everything with one command
just profile=<your-aws-profile> start
```

That's it! The browser opens automatically, connects to the room, and starts listening.

Press `Ctrl+C` to stop, or run `just stop` from another terminal.

### What `just start` Does

1. Verifies all prerequisites are installed
2. Starts LiveKit server in dev mode (if not already running)
3. Authenticates with AWS SSO (if session expired)
4. Exports AWS credentials to the environment
5. Starts the Python agent in the background
6. Generates a LiveKit access token
7. Starts the web frontend on port 3000
8. Opens Chrome with the token pre-filled and auto-connects

## Manual Setup (3 Terminals)

If you prefer controlling each component individually:

### Terminal 1: LiveKit Server

```bash
just livekit-server
# Or: livekit-server --dev
```

### Terminal 2: Python Agent

```bash
# With AWS SSO (recommended)
just profile=<your-aws-profile> agent-sso

# Or with static credentials
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=us-east-1
just agent
```

### Terminal 3: Frontend

```bash
just token       # Generate a LiveKit access token (valid 24h)
just frontend    # Serve web UI on http://localhost:3000
```

Open http://localhost:3000 in Chrome, paste the token, and click **Connect**.

## Manual Setup (Without just)

For environments where `just` is not available:

### 1. Install LiveKit

```bash
brew install livekit livekit-cli
```

### 2. Start LiveKit Server

```bash
livekit-server --dev
```

The server will be available at `ws://localhost:7880`.

### 3. Start Python Agent

```bash
# Login to AWS SSO
aws sso login --profile <your-aws-profile>

# Export credentials
eval $(aws configure export-credentials --profile <your-aws-profile> --format env)

# Set LiveKit environment
export LIVEKIT_URL=ws://localhost:7880
export LIVEKIT_API_KEY=devkey
export LIVEKIT_API_SECRET=secret

# Run agent
uv run python agent.py dev
```

### 4. Generate Token and Start Frontend

```bash
lk token create \
  --api-key devkey --api-secret secret \
  --join --room poc-room --identity user1 \
  --valid-for 24h
```

Copy the token, then serve the frontend:

```bash
cd web && python -m http.server 3000
```

Open http://localhost:3000 in Chrome, paste the token, and click **Connect**.

## Available Commands

Run `just --list` to see all recipes. Key commands:

### Lifecycle

| Command | Description |
|---------|-------------|
| `just profile=<p> start` | Start everything with one command (recommended) |
| `just stop` | Stop all POC processes |
| `just run` | Print manual multi-terminal instructions |

### Setup

| Command | Description |
|---------|-------------|
| `just check` | Verify all prerequisites are installed |
| `just install-livekit` | Install LiveKit server + CLI via Homebrew |
| `just install` | Install Python dependencies with uv |
| `just patch-voices` | Patch `livekit-plugins-aws` for Nova 2 Sonic voices |
| `just clean` | Remove `.venv`, `__pycache__`, `*.egg-info` |

### AWS SSO

| Command | Description |
|---------|-------------|
| `just profile=<p> sso-login` | Login to AWS SSO |
| `just profile=<p> sso-export` | Print credential export commands |
| `just profile=<p> sso-setup` | Login + print export commands |
| `just profile=<p> whoami` | Check current AWS identity |

### Individual Components

| Command | Description |
|---------|-------------|
| `just livekit-server` | Start LiveKit server in dev mode |
| `just profile=<p> agent-sso` | Start agent with SSO credentials |
| `just agent` | Start agent (requires credentials in env) |
| `just token` | Generate LiveKit access token (24h) |
| `just token identity=user2` | Generate token with custom identity |
| `just frontend` | Serve web UI on port 3000 |

## Project Structure

```
genai-nova-sonic-webrtc/
├── README.md           # This file
├── justfile            # Task runner with all automation recipes
├── pyproject.toml      # Python dependencies (uv)
├── uv.lock             # Locked dependencies for reproducibility
├── .gitignore          # Python, OS, IDE ignores
├── .python-version     # Python 3.12
├── agent.py            # LiveKit agent — bridges audio to Nova Sonic 2
└── web/
    └── index.html      # Vanilla JS frontend (no build step)
```

## Voice Configuration

The agent uses Brazilian Portuguese (pt-BR) by default with the native `leo` voice.

### Why `just patch-voices` Is Required

The `livekit-plugins-aws` package ships with voice definitions for Nova Sonic v1. Nova Sonic **2** adds new native voices (`leo`, `carolina`, `kiara`, `arjun`, `olivia`, `tina`) that aren't yet in the published package. The `patch-voices` recipe:

1. **Updates the model ID** from `amazon.nova-sonic-v1:0` to `amazon.nova-2-sonic-v1:0`
2. **Adds new voice definitions** to the plugin's `events.py` voice registry

This is a local `.venv` patch — it does not modify any system packages. Re-run after `uv sync` if the venv is recreated.

### Native pt-BR Voices (Nova Sonic 2)

| Voice ID | Gender | Language |
|----------|--------|----------|
| `leo` | Masculine | Portuguese (Brazil) — **default** |
| `carolina` | Feminine | Portuguese (Brazil) |

### All Available Voices

| Voice ID | Gender | Languages |
|----------|--------|-----------|
| `leo` | Masculine | Portuguese (Brazil) |
| `carolina` | Feminine | Portuguese (Brazil) |
| `tiffany` | Feminine | English, French, Italian, German, Spanish, Portuguese, Hindi |
| `matthew` | Masculine | English, French, Italian, German, Spanish, Portuguese, Hindi |
| `kiara` | Feminine | Hindi |
| `arjun` | Masculine | Hindi |
| `olivia` | Feminine | English (Australia) |
| `tina` | Feminine | German |
| `amy` | Feminine | English (UK) |
| `lupe` | Feminine | Spanish |
| `carlos` | Masculine | Spanish |
| `ambre` | Feminine | French |
| `florian` | Masculine | French |
| `beatrice` | Feminine | Italian |
| `lorenzo` | Masculine | Italian |
| `greta` | Feminine | German |
| `lennart` | Masculine | German |

### Changing the Voice

```bash
# Option 1: Environment variable
export VOICE_ID=carolina
just profile=<your-aws-profile> agent-sso

# Option 2: just variable
just voice=carolina profile=<your-aws-profile> agent-sso

# Option 3: Edit agent.py directly
VOICE_ID = os.environ.get("VOICE_ID", "carolina")
```

## Customization

### System Prompt

Edit `SYSTEM_PROMPT` in `agent.py` to change the agent's personality and language:

```python
SYSTEM_PROMPT = """Você é um assistente de IA caloroso, profissional e prestativo.
Responda sempre em português brasileiro.
Dê respostas precisas que soem naturais, diretas e humanas.
Seja breve e conciso, mantendo-se dentro de 3-5 frases curtas."""
```

### Adding Tools (Function Calling)

Nova Sonic 2 supports function calling through LiveKit's tool framework:

```python
from livekit.agents import function_tool

@function_tool()
async def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    # Your implementation here
    return f"The weather in {location} is sunny, 25°C"
```

See [LiveKit Agents — Function Calling](https://docs.livekit.io/agents/build/functions/) for full documentation.

### Room Configuration

The default room name is `poc-room`. Override it:

```bash
just room=my-custom-room profile=<your-aws-profile> start
```

## Team Configuration

Each team member can set their default AWS profile to avoid passing `profile=` every time:

```bash
# Option 1: Set in shell profile (~/.zshrc or ~/.bashrc)
export AWS_PROFILE=your-profile-name

# Option 2: Pass to just commands
just profile=your-profile-name start
```

## AWS Configuration

### Required Permissions

The AWS credentials need:

- `bedrock:InvokeModelWithBidirectionalStream` — for Nova Sonic 2 real-time streaming
- `bedrock:InvokeModel` — fallback permission

### Region

Nova Sonic 2 is available in **`us-east-1`** (N. Virginia). The agent defaults to this region. If your AWS profile is configured for a different region, the `justfile` overrides it automatically.

### Model Access

As of October 2025, all serverless Bedrock models (including Nova Sonic 2) are automatically enabled. No manual model access configuration is required. For legacy accounts, enable Nova Sonic 2 in the [Bedrock Console](https://console.aws.amazon.com/bedrock/home#/modelaccess).

## Production Deployment

This POC is structured for straightforward cloud deployment:

| Component | Recommended AWS Service | Notes |
|-----------|------------------------|-------|
| Python Agent | **ECS Fargate** | Containerize with the existing `pyproject.toml` + Dockerfile |
| LiveKit Server | **[LiveKit Cloud](https://livekit.io/cloud)** (managed) | Or self-host on EC2/ECS |
| Frontend | **S3 + CloudFront** | Static HTML, no build step needed |

For production, replace the dev credentials (`devkey`/`secret`) with proper LiveKit API keys from LiveKit Cloud or your self-hosted instance.

## Troubleshooting

### "Failed to connect"

- Ensure LiveKit server is running: `livekit-server --dev` or `just livekit-server`
- Ensure the Python agent is running and has joined the room (check terminal output)
- Verify the room name matches between token and agent (default: `poc-room`)
- Check that the token hasn't expired (default validity: 24h)

### No Audio Response

- Check AWS credentials: `just profile=<p> whoami`
- Verify the region is `us-east-1` (Nova Sonic 2 requirement)
- Check the agent terminal for Bedrock errors
- Ensure `just patch-voices` was run (required for `leo`/`carolina` voices)

### Permission Denied for Microphone

- Use **Chrome** (Firefox/Safari may have WebAudio compatibility issues with LiveKit)
- Access via `http://localhost:3000` (not `file://` — browsers block microphone on file URLs)
- Check Chrome's site permissions for microphone access

### Agent Crashes on Startup

- Run `just check` to verify all prerequisites
- Run `just install` to ensure dependencies are installed
- Run `just patch-voices` after reinstalling dependencies
- Check `/tmp/nova-sonic-agent.log` for detailed error output

### Token Errors

- Regenerate the token: `just token`
- Ensure you're using the LiveKit dev credentials (`devkey`/`secret`)
- Tokens are valid for 24 hours by default

## Dependencies

From `pyproject.toml`:

| Package | Purpose |
|---------|---------|
| `livekit-agents` | LiveKit agent framework (room management, audio routing) |
| `livekit-plugins-aws` | AWS Bedrock integration for Nova Sonic models |
| `aws-sdk-bedrock-runtime` | AWS Bedrock Runtime SDK for bidirectional streaming |

## Code Quality

**Always run Black 23.3.0 before committing:**

```bash
uvx --python 3.12 black==23.3.0 genai-nova-sonic-webrtc/
```

The repo CI runs `black==23.3.0 --check` on all Python files. Using a different Black version will produce incompatible formatting.

## References

- [Amazon Nova Sonic 2 Documentation](https://docs.aws.amazon.com/nova/latest/userguide/speech-to-speech.html)
- [LiveKit Agents Documentation](https://docs.livekit.io/agents/)
- [LiveKit Nova Sonic Plugin](https://docs.livekit.io/agents/integrations/realtime/nova-sonic/)
- [LiveKit Client JS SDK](https://docs.livekit.io/reference/client-sdks/js/)
- [just Command Runner](https://github.com/casey/just)

## License

Apache License 2.0 — See [LICENSE](../LICENSE.txt) for details.
