#!/bin/bash

if [ "$1" = "--local" ]; then
    export AGENTCORE_LOCAL_MODE=1
fi

# No sync needed - Streamlit auto-discovers agent config from SSM Parameter Store
export PYTHONPATH="${PYTHONPATH}:$(dirname "$PWD")"
uv run streamlit run app.py
