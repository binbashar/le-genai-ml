"""LiveKit Bridge Worker for AgentCore WebSocket voice agents.

Connects to a LiveKit room and bridges bidirectional audio to/from an
AgentCore voice agent over WebSocket.  The bridge does NOT use the LiveKit
high-level ``AgentSession`` or any LLM plugins -- it operates purely at
the audio-frame level:

1. Publishes a local audio track (agent output) into the room.
2. Subscribes to the first remote participant's audio track (user input).
3. Forwards user PCM frames to the AgentCore WebSocket.
4. Receives agent PCM frames from the WebSocket and pushes them to the room.

Environment variables
---------------------
AGENTCORE_WS_URL
    Direct WebSocket URL for local development (e.g. ``ws://localhost:8080/ws``).
AGENTCORE_RUNTIME_ARN
    ARN of the deployed AgentCore Runtime.  When set, the bridge uses the
    ``bedrock-agentcore`` SDK to open a SigV4-signed WSS connection.
    **Exactly one** of ``AGENTCORE_WS_URL`` or ``AGENTCORE_RUNTIME_ARN``
    must be provided.
VOICE_ID
    Voice to request from the backend (default ``tiffany``).
VOICE_BACKEND
    Backend name to request (default ``nova_sonic``).
SAMPLE_RATE
    Shared sample rate for both LiveKit and the backend (default ``24000``).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

import websockets
from livekit import agents, rtc

logger = logging.getLogger("bridge-worker")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AGENTCORE_WS_URL: str | None = os.environ.get("AGENTCORE_WS_URL")
AGENTCORE_RUNTIME_ARN: str | None = os.environ.get("AGENTCORE_RUNTIME_ARN")
VOICE_ID: str = os.environ.get("VOICE_ID", "tiffany")
VOICE_BACKEND: str = os.environ.get("VOICE_BACKEND", "nova_sonic")
SAMPLE_RATE: int = int(os.environ.get("SAMPLE_RATE", "24000"))
NUM_CHANNELS: int = 1  # mono throughout


# ---------------------------------------------------------------------------
# AgentCore WebSocket connection helpers
# ---------------------------------------------------------------------------


async def _connect_agentcore_ws():
    """Return an open WebSocket connection to AgentCore.

    When ``AGENTCORE_WS_URL`` is set, we connect directly via the
    ``websockets`` library.  When ``AGENTCORE_RUNTIME_ARN`` is set, we
    delegate to the AgentCore SDK which handles SigV4 signing
    transparently.
    """
    if AGENTCORE_WS_URL:
        logger.info("Connecting to AgentCore (direct): %s", AGENTCORE_WS_URL)
        ws = await websockets.connect(
            AGENTCORE_WS_URL,
            max_size=2**20,  # 1 MiB
            ping_interval=20,
            ping_timeout=10,
        )
        return ws

    if AGENTCORE_RUNTIME_ARN:
        logger.info("Connecting to AgentCore (SigV4): %s", AGENTCORE_RUNTIME_ARN)
        try:
            from bedrock_agentcore.runtime.client import (
                BedrockAgentCoreRuntimeClient,
            )
        except ImportError as exc:
            raise RuntimeError(
                "bedrock-agentcore SDK is required for ARN-based connections. "
                "Install it with: pip install bedrock-agentcore"
            ) from exc
        client = BedrockAgentCoreRuntimeClient()
        ws = await client.connect_websocket(
            agent_runtime_arn=AGENTCORE_RUNTIME_ARN,
        )
        return ws

    raise RuntimeError("Either AGENTCORE_WS_URL or AGENTCORE_RUNTIME_ARN must be set")


async def _handshake(ws) -> None:
    """Perform the session_start / session_ready handshake."""
    session_start = {
        "type": "session_start",
        "config": {
            "backend": VOICE_BACKEND,
            "voice_id": VOICE_ID,
            "sample_rate": SAMPLE_RATE,
        },
    }
    await ws.send(json.dumps(session_start))
    logger.info("Sent session_start: %s", session_start["config"])

    raw = await asyncio.wait_for(ws.recv(), timeout=15)
    if isinstance(raw, bytes):
        raw = raw.decode()
    reply = json.loads(raw)
    if reply.get("type") != "session_ready":
        raise RuntimeError(f"Expected session_ready, got: {reply}")
    logger.info("Received session_ready from AgentCore")


# ---------------------------------------------------------------------------
# Audio forwarding coroutines
# ---------------------------------------------------------------------------


async def _room_to_agentcore(
    audio_stream: rtc.AudioStream,
    ws,
) -> None:
    """Forward user audio from the LiveKit room to the AgentCore WebSocket.

    Iterates the ``AudioStream`` which yields ``AudioFrameEvent`` objects.
    Each frame's underlying int16 PCM data is sent as a binary WebSocket
    message.
    """
    logger.info("room->agentcore loop started")
    async for event in audio_stream:
        frame: rtc.AudioFrame = event.frame
        # frame.data is a memoryview of int16 samples; cast to raw bytes
        pcm_bytes = bytes(frame.data.cast("b"))
        try:
            await ws.send(pcm_bytes)
        except websockets.ConnectionClosed:
            logger.info("AgentCore WS closed while sending user audio")
            break
    logger.info("room->agentcore loop finished")


async def _agentcore_to_room(
    ws,
    audio_source: rtc.AudioSource,
) -> None:
    """Receive agent audio from AgentCore and push it into the LiveKit room.

    Each binary WebSocket message is raw PCM int16 mono audio at
    ``SAMPLE_RATE``.  We wrap it in an ``rtc.AudioFrame`` and capture it
    through the ``AudioSource``.
    """
    logger.info("agentcore->room loop started")
    try:
        async for message in ws:
            if isinstance(message, str):
                # Control message (e.g. server-side events) -- ignore.
                logger.debug("Ignoring text message from AgentCore: %s", message[:120])
                continue

            pcm_bytes = message
            if not pcm_bytes:
                continue

            # Compute samples_per_channel from byte length.
            # int16 = 2 bytes per sample; mono = 1 channel.
            num_samples = len(pcm_bytes) // (NUM_CHANNELS * 2)
            if num_samples == 0:
                continue

            frame = rtc.AudioFrame(
                data=pcm_bytes,
                sample_rate=SAMPLE_RATE,
                num_channels=NUM_CHANNELS,
                samples_per_channel=num_samples,
            )
            await audio_source.capture_frame(frame)
    except websockets.ConnectionClosed:
        logger.info("AgentCore WS closed while receiving agent audio")
    logger.info("agentcore->room loop finished")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def entrypoint(ctx: agents.JobContext) -> None:
    """LiveKit agent entrypoint: bridge audio between room and AgentCore."""
    logger.info("Bridge worker entrypoint called")

    # 1. Connect to the LiveKit room (audio only)
    await ctx.connect(auto_subscribe=agents.AutoSubscribe.AUDIO_ONLY)
    logger.info("Connected to LiveKit room: %s", ctx.room.name)

    # 2. Create an AudioSource and publish a local audio track so other
    #    participants hear the agent's voice.
    audio_source = rtc.AudioSource(
        sample_rate=SAMPLE_RATE,
        num_channels=NUM_CHANNELS,
    )
    track = rtc.LocalAudioTrack.create_audio_track("agent-voice", audio_source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE
    await ctx.room.local_participant.publish_track(track, options)
    logger.info("Published local audio track (agent-voice)")

    # 3. Wait for a remote participant to join and subscribe to their audio.
    participant = await ctx.wait_for_participant()
    logger.info(
        "Remote participant joined: %s (%s)",
        participant.identity,
        participant.sid,
    )

    # Create an AudioStream from the participant's microphone, resampled to
    # our target sample rate so frames match what AgentCore expects.
    audio_stream = rtc.AudioStream.from_participant(
        participant=participant,
        track_source=rtc.TrackSource.SOURCE_MICROPHONE,
        sample_rate=SAMPLE_RATE,
        num_channels=NUM_CHANNELS,
    )

    # 4. Open WebSocket to AgentCore and perform handshake.
    ws = await _connect_agentcore_ws()
    try:
        await _handshake(ws)

        # 5. Run bidirectional forwarding until either side disconnects.
        async with asyncio.TaskGroup() as tg:
            tg.create_task(
                _room_to_agentcore(audio_stream, ws),
                name="room-to-agentcore",
            )
            tg.create_task(
                _agentcore_to_room(ws, audio_source),
                name="agentcore-to-room",
            )
    except* websockets.ConnectionClosed:
        logger.info("AgentCore WebSocket connection closed")
    except* Exception:
        logger.exception("Error in audio bridge tasks")
    finally:
        # Clean up: tell AgentCore the session is over and close WS.
        try:
            await ws.send(json.dumps({"type": "session_end"}))
        except Exception:
            pass
        try:
            await ws.close()
        except Exception:
            pass
        await audio_stream.aclose()
        await audio_source.aclose()
        logger.info("Bridge worker shutdown complete")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
