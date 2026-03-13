"""
Evaluation Configuration Schema

Supports both Model Evaluation and RAG Evaluation with BYOI (Bring Your Own Inference).

Model Evaluation: Evaluates agent responses from CloudWatch logs (staging data)
RAG Evaluation: Evaluates RAG systems using pre-uploaded JSONL datasets
"""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional
import yaml

# Valid metrics for each evaluation type
MODEL_METRICS = [
    "Builtin.Correctness",
    "Builtin.Completeness",
    "Builtin.Harmfulness",
    "Builtin.Helpfulness",
    "Builtin.LogicalCoherence",
    "Builtin.Stereotyping",
    "Builtin.Refusal",
]

RAG_METRICS = [
    "Builtin.Faithfulness",
    "Builtin.ContextRelevance",
    "Builtin.ContextCoverage",
    "Builtin.CitationPrecision",
    "Builtin.CitationCoverage",
]

# Metrics that work with both Model and RAG evaluation
UNIVERSAL_METRICS = [
    "Builtin.Correctness",
    "Builtin.Completeness",
    "Builtin.Helpfulness",
    "Builtin.LogicalCoherence",
    "Builtin.Harmfulness",
    "Builtin.Stereotyping",
    "Builtin.Refusal",
]

VALID_EVALUATION_TYPES = ["MODEL", "RAG_RETRIEVE_AND_GENERATE", "RAG_RETRIEVE_ONLY"]


@dataclass
class EvaluationConfig:
    """
    Evaluation configuration supporting Model and RAG evaluation types.

    Attributes:
        agent_name: Identifier for the agent being evaluated
        start_date: Start of date range (ISO format, required for MODEL evaluation)
        end_date: End of date range (ISO format, required for MODEL evaluation)
        limit: Maximum number of records to evaluate (1-100)
        metrics: List of Builtin.* metrics to calculate
        evaluation_type: MODEL | RAG_RETRIEVE_AND_GENERATE | RAG_RETRIEVE_ONLY
        dataset_path: Local JSONL file path (required for RAG evaluation)
    """

    agent_name: str
    limit: int
    metrics: List[str]
    evaluation_type: str = "MODEL"
    start_date: Optional[str] = None  # Required for MODEL, optional for RAG
    end_date: Optional[str] = None  # Required for MODEL, optional for RAG
    dataset_path: Optional[str] = None  # Required for RAG evaluation

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "EvaluationConfig":
        """Load configuration from YAML file"""
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        return cls(
            agent_name=data["agent_name"],
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            limit=data.get("limit", 10),
            metrics=data["metrics"],
            evaluation_type=data.get("evaluation_type", "MODEL"),
            dataset_path=data.get("dataset_path"),
        )

    def validate(self) -> List[str]:
        """Validate configuration based on evaluation type"""
        errors = []

        # Validate agent name
        if not self.agent_name:
            errors.append("agent_name is required")

        # Validate evaluation_type
        if self.evaluation_type not in VALID_EVALUATION_TYPES:
            errors.append(
                f"evaluation_type must be one of {VALID_EVALUATION_TYPES}, "
                f"got: {self.evaluation_type}"
            )

        # Validation differs based on evaluation type
        is_rag_evaluation = self.evaluation_type.startswith("RAG_")

        if is_rag_evaluation:
            # RAG evaluation requires dataset_path
            if not self.dataset_path:
                errors.append("dataset_path is required for RAG evaluation")
            elif not Path(self.dataset_path).exists():
                errors.append(f"dataset_path does not exist: {self.dataset_path}")
            elif not self.dataset_path.endswith(".jsonl"):
                errors.append("dataset_path must be a .jsonl file")
        else:
            # MODEL evaluation requires date range
            if not self.start_date:
                errors.append("start_date is required for MODEL evaluation")
            if not self.end_date:
                errors.append("end_date is required for MODEL evaluation")

            # Validate date format (only for MODEL)
            start = None
            end = None
            if self.start_date:
                try:
                    start = date.fromisoformat(self.start_date)
                except ValueError:
                    errors.append(
                        f"start_date must be ISO format (YYYY-MM-DD), got: {self.start_date}"
                    )

            if self.end_date:
                try:
                    end = date.fromisoformat(self.end_date)
                except ValueError:
                    errors.append(
                        f"end_date must be ISO format (YYYY-MM-DD), got: {self.end_date}"
                    )

            # Validate date range
            if start and end and start > end:
                errors.append(
                    f"start_date ({self.start_date}) must be before or equal to end_date ({self.end_date})"
                )

        # Validate limit
        if self.limit < 1:
            errors.append(f"limit must be at least 1, got: {self.limit}")
        elif self.limit > 100:
            errors.append(f"limit must be at most 100, got: {self.limit}")

        # Validate metrics based on evaluation type
        if not self.metrics:
            errors.append("metrics list cannot be empty")
        else:
            # Build valid metrics list based on evaluation type
            if is_rag_evaluation:
                valid_metrics = set(RAG_METRICS + UNIVERSAL_METRICS)
            else:
                valid_metrics = set(MODEL_METRICS)

            for metric in self.metrics:
                if metric not in valid_metrics:
                    errors.append(
                        f"Invalid metric '{metric}' for {self.evaluation_type}. "
                        f"Valid: {', '.join(sorted(valid_metrics))}"
                    )

        return errors

    def to_dict(self) -> Dict:
        """Convert configuration to dictionary for Step Functions input"""
        result = {
            "agent_name": self.agent_name,
            "limit": self.limit,
            "metrics": self.metrics,
            "evaluation_type": self.evaluation_type,
        }

        # Include date range only for MODEL evaluation
        if self.start_date:
            result["start_date"] = self.start_date
        if self.end_date:
            result["end_date"] = self.end_date

        # Include dataset_path for RAG evaluation (will be processed by run_evaluation.py)
        if self.dataset_path:
            result["dataset_path"] = self.dataset_path

        return result


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
        print("Usage: python config_schema_mvp.py <config.yaml>")
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
        print(f"  Agent: {config.agent_name}")
        print(f"  Evaluation type: {config.evaluation_type}")

        if config.evaluation_type == "MODEL":
            print(f"  Date range: {config.start_date} to {config.end_date}")
        else:
            print(f"  Dataset path: {config.dataset_path}")

        print(f"  Limit: {config.limit} records")
        print(f"  Metrics: {', '.join(config.metrics)}")
        print(f"\nStep Functions input:")
        import json

        print(json.dumps(config.to_dict(), indent=2))
