"""Simple memory retrieval utility for injecting LTM context into agent prompts."""

import logging

logger = logging.getLogger(__name__)


def retrieve_and_inject_memories(
    memory_client,
    memory_id: str,
    actor_id: str,
    user_message: str,
    namespaces: dict = None,
) -> str:
    """
    Retrieve memories from specified namespaces and inject into user message.

    Args:
        memory_client: MemoryClient instance
        memory_id: Memory ID to retrieve from
        actor_id: Actor ID for namespace interpolation
        user_message: Original user message
        namespaces: Dict of {namespace_template: top_k}, e.g.:
            {
                "finance-assistant/user/{actorId}/preferences": 5,
                "finance-assistant/user/{actorId}/facts": 10
            }

    Returns:
        Augmented message with retrieved memories injected

    Note:
        Pre-check architecture prevents contamination at source (before storage),
        so no sanitization needed here.
    """
    if not namespaces:
        return user_message

    memory_context = []
    total_memories_retrieved = 0

    for namespace_template, top_k in namespaces.items():
        # Interpolate actor_id into namespace
        namespace = namespace_template.replace("{actorId}", actor_id)

        try:
            memories = memory_client.retrieve_memories(
                memory_id=memory_id,
                query=user_message,
                namespace=namespace,
                actor_id=actor_id,
                top_k=top_k,
            )

            # Extract text from each memory
            for mem in memories:
                content = mem.get("content", {})
                if isinstance(content, dict) and "text" in content:
                    text = content["text"]

                    # Label based on namespace type
                    if "preferences" in namespace:
                        memory_context.append(f"[User Preference] {text}")
                    elif "facts" in namespace:
                        memory_context.append(f"[Financial Fact] {text}")
                    else:
                        memory_context.append(f"[Memory] {text}")

            total_memories_retrieved += len(memories)
            logger.debug(f"Retrieved {len(memories)} memories from {namespace}")

        except Exception as e:
            logger.warning(f"Failed to retrieve from {namespace}: {e}")

    # Inject memories into message
    if memory_context:
        memory_prefix = "\n".join(memory_context)
        augmented_message = f"""<retrieved_memories>
{memory_prefix}
</retrieved_memories>

User: {user_message}"""

        logger.debug(f"Injected {total_memories_retrieved} memories into user message")
        return augmented_message

    return user_message
