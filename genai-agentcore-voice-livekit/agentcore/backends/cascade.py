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

    async def start_session(self, config: dict) -> None:
        raise NotImplementedError(
            "CascadeBackend is a stub. Implement with your STT/LLM/TTS stack. "
            "See NovaSonicBackend for a working reference."
        )

    async def send_audio(self, audio_bytes: bytes) -> None:
        raise NotImplementedError

    async def receive_audio(self) -> AsyncIterator[bytes]:
        raise NotImplementedError
        yield  # pragma: no cover

    async def close(self) -> None:
        raise NotImplementedError
