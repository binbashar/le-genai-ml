#!/bin/bash
# Run evaluation pipeline from YAML configuration
#
# Usage:
#   ./scripts/run_evaluation.sh config/runs/example.yaml
#   ./scripts/run_evaluation.sh config/runs/example.yaml --wait

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
export AWS_PROFILE=${AWS_PROFILE:-binbash}

uv run scripts/run_evaluation.py "$@"
