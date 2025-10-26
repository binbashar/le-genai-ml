#!/usr/bin/env python3
"""
Complete Finance Personal Assistant Deployment Script
Handles IAM role creation, permissions, container deployment, and agent setup
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import boto3
from config import DEFAULT_REGION, get_region

# Add parent directory to path for shared modules
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.auth_utils import load_auth_config, configure_agent_auth

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# AUTHENTICATION CONFIGURATION
# ============================================================================
# Authentication is configured per-agent via .auth_config file (local to this directory)
#
# To enable authentication for THIS agent:
#   Run: uv run setup_identity.py --agent finance-personal-assistant
#   This creates: .auth_config (gitignored)
#
# To disable authentication:
#   Delete: .auth_config (agent will use IAM)
#
# ============================================================================


class FinancePersonalAssistantDeployer:
    """Complete deployer for Finance Personal Assistant"""

    def __init__(self, region: str = None):
        self.region = region or get_region()
        self.iam_client = boto3.client("iam", region_name=self.region)
        self.agentcore_client = boto3.client("bedrock-agentcore-control", region_name=self.region)

    def create_execution_role(self, role_name: str) -> str:
        """Create IAM execution role with all required permissions"""

        # Trust policy for Bedrock AgentCore
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }

        # Comprehensive execution policy with all required permissions
        execution_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream",
                        "bedrock:ApplyGuardrail",
                    ],
                    "Resource": "*",
                    "Sid": "BedrockModelInvocation",
                },
                {
                    "Effect": "Allow",
                    "Action": ["bedrock-agentcore:*"],
                    "Resource": "*",
                    "Sid": "BedrockAgentCoreOperations",
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "ecr:GetAuthorizationToken",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage",
                    ],
                    "Resource": "*",
                    "Sid": "ECRAccess",
                },
                {
                    "Effect": "Allow",
                    "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
                    "Resource": "*",
                    "Sid": "XRayTracing",
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    "Resource": "*",
                    "Sid": "CloudWatchLogging",
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "ssm:GetParameter",
                        "ssm:PutParameter",
                        "ssm:DeleteParameter",
                    ],
                    "Resource": "arn:aws:ssm:*:*:parameter/bedrock-agentcore/finance-personal-assistant/*",
                    "Sid": "SSMParameterAccess",
                },
            ],
        }

        try:
            # Create the role
            logger.info(f"🔐 Creating IAM role: {role_name}")
            role_response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Execution role for Finance Personal Assistant with comprehensive permissions",
            )

            # Attach the comprehensive execution policy
            logger.info(
                f"📋 Attaching comprehensive execution policy to role: {role_name}"
            )
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName="FinancePersonalAssistantComprehensivePolicy",
                PolicyDocument=json.dumps(execution_policy),
            )

            role_arn = role_response["Role"]["Arn"]
            logger.info(f"✅ Created IAM role with ARN: {role_arn}")

            # Wait for role to propagate
            logger.info("⏳ Waiting for role to propagate...")
            time.sleep(10)

            return role_arn

        except self.iam_client.exceptions.EntityAlreadyExistsException:
            logger.info(f"📋 IAM role {role_name} already exists, using existing role")

            # Update the existing role with comprehensive permissions
            logger.info("📋 Updating existing role with comprehensive permissions...")
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName="FinancePersonalAssistantComprehensivePolicy",
                PolicyDocument=json.dumps(execution_policy),
            )

            role_response = self.iam_client.get_role(RoleName=role_name)
            return role_response["Role"]["Arn"]

        except Exception as e:
            logger.error(f"❌ Failed to create IAM role: {e}")
            raise

    def _configure_auth(self, runtime, auth_config: dict) -> None:
        """Configure authentication for the runtime (generic - supports multiple providers)"""

        try:
            # Get runtime ARN from runtime object
            status = runtime.status()
            runtime_arn = None
            if hasattr(status, "agent_arn"):
                runtime_arn = status.agent_arn
            elif hasattr(status, "config") and hasattr(status.config, "agent_arn"):
                runtime_arn = status.config.agent_arn

            if not runtime_arn:
                logger.error("❌ Could not extract runtime ARN for auth configuration")
                return

            logger.info(f"   Configuring authentication for runtime: {runtime_arn}")

            # Use generic configure_agent_auth utility
            configure_agent_auth(self.agentcore_client, runtime_arn, auth_config)

        except Exception as e:
            logger.error(f"❌ Failed to configure authentication: {e}")
            logger.error("   The agent is deployed but authentication is NOT enabled")
            logger.error("   You may need to configure it manually via AWS Console or API")

    def deploy_agent(
        self,
        agent_name: str,
        role_name: str = "FinancePersonalAssistantRole",
        entrypoint: str = "main.py",
        requirements_file: str = None,
    ) -> str:
        """Deploy the Finance Personal Assistant with all requirements"""

        try:
            from bedrock_agentcore_starter_toolkit import Runtime

            logger.info("🚀 Starting Finance Personal Assistant Deployment")
            logger.info(f"   📝 Agent Name: {agent_name}")
            logger.info(f"   📍 Region: {self.region}")
            logger.info(f"   🎯 Entrypoint: {entrypoint}")

            # Step 1: Determine dependency management approach
            if requirements_file is None:
                # Auto-detect: prefer uv if pyproject.toml exists, fallback to requirements.txt
                if Path("pyproject.toml").exists():
                    logger.info(
                        "📦 Using uv with pyproject.toml for dependency management"
                    )
                    requirements_file = "pyproject.toml"
                elif Path("requirements.txt").exists():
                    logger.info(
                        "📦 Using pip with requirements.txt for dependency management"
                    )
                    requirements_file = "requirements.txt"
                else:
                    raise FileNotFoundError(
                        "No pyproject.toml or requirements.txt found"
                    )

            logger.info(f"   📋 Dependencies: {requirements_file}")

            # Step 2: Create execution role with all permissions
            execution_role_arn = self.create_execution_role(role_name)

            # Step 3: Initialize runtime
            runtime = Runtime()

            # Step 4: Configure the runtime
            logger.info("⚙️ Configuring runtime...")

            runtime.configure(
                execution_role=execution_role_arn,
                entrypoint=entrypoint,
                requirements_file=requirements_file,
                region=self.region,
                agent_name=agent_name,
                auto_create_ecr=True,
            )

            logger.info("✅ Configuration completed")

            # Step 4: Launch the runtime
            logger.info("🚀 Launching runtime (this may take several minutes)...")
            logger.info("   📦 Building container image...")
            logger.info("   ⬆️ Pushing to ECR...")
            logger.info("   🏗️ Creating AgentCore Runtime...")

            runtime.launch()

            logger.info("✅ Launch completed")

            auth_config_file = Path(__file__).parent / ".auth_config"
            auth_config = load_auth_config(auth_config_file)

            if auth_config:
                provider = auth_config.get("provider", "unknown")
                logger.info(f"🔐 Authentication configured: {provider}")
                logger.info(f"   Config file: {auth_config_file}")
                self._configure_auth(runtime, auth_config)
            else:
                logger.info("🔓 Using IAM authentication (no .auth_config found)")
                logger.info("   To enable auth: uv run setup_identity.py --agent finance-personal-assistant")

            # Step 5: Get status and extract ARN
            logger.info("📊 Getting runtime status...")
            status = runtime.status()

            # Extract runtime ARN
            runtime_arn = None
            if hasattr(status, "agent_arn"):
                runtime_arn = status.agent_arn
            elif hasattr(status, "config") and hasattr(status.config, "agent_arn"):
                runtime_arn = status.config.agent_arn

            if runtime_arn:
                # Save ARN to file
                arn_file = Path(".agent_arn")
                with open(arn_file, "w") as f:
                    f.write(runtime_arn)

                logger.info("\n🎉 Finance Personal Assistant Deployed Successfully!")
                logger.info(f"🏷️ Runtime ARN: {runtime_arn}")
                logger.info(f"📍 Region: {self.region}")
                logger.info(f"🔐 Execution Role: {execution_role_arn}")
                logger.info(f"💾 ARN saved to: {arn_file}")

                auth_config = load_auth_config(Path(__file__).parent / ".auth_config")
                if auth_config:
                    provider = auth_config.get("provider", "unknown")
                    logger.info("\n🔒 Authentication:")
                    logger.info(f"   Provider: {provider}")
                    if provider == "cognito":
                        logger.info(f"   User Pool: {auth_config.get('user_pool_id', 'N/A')}")
                        logger.info(f"   Client ID: {auth_config.get('client_id', 'N/A')}")
                else:
                    logger.info("\n🔓 Authentication: IAM (default)")

                # Show CloudWatch logs info
                agent_id = runtime_arn.split("/")[-1]
                log_group = f"/aws/bedrock-agentcore/runtimes/{agent_id}-DEFAULT"
                logger.info("\n📊 Monitoring:")
                logger.info(f"   CloudWatch Logs: {log_group}")
                logger.info(f"   Tail logs: aws logs tail {log_group} --follow")

                logger.info("\n📋 Next Steps:")
                logger.info("1. Test your agent: uv run python test_orchestrator_complete.py")
                logger.info("2. Monitor logs in CloudWatch")
                logger.info("3. Use the Runtime ARN for integrations")

                return runtime_arn
            else:
                logger.error("❌ Could not extract runtime ARN")
                logger.info(f"Status: {status}")
                return None

        except ImportError:
            logger.error("❌ bedrock-agentcore-starter-toolkit not installed")
            if Path("pyproject.toml").exists():
                logger.info("Install with: uv add bedrock-agentcore-starter-toolkit")
            else:
                logger.info(
                    "Install with: pip install bedrock-agentcore-starter-toolkit"
                )
            return None
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            import traceback

            logger.error(f"Full error: {traceback.format_exc()}")
            return None


def check_prerequisites():
    """Check if all prerequisites are met"""
    logger.info("🔍 Checking prerequisites...")

    # Check if required files exist
    required_files = [
        "main.py",
        "budget_agent.py",
        "financial_analysis_agent.py",
        "config.py",
        "utils/__init__.py",
    ]

    # Check for dependency files (either pyproject.toml or requirements.txt)
    has_pyproject = Path("pyproject.toml").exists()
    has_requirements = Path("requirements.txt").exists()

    if not has_pyproject and not has_requirements:
        logger.error("❌ No dependency file found (pyproject.toml or requirements.txt)")
        return False

    if has_pyproject:
        logger.info("✅ Found pyproject.toml - will use uv for dependency management")
    elif has_requirements:
        logger.info(
            "✅ Found requirements.txt - will use pip for dependency management"
        )

    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)

    if missing_files:
        logger.error(f"❌ Missing required files: {missing_files}")
        return False

    # Check Docker/Podman
    import subprocess

    container_runtime = None

    # Try Docker first
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            container_runtime = "docker"
            logger.info("✅ Docker found")
    except FileNotFoundError:
        pass

    # Try Podman if Docker not found
    if not container_runtime:
        try:
            result = subprocess.run(
                ["podman", "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                container_runtime = "podman"
                logger.info("✅ Podman found")
        except FileNotFoundError:
            pass

    if not container_runtime:
        logger.error("❌ Neither Docker nor Podman found")
        logger.info("💡 Make sure Docker or Podman is installed and running")
        return False

    # Check AWS credentials
    try:
        boto3.client("sts").get_caller_identity()
        logger.info("✅ AWS credentials configured")
    except Exception as e:
        logger.error(f"❌ AWS credentials not configured: {e}")
        return False

    logger.info("✅ All prerequisites met")
    return True


def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(
        description="Deploy Finance Personal Assistant to Amazon Bedrock AgentCore Runtime"
    )
    parser.add_argument(
        "--agent-name",
        default="personal_finance_agent",
        help="Name for the agent (default: personal_finance_agent)",
    )
    parser.add_argument(
        "--role-name",
        default="FinancePersonalAssistantRole",
        help="IAM role name (default: FinancePersonalAssistantRole)",
    )
    parser.add_argument(
        "--region",
        default=None,
        help=f"AWS region (default: from AWS_REGION env or {DEFAULT_REGION})",
    )
    parser.add_argument(
        "--skip-checks", action="store_true", help="Skip prerequisite checks"
    )

    args = parser.parse_args()

    # Check prerequisites
    if not args.skip_checks and not check_prerequisites():
        logger.error("❌ Prerequisites not met. Fix issues above or use --skip-checks")
        exit(1)

    # Create deployer and deploy
    deployer = FinancePersonalAssistantDeployer(region=args.region)

    runtime_arn = deployer.deploy_agent(
        agent_name=args.agent_name, role_name=args.role_name
    )

    if runtime_arn:
        logger.info("\n🎯 Deployment completed successfully!")
        logger.info("Run 'uv run python test_orchestrator_complete.py' to test your deployed agent.")
    else:
        logger.error("❌ Deployment failed")
        exit(1)


if __name__ == "__main__":
    main()
