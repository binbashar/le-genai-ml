#!/bin/bash
set -e

echo "========================================"
echo "Finance Assistant - Firehose Setup"
echo "========================================"
echo ""

# Check we're in the right directory
if [ ! -f "../.bedrock_agentcore.yaml" ]; then
    echo "❌ Error: .bedrock_agentcore.yaml not found in parent directory"
    echo "   Please ensure the Finance Personal Assistant is deployed first:"
    echo "   cd .. && ./launch.sh"
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

# Install dependencies if needed
if ! python3 -c "import boto3, yaml" &>/dev/null; then
    echo "📦 Installing dependencies..."
    pip3 install -q -r requirements.txt
    echo "✅ Dependencies installed"
    echo ""
fi

# Run setup
python3 setup_firehose.py
