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
            logger.info(f"[✓] Using existing memory: {existing_memory['id']}")
            return existing_memory["id"]

        logger.info(f"[+] Creating memory with {len(self.config.strategies)} strategies")
        memory = self._client.create_memory_and_wait(
            name=self.config.name,
            description=self.config.description,
            strategies=self.config.strategies,
            event_expiry_days=self.config.event_expiry_days,
        )
        logger.info(f"[✓] Memory created: {memory['id']}")
        return memory["id"]


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
            "namespaces": [
                "finance-assistant/user/{actorId}/summaries/{sessionId}"
            ],
        }
    },
]

FINANCE_MEMORY_CONFIG = MemoryConfig(
    name="FinancePersonalAssistantMemory",
    description="Personal finance assistant with user preferences, budget data, and conversation summaries",
    strategies=MEMORY_STRATEGIES,
    event_expiry_days=90,
)

RETRIEVAL_CONFIG = {
    "finance-assistant/user/{actorId}/preferences": {
        "top_k": 5,
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
