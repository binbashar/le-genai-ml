"""Memory configuration for Finance Personal Assistant."""

import logging
from dataclasses import dataclass

from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.constants import StrategyType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MemoryConfig:
    name: str
    description: str
    strategies: list
    event_expiry_days: int = 90


class Memory:
    def __init__(self, region_name: str, config: MemoryConfig):
        self.region_name = region_name
        self.config = config
        self._client = MemoryClient(region_name=region_name)
        self.memory_id = self._ensure_exists()

    def _ensure_exists(self) -> str:
        import time

        # Check for existing memory
        existing_memories = self._client.list_memories()
        existing_memory = next(
            (
                m
                for m in existing_memories
                if m.get("id", "").startswith(self.config.name)
            ),
            None,
        )

        if existing_memory:
            logger.info(f"[✓] Found existing memory: {existing_memory['id']}")
            memory_id = existing_memory["id"]

            # Wait for memory to become ACTIVE (if it's still CREATING)
            self._wait_for_active(memory_id)
            return memory_id

        # Try to create memory (with race condition handling)
        logger.info(
            f"[+] Creating memory with {len(self.config.strategies)} strategies"
        )
        try:
            memory = self._client.create_memory_and_wait(
                name=self.config.name,
                description=self.config.description,
                strategies=self.config.strategies,
                event_expiry_days=self.config.event_expiry_days,
            )
            memory_id = memory["id"]
            logger.info(f"[✓] Memory created: {memory_id}")

            # Wait for memory to become ACTIVE
            self._wait_for_active(memory_id)
            return memory_id
        except Exception as e:
            # Another container might have created it simultaneously
            logger.warning(f"[!] Memory creation failed (race condition?): {e}")
            logger.info("[↻] Retrying: searching for newly created memory...")
            time.sleep(2)  # Brief delay to let other container finish creation

            # Retry lookup
            existing_memories = self._client.list_memories()
            existing_memory = next(
                (
                    m
                    for m in existing_memories
                    if m.get("id", "").startswith(self.config.name)
                ),
                None,
            )

            if existing_memory:
                memory_id = existing_memory["id"]
                logger.info(
                    f"[✓] Found memory created by parallel container: {memory_id}"
                )

                # Wait for memory to become ACTIVE
                self._wait_for_active(memory_id)
                return memory_id

            # If still not found, re-raise the original error
            logger.error("[✗] Memory creation failed and no existing memory found")
            raise

    def _wait_for_active(self, memory_id: str, max_wait_seconds: int = 300):
        """Wait for memory to become ACTIVE (max 5 minutes)"""
        import time

        start_time = time.time()
        while True:
            # Check status (AWS API uses camelCase: memoryId)
            # Response structure: {"memory": {"status": "ACTIVE", ...}, "ResponseMetadata": {...}}
            memory_detail = self._client.get_memory(memoryId=memory_id)
            status = memory_detail.get("memory", {}).get("status", "UNKNOWN")

            if status == "ACTIVE":
                elapsed = int(time.time() - start_time)
                logger.info(f"[✓] Memory is ACTIVE (waited {elapsed}s)")
                return

            if status == "FAILED":
                raise RuntimeError(f"Memory {memory_id} failed to provision")

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                raise TimeoutError(
                    f"Memory {memory_id} did not become ACTIVE after {max_wait_seconds}s (status: {status})"
                )

            # Log progress every 10 seconds
            if int(elapsed) % 10 == 0:
                logger.info(
                    f"[...] Waiting for memory to become ACTIVE (status: {status}, elapsed: {int(elapsed)}s)"
                )

            time.sleep(5)  # Check every 5 seconds


MEMORY_STRATEGIES = [
    {
        StrategyType.USER_PREFERENCE.value: {
            "name": "UserPreferences",
            "description": "User's name, financial goals, preferences, risk tolerance",
            "namespaces": ["finance-assistant/user/{actorId}/preferences"],
        }
    },
    {
        StrategyType.SEMANTIC.value: {
            "name": "BudgetFacts",
            "description": "Budget amounts, spending patterns, income sources, financial constraints",
            "namespaces": ["finance-assistant/user/{actorId}/facts"],
        }
    },
    {
        StrategyType.SUMMARY.value: {
            "name": "SessionSummaries",
            "description": "Conversation summaries and financial planning session outcomes",
            "namespaces": ["finance-assistant/user/{actorId}/summaries/{sessionId}"],
        }
    },
]

FINANCE_MEMORY_CONFIG = MemoryConfig(
    name="finance_personal_assistant_mem",
    description="Personal finance assistant with user preferences, budget data, and conversation summaries",
    strategies=MEMORY_STRATEGIES,
    event_expiry_days=90,
)

RETRIEVAL_CONFIG = {
    "finance-assistant/user/{actorId}/preferences": {
        "top_k": 10,
        "relevance_score": 0.7,
    },
    "finance-assistant/user/{actorId}/facts": {
        "top_k": 10,
        "relevance_score": 0.5,
    },
    "finance-assistant/user/{actorId}/summaries/{sessionId}": {
        "top_k": 3,
        "relevance_score": 0.6,
    },
}
