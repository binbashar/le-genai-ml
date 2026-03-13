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
