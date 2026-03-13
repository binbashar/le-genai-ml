# AgentCore + LiveKit Voice Agent Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal, functional POC demonstrating bidirectional voice communication through LiveKit (WebRTC) to an AgentCore Runtime voice agent (Nova Sonic 2), with a pluggable backend architecture.

**Architecture:** LiveKit Server handles WebRTC media transport. A stateless Bridge Worker (LiveKit Agent) captures audio frames and forwards them via WebSocket to an AgentCore Runtime voice agent. The agent uses a Strategy pattern (`VoiceBackend` ABC) to delegate to Nova Sonic 2 (functional) or a cascade pipeline (stub).

**Tech Stack:** Python 3.11+, LiveKit Agents SDK, bedrock-agentcore SDK, AWS Bedrock Nova Sonic 2, just (task runner), Docker Compose

**Spec:** `docs/superpowers/specs/2026-03-13-agentcore-livekit-voice-agent-design.md`

**Branch:** `feat/nova-sonic-livekit-poc`

**Project folder:** `genai-agentcore-voice-livekit/`

---

## Chunk 1: AgentCore Voice Agent (backend)

Build the AgentCore voice agent with the VoiceBackend strategy pattern. This is the "brain" that runs in AgentCore Runtime.

### Task 1: Project scaffolding and dependencies

**Files:**
- Create: `genai-agentcore-voice-livekit/agentcore/pyproject.toml`
- Create: `genai-agentcore-voice-livekit/agentcore/backends/__init__.py`

- [ ] **Step 1: Create project directory structure with .gitignore**

```bash
mkdir -p genai-agentcore-voice-livekit/agentcore/backends
mkdir -p genai-agentcore-voice-livekit/web
mkdir -p genai-agentcore-voice-livekit/k8s
```

Create `genai-agentcore-voice-livekit/.gitignore`:

```
.venv/
__pycache__/
*.pyc
*.egg-info/
.env
*.log
.bedrock_agentcore.yaml
```

- [ ] **Step 2: Create pyproject.toml for the AgentCore agent**

Create `genai-agentcore-voice-livekit/agentcore/pyproject.toml`:

```toml
[project]
name = "agentcore-voice-agent"
version = "0.1.0"
description = "Bidirectional voice agent for AgentCore Runtime with pluggable backends"
requires-python = ">=3.11"
dependencies = [
    "bedrock-agentcore",
    "boto3",
]

[tool.uv]
package = false
```

- [ ] **Step 3: Create backends __init__.py**

Create `genai-agentcore-voice-livekit/agentcore/backends/__init__.py` (empty file).

- [ ] **Step 4: Install dependencies and verify**

```bash
cd genai-agentcore-voice-livekit/agentcore
uv sync
```

Expected: Dependencies install successfully, `.venv/` created.

- [ ] **Step 5: Commit**

```bash
git add genai-agentcore-voice-livekit/.gitignore genai-agentcore-voice-livekit/agentcore/
git commit -m "feat: scaffold agentcore voice agent project"
```

### Task 2: VoiceBackend ABC

**Files:**
- Create: `genai-agentcore-voice-livekit/agentcore/backends/base.py`

- [ ] **Step 1: Create the abstract base class**

Create `genai-agentcore-voice-livekit/agentcore/backends/base.py`:

```python
"""Abstract base class for bidirectional voice processing backends."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class VoiceBackend(ABC):
    """Interface for bidirectional voice processing backends.

    Implementations handle the actual speech model interaction.
    The WebSocket handler in voice_agent.py delegates all audio
    processing to a VoiceBackend, keeping protocol and AI logic separate.
    """

    @abstractmethod
    async def start_session(self, config: dict) -> None:
        """Initialize the voice session (model connection, etc.)."""

    @abstractmethod
    async def send_audio(self, audio_bytes: bytes) -> None:
        """Send an audio chunk from the user to the backend."""

    @abstractmethod
    async def receive_audio(self) -> AsyncIterator[bytes]:
        """Yield audio chunks from the backend to send back to the user."""

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources (close streams, connections)."""
```

- [ ] **Step 2: Verify import works**

```bash
cd genai-agentcore-voice-livekit/agentcore
uv run python -c "from backends.base import VoiceBackend; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add genai-agentcore-voice-livekit/agentcore/backends/base.py
git commit -m "feat: add VoiceBackend abstract base class"
```

### Task 3: Nova Sonic 2 backend

**Files:**
- Create: `genai-agentcore-voice-livekit/agentcore/backends/nova_sonic.py`

**Reference docs:**
- Nova Sonic 2 bidirectional streaming: https://docs.aws.amazon.com/nova/latest/userguide/speech-to-speech.html
- Bedrock InvokeModelWithBidirectionalStream API
- AWS sample: https://github.com/aws-samples/amazon-nova-samples/tree/main/speech-to-speech/amazon-nova-2-sonic

- [ ] **Step 1: Research Nova Sonic 2 bidirectional API**

Before writing code, fetch the Nova Sonic 2 bidirectional streaming API docs and the `amazon-nova-samples` repo to understand:
- The exact event format for `InvokeModelWithBidirectionalStream`
- How to send audio input events and receive audio output events
- Session configuration (voice ID, system prompt, sample rates)
- The streaming session lifecycle (start → audio exchange → close)

This is critical — the implementation depends on the exact Bedrock streaming API contract.

- [ ] **Step 2: Implement NovaSonicBackend**

Create `genai-agentcore-voice-livekit/agentcore/backends/nova_sonic.py`.

**This is a research-heavy task.** The Nova Sonic 2 bidirectional streaming API uses a specific JSON event protocol. Study the reference docs and `amazon-nova-samples` repo before writing the final implementation. The skeleton below shows the structure; fill in the event protocol details from the API docs.

**Key implementation detail:** Nova Sonic uses a specific JSON event protocol over the bidirectional stream. Each event has a `type` field. Audio is sent as base64-encoded PCM within JSON events, NOT as raw binary. The backend must handle this encoding/decoding.

Skeleton structure (fill in from API research):

```python
"""Nova Sonic 2 bidirectional voice backend."""

import asyncio
import base64
import json
import os
from collections.abc import AsyncIterator

import boto3

from backends.base import VoiceBackend

MODEL_ID = "amazon.nova-2-sonic-v1:0"


class NovaSonicBackend(VoiceBackend):
    """Bidirectional voice backend using Amazon Nova Sonic 2.

    Opens a bidirectional stream to Bedrock and translates between
    raw PCM audio bytes and Nova Sonic's JSON event protocol.
    """

    def __init__(self, config: dict):
        self.voice_id = config.get("voice_id", "tiffany")
        self.system_prompt = config.get(
            "system_prompt", "You are a helpful voice assistant."
        )
        self.sample_rate = config.get("sample_rate", 24000)
        self.region = os.environ.get("AWS_REGION", "us-east-1")
        self._client = None
        self._stream = None
        self._audio_output_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    async def start_session(self, config: dict) -> None:
        """Open bidirectional stream to Nova Sonic 2.

        Sends session configuration event with voice_id, system_prompt,
        and sample_rate. Then starts a background task to read output events.

        Implementation: Use boto3 bedrock-runtime client's
        invoke_model_with_bidirectional_stream() method. Send the
        session config as the first event. Start _read_output_loop().
        """
        # TODO: Research exact event format from Nova Sonic docs
        # self._client = boto3.client("bedrock-runtime", region_name=self.region)
        # self._stream = self._client.invoke_model_with_bidirectional_stream(
        #     modelId=MODEL_ID, ...
        # )
        # Send session config event (voice_id, system_prompt, sample_rate)
        # Start background task: asyncio.create_task(self._read_output_loop())
        raise NotImplementedError("Fill in from Nova Sonic API research")

    async def send_audio(self, audio_bytes: bytes) -> None:
        """Send audio input event to Nova Sonic stream.

        Encodes raw PCM bytes as base64, wraps in JSON event with
        type "audioInput", sends to the bidirectional stream.
        """
        # encoded = base64.b64encode(audio_bytes).decode()
        # event = {"type": "audioInput", "audio": encoded, ...}
        # self._stream.send(json.dumps(event))
        raise NotImplementedError("Fill in from Nova Sonic API research")

    async def receive_audio(self) -> AsyncIterator[bytes]:
        """Yield audio chunks from Nova Sonic output stream.

        Reads from _audio_output_queue which is populated by
        _read_output_loop(). Yields raw PCM bytes (decoded from base64).
        None sentinel signals end of stream.
        """
        while True:
            chunk = await self._audio_output_queue.get()
            if chunk is None:
                break
            yield chunk

    async def _read_output_loop(self) -> None:
        """Background task: read events from Nova Sonic output stream.

        Parses JSON events, decodes audio from base64, puts raw PCM
        bytes into _audio_output_queue. Handles contentStart,
        audioOutput, contentEnd, and error events.
        """
        # TODO: Iterate over self._stream output events
        # For each event with audio data:
        #   audio_bytes = base64.b64decode(event["audio"])
        #   await self._audio_output_queue.put(audio_bytes)
        # On stream end:
        #   await self._audio_output_queue.put(None)
        pass

    async def close(self) -> None:
        """Send end-of-session event and close the stream."""
        # TODO: Send session end event, close stream
        await self._audio_output_queue.put(None)
```

**Note:** The `start_session()`, `send_audio()`, and `_read_output_loop()` methods contain `raise NotImplementedError` / `pass` placeholders. The implementer MUST research the exact Nova Sonic 2 event protocol from the reference docs and fill these in. The `receive_audio()` method and the queue-based architecture are complete.

- [ ] **Step 3: Verify backend instantiation**

```bash
cd genai-agentcore-voice-livekit/agentcore
uv run python -c "
from backends.nova_sonic import NovaSonicBackend
b = NovaSonicBackend({'voice_id': 'tiffany', 'system_prompt': 'You are a helpful assistant.'})
print(f'Backend created: {type(b).__name__}')
"
```

Expected: `Backend created: NovaSonicBackend` (no AWS calls yet, just instantiation).

- [ ] **Step 4: Commit**

```bash
git add genai-agentcore-voice-livekit/agentcore/backends/nova_sonic.py
git commit -m "feat: add Nova Sonic 2 bidirectional voice backend"
```

### Task 4: Cascade backend (stub)

**Files:**
- Create: `genai-agentcore-voice-livekit/agentcore/backends/cascade.py`

- [ ] **Step 1: Create the stub implementation**

Create `genai-agentcore-voice-livekit/agentcore/backends/cascade.py`:

```python
"""Cascade pipeline backend stub (STT -> LLM -> TTS).

This is a documented extension point showing where to plug in
STT (Transcribe, Whisper, Deepgram), LLM (Claude, Nova), and
TTS (Polly, ElevenLabs) services for a traditional voice pipeline.

Not functional — see NovaSonicBackend for a working implementation.
"""

from collections.abc import AsyncIterator

from backends.base import VoiceBackend


class CascadeBackend(VoiceBackend):
    """Traditional STT -> LLM -> TTS voice pipeline.

    To implement:
    1. Replace start_session() with STT/LLM/TTS client initialization
    2. In send_audio(), feed audio to your STT service
    3. When STT produces a transcript, send it to your LLM
    4. Feed LLM response to TTS
    5. Yield TTS audio chunks from receive_audio()
    """

    def __init__(self, config: dict):
        self.config = config
        # TODO: Initialize your STT client (e.g., Transcribe, Deepgram)
        # self.stt_client = ...
        # TODO: Initialize your LLM client (e.g., Bedrock, OpenAI)
        # self.llm_client = ...
        # TODO: Initialize your TTS client (e.g., Polly, ElevenLabs)
        # self.tts_client = ...

    async def start_session(self, config: dict) -> None:
        """Initialize STT, LLM, and TTS connections."""
        raise NotImplementedError(
            "CascadeBackend is a stub. Implement with your STT/LLM/TTS stack. "
            "See NovaSonicBackend for a working reference."
        )

    async def send_audio(self, audio_bytes: bytes) -> None:
        """Feed audio to STT service.

        Typical flow:
        1. Send audio_bytes to STT streaming API
        2. When STT returns transcript, queue it for LLM processing
        """
        raise NotImplementedError

    async def receive_audio(self) -> AsyncIterator[bytes]:
        """Yield TTS audio chunks.

        Typical flow:
        1. Read transcript from STT queue
        2. Send to LLM, get response text
        3. Feed response to TTS
        4. Yield audio chunks as they're synthesized
        """
        raise NotImplementedError
        yield  # pragma: no cover

    async def close(self) -> None:
        """Close all service connections."""
        raise NotImplementedError
```

- [ ] **Step 2: Verify import**

```bash
cd genai-agentcore-voice-livekit/agentcore
uv run python -c "from backends.cascade import CascadeBackend; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add genai-agentcore-voice-livekit/agentcore/backends/cascade.py
git commit -m "feat: add cascade pipeline backend stub with extension points"
```

### Task 5: Backend factory

**Files:**
- Modify: `genai-agentcore-voice-livekit/agentcore/backends/__init__.py`

- [ ] **Step 1: Add factory function to __init__.py**

Update `genai-agentcore-voice-livekit/agentcore/backends/__init__.py`:

```python
"""Voice backend factory."""

from backends.base import VoiceBackend
from backends.nova_sonic import NovaSonicBackend
from backends.cascade import CascadeBackend

BACKENDS = {
    "nova_sonic": NovaSonicBackend,
    "cascade": CascadeBackend,
}


def create_backend(config: dict) -> VoiceBackend:
    """Create a VoiceBackend from a config dict.

    Args:
        config: Must contain "backend" key ("nova_sonic" or "cascade").
                Remaining keys are passed to the backend constructor.
    """
    backend_type = config.get("backend", "nova_sonic")
    cls = BACKENDS.get(backend_type)
    if cls is None:
        raise ValueError(
            f"Unknown backend: {backend_type!r}. Available: {list(BACKENDS)}"
        )
    return cls(config)
```

- [ ] **Step 2: Verify factory**

```bash
cd genai-agentcore-voice-livekit/agentcore
uv run python -c "
from backends import create_backend
b = create_backend({'backend': 'nova_sonic', 'voice_id': 'tiffany'})
print(f'Created: {type(b).__name__}')
"
```

Expected: `Created: NovaSonicBackend`

- [ ] **Step 3: Commit**

```bash
git add genai-agentcore-voice-livekit/agentcore/backends/__init__.py
git commit -m "feat: add backend factory with nova_sonic and cascade support"
```

### Task 6: AgentCore WebSocket voice agent

**Files:**
- Create: `genai-agentcore-voice-livekit/agentcore/voice_agent.py`

**Reference docs:**
- AgentCore WebSocket: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-websocket.html
- `@app.websocket` decorator pattern from AgentCore bidirectional streaming tutorial

- [ ] **Step 1: Research AgentCore @app.websocket API**

Before writing code, verify the exact API for `@app.websocket` decorator:
- How to accept the WebSocket connection
- How to receive JSON vs binary messages
- How to send JSON vs binary messages
- The WebSocket lifecycle (accept → exchange → close)
- How `app.run()` works for local development

Check the `bedrock-agentcore` SDK source or the official tutorial at:
https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/01-AgentCore-runtime/06-bi-directional-streaming

- [ ] **Step 2: Implement voice_agent.py**

Create `genai-agentcore-voice-livekit/agentcore/voice_agent.py`.

**Fallback:** If `@app.websocket` is not available in the installed `bedrock-agentcore` version, use the raw Starlette WebSocket route pattern as shown in the AgentCore bidirectional streaming tutorial (Starlette's `WebSocket` class directly).

Skeleton structure:

```python
"""AgentCore WebSocket voice agent with pluggable backends."""

import asyncio
import json
import logging

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from backends import create_backend

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()


@app.websocket
async def ws_handler(websocket, context):
    """Handle bidirectional voice streaming over WebSocket."""
    await websocket.accept()
    backend = None

    try:
        # 1. Receive session_start config
        data = await websocket.receive_json()
        if data.get("type") != "session_start":
            await websocket.close(code=1008, reason="Expected session_start")
            return

        # 2. Create and start backend
        config = data.get("config", {})
        backend = create_backend(config)
        await backend.start_session(config)
        await websocket.send_json({"type": "session_ready"})

        # 3. Run bidirectional audio loops concurrently
        async with asyncio.TaskGroup() as tg:
            tg.create_task(_user_to_backend(websocket, backend))
            tg.create_task(_backend_to_user(websocket, backend))

    except Exception:
        logger.exception("WebSocket handler error")
    finally:
        if backend:
            await backend.close()
        await websocket.close()


async def _user_to_backend(websocket, backend):
    """Receive audio/control from bridge, forward to backend."""
    while True:
        message = await websocket.receive()
        if message.get("type") == "websocket.disconnect":
            break
        if "bytes" in message:
            await backend.send_audio(message["bytes"])
        elif "text" in message:
            data = json.loads(message["text"])
            if data.get("type") == "session_end":
                break
            # Handle other control messages (interrupt, etc.)


async def _backend_to_user(websocket, backend):
    """Receive audio from backend, forward to bridge."""
    async for audio_chunk in backend.receive_audio():
        await websocket.send_bytes(audio_chunk)


if __name__ == "__main__":
    app.run(log_level="info")
```

- [ ] **Step 3: Verify local startup**

Ensure dependencies are installed first:

```bash
cd genai-agentcore-voice-livekit/agentcore
uv sync
uv run python voice_agent.py &
sleep 2
# Check that WebSocket endpoint is listening
curl -s http://localhost:8080/ping
kill %1
```

Expected: `/ping` returns 200 OK.

- [ ] **Step 4: Commit**

```bash
git add genai-agentcore-voice-livekit/agentcore/voice_agent.py
git commit -m "feat: add AgentCore WebSocket voice agent with backend factory"
```

### Task 7: AgentCore Dockerfile

**Files:**
- Create: `genai-agentcore-voice-livekit/agentcore/Dockerfile`

- [ ] **Step 1: Create Dockerfile**

Create `genai-agentcore-voice-livekit/agentcore/Dockerfile`:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

RUN useradd --create-home bedrock_agentcore

COPY pyproject.toml uv.lock* ./
RUN uv pip install --system .

COPY . .

USER bedrock_agentcore

EXPOSE 8080

ENTRYPOINT ["opentelemetry-instrument", "python", "-m", "voice_agent"]
```

- [ ] **Step 2: Commit**

```bash
git add genai-agentcore-voice-livekit/agentcore/Dockerfile
git commit -m "feat: add AgentCore voice agent Dockerfile"
```

---

## Chunk 2: Bridge Worker (LiveKit ↔ AgentCore)

The Bridge Worker is a LiveKit Agent that translates between LiveKit AudioFrames and the AgentCore WebSocket protocol.

### Task 8: Bridge Worker project setup

**Files:**
- Create: `genai-agentcore-voice-livekit/pyproject.toml`
- Create: `genai-agentcore-voice-livekit/.python-version`

- [ ] **Step 1: Create pyproject.toml**

Create `genai-agentcore-voice-livekit/pyproject.toml`:

```toml
[project]
name = "agentcore-voice-livekit-bridge"
version = "0.1.0"
description = "LiveKit Bridge Worker for AgentCore bidirectional voice agents"
requires-python = ">=3.11"
dependencies = [
    "livekit-agents",
    "livekit-plugins-aws",
    "bedrock-agentcore",
    "websockets",
]

[tool.uv]
package = false
```

- [ ] **Step 2: Create .python-version**

Note: Set to 3.13 to match Docker images. `requires-python = ">=3.11"` in pyproject.toml keeps the minimum compatible.

```
3.13
```

- [ ] **Step 3: Install and verify**

```bash
cd genai-agentcore-voice-livekit
uv sync
```

- [ ] **Step 4: Commit**

```bash
git add genai-agentcore-voice-livekit/pyproject.toml genai-agentcore-voice-livekit/.python-version
git commit -m "feat: scaffold bridge worker project with dependencies"
```

### Task 9: Bridge Worker implementation

**Files:**
- Create: `genai-agentcore-voice-livekit/agent.py`

**Reference docs:**
- LiveKit Agents: https://docs.livekit.io/agents/
- LiveKit Audio: https://docs.livekit.io/agents/multimodality/audio/
- AgentCore WebSocket client: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-websocket.html
- Existing POC for LiveKit agent pattern: `genai-nova-sonic-livekit/agent.py`

- [ ] **Step 1: Implement the Bridge Worker**

Create `genai-agentcore-voice-livekit/agent.py`.

**Reference:** Existing POC at `genai-nova-sonic-livekit/agent.py` for the LiveKit agent pattern. The bridge replaces the direct `RealtimeModel` usage with a WebSocket connection to AgentCore.

Skeleton structure:

```python
"""LiveKit Bridge Worker: translates between LiveKit AudioFrames and AgentCore WebSocket."""

import asyncio
import json
import os

import websockets
from livekit import agents, rtc
from livekit.agents import AutoSubscribe

# Connection routing
AGENTCORE_WS_URL = os.environ.get("AGENTCORE_WS_URL")  # Local dev
AGENTCORE_RUNTIME_ARN = os.environ.get("AGENTCORE_RUNTIME_ARN")  # AWS

VOICE_BACKEND = os.environ.get("VOICE_BACKEND", "nova_sonic")
VOICE_ID = os.environ.get("VOICE_ID", "tiffany")
SAMPLE_RATE = 24000


async def _connect_to_agentcore():
    """Connect to AgentCore WebSocket (local or AWS)."""
    if AGENTCORE_WS_URL:
        # Local dev: direct WebSocket
        return await websockets.connect(AGENTCORE_WS_URL)
    elif AGENTCORE_RUNTIME_ARN:
        # AWS: WSS + SigV4
        from bedrock_agentcore.runtime import AgentCoreRuntimeClient

        client = AgentCoreRuntimeClient(
            region=os.environ.get("AWS_REGION", "us-east-1")
        )
        ws_url, headers = client.generate_ws_connection(
            runtime_arn=AGENTCORE_RUNTIME_ARN
        )
        return await websockets.connect(ws_url, additional_headers=headers)
    else:
        raise ValueError("Set AGENTCORE_WS_URL or AGENTCORE_RUNTIME_ARN")


async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint: bridge LiveKit room audio to AgentCore."""
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Connect to AgentCore
    ws = await _connect_to_agentcore()

    # Send session config
    await ws.send(
        json.dumps(
            {
                "type": "session_start",
                "config": {
                    "backend": VOICE_BACKEND,
                    "voice_id": VOICE_ID,
                    "sample_rate": SAMPLE_RATE,
                },
            }
        )
    )

    # Wait for session_ready
    resp = json.loads(await ws.recv())
    assert resp["type"] == "session_ready"

    # Create audio source for publishing agent audio to the room
    audio_source = rtc.AudioSource(SAMPLE_RATE, num_channels=1)
    track = rtc.LocalAudioTrack.create_audio_track("agent-audio", audio_source)
    await ctx.room.local_participant.publish_track(track)

    # Run bidirectional audio loops
    async with asyncio.TaskGroup() as tg:
        tg.create_task(_room_to_agentcore(ctx.room, ws))
        tg.create_task(_agentcore_to_room(ws, audio_source))


async def _room_to_agentcore(room, ws):
    """Forward user audio from LiveKit room to AgentCore WebSocket."""
    # TODO: Subscribe to user audio track via RoomEvent.TrackSubscribed
    # Read AudioFrames from the track's AudioStream
    # Send frame.data (raw PCM bytes) as binary WebSocket messages
    # On participant disconnect, send {"type": "session_end"}
    pass


async def _agentcore_to_room(ws, audio_source):
    """Forward agent audio from AgentCore WebSocket to LiveKit room."""
    # TODO: Receive binary messages from WebSocket
    # Construct rtc.AudioFrame from raw bytes
    # Publish via audio_source.capture_frame(frame)
    pass


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
```

**Key implementation details to fill in:**
- `_room_to_agentcore()`: Use `room.on(RoomEvent.TrackSubscribed)` to get the user's audio track, then iterate its `AudioStream` for `AudioFrame` objects. Each frame has `.data` (raw bytes).
- `_agentcore_to_room()`: Receive binary from WebSocket, construct `rtc.AudioFrame(data=bytes, sample_rate=SAMPLE_RATE, num_channels=1, samples_per_channel=len(bytes)//2)`, then `audio_source.capture_frame(frame)`.

- [ ] **Step 2: Verify syntax**

```bash
cd genai-agentcore-voice-livekit
uv run python -c "import agent; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add genai-agentcore-voice-livekit/agent.py
git commit -m "feat: add LiveKit bridge worker for AgentCore WebSocket"
```

### Task 10: Bridge Worker Dockerfile

**Files:**
- Create: `genai-agentcore-voice-livekit/Dockerfile.bridge`

- [ ] **Step 1: Create Dockerfile.bridge**

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv pip install --system .

COPY agent.py .

ENTRYPOINT ["python", "agent.py", "start"]
```

- [ ] **Step 2: Commit**

```bash
git add genai-agentcore-voice-livekit/Dockerfile.bridge
git commit -m "feat: add Bridge Worker Dockerfile"
```

---

## Chunk 3: Frontend and orchestration

### Task 11: Frontend (web/index.html)

**Files:**
- Create: `genai-agentcore-voice-livekit/web/index.html`

**Reference:** Existing POC at `genai-nova-sonic-livekit/web/index.html` — evolve it with connection status indicators.

- [ ] **Step 1: Create frontend**

Create `genai-agentcore-voice-livekit/web/index.html`.

Evolve from the existing POC frontend (`genai-nova-sonic-livekit/web/index.html`), adding:
- Connection status indicators (disconnected/connecting/connected/error) — already present
- "Agent responding" indicator when audio is being received from the agent
- Auto-connect from URL token parameter — already present
- Title updated to "AgentCore Voice Agent"

The frontend does NOT change between local and production modes — it always connects to a LiveKit room via the LiveKit Client SDK.

- [ ] **Step 2: Commit**

```bash
git add genai-agentcore-voice-livekit/web/
git commit -m "feat: add frontend with LiveKit WebRTC audio"
```

### Task 12: Environment config

**Files:**
- Create: `genai-agentcore-voice-livekit/.env.example`

- [ ] **Step 1: Create .env.example**

Create `genai-agentcore-voice-livekit/.env.example`:

```bash
# === Bridge Worker ===

# LiveKit Server connection
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# AgentCore connection (use ONE of these, not both)
# For local dev: direct WebSocket to voice_agent.py running locally
AGENTCORE_WS_URL=ws://localhost:8080/ws
# For AWS: AgentCore Runtime ARN (uses WSS + SigV4 auth)
# AGENTCORE_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/voice-agent-xyz

# Voice backend configuration
VOICE_BACKEND=nova_sonic
VOICE_ID=tiffany

# === AgentCore Voice Agent ===

# AWS region for Bedrock
AWS_REGION=us-east-1
```

- [ ] **Step 2: Commit**

```bash
git add genai-agentcore-voice-livekit/.env.example
git commit -m "feat: add .env.example with documented configuration"
```

### Task 13: Justfile (task runner)

**Files:**
- Create: `genai-agentcore-voice-livekit/justfile`

**Reference:** Existing POC at `genai-nova-sonic-livekit/justfile` — adapt recipes for the new architecture.

- [ ] **Step 1: Create justfile**

Create `genai-agentcore-voice-livekit/justfile` with recipes for:

- `install-livekit` — Install LiveKit Server + CLI via Homebrew
- `install` — Install Python deps for both bridge and agentcore
- `check` — Verify prerequisites (aws, livekit-server, lk, uv, python3)

Level 1 (all local):
- `voice-agent` — Run voice_agent.py locally on port 8080
- `bridge` — Run bridge worker connecting to local voice agent
- `frontend` — Serve web/ on port 3000
- `token` — Generate LiveKit JWT token
- `start` — One-command: LiveKit server + voice agent + bridge + token + open browser
- `stop` — Kill all processes

Level 2 (hybrid):
- `deploy-agentcore` — Configure + launch voice agent to AgentCore Runtime
- `start-hybrid` — LiveKit server + bridge (connecting to AWS AgentCore) + frontend + browser

AWS SSO helpers (reuse from existing POC):
- `sso-login`, `sso-export`, `agent-sso`
- `whoami` — Check AWS identity

Utilities:
- `clean` — Remove .venv, __pycache__

- [ ] **Step 2: Verify recipes list**

```bash
cd genai-agentcore-voice-livekit
just --list
```

Expected: All recipes listed without errors.

- [ ] **Step 3: Commit**

```bash
git add genai-agentcore-voice-livekit/justfile
git commit -m "feat: add justfile with local, hybrid, and deploy recipes"
```

### Task 14: Docker Compose

**Files:**
- Create: `genai-agentcore-voice-livekit/docker-compose.yml`
- Create: `genai-agentcore-voice-livekit/docker-compose.override.yml`

- [ ] **Step 1: Create docker-compose.yml**

Production-oriented compose with LiveKit Server + Bridge Worker:

```yaml
services:
  livekit-server:
    image: livekit/livekit-server:latest
    command: --dev
    ports:
      - "7880:7880"   # WebSocket
      - "7881:7881"   # HTTP
      - "7882:7882"   # TCP TURN

  bridge-worker:
    build:
      context: .
      dockerfile: Dockerfile.bridge
    environment:
      - LIVEKIT_URL=ws://livekit-server:7880
      - LIVEKIT_API_KEY=devkey
      - LIVEKIT_API_SECRET=secret
      - AGENTCORE_RUNTIME_ARN=${AGENTCORE_RUNTIME_ARN}
      - VOICE_BACKEND=${VOICE_BACKEND:-nova_sonic}
      - VOICE_ID=${VOICE_ID:-tiffany}
      - AWS_REGION=${AWS_REGION:-us-east-1}
    depends_on:
      - livekit-server
```

- [ ] **Step 2: Create docker-compose.override.yml for local dev**

```yaml
# Override for local development (bridge connects to local voice agent)
services:
  bridge-worker:
    environment:
      - AGENTCORE_WS_URL=ws://host.docker.internal:8080/ws
      - AGENTCORE_RUNTIME_ARN=
```

- [ ] **Step 3: Commit**

```bash
git add genai-agentcore-voice-livekit/docker-compose.yml genai-agentcore-voice-livekit/docker-compose.override.yml
git commit -m "feat: add Docker Compose for LiveKit + Bridge Worker"
```

### Task 15: Kubernetes reference manifests

**Files:**
- Create: `genai-agentcore-voice-livekit/k8s/bridge-deployment.yaml`
- Create: `genai-agentcore-voice-livekit/k8s/livekit-values.yaml`

- [ ] **Step 1: Create bridge-deployment.yaml**

Reference Kubernetes Deployment for the Bridge Worker with:
- IRSA annotations for IAM role (`bedrock-agentcore:InvokeAgentRuntimeWithWebSocketStream`)
- Environment variables from ConfigMap/Secret
- Resource limits (256Mi memory, 250m CPU — lightweight)
- Liveness probe

- [ ] **Step 2: Create livekit-values.yaml**

Reference Helm values for LiveKit Server on EKS:
- Key and secret configuration
- Resource limits
- Ingress/ALB annotations for WebSocket support
- TURN server configuration placeholder

- [ ] **Step 3: Commit**

```bash
git add genai-agentcore-voice-livekit/k8s/
git commit -m "feat: add reference Kubernetes manifests for EKS deployment"
```

---

## Chunk 4: Documentation and local testing

### Task 16: CLAUDE.md

**Files:**
- Create: `genai-agentcore-voice-livekit/CLAUDE.md`

- [ ] **Step 1: Create CLAUDE.md**

Create project-specific CLAUDE.md covering:
- Project overview (AgentCore + LiveKit voice agent architecture)
- Build & run commands (just recipes for all 3 levels)
- Key files and their responsibilities
- Code quality (Black 23.3.0 before commit)
- Architecture diagram (ASCII)
- Environment variables reference

- [ ] **Step 2: Commit**

```bash
git add genai-agentcore-voice-livekit/CLAUDE.md
git commit -m "docs: add CLAUDE.md for agentcore voice livekit project"
```

### Task 17: End-to-end local test (Level 1)

This task validates the full local stack works together.

- [ ] **Step 0: Create .env from example**

```bash
cd genai-agentcore-voice-livekit
cp .env.example .env
# .env defaults to local mode (AGENTCORE_WS_URL set, AGENTCORE_RUNTIME_ARN commented out)
```

- [ ] **Step 1: Start the voice agent locally**

```bash
cd genai-agentcore-voice-livekit/agentcore
uv run python voice_agent.py &
```

Verify: `curl http://localhost:8080/ping` returns 200.

- [ ] **Step 2: Start LiveKit server + bridge + frontend**

```bash
cd genai-agentcore-voice-livekit
just start
```

Verify:
- LiveKit server running on port 7880
- Bridge worker connected to local voice agent on port 8080
- Frontend accessible on port 3000
- Browser opens with token pre-filled

- [ ] **Step 3: Test voice interaction**

Open browser, click Connect, speak into microphone.

Expected behavior:
- Status shows "Connected"
- Audio indicator shows active
- Agent responds with voice (Nova Sonic 2 via Bedrock)
- Barge-in works (speak while agent is talking)

- [ ] **Step 4: Stop and verify clean shutdown**

```bash
just stop
```

All processes stopped cleanly.

- [ ] **Step 5: Run Black formatter**

```bash
uvx --python 3.12 black==23.3.0 genai-agentcore-voice-livekit/
```

- [ ] **Step 6: Commit any formatting fixes**

```bash
git add genai-agentcore-voice-livekit/
git commit -m "style: format with black 23.3.0"
```

### Task 18: README.md

**Files:**
- Create: `genai-agentcore-voice-livekit/README.md`

- [ ] **Step 1: Create README.md**

Create comprehensive README covering:
- Architecture diagram (the 4-component diagram from the spec)
- Quick start (Level 1: `just start`)
- Hybrid mode (Level 2: `just deploy-agentcore && just start-hybrid`)
- Docker Compose mode (Level 3)
- Backend extensibility (how to add new VoiceBackend implementations)
- Kubernetes deployment reference
- Environment variables table
- Troubleshooting section
- Links to AgentCore docs, LiveKit docs, Nova Sonic docs

- [ ] **Step 2: Commit**

```bash
git add genai-agentcore-voice-livekit/README.md
git commit -m "docs: add comprehensive README with architecture and setup guide"
```
