"""
Model configuration for Bedrock structured output examples.
"""

import os
from enum import Enum
from dataclasses import dataclass
from typing import Optional

# Defaults
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TOP_P = 0.9


@dataclass
class ModelConfig:
    """Model configuration."""

    id: str
    name: str
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    top_p: Optional[float] = DEFAULT_TOP_P

    def get_params(self) -> dict:
        """Get model parameters."""
        params = {"temperature": self.temperature, "max_tokens": self.max_tokens}
        if self.top_p is not None:
            params["top_p"] = self.top_p
        return params


class Model(Enum):
    """Available Bedrock models."""

    NOVA_MICRO = ModelConfig(id="us.amazon.nova-micro-v1:0", name="Amazon Nova Micro")
    NOVA_LITE = ModelConfig(id="us.amazon.nova-lite-v1:0", name="Amazon Nova Lite")
    NOVA_PRO = ModelConfig(id="us.amazon.nova-pro-v1:0", name="Amazon Nova Pro")
    NOVA_PREMIER = ModelConfig(
        id="us.amazon.nova-premier-v1:0", name="Amazon Nova Premier"
    )

    CLAUDE_HAIKU = ModelConfig(
        id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        name="Claude 4.5 Haiku",
        top_p=None,  # Claude doesn't support top_p with temperature
    )
    CLAUDE_SONNET = ModelConfig(
        id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        name="Claude 4.5 Sonnet",
        top_p=None,
    )
    GPT_OSS_20B = ModelConfig(id="openai.gpt-oss-20b-1:0", name="GPT-OSS 20B")
    GPT_OSS_120B = ModelConfig(
        id="openai.gpt-oss-120b-1:0",
        name="GPT-OSS 120B",
    )


def get_bedrock_client_kwargs():
    """Get AWS client configuration."""
    kwargs = {"region_name": os.getenv("AWS_REGION", "us-east-1")}
    if os.getenv("AWS_PROFILE"):
        kwargs["credentials_profile_name"] = os.getenv("AWS_PROFILE")
    return kwargs
