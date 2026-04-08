"""Nova 2 Sonic bidirectional voice agent via WebSocket.

Uses Strands BidiAgent with custom WebSocket I/O classes to bridge
browser audio (WebSocket) to Nova 2 Sonic (Bedrock bidirectional stream).

Protocol:
    Browser → Agent: binary PCM (16kHz 16-bit mono) or JSON control messages
    Agent → Browser: binary PCM (24kHz 16-bit mono) or JSON control messages

Running locally:
    uv run python agent.py          # listens on ws://localhost:8080/ws
    curl http://localhost:8080/ping  # health check
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os

import pathlib

import boto3
from starlette.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands.experimental.bidi import BidiAgent
from strands.experimental.bidi.models.nova_sonic import (
    BidiNovaSonicModel,
    NOVA_SONIC_V2_MODEL_ID,
)
from strands.experimental.bidi.types.events import (
    BidiAudioInputEvent,
    BidiAudioStreamEvent,
    BidiInterruptionEvent,
    BidiOutputEvent,
    BidiTranscriptStreamEvent,
)
from strands.experimental.bidi.types.io import BidiInput, BidiOutput

logger = logging.getLogger(__name__)

# ===========================================================================
# Configuration — edit these values to customize the agent
# ===========================================================================

# AWS credentials (required — run: aws sso login --profile <name>)
AWS_PROFILE = os.environ["AWS_PROFILE"]
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Model
MODEL_ID = NOVA_SONIC_V2_MODEL_ID  # "amazon.nova-2-sonic-v1:0"

# Voice — "lupe" (es), "carlos" (es), "tiffany" (en, polyglot), "matthew" (en, polyglot)
VOICE = "lupe"

# Audio sample rates (Hz) — OUTPUT_SAMPLE_RATE must match OUTPUT_RATE in web/index.html
OUTPUT_SAMPLE_RATE = 24000
INPUT_SAMPLE_RATE = 16000

# Turn detection — how quickly the model responds after the user stops speaking
# Options: "HIGH" (fast), "MEDIUM", "LOW" (patient), or None for model default
ENDPOINTING_SENSITIVITY = None

# System prompt
SYSTEM_PROMPT = (
    "You are a friendly and helpful voice assistant. "
    "Keep your responses concise but complete."
)

# Session limit (Nova 2 Sonic caps connections at ~8 minutes)
SESSION_TIMEOUT_SECONDS = 8 * 60

# ===========================================================================

app = BedrockAgentCoreApp()

WEB_DIR = pathlib.Path(__file__).parent / "web"


@app.route("/")
async def serve_index(request):  # noqa: ARG001
    return HTMLResponse(WEB_DIR.joinpath("index.html").read_text())


# ---------------------------------------------------------------------------
# Custom I/O: bridge WebSocket <-> Strands BidiAgent
# ---------------------------------------------------------------------------


class WebSocketBidiInput(BidiInput):
    """Read PCM audio from a WebSocket and emit BidiAudioInputEvents."""

    def __init__(self, audio_queue: asyncio.Queue[bytes | None]) -> None:
        self._queue = audio_queue

    async def start(self, agent: object) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def __call__(self) -> BidiAudioInputEvent:
        pcm = await self._queue.get()
        if pcm is None:
            raise asyncio.CancelledError
        logger.debug("Audio IN: %d bytes from browser", len(pcm))
        return BidiAudioInputEvent(
            audio=base64.b64encode(pcm).decode("utf-8"),
            format="pcm",
            sample_rate=INPUT_SAMPLE_RATE,
            channels=1,
        )


class WebSocketBidiOutput(BidiOutput):
    """Receive BidiAgent output events and enqueue them for the WebSocket writer."""

    def __init__(self, output_queue: asyncio.Queue[tuple[str, bytes | dict]]) -> None:
        self._queue = output_queue

    async def start(self, agent: object) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def __call__(self, event: BidiOutputEvent) -> None:
        if isinstance(event, BidiAudioStreamEvent):
            pcm = base64.b64decode(event.audio)
            logger.debug("Audio OUT: %d bytes to browser", len(pcm))
            await self._queue.put(("audio", pcm))
        elif isinstance(event, BidiTranscriptStreamEvent):
            logger.info(
                "Transcript: role=%s final=%s text=%s",
                event.role,
                event.is_final,
                event.text[:80],
            )
            await self._queue.put(
                (
                    "transcript",
                    {
                        "type": "transcript",
                        "role": event.role,
                        "text": event.text,
                        "is_final": event.is_final,
                    },
                )
            )
        elif isinstance(event, BidiInterruptionEvent):
            await self._queue.put(("barge_in", {"type": "barge_in"}))


# ---------------------------------------------------------------------------
# WebSocket handler
# ---------------------------------------------------------------------------


@app.websocket
async def ws_handler(websocket, context):  # noqa: ARG001
    await websocket.accept()

    audio_in_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
    output_queue: asyncio.Queue[tuple[str, bytes | dict]] = asyncio.Queue()

    try:
        # --- Handshake ---
        raw = await websocket.receive_text()
        data = json.loads(raw)
        if data.get("type") != "session_start":
            await websocket.close(code=1008, reason="Expected session_start")
            return

        logger.info("session_start received")

        # --- Build Strands BidiAgent ---
        try:
            session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
            creds = session.get_credentials()
            if not creds:
                raise ValueError(f"No credentials for profile '{AWS_PROFILE}'")
            sts = session.client("sts")
            identity = sts.get_caller_identity()
            logger.info("AWS identity: %s (profile=%s)", identity["Arn"], AWS_PROFILE)
        except Exception as exc:
            error_msg = f"AWS credentials error (profile={AWS_PROFILE}): {exc}"
            logger.error(error_msg)
            await websocket.send_text(
                json.dumps({"type": "error", "message": error_msg})
            )
            await websocket.close(code=1011, reason="AWS credentials error")
            return

        provider_config = {
            "audio": {"voice": VOICE, "output_rate": OUTPUT_SAMPLE_RATE},
        }
        if ENDPOINTING_SENSITIVITY:
            provider_config["turn_detection"] = {
                "endpointingSensitivity": ENDPOINTING_SENSITIVITY,
            }

        model = BidiNovaSonicModel(
            model_id=MODEL_ID,
            provider_config=provider_config,
            client_config={"boto_session": session},
        )
        agent = BidiAgent(
            model=model,
            tools=[],
            system_prompt=SYSTEM_PROMPT,
        )

        await websocket.send_text(json.dumps({"type": "session_ready"}))

        ws_input = WebSocketBidiInput(audio_in_queue)
        ws_output = WebSocketBidiOutput(output_queue)

        # --- Concurrent tasks ---
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(_ws_reader(websocket, audio_in_queue), name="ws-reader")
                tg.create_task(_ws_writer(websocket, output_queue), name="ws-writer")
                tg.create_task(
                    agent.run(inputs=[ws_input], outputs=[ws_output]),
                    name="agent-runner",
                )
                tg.create_task(
                    _session_timeout(websocket, output_queue), name="timeout"
                )
        except* WebSocketDisconnect:
            logger.info("WebSocket disconnected during streaming")
        except* asyncio.CancelledError:
            logger.info("Tasks cancelled (normal shutdown)")
        except* Exception as eg:
            logger.exception("Error in streaming tasks")
            try:
                msg = str(eg.exceptions[0]) if eg.exceptions else "Unknown error"
                await websocket.send_text(json.dumps({"type": "error", "message": msg}))
            except Exception:
                pass

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON in handshake: %s", exc)
        try:
            await websocket.close(code=1007, reason="Invalid JSON")
        except Exception:
            pass
    except Exception:
        logger.exception("Unhandled error in ws_handler")
    finally:
        # Signal input to stop
        await audio_in_queue.put(None)
        try:
            await websocket.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Subtasks
# ---------------------------------------------------------------------------


async def _ws_reader(websocket, audio_in_queue: asyncio.Queue[bytes | None]) -> None:
    """Read frames from WebSocket and route to audio queue or handle control messages."""
    while True:
        message = await websocket.receive()
        msg_type = message.get("type")

        if msg_type == "websocket.disconnect":
            break

        if msg_type == "websocket.receive":
            if "bytes" in message and message["bytes"]:
                logger.debug("WS recv: %d audio bytes", len(message["bytes"]))
                await audio_in_queue.put(message["bytes"])
            elif "text" in message and message["text"]:
                try:
                    control = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue
                if control.get("type") == "session_end":
                    logger.info("Received session_end from client")
                    break

    # Signal input to stop
    await audio_in_queue.put(None)


async def _ws_writer(
    websocket,
    output_queue: asyncio.Queue[tuple[str, bytes | dict]],
) -> None:
    """Read events from output queue and send to WebSocket."""
    while True:
        kind, payload = await output_queue.get()
        try:
            if kind == "audio":
                await websocket.send_bytes(payload)
            else:
                await websocket.send_text(json.dumps(payload))
        except Exception:
            break


async def _session_timeout(
    websocket,
    output_queue: asyncio.Queue[tuple[str, bytes | dict]],
) -> None:
    """Enforce Nova 2 Sonic's ~8 minute connection limit."""
    await asyncio.sleep(SESSION_TIMEOUT_SECONDS)
    logger.info("Session timeout reached (%ds)", SESSION_TIMEOUT_SECONDS)
    await output_queue.put(("timeout", {"type": "session_timeout"}))
    try:
        await websocket.close(code=1000, reason="Session timeout")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("smithy_aws_event_stream").setLevel(logging.WARNING)
    app.run(log_level="info")
