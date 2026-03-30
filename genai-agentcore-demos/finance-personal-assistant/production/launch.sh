#!/bin/bash
#
# Finance Personal Assistant - Deploy Agent
#
# Builds Docker image, pushes to ECR, and deploys to AWS Bedrock AgentCore Runtime.
# Automatically publishes agent ARN to SSM Parameter Store for service discovery.
#
# Usage:
#   ./launch.sh
#
# Prerequisites:
#   - .bedrock_agentcore.yaml exists (created by ./configure.sh)
#   - Docker daemon running (for image build)
#   - AWS credentials configured (AWS_PROFILE=binbash)
#   - Dependencies installed (uv sync)
#
# What this script does:
#   1. Builds Docker container with agent code (automatic via 'agentcore launch')
#   2. Pushes image to ECR repository (auto-created if not exists)
#   3. Creates/updates AgentCore Runtime instance
#   4. Creates DEFAULT endpoint (points to latest version)
#   5. Publishes agent ARN to SSM: /agentcore/finance_personal_assistant/config
#
# Output:
#   - AgentCore Runtime with immutable version number
#   - ECR repository and Docker image
#   - SSM parameter updated with agent ARN (enables Streamlit UI discovery)
#
# Deployment features:
#   - Immutable versioning (new version on each deployment)
#   - --auto-update-on-conflict (updates existing agents)
#   - OpenTelemetry instrumentation (automatic observability)
#   - Non-root container user (security best practice)
#
# After deployment:
#   - Test with: ./health.sh
#   - View logs: aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow
#   - Streamlit UI auto-discovers agent via SSM (no manual sync needed)
#
set -e

AGENT_NAME="finance_personal_assistant"

echo "🚀 Deploying agent to AWS Bedrock AgentCore Runtime..."
echo ""

# Launch agent - Always use --auto-update-on-conflict to update existing agents
uv run agentcore launch --auto-update-on-conflict "$@"

# Patch IAM execution role to include ListMemories permission
# The agentcore CLI omits this action from the auto-generated policy,
# but the agent needs it to search for existing memory instances during initialization.
ROLE_NAME=$(uv run python -c "
import yaml
with open('.bedrock_agentcore.yaml') as f:
    cfg = yaml.safe_load(f)
arn = cfg.get('agents', {}).get('main', {}).get('aws', {}).get('execution_role', '')
print(arn.split('/')[-1] if arn else '')
")
if [ -n "$ROLE_NAME" ] && [ "$ROLE_NAME" != "null" ]; then
    POLICY_NAME="BedrockAgentCoreRuntimeExecutionPolicy-main"
    CURRENT_POLICY=$(aws iam get-role-policy --role-name "$ROLE_NAME" --policy-name "$POLICY_NAME" --query 'PolicyDocument' --output json 2>/dev/null || echo "")
    if [ -n "$CURRENT_POLICY" ]; then
        HAS_LIST_MEMORIES=$(echo "$CURRENT_POLICY" | python3 -c "
import json, sys
policy = json.load(sys.stdin)
for s in policy.get('Statement', []):
    if s.get('Sid') == 'BedrockAgentCoreMemory' and 'bedrock-agentcore:ListMemories' in s.get('Action', []):
        print('yes'); sys.exit()
print('no')
")
        if [ "$HAS_LIST_MEMORIES" = "no" ]; then
            echo ""
            echo "🔧 Patching IAM policy: adding ListMemories permission..."
            UPDATED_POLICY=$(echo "$CURRENT_POLICY" | python3 -c "
import json, sys
policy = json.load(sys.stdin)
for s in policy['Statement']:
    if s.get('Sid') == 'BedrockAgentCoreMemory':
        s['Action'].append('bedrock-agentcore:ListMemories')
        break
json.dump(policy, sys.stdout)
")
            echo "$UPDATED_POLICY" | aws iam put-role-policy \
                --role-name "$ROLE_NAME" \
                --policy-name "$POLICY_NAME" \
                --policy-document file:///dev/stdin
            echo "✅ IAM policy patched successfully"
        fi
    fi
fi

echo ""
echo "📝 Publishing agent configuration to SSM Parameter Store..."
uv run python ../../libs/python/post_agent_deploy.py "$AGENT_NAME" .

echo ""
echo "✅ Deployment complete! Agent is now discoverable via SSM."
