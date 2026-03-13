"""Echo backend for testing the voice pipeline without AWS.

Simply echoes back the user's audio with a short delay, proving
that the full pipeline (Browser -> LiveKit -> Bridge -> AgentCore -> Backend)
works end-to-end without requiring Bedrock credentials.

Usage:
    Set VOICE_BACKEND=echo (or pass {"backend": "echo"} in session_start config).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from backends.base import VoiceBackend

logger = logging.getLogger(__name__)


class EchoBackend(VoiceBackend):
    """Test backend that echoes user audio back after a short delay."""

    def __init__(self, config: dict) -> None:
        self.delay: float = config.get("echo_delay", 0.3)
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._active = False

    async def start_session(self, config: dict) -> None:
        self._active = True
        logger.info("EchoBackend session started (delay=%.1fs)", self.delay)

    async def send_audio(self, audio_bytes: bytes) -> None:
        if self._active:
            await self._queue.put(audio_bytes)

    async def receive_audio(self) -> AsyncIterator[bytes]:
        while True:
            chunk = await self._queue.get()
            if chunk is None:
                break
            yield chunk

    async def close(self) -> None:
        self._active = False
        await self._queue.put(None)
        logger.info("EchoBackend session closed")
