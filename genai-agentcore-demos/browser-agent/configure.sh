#!/bin/bash
set -e

echo "=========================================="
echo "Browser Agent - Configuration"
echo "=========================================="

# Run agentcore configure to create .bedrock_agentcore.yaml
echo "Running agentcore configure..."
uv run agentcore configure -e main.py

echo ""
echo "=========================================="
echo "Configuration complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review .bedrock_agentcore.yaml"
echo "  2. Run ./launch.sh to deploy"
echo ""
