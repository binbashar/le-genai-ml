#!/bin/bash
export PYTHONPATH="${PYTHONPATH}:$(dirname "$PWD")"
uv run streamlit run app.py
