#!/bin/bash
cd "$(dirname "$0")/.." && ./sync.sh && cd - > /dev/null
export PYTHONPATH="${PYTHONPATH}:$(dirname "$PWD")"
uv run streamlit run app.py
