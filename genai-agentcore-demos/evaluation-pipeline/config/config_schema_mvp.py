"""
MVP Configuration Schema - Simplified for Step Functions Testing

Goal: Test that Step Functions can read YAML config and pass it through
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, List
import yaml


@dataclass
class EvaluationConfig:
    """Minimal evaluation configuration for MVP connectivity test"""
    agent_name: str
    start_date: str  # ISO format: YYYY-MM-DD
    end_date: str    # ISO format: YYYY-MM-DD
    limit: int
    metrics: List[str]

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "EvaluationConfig":
        """Load configuration from YAML file"""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        return cls(
            agent_name=data['agent_name'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            limit=data.get('limit', 10),
            metrics=data['metrics']
        )

    def validate(self) -> List[str]:
        """Validate configuration"""
        errors = []

        # Validate agent name
        if not self.agent_name:
            errors.append("agent_name is required")

        # Validate date format
        try:
            start = date.fromisoformat(self.start_date)
        except ValueError:
            errors.append(f"start_date must be ISO format (YYYY-MM-DD), got: {self.start_date}")
            start = None

        try:
            end = date.fromisoformat(self.end_date)
        except ValueError:
            errors.append(f"end_date must be ISO format (YYYY-MM-DD), got: {self.end_date}")
            end = None

        # Validate date range
        if start and end and start > end:
            errors.append(f"start_date ({self.start_date}) must be before or equal to end_date ({self.end_date})")

        # Validate limit
        if self.limit < 1:
            errors.append(f"limit must be at least 1, got: {self.limit}")
        elif self.limit > 100:
            errors.append(f"limit must be at most 100, got: {self.limit}")

        # Validate metrics
        if not self.metrics:
            errors.append("metrics list cannot be empty")

        valid_metrics = [
            "Builtin.Correctness",
            "Builtin.Completeness",
            "Builtin.Harmfulness"
        ]

        for metric in self.metrics:
            if metric not in valid_metrics:
                errors.append(f"Invalid metric '{metric}'. Valid: {', '.join(valid_metrics)}")

        return errors

    def to_dict(self) -> Dict:
        """Convert configuration to dictionary for Step Functions input"""
        return {
            "agent_name": self.agent_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "limit": self.limit,
            "metrics": self.metrics
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
        print(f"  Date range: {config.start_date} to {config.end_date}")
        print(f"  Limit: {config.limit} records")
        print(f"  Metrics: {', '.join(config.metrics)}")
        print(f"\nStep Functions input:")
        import json
        print(json.dumps(config.to_dict(), indent=2))
