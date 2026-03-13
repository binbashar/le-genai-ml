"""
Chat Agent - Configuration Module

Model configuration and AWS setup for the chat agent.
Based on the shared pattern from finance-personal-assistant.
"""

import os
from dataclasses import asdict, dataclass
from enum import Enum
from functools import lru_cache
from typing import Any

import boto3

# ============================================================================
# Model Configuration Registry
# ============================================================================


class BedrockModelCatalog(Enum):
    """Available Bedrock models with type safety"""

    NOVA_MICRO = "nova_micro"
    NOVA_LITE = "nova_lite"
    NOVA_PRO = "nova_pro"
    NOVA_PREMIER = "nova_premier"
    CLAUDE_HAIKU_45 = "claude_haiku_45"
    CLAUDE_SONNET_37 = "claude_sonnet_37"
    CLAUDE_SONNET_45 = "claude_sonnet_45"


@dataclass(frozen=True)
class ModelConfig:
    """Immutable model configuration with factory methods"""

    model_id: str
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.9
    description: str = ""
    streaming: bool = True

    @classmethod
    def from_enum(cls, model: "BedrockModelCatalog", **overrides) -> "ModelConfig":
        """Factory method to get model config from enum with optional overrides."""
        base_config = MODEL_REGISTRY[model]
        if overrides:
            config_dict = asdict(base_config)
            config_dict.update(overrides)
            return cls(**config_dict)
        return base_config

    def to_bedrock_kwargs(self, framework: str = "langchain") -> dict[str, Any]:
        """Convert config to kwargs for different frameworks."""
        if framework == "strands":
            return {
                "model_id": self.model_id,
                "region_name": get_region(),
                "temperature": self.temperature,
            }
        else:
            # LangGraph/LangChain format
            return {
                "model_id": self.model_id,
                "model_kwargs": {
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "top_p": self.top_p,
                },
                "streaming": self.streaming,
            }


MODEL_REGISTRY = {
    BedrockModelCatalog.NOVA_MICRO: ModelConfig(
        model_id="us.amazon.nova-micro-v1:0",
        temperature=0.4,
        max_tokens=4096,
        description="Ultra-fast, lowest cost model for simple tasks",
    ),
    BedrockModelCatalog.NOVA_LITE: ModelConfig(
        model_id="us.amazon.nova-lite-v1:0",
        temperature=0.7,
        max_tokens=4096,
        description="Fast, low-latency model for demos and experimentation",
    ),
    BedrockModelCatalog.NOVA_PRO: ModelConfig(
        model_id="us.amazon.nova-pro-v1:0",
        temperature=0.4,
        max_tokens=4096,
        description="Balanced model for complex tasks",
    ),
    BedrockModelCatalog.NOVA_PREMIER: ModelConfig(
        model_id="us.amazon.nova-premier-v1:0",
        temperature=0.4,
        max_tokens=4096,
        description="Premium model for most complex tasks",
    ),
    BedrockModelCatalog.CLAUDE_HAIKU_45: ModelConfig(
        model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        temperature=0.7,
        max_tokens=8192,
        description="Fast Claude model for quick responses",
    ),
    BedrockModelCatalog.CLAUDE_SONNET_37: ModelConfig(
        model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        temperature=0.7,
        max_tokens=8192,
        description="Advanced reasoning for complex analysis (prev gen)",
    ),
    BedrockModelCatalog.CLAUDE_SONNET_45: ModelConfig(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        temperature=0.7,
        max_tokens=4096,
        description="Enhanced reasoning for complex analysis (latest)",
    ),
}


# ============================================================================
# AWS Configuration
# ============================================================================

DEFAULT_REGION = "us-west-2"


def get_region() -> str:
    """
    Get AWS region with standard precedence order:
    1. AWS_REGION environment variable
    2. AWS_DEFAULT_REGION environment variable
    3. boto3 session default (from ~/.aws/config)
    4. Hardcoded default (us-west-2)
    """
    return (
        os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or boto3.Session().region_name
        or DEFAULT_REGION
    )


@lru_cache(maxsize=1)
def get_boto3_session() -> boto3.Session:
    """Get or create a cached boto3 session."""
    profile_name = os.environ.get("AWS_PROFILE")
    return boto3.Session(profile_name=profile_name, region_name=get_region())


def get_client(service_name: str, **kwargs):
    """Create AWS service client with configured region."""
    session = get_boto3_session()
    return session.client(service_name, **kwargs)


# ============================================================================
# Bedrock Model Factory
# ============================================================================


def get_bedrock_model(
    framework: str,
    model: BedrockModelCatalog | ModelConfig,
    **kwargs,
):
    """
    Get a Bedrock model for a given framework and model configuration.

    Args:
        framework: "strands" or "langchain"
        model: BedrockModelCatalog enum or ModelConfig instance
        **kwargs: Config overrides (temperature, max_tokens, top_p)

    Returns:
        Instantiated model (BedrockModel for strands, ChatBedrockConverse for langchain)

    Examples:
        # LangChain with custom temperature
        llm = get_bedrock_model("langchain", BedrockModelCatalog.NOVA_LITE, temperature=0.7)
    """
    config_overrides = {
        k: v
        for k, v in kwargs.items()
        if k in ["temperature", "max_tokens", "top_p", "streaming"]
    }
    extra_kwargs = {k: v for k, v in kwargs.items() if k not in config_overrides}

    if isinstance(model, ModelConfig):
        config = model
    else:
        config = ModelConfig.from_enum(model, **config_overrides)

    model_kwargs = config.to_bedrock_kwargs(framework)
    model_kwargs.update(extra_kwargs)

    if framework == "strands":
        from strands.models import BedrockModel

        return BedrockModel(**model_kwargs)
    elif framework == "langchain":
        from langchain_aws import ChatBedrockConverse

        return ChatBedrockConverse(**model_kwargs)
    else:
        return model_kwargs
