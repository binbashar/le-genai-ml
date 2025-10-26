import json
from pathlib import Path

outputs_file = Path(__file__).parent / "outputs.json"
with open(outputs_file) as f:
    stack_outputs = list(json.load(f).values())[0]

auth_config = {
    "provider": "cognito",
    "user_pool_id": stack_outputs["UserPoolId"],
    "client_id": stack_outputs["ClientId"],
    "discovery_url": f"https://cognito-idp.{stack_outputs['Region']}.amazonaws.com/{stack_outputs['UserPoolId']}/.well-known/openid-configuration",
    "region": stack_outputs["Region"]
}

config_file = Path(__file__).parent.parent / ".auth_config"
with open(config_file, "w") as f:
    json.dump(auth_config, f, indent=2)