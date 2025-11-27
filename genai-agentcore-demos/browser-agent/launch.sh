#!/bin/bash
set -e

echo "=========================================="
echo "Browser Agent - Deployment"
echo "=========================================="

# Deploy to AgentCore Runtime
echo "Deploying browser agent to AgentCore Runtime..."
uv run agentcore launch --auto-update-on-conflict

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Run ./health.sh to verify deployment"
echo "  2. Check logs: aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow"
echo ""
