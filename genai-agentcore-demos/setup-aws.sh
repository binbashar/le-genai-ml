#!/bin/bash
# Setup AWS credentials for AgentCore demos
#
# Usage:
#   source setup-aws.sh
#
# Set your AWS credentials:
# export AWS_ACCESS_KEY_ID="your-access-key"
# export AWS_SECRET_ACCESS_KEY="your-secret-key"
# export AWS_SESSION_TOKEN="your-session-token"  # If using SSO
# export AWS_REGION="us-west-2"  # Or your region

# Alternative: Set profile name if you have AWS config
# export AWS_PROFILE="your-profile-name"

echo "AWS Environment Variables:"
echo "  AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:0:10}..."
echo "  AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:+[set]}"
echo "  AWS_SESSION_TOKEN: ${AWS_SESSION_TOKEN:+[set]}"
echo "  AWS_REGION: ${AWS_REGION:-not set}"
echo "  AWS_PROFILE: ${AWS_PROFILE:-not set}"
echo ""
echo "To test credentials:"
echo "  cd /home/user/le-genai-ml/genai-agentcore-demos"
echo "  python health.py"
