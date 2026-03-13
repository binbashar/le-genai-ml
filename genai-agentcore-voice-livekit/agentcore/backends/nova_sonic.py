"""Nova Sonic 2 bidirectional voice backend.

Uses the aws_sdk_bedrock_runtime Smithy-generated client (not boto3) because
the standard boto3 bedrock-runtime client does not expose
invoke_model_with_bidirectional_stream.  The Smithy SDK is a required
dependency listed in pyproject.toml.

Protocol summary (from AWS sample code):
- All messages are JSON wrapped in BidirectionalInputPayloadPart
- Session lifecycle: sessionStart → promptStart → [system] contentStart →
  textInput → contentEnd → [audio] contentStart → (N × audioInput) →
  contentEnd → promptEnd → sessionEnd
- Response events include: contentStart, textOutput, audioOutput, contentEnd
- Audio is base64-encoded LPCM (PCM16LE)
  Input:  16 kHz, 16-bit, mono
  Output: 24 kHz, 16-bit, mono (configurable via voiceId + sampleRateHertz)
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import uuid

import boto3
from collections.abc import AsyncIterator

from aws_sdk_bedrock_runtime.client import (
    BedrockRuntimeClient,
    InvokeModelWithBidirectionalStreamOperationInput,
)
from aws_sdk_bedrock_runtime.config import Config
from aws_sdk_bedrock_runtime.models import (
    BidirectionalInputPayloadPart,
    InvokeModelWithBidirectionalStreamInputChunk,
)
from smithy_aws_core.identity.environment import EnvironmentCredentialsResolver

from backends.base import VoiceBackend

logger = logging.getLogger(__name__)

MODEL_ID = "amazon.nova-sonic-v1:0"

# Default audio parameters
INPUT_SAMPLE_RATE = 16000  # Hz — Nova Sonic expects 16 kHz PCM input
OUTPUT_SAMPLE_RATE = 24000  # Hz — Nova Sonic emits 24 kHz PCM output


class NovaSonicBackend(VoiceBackend):
    """Bidirectional voice backend using Amazon Nova Sonic 2.

    Lifecycle:
        backend = NovaSonicBackend(config)
        await backend.start_session(config)       # opens stream, sends init events
        await backend.send_audio(pcm_bytes)        # send 16 kHz PCM audio
        async for chunk in backend.receive_audio(): # yield 24 kHz PCM chunks
            ...
        await backend.close()                      # graceful shutdown
    """

    def __init__(self, config: dict) -> None:
        self.voice_id: str = config.get("voice_id", "tiffany")
        self.system_prompt: str = config.get(
            "system_prompt",
            "You are a friendly and helpful voice assistant. "
            "Keep your responses concise, generally two or three sentences.",
        )
        self.input_sample_rate: int = config.get("input_sample_rate", INPUT_SAMPLE_RATE)
        self.output_sample_rate: int = config.get(
            "output_sample_rate", OUTPUT_SAMPLE_RATE
        )
        self.region: str = config.get(
            "region",
            os.environ.get(
                "AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
            ),
        )

        # Session identifiers (UUIDs assigned fresh per start_session call)
        self._prompt_name: str = ""
        self._system_content_name: str = ""
        self._audio_content_name: str = ""

        # Smithy stream handle
        self._stream: object | None = None
        self._bedrock_client: BedrockRuntimeClient | None = None

        # Queue that _read_output_loop populates; receive_audio drains it.
        # None sentinel signals end-of-stream.
        self._audio_output_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        self._read_task: asyncio.Task | None = None
        self._is_active: bool = False

    # ------------------------------------------------------------------
    # VoiceBackend interface
    # ------------------------------------------------------------------

    async def start_session(self, config: dict) -> None:  # noqa: ARG002
        """Open bidirectional stream to Nova Sonic and send initialisation events."""
        # Fresh identifiers for each session
        self._prompt_name = str(uuid.uuid4())
        self._system_content_name = str(uuid.uuid4())
        self._audio_content_name = str(uuid.uuid4())

        self._bedrock_client = self._build_client()

        logger.info(
            "Opening bidirectional stream to Nova Sonic (region=%s)", self.region
        )
        self._stream = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: None,  # placeholder — actual call is async below
        )

        # invoke_model_with_bidirectional_stream is a true async method on the
        # Smithy client, so we can await it directly.
        self._stream = (
            await self._bedrock_client.invoke_model_with_bidirectional_stream(
                InvokeModelWithBidirectionalStreamOperationInput(model_id=MODEL_ID)
            )
        )

        self._is_active = True

        # Send the required initialisation event sequence
        await self._send_raw(self._build_session_start())
        await self._send_raw(self._build_prompt_start())
        await self._send_raw(self._build_system_content_start())
        await self._send_raw(self._build_text_input(self.system_prompt))
        await self._send_raw(self._build_content_end(self._system_content_name))

        # Open the audio input content block
        await self._send_raw(self._build_audio_content_start())

        # Start background loop that reads model output events
        self._read_task = asyncio.create_task(
            self._read_output_loop(), name="nova-sonic-read"
        )
        logger.info("Nova Sonic session started (prompt=%s)", self._prompt_name)

    async def send_audio(self, audio_bytes: bytes) -> None:
        """Send a PCM audio chunk to Nova Sonic.

        Args:
            audio_bytes: Raw 16-bit PCM at ``input_sample_rate`` Hz, mono.
        """
        if not self._is_active:
            logger.warning("send_audio called on inactive session — ignoring")
            return
        blob = base64.b64encode(audio_bytes).decode("utf-8")
        event = json.dumps(
            {
                "event": {
                    "audioInput": {
                        "promptName": self._prompt_name,
                        "contentName": self._audio_content_name,
                        "content": blob,
                    }
                }
            }
        )
        await self._send_raw(event)

    async def receive_audio(self) -> AsyncIterator[bytes]:
        """Yield 24 kHz PCM audio chunks from Nova Sonic.

        Yields chunks until the session ends (None sentinel from the queue).
        """
        while True:
            chunk = await self._audio_output_queue.get()
            if chunk is None:
                break
            yield chunk

    async def close(self) -> None:
        """Gracefully close the Nova Sonic session."""
        if not self._is_active:
            return

        try:
            # End the audio content block and the prompt, then the session
            await self._send_raw(self._build_content_end(self._audio_content_name))
            await self._send_raw(self._build_prompt_end())
            await self._send_raw(self._build_session_end())
        except Exception:
            logger.exception("Error sending close events to Nova Sonic")
        finally:
            self._is_active = False

        # Close the underlying HTTP/2 stream
        if self._stream is not None:
            try:
                await self._stream.input_stream.close()
            except Exception:
                logger.exception("Error closing Nova Sonic input stream")

        # Cancel the background reader
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        # Signal receive_audio to stop
        await self._audio_output_queue.put(None)
        logger.info("Nova Sonic session closed")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_client(self) -> BedrockRuntimeClient:
        """Create the Smithy Bedrock Runtime client.

        Uses boto3 to resolve credentials first, which supports SSO profiles,
        instance roles, env vars, and all standard AWS credential sources.
        The resolved credentials are then injected into the Smithy client
        via environment variables (the only mechanism EnvironmentCredentialsResolver
        supports).
        """
        # Resolve credentials via boto3 (supports profiles, SSO, etc.)
        session = boto3.Session(region_name=self.region)
        creds = session.get_credentials()
        if creds:
            resolved = creds.get_frozen_credentials()
            os.environ["AWS_ACCESS_KEY_ID"] = resolved.access_key
            os.environ["AWS_SECRET_ACCESS_KEY"] = resolved.secret_key
            if resolved.token:
                os.environ["AWS_SESSION_TOKEN"] = resolved.token
            logger.debug("Resolved AWS credentials via boto3 session")

        cfg = Config(
            endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            region=self.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        )
        return BedrockRuntimeClient(cfg)

    async def _send_raw(self, event_json: str) -> None:
        """Encode and send a raw JSON event string to the stream."""
        if not self._stream or not self._is_active:
            return
        chunk = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=event_json.encode("utf-8"))
        )
        await self._stream.input_stream.send(chunk)

    async def _read_output_loop(self) -> None:
        """Background task: read events from Nova Sonic and dispatch them."""
        try:
            while self._is_active:
                try:
                    output = await self._stream.await_output()
                    result = await output[1].receive()
                except StopAsyncIteration:
                    logger.info("Nova Sonic output stream ended")
                    break
                except Exception:
                    logger.exception("Error receiving Nova Sonic output")
                    break

                if not (result.value and result.value.bytes_):
                    continue

                try:
                    payload = json.loads(result.value.bytes_.decode("utf-8"))
                except json.JSONDecodeError:
                    logger.warning("Non-JSON event from Nova Sonic — skipping")
                    continue

                await self._dispatch_event(payload)

        finally:
            # Ensure receive_audio() can exit even on unexpected errors
            await self._audio_output_queue.put(None)

    async def _dispatch_event(self, payload: dict) -> None:
        """Route a decoded Nova Sonic event to the appropriate handler."""
        event = payload.get("event", {})

        if "audioOutput" in event:
            content_b64: str = event["audioOutput"].get("content", "")
            if content_b64:
                audio_bytes = base64.b64decode(content_b64)
                await self._audio_output_queue.put(audio_bytes)

        elif "textOutput" in event:
            text = event["textOutput"].get("content", "")
            # Barge-in detection
            if '{"interrupted":true}' in text or '"interrupted" : true' in text:
                logger.debug("Barge-in detected — clearing audio queue")
                while not self._audio_output_queue.empty():
                    try:
                        self._audio_output_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
            else:
                logger.debug("Nova Sonic text: %s", text)

        elif "contentStart" in event:
            logger.debug("Content start: role=%s", event["contentStart"].get("role"))

        elif "contentEnd" in event:
            logger.debug("Content end event received")

        elif "sessionEnd" in event:
            logger.info("Nova Sonic session end event received")
            self._is_active = False

    # ------------------------------------------------------------------
    # Event builders — keep JSON construction in one place
    # ------------------------------------------------------------------

    def _build_session_start(self) -> str:
        return json.dumps(
            {
                "event": {
                    "sessionStart": {
                        "inferenceConfiguration": {
                            "maxTokens": 1024,
                            "topP": 0.9,
                            "temperature": 0.7,
                        }
                    }
                }
            }
        )

    def _build_prompt_start(self) -> str:
        return json.dumps(
            {
                "event": {
                    "promptStart": {
                        "promptName": self._prompt_name,
                        "textOutputConfiguration": {"mediaType": "text/plain"},
                        "audioOutputConfiguration": {
                            "mediaType": "audio/lpcm",
                            "sampleRateHertz": self.output_sample_rate,
                            "sampleSizeBits": 16,
                            "channelCount": 1,
                            "voiceId": self.voice_id,
                            "encoding": "base64",
                            "audioType": "SPEECH",
                        },
                    }
                }
            }
        )

    def _build_system_content_start(self) -> str:
        return json.dumps(
            {
                "event": {
                    "contentStart": {
                        "promptName": self._prompt_name,
                        "contentName": self._system_content_name,
                        "type": "TEXT",
                        "interactive": False,
                        "role": "SYSTEM",
                        "textInputConfiguration": {"mediaType": "text/plain"},
                    }
                }
            }
        )

    def _build_text_input(self, text: str) -> str:
        return json.dumps(
            {
                "event": {
                    "textInput": {
                        "promptName": self._prompt_name,
                        "contentName": self._system_content_name,
                        "content": text,
                    }
                }
            }
        )

    def _build_audio_content_start(self) -> str:
        return json.dumps(
            {
                "event": {
                    "contentStart": {
                        "promptName": self._prompt_name,
                        "contentName": self._audio_content_name,
                        "type": "AUDIO",
                        "interactive": True,
                        "role": "USER",
                        "audioInputConfiguration": {
                            "mediaType": "audio/lpcm",
                            "sampleRateHertz": self.input_sample_rate,
                            "sampleSizeBits": 16,
                            "channelCount": 1,
                            "audioType": "SPEECH",
                            "encoding": "base64",
                        },
                    }
                }
            }
        )

    def _build_content_end(self, content_name: str) -> str:
        return json.dumps(
            {
                "event": {
                    "contentEnd": {
                        "promptName": self._prompt_name,
                        "contentName": content_name,
                    }
                }
            }
        )

    def _build_prompt_end(self) -> str:
        return json.dumps({"event": {"promptEnd": {"promptName": self._prompt_name}}})

    def _build_session_end(self) -> str:
        return json.dumps({"event": {"sessionEnd": {}}})
