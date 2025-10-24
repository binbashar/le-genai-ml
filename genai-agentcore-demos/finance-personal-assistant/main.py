# Create AgentCore-compatible deployment file with streaming endpoint

from bedrock_agentcore import BedrockAgentCoreApp
from budget_agent import FinancialReport, budget_agent
from config import BedrockModelCatalog, get_bedrock_model
from financial_analysis_agent import financial_analysis_agent
from strands import Agent, tool
from strands.agent.conversation_manager import SummarizingConversationManager
from utils import get_guardrail_id

app = BedrockAgentCoreApp()
agent = Agent()

ORCHESTRATOR_PROMPT = """You are a comprehensive financial advisor orchestrator that coordinates between specialized financial agents to provide complete financial guidance. 

Your specialized agents are:
1. **budget_agent**: Handles budgeting, spending analysis, savings recommendations, and expense tracking
2. **financial_analysis_agent_tool**: Handles investment analysis, stock research, portfolio creation, and performance comparisons

Guidelines for using your agents:
- Use **budget_agent** for questions about: budgets, spending habits, expense tracking, savings goals, debt management
- Use **financial_analysis_agent_tool** for questions about: stocks, investments, portfolios, market analysis, investment recommendations
- You can use both agents together for comprehensive financial planning
- Always provide a cohesive summary that combines insights from multiple agents when applicable
- Maintain a helpful, professional tone and include appropriate disclaimers about financial advice

When a user asks a question:
1. Determine which agent(s) are most appropriate
2. Call the relevant agent(s) with focused queries
3. Synthesize the responses into a coherent, comprehensive answer
4. Provide actionable next steps when possible"""

# Add conversation management to maintain context
conversation_manager = SummarizingConversationManager(
    summary_ratio=0.3,  # Summarize 30% of messages when context reduction is needed
    preserve_recent_messages=5,  # Always keep 5 most recent messages
)

guardrail_id = get_guardrail_id()

if guardrail_id:
    guardrails_config = {
        "guardrail_id": guardrail_id,
        "guardrail_version": "DRAFT",
        "guardrail_trace": "enabled",
    }
    model = get_bedrock_model(
        model=BedrockModelCatalog.NOVA_LITE,
        framework="strands",
        **guardrails_config,
    )
else:
    model = get_bedrock_model(
        model=BedrockModelCatalog.NOVA_LITE,
        framework="strands",
    )


@tool
def budget_agent_tool(query: str) -> FinancialReport:
    """Generate structured financial reports with budget analysis and recommendations."""
    try:
        structured_response = budget_agent.structured_output(
            output_model=FinancialReport, prompt=query
        )
        return structured_response
    except Exception as e:
        # Return a default structured response on error
        return FinancialReport(
            monthly_income=0.0,
            budget_categories=[],
            recommendations=[f"Error generating report: {str(e)}"],
            financial_health_score=1,
        )


# Wrap Financial Analysis Agent as a Tool
@tool
def financial_analysis_agent_tool(query: str) -> str:
    """Handle investment analysis queries including stock research, portfolio creation, and performance comparisons."""
    try:
        response = financial_analysis_agent(query)
        return str(response)
    except Exception as e:
        return f"❌ Financial analysis error: {str(e)}"


orchestrator_agent = Agent(
    model=model,
    system_prompt=ORCHESTRATOR_PROMPT,
    tools=[budget_agent_tool, financial_analysis_agent_tool],
    conversation_manager=conversation_manager,
)


@app.entrypoint
async def invoke(payload):
    """Your AI agent function"""
    user_message = payload["prompt"]
    async for event in orchestrator_agent.stream_async(user_message):
        if "data" in event:
            # Only stream text chunks to the client
            yield event["data"]


if __name__ == "__main__":
    app.run()
