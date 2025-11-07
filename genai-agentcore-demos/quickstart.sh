#!/bin/bash
#
# Quickstart Validation Script
#
# Automatically validates all prerequisites for the AgentCore Workshop.
# Run this script before starting the workshop to ensure your environment is ready.
#
# Usage:
#   ./quickstart.sh
#
# Exit codes:
#   0 - All prerequisites met, ready to start workshop
#   1 - One or more prerequisites missing or failed validation
#

# Note: Not using 'set -e' to allow all checks to run even if some fail
set -o pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Detect AWS profile (use AWS_PROFILE env var, or default profile)
if [ -n "$AWS_PROFILE" ]; then
    PROFILE_ARG="--profile $AWS_PROFILE"
    PROFILE_NAME="$AWS_PROFILE"
else
    PROFILE_ARG=""
    PROFILE_NAME="default"
fi

# Helper function to run AWS CLI with correct profile
aws_cmd() {
    if [ -n "$PROFILE_ARG" ]; then
        aws $PROFILE_ARG "$@"
    else
        aws "$@"
    fi
}

# Print section header
print_header() {
    echo -e "\n${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}\n"
}

# Print check result
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((CHECKS_PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    echo -e "  ${YELLOW}→${NC} $2"
    if [ -n "$3" ]; then
        echo -e "  ${BLUE}ℹ${NC} See: TROUBLESHOOTING.md#$3"
    fi
    ((CHECKS_FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    echo -e "  ${YELLOW}→${NC} $2"
    ((CHECKS_WARNING++))
}

# Start validation
print_header "AgentCore Workshop - Prerequisites Validation"

echo "This script will validate your environment setup."
echo "Please wait while we check all prerequisites..."

# ============================================================
# 1. AWS CLI
# ============================================================
# AWS CLI v2 is required for managing AWS services from the terminal.
# v2 is 2-3x faster than v1 and includes modern features like SSO support.
print_header "1. Checking AWS CLI"

if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version 2>&1 | cut -d' ' -f1 | cut -d'/' -f2)
    AWS_MAJOR=$(echo "$AWS_VERSION" | cut -d'.' -f1)

    if [ "$AWS_MAJOR" -ge 2 ]; then
        check_pass "AWS CLI v$AWS_VERSION installed"
    else
        check_fail "AWS CLI v$AWS_VERSION (v2+ required)" "Upgrade: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html" "aws-credentials--authentication"
    fi
else
    check_fail "AWS CLI not found" "Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html" "aws-credentials--authentication"
fi

# ============================================================
# 2. AWS Credentials
# ============================================================
# Credentials authenticate your CLI commands to AWS.
# We validate that access keys are configured and working.
print_header "2. Checking AWS Credentials"

if aws_cmd sts get-caller-identity &> /dev/null; then
    ACCOUNT_ID=$(aws_cmd sts get-caller-identity --query Account --output text)
    USER_ARN=$(aws_cmd sts get-caller-identity --query Arn --output text)
    check_pass "AWS credentials valid (Account: $ACCOUNT_ID)"
    echo -e "  ${BLUE}→${NC} Identity: $USER_ARN"
else
    check_fail "AWS credentials not configured" "Run: aws configure" "aws-credentials--authentication"
fi

# Check default region (us-west-2 recommended for San Francisco proximity + full Bedrock/AgentCore availability)
if aws_cmd configure get region &> /dev/null; then
    REGION=$(aws_cmd configure get region)
    check_pass "Default region set: $REGION"

    if [ "$REGION" != "us-west-2" ]; then
        check_warn "Region is $REGION (workshop uses us-west-2)" "Consider setting: aws configure set region us-west-2"
    fi
else
    check_warn "No default region configured" "Set region: aws configure set region us-west-2"
fi

# ============================================================
# 3. Bedrock Model Access
# ============================================================
# Amazon Bedrock provides foundation models (Nova, Claude) for our agents.
# We verify you can access the models needed for the workshop.
# Note: As of October 2025, models are auto-enabled for new accounts.
print_header "3. Checking Bedrock Model Access"

if aws_cmd bedrock list-foundation-models --region us-west-2 --query 'modelSummaries[?contains(modelId, `nova-premier`)].modelId' --output text &> /dev/null; then
    NOVA_COUNT=$(aws_cmd bedrock list-foundation-models --region us-west-2 --query 'modelSummaries[?contains(modelId, `nova`)].modelId' --output text 2>/dev/null | wc -w)
    CLAUDE_COUNT=$(aws_cmd bedrock list-foundation-models --region us-west-2 --query 'modelSummaries[?contains(modelId, `claude`)].modelId' --output text 2>/dev/null | wc -w)

    check_pass "Bedrock model access enabled ($NOVA_COUNT Nova, $CLAUDE_COUNT Claude models)"

    # Check for Nova Premier (required for vision analysis of receipts/invoices)
    # We search for the base model ID (not inference profile) to ensure availability
    NOVA_CHECK=$(aws_cmd bedrock list-foundation-models --region us-west-2 --query 'modelSummaries[?contains(modelId, `nova-premier`)].modelId' --output text 2>/dev/null || true)
    if echo "$NOVA_CHECK" | grep -q "nova-premier"; then
        check_pass "Amazon Nova Premier (required for vision) - Available"
    else
        check_fail "Amazon Nova Premier not available" "Enable at: https://console.aws.amazon.com/bedrock/home#/modelaccess" "bedrock-model-access"
    fi
else
    check_fail "Cannot access Bedrock models" "Enable model access: https://console.aws.amazon.com/bedrock/home#/modelaccess" "bedrock-model-access"
fi

# ============================================================
# 4. Python
# ============================================================
# Python 3.13+ is required for latest features and performance improvements.
# Includes experimental free-threaded mode and JIT compiler for better performance.
print_header "4. Checking Python"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)

    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 13 ]; then
        check_pass "Python $PYTHON_VERSION installed (3.13+ required)"
    else
        check_fail "Python $PYTHON_VERSION (3.13+ required)" "Install: https://www.python.org/downloads/" "python--dependencies"
    fi
else
    check_fail "Python not found" "Install Python 3.13+: https://www.python.org/downloads/" "python--dependencies"
fi

# ============================================================
# 5. UV Package Manager
# ============================================================
# UV is a blazingly fast Python package manager (10-100x faster than pip).
# Written in Rust, it dramatically speeds up dependency installation.
print_header "5. Checking UV Package Manager"

if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version | cut -d' ' -f2)
    check_pass "uv v$UV_VERSION installed"
else
    check_fail "uv not found" "Install: curl -LsSf https://astral.sh/uv/install.sh | sh" "python--dependencies"
fi

# ============================================================
# 6. Docker
# ============================================================
# Docker packages agents into containers for AgentCore Runtime deployment.
# Both Docker installation and running daemon are required.
print_header "6. Checking Docker"

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
    check_pass "Docker v$DOCKER_VERSION installed"

    # Check if Docker daemon is running
    if docker ps &> /dev/null; then
        check_pass "Docker daemon is running"
    else
        check_fail "Docker daemon not running" "Start Docker Desktop or run: sudo systemctl start docker" "docker-issues"
    fi
else
    check_fail "Docker not found" "Install: https://docs.docker.com/get-docker/" "docker-issues"
fi

# ============================================================
# 7. AWS CDK
# ============================================================
# AWS CDK (Cloud Development Kit) deploys infrastructure as code.
# Bootstrapping creates S3 buckets, ECR repositories, and IAM roles needed for deployments.
print_header "7. Checking AWS CDK"

if command -v cdk &> /dev/null; then
    CDK_VERSION=$(cdk --version | cut -d' ' -f1)
    check_pass "AWS CDK v$CDK_VERSION installed"

    # Check if CDK is bootstrapped (optional check)
    if aws_cmd cloudformation describe-stacks --region us-west-2 --stack-name CDKToolkit &> /dev/null; then
        check_pass "CDK bootstrapped in us-west-2"
    else
        check_warn "CDK not bootstrapped in us-west-2" "Run: cdk bootstrap aws://$ACCOUNT_ID/us-west-2"
    fi
else
    check_fail "AWS CDK not found" "Install: npm install -g aws-cdk" "cdk-infrastructure"
fi

# ============================================================
# 8. Repository Setup
# ============================================================
print_header "8. Checking Repository Setup"

# Check if we're in the right directory
if [ -f "pyproject.toml" ] && grep -q "genai-agentcore-demos" pyproject.toml; then
    check_pass "In correct directory (genai-agentcore-demos)"
else
    check_warn "Not in genai-agentcore-demos directory" "Navigate to: cd genai-agentcore-demos"
fi

# Check if dependencies are installed
if [ -d ".venv" ]; then
    check_pass "Virtual environment exists (.venv)"
else
    check_warn "Virtual environment not found" "Run: uv sync"
fi

# ============================================================
# 9. IAM Permissions Check
# ============================================================
print_header "9. Checking IAM Permissions (sample)"

# Test a few key permissions
if aws_cmd bedrock list-foundation-models --region us-west-2 --query 'modelSummaries[0].modelId' --output text &> /dev/null; then
    check_pass "Bedrock API access verified"
else
    check_fail "Cannot access Bedrock API" "Check IAM permissions for bedrock:ListFoundationModels" "bedrock-model-access"
fi

if aws_cmd ecr describe-repositories --region us-west-2 --max-results 1 &> /dev/null; then
    check_pass "ECR access verified"
else
    check_warn "ECR access may be limited" "Ensure IAM permissions for ecr:DescribeRepositories"
fi

# ============================================================
# Summary
# ============================================================
print_header "Validation Summary"

echo -e "${GREEN}Passed:${NC}   $CHECKS_PASSED"
echo -e "${YELLOW}Warnings:${NC} $CHECKS_WARNING"
echo -e "${RED}Failed:${NC}   $CHECKS_FAILED"

echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    if [ $CHECKS_WARNING -eq 0 ]; then
        echo ""
        echo -e "${GREEN}"
        echo "              !"
        echo "              !"
        echo "              ^"
        echo "             / \\"
        echo "            /___\\"
        echo "           |=   =|"
        echo "           |     |"
        echo "           |     |"
        echo "           |     |"
        echo "           |     |"
        echo "          /|##!##|\\"
        echo "         / |##!##| \\"
        echo "        /  |##!##|  \\"
        echo "       |  / ^ | ^ \  |"
        echo "       | /  ( | )  \ |"
        echo "       |/   ( | )   \|"
        echo "           ((   ))"
        echo "          ((  :  ))"
        echo "           ((   ))"
        echo "            (( ))"
        echo "             ( )"
        echo "              ."
        echo "              ."
        echo -e "${NC}"
        echo ""
        echo -e "${GREEN}✓ All checks passed! You're ready for LIFTOFF! 🚀${NC}"
        echo ""
        echo -e "Next steps:"
        echo -e "  1. cd finance-personal-assistant/workshop"
        echo -e "  2. Open: lab1-develop_a_personal_budget_assistant_strands_agent.ipynb"
        echo ""
        exit 0
    else
        echo -e "${YELLOW}⚠ All critical checks passed, but there are warnings.${NC}"
        echo -e "${YELLOW}  Review warnings above before proceeding.${NC}"
        echo ""
        exit 0
    fi
else
    echo -e "${RED}✗ $CHECKS_FAILED check(s) failed. Please resolve issues before starting.${NC}"
    echo ""
    echo -e "Need help? See: PRE_WORKSHOP_CHECKLIST.md and TROUBLESHOOTING.md"
    echo ""
    exit 1
fi
