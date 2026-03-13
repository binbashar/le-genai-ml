"""AgentCore WebSocket voice agent with pluggable backends.

Registers a WebSocket handler at ``/ws`` (automatically provided by
:class:`BedrockAgentCoreApp`) and a ``/ping`` health endpoint (also
built-in).

Protocol
--------
1. Client connects and sends ``{"type": "session_start", "config": {...}}``.
2. Agent creates the requested backend, starts the session, and replies
   ``{"type": "session_ready"}``.
3. Bidirectional binary audio frames flow until either side terminates:
   - **Client → Agent**: raw PCM bytes, or a JSON text frame with
     ``{"type": "session_end"}`` to request graceful shutdown.
   - **Agent → Client**: raw PCM bytes from the backend.
4. On disconnect or error, all resources are cleaned up before the handler
   returns.

Running locally
---------------
::

    uv run python voice_agent.py          # listens on ws://localhost:8080/ws
    curl http://localhost:8080/ping        # → {"status": "Healthy", ...}

Deployed to AgentCore Runtime the same binary is served behind the
runtime's managed endpoint.
"""

from __future__ import annotations

import asyncio
import json
import logging

from starlette.websockets import WebSocketDisconnect

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from backends import create_backend

logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()


# ---------------------------------------------------------------------------
# WebSocket handler
# ---------------------------------------------------------------------------


@app.websocket
async def ws_handler(websocket, context):  # noqa: ARG001  (context unused but required)
    """Handle a single bidirectional voice streaming session.

    The handler follows the handshake described in the module docstring,
    then fans out into two concurrent tasks:

    * ``_user_to_backend`` – bridges client → backend (audio + control)
    * ``_backend_to_user`` – bridges backend → client (audio)

    Both tasks run inside an :class:`asyncio.TaskGroup` so that an error or
    normal completion in either task immediately cancels the other.
    """
    await websocket.accept()
    backend = None

    try:
        # ------------------------------------------------------------------
        # Handshake: expect session_start as the very first message
        # ------------------------------------------------------------------
        raw = await websocket.receive_text()
        data = json.loads(raw)

        if data.get("type") != "session_start":
            logger.warning(
                "Expected session_start, got type=%r — closing", data.get("type")
            )
            await websocket.close(code=1008, reason="Expected session_start")
            return

        config: dict = data.get("config", {})
        logger.info(
            "session_start received: backend=%r voice_id=%r",
            config.get("backend", "nova_sonic"),
            config.get("voice_id"),
        )

        # ------------------------------------------------------------------
        # Create and initialise backend
        # ------------------------------------------------------------------
        backend = create_backend(config)
        await backend.start_session(config)
        logger.info("Backend session started; sending session_ready")
        await websocket.send_text(json.dumps({"type": "session_ready"}))

        # ------------------------------------------------------------------
        # Bidirectional audio loop
        # ------------------------------------------------------------------
        # TaskGroup cancels the sibling task the moment one of them exits
        # (either normally or via an exception).  We rely on this to avoid
        # orphaned tasks after a disconnect or session_end.
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(
                    _user_to_backend(websocket, backend),
                    name="user-to-backend",
                )
                tg.create_task(
                    _backend_to_user(websocket, backend),
                    name="backend-to-user",
                )
        except* WebSocketDisconnect:
            logger.info("WebSocket disconnected during audio streaming")
        except* Exception:
            logger.exception("Error in audio streaming tasks")

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
        if backend is not None:
            try:
                await backend.close()
            except Exception:
                logger.exception("Error closing backend")
        try:
            await websocket.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Subtasks
# ---------------------------------------------------------------------------


async def _user_to_backend(websocket, backend) -> None:
    """Read frames from the WebSocket and forward them to the backend.

    * **Binary frames** are forwarded directly as PCM audio.
    * **Text frames** are decoded as JSON; ``{"type": "session_end"}``
      triggers a clean exit.
    * A ``websocket.disconnect`` ASGI event signals the client has gone away.
    """
    while True:
        # receive() returns the raw ASGI message dict, which lets us
        # distinguish binary, text, and disconnect events without raising.
        message = await websocket.receive()

        msg_type = message.get("type")

        if msg_type == "websocket.disconnect":
            logger.debug("Received websocket.disconnect in user→backend loop")
            break

        if msg_type == "websocket.receive":
            if "bytes" in message and message["bytes"]:
                await backend.send_audio(message["bytes"])
            elif "text" in message and message["text"]:
                try:
                    control = json.loads(message["text"])
                except json.JSONDecodeError:
                    logger.warning(
                        "Non-JSON text frame from client: %r", message["text"][:120]
                    )
                    continue
                if control.get("type") == "session_end":
                    logger.info("Received session_end from client; stopping loops")
                    break
                else:
                    logger.debug("Unhandled control message: %r", control.get("type"))


async def _backend_to_user(websocket, backend) -> None:
    """Read audio chunks from the backend and forward them to the client."""
    async for audio_chunk in backend.receive_audio():
        await websocket.send_bytes(audio_chunk)
    logger.debug("Backend audio stream exhausted; backend→user loop done")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app.run(log_level="info")
