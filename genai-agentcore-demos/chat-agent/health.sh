#!/bin/bash
#
# Chat Agent - Health Check
#
# Tests the deployed agent using cascading fallback strategy (AWS → Local).
# Uses shared health check module (libs/python/agentcore_health.py) for consistency.
#
# Usage:
#   ./health.sh                # Cascading: Try AWS, fallback to Local
#   ./health.sh --aws          # Test only AWS deployment
#   ./health.sh --local        # Test only local HTTP endpoint (port 8080)
#   ./health.sh --timeout 120  # Custom timeout (default: 60 seconds)
#
# Exit codes:
#   0 - Agent healthy (AWS or Local)
#   1 - Agent unhealthy or unreachable
#
# Prerequisites:
#   - Agent deployed (./launch.sh) OR running locally (agentcore launch --local)
#   - AWS credentials configured (AWS_PROFILE=binbash) for AWS mode
#   - .bedrock_agentcore.yaml exists (created by ./configure.sh)
#
# Features:
#   - Dynamic region detection (respects AWS_REGION environment variable)
#   - Configurable timeout via --timeout flag
#   - Automatic cascading fallback (tries AWS first, then Local if AWS fails)
#   - Detailed error reporting with suggestions
#

uv run health.py "$@"
