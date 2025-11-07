# AWS AgentCore FinTech Demo - Streamlit Interface

Simple demonstration interface for AWS AgentCore's multi-agent orchestration capabilities.

## Quick Setup

### Prerequisites
- Python 3.13+
- AWS credentials configured
- Access to deployed AgentCore agents

### Installation
```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup environment
uv venv
uv sync

# Run demo
uv run streamlit run app.py
```

### Configuration
Update agent ARNs in `app.py`:
```python
AGENTS = {
    "Finance": {
        "arn": "arn:aws:bedrock:us-west-2:YOUR_ACCOUNT:agent/finance",
        "query": "..."
    },
    "Market": {
        "arn": "arn:aws:bedrock:us-west-2:YOUR_ACCOUNT:agent/market",
        "query": "..."
    }
}
```

## Running the Demo

1. Start the app: `uv run streamlit run app.py`
2. Browser opens automatically to `http://localhost:8501`
3. Select Finance or Market tab
4. Click "Run Demo Scenario"
5. Watch tool messages and streaming response

## Demo Script

### Finance Demo
"Let me show you our Finance Assistant helping Sarah, a tech professional in San Francisco..."
- Click "Run Demo Scenario"
- Point out tool messages: budget calculation, spending analysis
- Highlight personalized recommendations

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection failed | Check AWS credentials: `aws sts get-caller-identity` |
| Agent not found | Verify ARN in app.py matches deployed agent |
| No response | Check agent is deployed and active |
| Slow response | Normal - agents take 10-30 seconds |

## Documentation

- `PRD.md` - Product requirements
- `requirements.md` - Functional specifications
- `design.md` - Technical design
- `tasks.md` - Implementation tasks

## Notes

- This is a demo application, not for production use
- Queries are hard-coded for reliability
- No error retry logic - restart if issues occur
- Requires active internet connection

## License & Attribution

This project is inspired by and based on examples from the [Amazon Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) repository by AWS Labs.

**Original Source**: https://github.com/awslabs/amazon-bedrock-agentcore-samples

**License**: Apache License 2.0 - See [LICENSE](../LICENSE) file for details.

This Streamlit interface demonstrates real-time streaming and tool orchestration capabilities of AWS Bedrock AgentCore agents, created for event demonstrations and educational purposes.