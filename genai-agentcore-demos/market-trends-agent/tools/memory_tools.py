"""
Memory Tools for Market Trends Agent

This module contains all memory-related tools for managing broker profiles,
conversation history, and financial interests using AgentCore Memory.
"""

import asyncio
import logging
from typing import Dict

from bedrock_agentcore.memory import MemoryClient
from config import get_region
from langchain_core.tools import tool

# Configure logging
logger = logging.getLogger(__name__)


def create_memory():
    """
    Create or retrieve existing AgentCore Memory using built-in discovery.

    Uses the MemoryClient's create_or_get_memory() method which handles:
    - Finding existing memory by name
    - Creating new memory if none exists
    - Race condition protection during concurrent deployments

    Returns:
        tuple: (MemoryClient, memory_id)
    """
    from bedrock_agentcore.memory.constants import StrategyType

    region = get_region()
    memory_name = "MarketTrendsAgentMultiStrategy"
    client = MemoryClient(region_name=region)

    # Define memory strategies for market trends agent
    strategies = [
        {
            StrategyType.USER_PREFERENCE.value: {
                "name": "BrokerPreferences",
                "description": "Captures broker preferences, risk tolerance, and investment styles",
                "namespaces": ["market-trends/broker/{actorId}/preferences"],
            }
        },
        {
            StrategyType.SEMANTIC.value: {
                "name": "MarketTrendsSemantic",
                "description": "Stores financial facts, market analysis, and investment insights",
                "namespaces": ["market-trends/broker/{actorId}/semantic"],
            }
        },
    ]

    # Use built-in create_or_get_memory - handles discovery and creation automatically
    logger.info(f"Getting or creating memory: {memory_name}")
    memory = client.create_or_get_memory(
        name=memory_name,
        description="Market Trends Agent with multi-strategy memory for broker financial interests",
        strategies=strategies,
        event_expiry_days=90,  # Keep conversations for 90 days (longer for financial data)
    )

    memory_id = memory["id"]
    logger.info(f"Using memory: {memory_id}")

    return client, memory_id


def get_namespaces(mem_client: MemoryClient, memory_id: str) -> dict:
    """Get namespace mapping for memory strategies."""
    try:
        strategies = mem_client.get_memory_strategies(memory_id)
        return {i["type"]: i["namespaces"][0] for i in strategies}
    except Exception as e:
        logger.error(f"Error getting namespaces: {e}")
        return {}


def retrieve_stm(
    memory_client: MemoryClient, memory_id: str, session_id: str, actor_id: str
) -> str:
    """
    Retrieve short-term memory (conversation history) for the current session.

    Args:
        memory_client: MemoryClient instance
        memory_id: Memory ID
        session_id: Current session ID
        actor_id: Actor ID

    Returns:
        Formatted conversation history string, or empty string if no history
    """
    # Retrieve recent conversation history (STM only)
    logger.info(
        f"🔍 STM DEBUG: Retrieving conversation history for session={session_id}, actor={actor_id}"
    )
    try:
        events = memory_client.list_events(
            memory_id=memory_id,
            actor_id=actor_id,
            session_id=session_id,
            max_results=5,  # Last 5 conversation turns
        )

        logger.info(
            f"🔍 STM DEBUG: Retrieved {len(events) if events else 0} events from AgentCore Memory"
        )

        if events:
            conversation_history = []
            for idx, event in enumerate(events):
                logger.info(
                    f"🔍 STM DEBUG: Event {idx + 1}: {event.get('eventId', 'unknown')}"
                )

                # AgentCore stores messages in 'payload' field, not 'messages'
                if "payload" in event:
                    payload = event["payload"]
                    logger.info(
                        f"🔍 STM DEBUG: Processing {len(payload)} messages from payload"
                    )

                    for msg_idx, message_wrapper in enumerate(payload):
                        # Each message is wrapped in 'conversational' key
                        if "conversational" in message_wrapper:
                            message = message_wrapper["conversational"]

                            # Extract text from nested content structure
                            content_obj = message.get("content", {})
                            if isinstance(content_obj, dict):
                                content = content_obj.get("text", "").strip()
                            else:
                                content = str(content_obj).strip()

                            role = message.get("role", "unknown")

                            logger.info(
                                f"🔍 STM DEBUG:   - {role}: {content[:100]}..."
                                if len(content) > 100
                                else f"🔍 STM DEBUG:   - {role}: {content}"
                            )

                            if content:
                                # Truncate long messages for context
                                truncated = (
                                    content[:150] + "..."
                                    if len(content) > 150
                                    else content
                                )
                                conversation_history.append(
                                    f"{role.upper()}: {truncated}"
                                )
                        else:
                            logger.warning(
                                f"⚠️ STM DEBUG: Message {msg_idx + 1} missing 'conversational' wrapper"
                            )
                else:
                    logger.warning("⚠️ STM DEBUG: Event has no 'payload' field!")

            if conversation_history:
                formatted = "Recent Conversation History:\n" + "\n".join(conversation_history[-10:])
                logger.info(
                    f"✅ STM DEBUG: Retrieved {len(formatted)} characters of conversation history"
                )
                return formatted
            else:
                logger.warning(
                    "⚠️ STM DEBUG: Events found but no valid messages extracted"
                )
        else:
            logger.info("📭 STM DEBUG: No conversation history found (empty session)")
    except Exception as e:
        logger.error(
            f"❌ STM DEBUG: Error retrieving conversation history: {e}", exc_info=True
        )

    return ""


def retrieve_ltm(
    memory_client: MemoryClient, memory_id: str, actor_id: str
) -> str:
    """
    Retrieve long-term memory (broker profile) from all memory strategies.

    Args:
        memory_client: MemoryClient instance
        memory_id: Memory ID
        actor_id: Actor ID

    Returns:
        Formatted broker profile string, or empty string if no profile found
    """
    logger.info(f"🔍 LTM DEBUG: Retrieving broker profile for actor={actor_id}")

    try:
        namespaces_dict = get_namespaces(memory_client, memory_id)
        all_profile_info = []

        for strategy_type, namespace_template in namespaces_dict.items():
            try:
                namespace = namespace_template.format(actorId=actor_id)
                memories = memory_client.retrieve_memories(
                    memory_id=memory_id,
                    namespace=namespace,
                    query="broker financial profile investment preferences risk tolerance",
                    top_k=3,
                )

                for memory in memories:
                    if isinstance(memory, dict):
                        content = memory.get("content", {})
                        if isinstance(content, dict):
                            text = content.get("text", "").strip()
                            if text and len(text) > 20:
                                all_profile_info.append(
                                    f"[{strategy_type.upper()}] {text}"
                                )

            except Exception as strategy_error:
                logger.info(
                    f"No memories found in {strategy_type} strategy: {strategy_error}"
                )

        if all_profile_info:
            formatted = "Broker Financial Profile:\n" + "\n\n".join(all_profile_info)
            logger.info(
                f"✅ LTM DEBUG: Retrieved {len(formatted)} characters of broker profile"
            )
            return formatted
        else:
            logger.info("📭 LTM DEBUG: No broker profile found")
            return ""

    except Exception as e:
        logger.error(f"❌ LTM DEBUG: Error retrieving broker profile: {e}", exc_info=True)
        return ""


async def retrieve_context_parallel(
    memory_client: MemoryClient, memory_id: str, session_id: str, actor_id: str
) -> Dict[str, str]:
    """
    Retrieve all context sources in parallel for performance.

    Uses asyncio.gather to fetch STM (conversation) and LTM (profile) concurrently,
    reducing total latency to max(stm_time, ltm_time) instead of stm_time + ltm_time.

    Args:
        memory_client: MemoryClient instance
        memory_id: Memory ID
        session_id: Current session ID
        actor_id: Actor ID

    Returns:
        dict: {'conversation': str, 'profile': str}
              Empty strings for any failed retrievals
    """
    logger.info(f"🔄 Starting parallel context retrieval for session={session_id}, actor={actor_id}")

    # Execute both retrievals in parallel
    stm, ltm = await asyncio.gather(
        asyncio.to_thread(retrieve_stm, memory_client, memory_id, session_id, actor_id),
        asyncio.to_thread(retrieve_ltm, memory_client, memory_id, actor_id),
        return_exceptions=True  # Don't fail all if one fails
    )

    # Handle exceptions gracefully
    conversation = stm if not isinstance(stm, Exception) else ""
    profile = ltm if not isinstance(ltm, Exception) else ""

    if isinstance(stm, Exception):
        logger.error(f"❌ STM retrieval failed: {stm}")
    if isinstance(ltm, Exception):
        logger.error(f"❌ LTM retrieval failed: {ltm}")

    logger.info(f"✅ Parallel retrieval complete - STM: {len(conversation)} chars, LTM: {len(profile)} chars")

    return {
        'conversation': conversation,
        'profile': profile,
    }


def compose_context(context_dict: Dict[str, str]) -> str:
    """
    Compose context dictionary into XML format for LLM injection.

    Creates structured XML with separate sections for conversation history
    and broker profile, wrapped in a single <context> tag.

    Args:
        context_dict: Dictionary with 'conversation' and 'profile' keys

    Returns:
        Formatted XML string, or empty string if no context available
    """
    parts = []

    if context_dict.get('conversation'):
        parts.append(
            f"<conversation_history>\n{context_dict['conversation']}\n</conversation_history>"
        )

    if context_dict.get('profile'):
        parts.append(
            f"<broker_profile>\n{context_dict['profile']}\n</broker_profile>"
        )

    if parts:
        composed = f"<context>\n{''.join(parts)}\n</context>\n\n"
        logger.info(f"📝 Composed {len(composed)} characters of context")
        return composed

    logger.info("📝 No context to compose")
    return ""


def create_memory_tools(
    memory_client: MemoryClient, memory_id: str, session_id: str, actor_id: str
):
    """Create memory tools with the provided memory client and configuration"""

    @tool
    def update_broker_financial_interests(interests_update: str):
        """Update or add to the broker's financial interests and investment preferences

        Args:
            interests_update: New financial interests, preferences, or profile updates to store
        """
        try:
            conversation = [
                (
                    f"Please update my financial profile with this information: {interests_update}",
                    "USER",
                ),
                (
                    "I've updated your financial profile with the new information. This will be included in your long-term investment profile for future reference.",
                    "ASSISTANT",
                ),
            ]

            memory_client.create_event(
                memory_id=memory_id,
                actor_id=actor_id,
                session_id=session_id,
                messages=conversation,
            )

            return (
                "Financial interests successfully updated in long-term memory profile"
            )

        except Exception as e:
            logger.error(f"Error updating financial interests: {e}")
            return "Unable to update financial interests at this time"

    return [update_broker_financial_interests]
