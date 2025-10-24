import os
from dataclasses import asdict, dataclass
from enum import Enum
from functools import lru_cache
from typing import Any, Optional

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
    temperature: float = 0.1
    max_tokens: int = 4096
    top_p: Optional[float] = None
    description: str = ""
    streaming: bool = True

    @classmethod
    def from_enum(cls, model: "BedrockModelCatalog", **overrides) -> "ModelConfig":
        """
        Factory method to get model config from enum with optional overrides.

        Args:
            model: BedrockModelCatalog enum value
            **overrides: Override any configuration parameter

        Returns:
            ModelConfig instance

        Examples:
            # Use default config
            config = ModelConfig.from_enum(BedrockModelCatalog.NOVA_LITE)

            # Override temperature
            config = ModelConfig.from_enum(BedrockModelCatalog.NOVA_LITE, temperature=0.5)

            # Override multiple parameters
            config = ModelConfig.from_enum(
                BedrockModelCatalog.CLAUDE_SONNET_45,
                temperature=0.0,
                max_tokens=8192
            )
        """
        base_config = MODEL_REGISTRY[model]
        if overrides:
            config_dict = asdict(base_config)
            config_dict.update(overrides)
            return cls(**config_dict)
        return base_config

    def to_bedrock_kwargs(self, framework: str = "langchain") -> dict[str, Any]:
        """
        Convert config to kwargs for different frameworks.

        Args:
            framework: "langchain" for LangGraph/LangChain ChatBedrock,
                      "strands" for Strands BedrockModel/BedrockModelConverse

        Returns:
            Dictionary ready to unpack into model constructor

        Examples:
            # LangChain/LangGraph (market-trends-agent)
            config = ModelConfig.from_enum(BedrockModelCatalog.NOVA_LITE)
            llm = ChatBedrock(**config.to_bedrock_kwargs("langchain"))

            # Strands (finance-personal-assistant)
            config = ModelConfig.from_enum(BedrockModelCatalog.NOVA_LITE)
            model = BedrockModel(**config.to_bedrock_kwargs("strands"))
        """
        if framework == "strands":
            # Strands framework format (flat structure)
            return {
                "model_id": self.model_id,
                "region_name": get_region(),
                "temperature": self.temperature,
            }
        else:
            # LangChain/LangGraph format (direct parameters)
            kwargs = {
                "model": self.model_id,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            if self.top_p is not None:
                kwargs["top_p"] = self.top_p
            return kwargs


# Model Registry - Single source of truth
MODEL_REGISTRY = {
    BedrockModelCatalog.NOVA_MICRO: ModelConfig(
        model_id="us.amazon.nova-micro-v1:0",
        temperature=0.1,
        max_tokens=4096,
        description="Ultra-fast, lowest cost model for simple tasks",
    ),
    BedrockModelCatalog.NOVA_LITE: ModelConfig(
        model_id="us.amazon.nova-lite-v1:0",
        temperature=0.1,
        max_tokens=4096,
        description="Fast, low-latency model for demos and production",
    ),
    BedrockModelCatalog.NOVA_PRO: ModelConfig(
        model_id="us.amazon.nova-pro-v1:0",
        temperature=0.1,
        max_tokens=4096,
        description="Balanced model for complex tasks",
    ),
    BedrockModelCatalog.NOVA_PREMIER: ModelConfig(
        model_id="us.amazon.nova-premier-v1:0",
        temperature=0.1,
        max_tokens=4096,
        description="Premium model for most complex tasks",
    ),
    BedrockModelCatalog.CLAUDE_HAIKU_45: ModelConfig(
        model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        temperature=0.1,
        top_p=None,
        max_tokens=8192,
        description="Fast Claude model for quick responses",
    ),
    BedrockModelCatalog.CLAUDE_SONNET_37: ModelConfig(
        model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        temperature=0.1,
        top_p=None,
        max_tokens=8192,
        description="Advanced reasoning for complex analysis (prev gen)",
    ),
    BedrockModelCatalog.CLAUDE_SONNET_45: ModelConfig(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        temperature=0.1,
        top_p=None,
        max_tokens=8192,
        description="Enhanced reasoning for complex analysis (latest)",
    ),
}


# ============================================================================
# AWS Configuration with Smart Detection
# ============================================================================

DEFAULT_REGION = "us-west-2"


def get_region() -> str:
    """
    Get AWS region with standard precedence order:
    1. AWS_REGION environment variable
    2. AWS_DEFAULT_REGION environment variable
    3. boto3 session default (from ~/.aws/config)
    4. Hardcoded default (us-west-2)

    Returns:
        str: AWS region name
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
    return boto3.Session(region_name=get_region())


def get_client(service_name: str, **kwargs):
    """Create AWS service client with configured region."""
    session = get_boto3_session()
    return session.client(service_name, **kwargs)


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
        **kwargs: Config overrides (temperature, max_tokens, top_p) AND
                 extra kwargs (guardrail_id, guardrail_version, etc.)

    Returns:
        Instantiated model (BedrockModel/BedrockModelConverse for strands,
        ChatBedrock for langchain) OR raw kwargs for unknown frameworks

    Examples:
        # Strands - Basic
        model = get_bedrock_model("strands", BedrockModelCatalog.NOVA_LITE)

        # LangChain with custom temperature
        llm = get_bedrock_model("langchain", BedrockModelCatalog.CLAUDE_SONNET_45, temperature=0.7)

        # Strands with optional guardrails (only if guardrail exists)
        guardrail_id = get_guardrail_id()  # Returns None if not found
        if guardrail_id:
            guardrails_config = {
                "guardrail_id": guardrail_id,
                "guardrail_version": "DRAFT",
                "guardrail_trace": "enabled",
            }
            model = get_bedrock_model("strands", BedrockModelCatalog.NOVA_LITE, **guardrails_config)
        else:
            model = get_bedrock_model("strands", BedrockModelCatalog.NOVA_LITE)

        # Custom ModelConfig
        custom_config = ModelConfig(model_id="custom-model-id", temperature=0.2)
        model = get_bedrock_model("strands", custom_config)
    """
    # Separate config overrides (temperature, max_tokens, top_p) from extra kwargs
    config_overrides = {
        k: v
        for k, v in kwargs.items()
        if k in ["temperature", "max_tokens", "top_p", "streaming"]
    }
    extra_kwargs = {k: v for k, v in kwargs.items() if k not in config_overrides}

    # Get config (either from enum or use provided ModelConfig)
    if isinstance(model, ModelConfig):
        config = model
    else:
        config = ModelConfig.from_enum(model, **config_overrides)

    # Get framework-specific kwargs and merge with extra kwargs
    model_kwargs = config.to_bedrock_kwargs(framework)
    model_kwargs.update(extra_kwargs)

    # Instantiate model or return kwargs
    if framework == "strands":
        from strands.models import BedrockModel

        return BedrockModel(**model_kwargs)
    elif framework == "langchain":
        from langchain_aws import ChatBedrockConverse

        return ChatBedrockConverse(**model_kwargs)
    else:
        # Return raw kwargs for unknown frameworks (demo/workshop friendly)
        return model_kwargs


# ============================================================================
# Convenience Functions
# ============================================================================


def list_available_models() -> dict[BedrockModelCatalog, ModelConfig]:
    """List all available models and their configurations."""
    return MODEL_REGISTRY.copy()


def get_model_info(model: BedrockModelCatalog) -> str:
    """Get human-readable model information."""
    config = MODEL_REGISTRY[model]
    return f"{model.value}: {config.description}"
