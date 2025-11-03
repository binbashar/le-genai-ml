#!/bin/bash

# Deploy AgentCore Gateway CDK stacks
#
# Usage:
#   ./deploy.sh              # Deploy all stacks
#   ./deploy.sh --profile X  # Deploy with specific AWS profile

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}AgentCore Gateway CDK Deployment${NC}"
echo "=================================="

# Check AWS credentials
echo -e "\n${YELLOW}Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity "$@" > /dev/null 2>&1; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    echo "Please configure AWS credentials or use --profile flag"
    exit 1
fi

ACCOUNT=$(aws sts get-caller-identity "$@" --query Account --output text)
REGION=$(aws configure get region "$@" || echo "us-west-2")

echo -e "${GREEN}✓${NC} Account: $ACCOUNT"
echo -e "${GREEN}✓${NC} Region: $REGION"

# Set environment variables for CDK
export CDK_DEFAULT_ACCOUNT=$ACCOUNT
export CDK_DEFAULT_REGION=$REGION

# Bootstrap CDK if needed
echo -e "\n${YELLOW}Checking CDK bootstrap...${NC}"
if ! aws cloudformation describe-stacks --stack-name CDKToolkit "$@" > /dev/null 2>&1; then
    echo -e "${YELLOW}CDK not bootstrapped. Running bootstrap...${NC}"
    cdk bootstrap "$@"
else
    echo -e "${GREEN}✓${NC} CDK already bootstrapped"
fi

# Synthesize CloudFormation templates
echo -e "\n${YELLOW}Synthesizing CloudFormation templates...${NC}"
uv run cdk synth "$@"

# Deploy all stacks
echo -e "\n${YELLOW}Deploying Gateway stacks...${NC}"
uv run cdk deploy --all --require-approval never "$@"

# Post-deployment: Generate local config files for development
echo -e "\n${YELLOW}Generating local configuration files...${NC}"
uv run python post_deploy.py "$@"

echo -e "\n${GREEN}✓ Deployment complete!${NC}"
echo -e "\nNext steps:"
echo "1. Check SSM parameters: aws ssm get-parameter --name /agentcore/agentcore-gateway/config"
echo "2. Test Gateway: python3 ../scripts/test_m2m_auth.py"
echo "3. Configure agents: Update agent's utils/gateway.py to read from SSM"
