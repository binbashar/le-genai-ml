#!/bin/bash
# Health check wrapper - forwards all arguments to health.py
uv run health.py "$@"
