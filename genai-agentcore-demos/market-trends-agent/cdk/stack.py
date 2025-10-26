from pathlib import Path
import json
from aws_cdk import Stack, CfnOutput, Duration, aws_cognito as cognito
from constructs import Construct

class CognitoStack(Stack):
    def __init__(self, scope: Construct):
        agent_name = Path(__file__).parent.parent.name
        super().__init__(scope, f"{agent_name}-cognito")

        pool = cognito.UserPool(
            self, "Pool",
            user_pool_name=f"AgentCore-{agent_name}",
            sign_in_case_sensitive=False,
            password_policy=cognito.PasswordPolicy(min_length=8),
            self_sign_up_enabled=False
        )

        client = pool.add_client(
            "Client",
            auth_flows=cognito.AuthFlow(user_password=True),
            access_token_validity=Duration.minutes(60),
            id_token_validity=Duration.minutes(60),
            refresh_token_validity=Duration.days(30)
        )

        users_file = Path(__file__).parent.parent.parent / ".demo_users.json"
        if users_file.exists():
            with open(users_file) as f:
                users = json.load(f)
            for user in users:
                cognito.CfnUserPoolUser(
                    self, f"User-{user['username']}",
                    user_pool_id=pool.user_pool_id,
                    username=user["username"],
                    user_attributes=[
                        cognito.CfnUserPoolUser.AttributeTypeProperty(
                            name="email",
                            value=user["email"]
                        ),
                        cognito.CfnUserPoolUser.AttributeTypeProperty(
                            name="email_verified",
                            value="true"
                        ),
                        cognito.CfnUserPoolUser.AttributeTypeProperty(
                            name="name",
                            value=user["name"]
                        )
                    ],
                    message_action="SUPPRESS"
                )

        CfnOutput(self, "UserPoolId", value=pool.user_pool_id)
        CfnOutput(self, "ClientId", value=client.user_pool_client_id)
        CfnOutput(self, "Region", value=self.region)