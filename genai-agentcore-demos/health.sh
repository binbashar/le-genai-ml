#!/bin/bash
# Health check for all agents

# Add new agents here
agents=(
    "market-trends-agent"
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
