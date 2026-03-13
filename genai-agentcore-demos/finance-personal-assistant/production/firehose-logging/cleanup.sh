#!/bin/bash
set -e

echo "========================================"
echo "Finance Assistant - Firehose Cleanup"
echo "========================================"
echo ""

# Check we're in the right directory
if [ ! -f "../.bedrock_agentcore.yaml" ]; then
    echo "❌ Error: .bedrock_agentcore.yaml not found in parent directory"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS credentials not configured. Please run:"
    echo "   export AWS_PROFILE=binbash"
    echo "   aws sso login --profile binbash"
    exit 1
fi

echo "✅ AWS credentials verified"
echo ""

# Confirmation
read -p "⚠️  This will DELETE all Firehose resources and logs. Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Run cleanup
python3 cleanup_firehose.py
