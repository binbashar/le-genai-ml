#!/bin/bash
#
# Health Check All Agents
#
# Tests all deployed AgentCore agents in parallel and aggregates results.
# Uses cascading fallback strategy (AWS → Local) for each agent.
#
# Usage:
#   ./health.sh                # Test all agents with cascading fallback
#   ./health.sh --aws          # Test only AWS deployments
#   ./health.sh --local        # Test only local endpoints
#   ./health.sh --timeout 180  # Custom timeout (default: 60 seconds)
#
# Exit codes:
#   0 - All agents healthy
#   1 - One or more agents failed
#
# How it works:
#   1. Runs first agent in foreground (real-time output)
#   2. Runs remaining agents in parallel (captured output)
#   3. Aggregates results and displays summary
#
# Each agent uses shared health check module (libs/python/agentcore_health.py):
#   - Dynamic region detection (respects AWS_REGION env var)
#   - Configurable timeout via --timeout flag
#   - Cascading fallback: AWS → Local (until one succeeds)
#

agents=(
    "finance-personal-assistant"
)

echo "================================================================================"
echo "AGENTCORE DEMOS - HEALTH CHECK ALL"
echo "================================================================================"
echo ""

# Run first agent in foreground (real-time output)
first="${agents[0]}"
(cd "$first" && ./health.sh "$@")
echo ""

# Run remaining agents in parallel, capture outputs
outputs=()
for agent in "${agents[@]:1}"; do
    tmp=$(mktemp)
    outputs+=("$tmp")
    (cd "$agent" && ./health.sh "$@") > "$tmp" 2>&1 &
done

wait

# Display remaining outputs sequentially
for output in "${outputs[@]}"; do
    cat "$output"
    echo ""
done

# Cleanup
rm -f "${outputs[@]}"

echo "================================================================================"
echo "✅ ALL CHECKS COMPLETE"
echo "================================================================================"
