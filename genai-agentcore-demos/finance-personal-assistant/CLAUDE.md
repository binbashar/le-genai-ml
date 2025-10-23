# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a **Multi-Agent Financial Advisory System** workshop repository that demonstrates building sophisticated AI agents using Amazon Bedrock, Strands Agents, and Amazon Bedrock AgentCore. The system consists of three specialized agents:

1. **Budget Agent** - Personal budgeting, spending analysis, and financial discipline
2. **Financial Analysis Agent** - Investment research, portfolio management, and market analysis
3. **Orchestrator Agent** - Coordinates specialized agents and synthesizes comprehensive responses

## Repository Structure

- **Lab Notebooks**: Three Jupyter notebooks (`lab1-*.ipynb`, `lab2-*.ipynb`, `lab3-*.ipynb`) guide users through building and deploying the multi-agent system
- **utils/**: Shared utility modules supporting the notebooks
  - `message_formatter.py` - Formatting and displaying agent messages
  - `guardrail.py` - AWS Bedrock guardrail creation/management (prevents Bitcoin investment advice)
  - `agentcore_utils.py` - AWS Cognito user pool setup and authentication for AgentCore deployment
  - `__init__.py` - Exports utility functions

## Environment Setup

### Requirements
- Python 3.8+
- AWS credentials configured for Amazon Bedrock access
- Model access enabled for Anthropic Claude 3.7 Sonnet on Amazon Bedrock
- Jupyter Notebook or compatible IDE

### Dependencies Installation
```bash
pip install -r requirements.txt
```

The project uses these key dependencies:
- `strands-agents` (1.7.1) - Core agent framework
- `strands-agents-tools` (0.2.6) - Pre-built tools for agents
- `bedrock-agentcore` (0.1.3) - Amazon Bedrock AgentCore SDK
- `bedrock-agentcore-starter-toolkit` (0.1.10) - Deployment utilities
- `boto3` (1.40.27) - AWS SDK
- `yfinance` (0.2.65) - Financial data retrieval
- `pandas`, `matplotlib` - Data analysis and visualization

## Running the Notebooks

Execute the lab notebooks sequentially in Jupyter:

```bash
jupyter notebook lab1-develop_a_personal_budget_assistant_strands_agent.ipynb
```

**Lab Sequence:**
1. **Lab 1** (20 min): Build a personal finance assistant with Strands agents
2. **Lab 2** (20 min): Implement multi-agent workflows and orchestration
3. **Lab 3** (15 min): Deploy agents to production using Amazon Bedrock AgentCore

## Production Deployment

Deploy the orchestrator agent (`main.py`) without Cognito auth:
```bash
uv run agentcore configure --entrypoint main.py --name personal_finance_agent --non-interactive
uv run agentcore launch  # Builds and deploys via CodeBuild (~1 min)
uv run agentcore invoke '{"prompt": "Create a budget for $180K income"}'
```

## Agent Architecture

### Budget Agent Tools
- `calculate_budget_breakdown` - 50/30/20 budget calculations
- `analyze_spending_pattern` - Spending analysis with recommendations
- `calculator` - Financial calculations

### Financial Analysis Agent Tools
- `get_stock_analysis` - Real-time stock data and analysis
- `create_diversified_portfolio` - Risk-based portfolio recommendations
- `compare_stock_performance` - Multi-stock performance comparison

### Orchestrator Agent
Routes queries to appropriate specialist agents, coordinates multi-agent interactions, and synthesizes responses from multiple agents.

## Utility Functions

### Message Formatting
```python
from utils import pretty_print_messages, print_conversation_stats, print_last_exchange

# Display conversation history with formatting
pretty_print_messages(agent.messages)

# Show conversation statistics
print_conversation_stats(agent.messages)

# Display only recent exchanges
print_last_exchange(agent.messages, num_pairs=1)
```

### Guardrails
```python
from utils import create_guardrail, delete_guardrail, get_guardrail_id

# Create guardrail that prevents Bitcoin investment advice
guardrail_id, guardrail_arn = create_guardrail()

# Clean up guardrail
delete_guardrail(guardrail_id)
```

### AgentCore Authentication
```python
from utils import setup_cognito_user_pool, reauthenticate_user, delete_cognito_user_pool

# Setup Cognito user pool for AgentCore
auth_info = setup_cognito_user_pool()
# Returns: pool_id, client_id, bearer_token, discovery_url

# Re-authenticate to get new token
bearer_token = reauthenticate_user(client_id)

# Clean up user pool
delete_cognito_user_pool(pool_id)
```

## Cleanup

Each lab notebook includes cleanup steps at the end (commented out by default). Uncomment and run them to delete AWS resources:
- Guardrails created in Lab 1
- Cognito user pools created in Lab 3
- Any other temporary AWS resources

## AWS Services Used

- **Amazon Bedrock** - Foundation model access (Claude 3.7 Sonnet)
- **Amazon Bedrock Guardrails** - Content filtering and policy enforcement
- **Amazon Bedrock AgentCore** - Production agent deployment and scaling
- **Amazon Cognito** - Authentication for deployed agents

## Sample Queries

The system can handle complex financial queries like:
- "I make $6000/month and want to start investing $500/month. Help me create a budget and suggest an investment portfolio."
- "I spend too much on dining out ($800/month) and want to invest the savings. What should I do?"
- "Compare Tesla and Apple stocks, and tell me if I can afford to invest $2000 with my $4000 monthly income."

## Development Notes

- The repository is part of an AWS workshop at https://catalog.us-east-1.prod.workshops.aws/workshops/57f577e3-9a24-45e2-9937-e48b2cdf6986/en-US
- When modifying agent tools or configurations, test in the notebooks first before deploying to AgentCore
- The guardrail configuration blocks Bitcoin investment advice - modify `guardrail.py` to add additional content policies
- Authentication tokens from Cognito expire; use `reauthenticate_user()` to refresh
