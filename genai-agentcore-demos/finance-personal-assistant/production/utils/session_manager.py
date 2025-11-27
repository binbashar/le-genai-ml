"""
AgentCore session and actor management utilities.

Provides patterns for extracting session context from
AgentCore Runtime invocations with Protocol-based extensibility.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SessionContext:
    """
    Immutable session context for AgentCore invocations.

    Attributes:
        session_id: Session identifier
        actor_id: Actor/user identifier (from request headers)
        is_generated_session: True if session_id was generated (not provided by AgentCore)
    """

    session_id: str
    actor_id: str
    is_generated_session: bool = False


class AgentCoreContextExtractor(Protocol):
    """
    Protocol for extracting context from AgentCore Runtime.

    Enables extensible context extraction strategies for different
    invocation types (OAuth, IAM, local testing, etc.).
    """

    def extract_session_id(self, context: Any) -> tuple[str, bool]:
        """
        Extract session ID with fallback generation.

        Args:
            context: AgentCore Runtime context object

        Returns:
            Tuple of (session_id, is_generated)
        """
        ...

    def extract_actor_id(self, context: Any) -> str:
        """
        Extract actor ID from request headers.

        Args:
            context: AgentCore Runtime context object

        Returns:
            Actor/user identifier
        """
        ...


class DefaultContextExtractor:
    """
    Default implementation for AgentCore context extraction.

    Follows best practices for session and actor management:
    - Session ID: Provided via context.session_id (33+ chars)
    - Actor ID: Custom header X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id
    """

    # AgentCore requires 33+ character session IDs
    MIN_SESSION_ID_LENGTH = 33

    # Default header for custom user ID
    ACTOR_ID_HEADER = "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id"

    # Fallback values
    DEFAULT_ACTOR_ID = "user"

    def extract_session_id(self, context: Any) -> tuple[str, bool]:
        """
        Extract session ID from AgentCore context with validation.

        Args:
            context: AgentCore Runtime context object

        Returns:
            Tuple of (session_id, is_generated)

        Example:
            >>> context = MockContext(session_id="valid-session-id-12345678901234567890123")
            >>> extractor = DefaultContextExtractor()
            >>> session_id, is_generated = extractor.extract_session_id(context)
            >>> print(session_id, is_generated)
            valid-session-id-12345678901234567890123 False
        """
        session_id = getattr(context, "session_id", None)

        if not session_id or len(session_id) < self.MIN_SESSION_ID_LENGTH:
            generated_id = str(uuid.uuid4())
            logger.warning(f"No valid session_id provided, generated: {generated_id}")
            return generated_id, True

        return session_id, False

    def extract_actor_id(self, context: Any, payload: dict = None) -> str:
        """
        Extract actor ID from payload or request headers.

        Args:
            context: AgentCore Runtime context object with request_headers
            payload: Request payload dict (checked first for actor_id)

        Returns:
            User ID from payload, header, or default fallback

        Example:
            >>> payload = {"prompt": "...", "actor_id": "broker_demo"}
            >>> extractor = DefaultContextExtractor()
            >>> actor_id = extractor.extract_actor_id(context, payload)
            >>> print(actor_id)
            broker_demo
        """
        # LOG: Show payload keys for debugging
        if payload:
            logger.info(f"[SESSION DEBUG] Payload keys: {list(payload.keys())}")

        # Try payload first (most reliable - works for both OAuth and IAM)
        if payload and "actor_id" in payload:
            actor_id = payload["actor_id"]
            logger.info(f"[AUTH] ✓ Extracted actor_id={actor_id} from payload")
            return actor_id

        # Fallback to custom header (OAuth mode with HTTP invocation)
        headers = getattr(context, "request_headers", {}) or {}
        logger.info(f"[SESSION DEBUG] Request headers: {list(headers.keys())}")

        actor_id = headers.get(self.ACTOR_ID_HEADER, self.DEFAULT_ACTOR_ID)

        if actor_id == self.DEFAULT_ACTOR_ID:
            logger.warning(
                f"[AUTH] ⚠ Using default actor_id={actor_id} (no payload or header found)"
            )
        else:
            logger.info(f"[AUTH] ✓ Extracted actor_id={actor_id} from request headers")
        return actor_id


def extract_session_context(
    context: Any,
    payload: dict = None,
    extractor: AgentCoreContextExtractor | None = None,
) -> SessionContext:
    """
    Extract session context from AgentCore Runtime.

    Factory function following pattern for session management.
    Uses Protocol-based extractor for extensibility.

    Args:
        context: AgentCore Runtime context object
        payload: Request payload dict (checked for actor_id)
        extractor: Custom context extractor (uses DefaultContextExtractor if None)

    Returns:
        Immutable SessionContext with session_id and actor_id

    Example:
        @app.entrypoint
        async def invoke(payload, context):
            session_ctx = extract_session_context(context, payload)
            logger.info(f"Session: {session_ctx.session_id}")
            logger.info(f"Actor: {session_ctx.actor_id}")

            # Use in memory session manager
            session_manager = create_session_manager(
                memory_id=memory.memory_id,
                session_id=session_ctx.session_id,
                actor_id=session_ctx.actor_id,
                region_name=region
            )
    """
    logger.info("=" * 70)
    logger.info("[SESSION DEBUG] Extracting session context")

    extractor = extractor or DefaultContextExtractor()

    session_id, is_generated = extractor.extract_session_id(context)
    actor_id = extractor.extract_actor_id(context, payload)

    session_ctx = SessionContext(
        session_id=session_id,
        actor_id=actor_id,
        is_generated_session=is_generated,
    )

    logger.info(f"  • Session ID: {session_ctx.session_id}")
    logger.info(f"  • Actor ID: {session_ctx.actor_id}")
    logger.info(f"  • Is Generated Session: {session_ctx.is_generated_session}")
    logger.info("=" * 70)

    return session_ctx
