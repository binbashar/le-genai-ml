"""
Configuration Schema and Validation

This module defines the structure and validation logic for evaluation pipeline configurations.
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional
import yaml


@dataclass
class EvaluationMetadata:
    """Evaluation run metadata"""
    name: str
    description: Optional[str] = None

    def validate(self) -> List[str]:
        """Validate evaluation metadata"""
        errors = []

        if not self.name:
            errors.append("evaluation.name is required")
        elif not self.name.replace("-", "").replace("_", "").isalnum():
            errors.append("evaluation.name must contain only alphanumeric characters, hyphens, and underscores")

        return errors


@dataclass
class FilterConfig:
    """Data filtering configuration"""
    agent_name: str
    start_date: str  # ISO format: YYYY-MM-DD
    end_date: str    # ISO format: YYYY-MM-DD
    limit: int = 10  # Default 10 for testing, max 100

    def validate(self) -> List[str]:
        """Validate filter configuration"""
        errors = []

        if not self.agent_name:
            errors.append("filters.agent_name is required")

        # Validate date format
        try:
            start = date.fromisoformat(self.start_date)
        except ValueError:
            errors.append(f"filters.date_range.start must be ISO format (YYYY-MM-DD), got: {self.start_date}")
            start = None

        try:
            end = date.fromisoformat(self.end_date)
        except ValueError:
            errors.append(f"filters.date_range.end must be ISO format (YYYY-MM-DD), got: {self.end_date}")
            end = None

        # Validate date range
        if start and end and start > end:
            errors.append(f"filters.date_range.start ({self.start_date}) must be before or equal to end ({self.end_date})")

        # Validate limit
        if self.limit < 1:
            errors.append(f"filters.limit must be at least 1, got: {self.limit}")
        elif self.limit > 100:
            errors.append(f"filters.limit must be at most 100 (Bedrock evaluation limit), got: {self.limit}")

        return errors


@dataclass
class EvaluatorConfig:
    """Evaluator model configuration"""
    model_id: str
    inference_params: Optional[Dict] = None

    def validate(self) -> List[str]:
        """Validate evaluator configuration"""
        errors = []

        if not self.model_id:
            errors.append("evaluator.model_id is required")

        # Validate recommended models
        recommended_models = [
            "amazon.nova-pro-v1:0",
            "amazon.nova-lite-v1:0",
            "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            "us.anthropic.claude-haiku-3-5-20241022-v1:0"
        ]

        if self.model_id not in recommended_models:
            errors.append(
                f"evaluator.model_id '{self.model_id}' is not in recommended models. "
                f"Recommended: {', '.join(recommended_models)}"
            )

        return errors


@dataclass
class OutputConfig:
    """Output configuration"""
    s3_bucket: str
    s3_prefix: str = "evaluation-results"

    def validate(self) -> List[str]:
        """Validate output configuration"""
        errors = []

        if not self.s3_bucket:
            errors.append("output.s3_bucket is required")

        # S3 bucket name validation
        if not (3 <= len(self.s3_bucket) <= 63):
            errors.append(f"output.s3_bucket must be 3-63 characters, got: {len(self.s3_bucket)}")

        return errors


@dataclass
class EvaluationConfig:
    """Complete evaluation configuration"""
    evaluation: EvaluationMetadata
    filters: FilterConfig
    metrics: List[str]
    evaluator: EvaluatorConfig
    output: OutputConfig
    tags: Optional[Dict[str, str]] = None

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "EvaluationConfig":
        """Load configuration from YAML file"""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        return cls(
            evaluation=EvaluationMetadata(
                name=data['evaluation']['name'],
                description=data['evaluation'].get('description')
            ),
            filters=FilterConfig(
                agent_name=data['filters']['agent_name'],
                start_date=data['filters']['date_range']['start'],
                end_date=data['filters']['date_range']['end'],
                limit=data['filters'].get('limit', 10)
            ),
            metrics=data['metrics'],
            evaluator=EvaluatorConfig(
                model_id=data['evaluator']['model_id'],
                inference_params=data.get('advanced', {}).get('inference_params')
            ),
            output=OutputConfig(
                s3_bucket=data['output']['s3_bucket'],
                s3_prefix=data['output'].get('s3_prefix', 'evaluation-results')
            ),
            tags=data.get('advanced', {}).get('tags')
        )

    def validate(self) -> List[str]:
        """Validate entire configuration"""
        errors = []

        errors.extend(self.evaluation.validate())
        errors.extend(self.filters.validate())
        errors.extend(self.evaluator.validate())
        errors.extend(self.output.validate())

        # Validate metrics
        if not self.metrics:
            errors.append("metrics list cannot be empty")

        valid_metrics = [
            "Builtin.Correctness",
            "Builtin.Completeness",
            "Builtin.Harmfulness",
            "Builtin.Accuracy",
            "Builtin.Robustness"
        ]

        for metric in self.metrics:
            if metric not in valid_metrics:
                errors.append(
                    f"Invalid metric '{metric}'. Valid metrics: {', '.join(valid_metrics)}"
                )

        return errors

    def to_dict(self) -> Dict:
        """Convert configuration to dictionary for Step Functions input"""
        return {
            "evaluation": {
                "name": self.evaluation.name,
                "description": self.evaluation.description
            },
            "filters": {
                "agent_name": self.filters.agent_name,
                "date_range": {
                    "start": self.filters.start_date,
                    "end": self.filters.end_date
                },
                "limit": self.filters.limit
            },
            "metrics": self.metrics,
            "evaluator": {
                "model_id": self.evaluator.model_id,
                "inference_params": self.evaluator.inference_params
            },
            "output": {
                "s3_bucket": self.output.s3_bucket,
                "s3_prefix": self.output.s3_prefix
            },
            "tags": self.tags
        }


def validate_config_file(yaml_path: str) -> tuple[EvaluationConfig, List[str]]:
    """
    Validate configuration file and return config + errors

    Returns:
        tuple: (config, list of error messages)
    """
    try:
        config = EvaluationConfig.from_yaml(yaml_path)
        errors = config.validate()
        return config, errors
    except Exception as e:
        return None, [f"Failed to parse configuration: {str(e)}"]


if __name__ == "__main__":
    # Test configuration validation
    import sys

    if len(sys.argv) < 2:
        print("Usage: python config_schema.py <config.yaml>")
        sys.exit(1)

    config_path = sys.argv[1]
    config, errors = validate_config_file(config_path)

    if errors:
        print("❌ Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("✅ Configuration is valid!")
        print(f"\nConfiguration summary:")
        print(f"  Evaluation: {config.evaluation.name}")
        print(f"  Agent: {config.filters.agent_name}")
        print(f"  Date range: {config.filters.start_date} to {config.filters.end_date}")
        print(f"  Limit: {config.filters.limit} records")
        print(f"  Metrics: {', '.join(config.metrics)}")
        print(f"  Evaluator: {config.evaluator.model_id}")
