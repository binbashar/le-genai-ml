#!/bin/bash

if [ "$1" = "--local" ]; then
    export AGENTCORE_LOCAL_MODE=1
fi

cd "$(dirname "$0")/.." && ./sync.sh && cd - > /dev/null
export PYTHONPATH="${PYTHONPATH}:$(dirname "$PWD")"
uv run streamlit run app.py
