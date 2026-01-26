 wsl.exe -d Ubuntu-24.04

 export AWS_PROFILE=DataScientist-905418344519

 aws configure sso

 uv run agentcore configure -e translator_agent_with_tools.py

 uv run agentcore launch


 aws bedrock-agentcore-control create-gateway \
    --name translator-agent-gateway \
    --role-arn arn:aws:iam::905418344519:role/AgentCoreGatewayRole \
    --protocol-type MCP \
    --authorizer-type AWS_IAM \
    --region us-west-2