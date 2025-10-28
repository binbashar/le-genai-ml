# Create AgentCore-compatible deployment file with streaming endpoint

import logging
import uuid

from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.integrations.strands.config import (
    AgentCoreMemoryConfig,
    RetrievalConfig,
)
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from budget_agent import FinancialReport, budget_agent
from config import BedrockModelCatalog, get_bedrock_model, get_region
from financial_analysis_agent import financial_analysis_agent
from strands import Agent, tool
from strands.agent.conversation_manager import SummarizingConversationManager
from utils import get_guardrail_id
from utils.vision_analyzer import analyze_image

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = BedrockAgentCoreApp()
agent = Agent()

ORCHESTRATOR_PROMPT = """You are a comprehensive financial advisor orchestrator that coordinates between specialized financial agents to provide complete financial guidance.

Your specialized agents are:
1. **budget_agent**: Handles budgeting, spending analysis, savings recommendations, and expense tracking
2. **financial_analysis_agent_tool**: Handles investment analysis, stock research, portfolio creation, and performance comparisons

<memory_behavior>
You have access to conversation history and user profile information.
Use the user's name and previous topics naturally in responses.
When users share personal details, financial goals, or budget info, remember them for future conversations.

E.g. John: "Hi, again!" -> "Hello John, how is your financial presentation going?"
</memory_behavior>

<vision_capability>
You can analyze images of financial documents (receipts, invoices, bank statements).
When you see [Vision Analysis: ...] in the message, an image has been automatically analyzed.

If vision status is "success": Use the extracted data to help the user. Present the information clearly:
  - Show merchant, date, total, and items found
  - Suggest expense category if provided
  - Offer to help with budget tracking or expense management

If vision status is "unknown": Politely inform the user that the image could not be recognized.
  Say something like: "I couldn't recognize that image as a financial document. Please upload a receipt or invoice."

If vision status is "error": Acknowledge the technical issue briefly and offer to help via text instead.
</vision_capability>

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
        model=BedrockModelCatalog.CLAUDE_SONNET_45,
        framework="strands",
        **guardrails_config,
    )
    logger.info(f"Guardrails enabled with ID: {guardrail_id}")
else:
    model = get_bedrock_model(
        model=BedrockModelCatalog.CLAUDE_SONNET_45,
        framework="strands",
    )
    logger.info("No guardrails configured, proceeding without guardrails")


def create_or_get_memory(region: str) -> str:
    """Create or retrieve AgentCore Memory with LTM strategies."""
    logger.info("[+] Initializing AgentCore Memory with 3 LTM strategies")
    try:
        client = MemoryClient(region_name=region)

        # Check if memory already exists to avoid ValidationException in logs
        # Note: list_memories() returns memory IDs, not names
        memory_name = "FinancePersonalAssistantMemory"
        existing_memories = client.list_memories()

        # Memory IDs are in format: "MemoryName-RandomId"
        existing_memory = next(
            (m for m in existing_memories if m.get("id", "").startswith(memory_name)),
            None,
        )

        if existing_memory:
            memory_id = existing_memory["id"]
            logger.info(f"[✓] Using existing memory: {memory_id}")
        else:
            # Memory doesn't exist, create it
            memory = client.create_memory_and_wait(
                name=memory_name,
                description="Personal finance assistant with user preferences, budget data, and conversation summaries",
                strategies=[
                    {
                        "userPreferenceMemoryStrategy": {
                            "name": "UserPreferences",
                            "description": "User's name, financial goals, preferences, risk tolerance",
                            "namespaces": [
                                "finance-assistant/user/{actorId}/preferences"
                            ],
                        }
                    },
                    {
                        "semanticMemoryStrategy": {
                            "name": "BudgetFacts",
                            "description": "Budget amounts, spending patterns, income sources, financial constraints",
                            "namespaces": ["finance-assistant/user/{actorId}/facts"],
                        }
                    },
                    {
                        "summaryMemoryStrategy": {
                            "name": "SessionSummaries",
                            "description": "Conversation summaries and financial planning session outcomes",
                            "namespaces": [
                                "finance-assistant/user/{actorId}/summaries/{sessionId}"
                            ],
                        }
                    },
                ],
                event_expiry_days=90,
            )
            memory_id = memory["id"]
            logger.info("[✓] Memory created successfully (90-day retention)")

        return memory_id
    except Exception as e:
        logger.error(f"[✗] Memory initialization failed: {type(e).__name__}")
        raise


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


def extract_actor_id(context) -> str:
    """Extract actor ID from request headers.

    Args:
        context: AgentCore Runtime context object with request_headers

    Returns:
        User ID from custom header, or 'demo-user' as fallback
    """
    headers = getattr(context, "request_headers", {}) or {}
    actor_id = headers.get(
        "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id", "demo-user"
    )
    logger.info(f"[AUTH] Extracted actor_id={actor_id} from request headers")
    return actor_id


def format_vision_data(data: dict) -> str:
    """
    Format vision-extracted data for context injection.

    Args:
        data: Dictionary of extracted financial data

    Returns:
        Formatted string for injection into user message
    """
    if not data:
        return ""

    lines = []
    for key, value in data.items():
        if isinstance(value, list):
            # Format list items (e.g., line items from receipt)
            if value:
                lines.append(f"{key.title()}: {len(value)} items")
                for item in value[:3]:  # Show first 3 items
                    lines.append(f"  - {item}")
                if len(value) > 3:
                    lines.append(f"  - ... and {len(value) - 3} more")
            else:
                lines.append(f"{key.title()}: (empty)")
        elif isinstance(value, (int, float)):
            # Format numbers (e.g., totals, prices)
            if key.lower() in ["total", "subtotal", "tax", "amount"]:
                lines.append(f"{key.title()}: ${value:.2f}")
            else:
                lines.append(f"{key.title()}: {value}")
        else:
            # Format strings (e.g., merchant, date, category)
            lines.append(f"{key.title()}: {value}")

    return "\n".join(lines)


@app.entrypoint
async def invoke(payload, context):
    """Your AI agent function with memory and vision support"""
    # AWS provides session_id via context (not payload)
    # This works for all invocation types: OAuth, IAM, local, CLI
    session_id = context.session_id

    # UUID fallback only if context doesn't provide one (AWS requires 33+ chars)
    if not session_id or len(session_id) < 33:
        session_id = str(uuid.uuid4())
        logger.warning(f"No valid session_id provided, generated: {session_id}")

    # Extract actor ID from request headers (custom header)
    actor_id = extract_actor_id(context)

    logger.info("[>] Finance Personal Assistant invoked with memory support")

    # Get user message from payload
    user_message = payload["prompt"]

    # Check for image in payload (vision preprocessing)
    image_base64 = payload.get("image_base64")
    if image_base64:
        logger.info("[VISION] Image detected in payload, analyzing...")

        try:
            # Automatic vision analysis (backend decides model, not frontend!)
            vision_result = analyze_image(image_base64=image_base64)

            logger.info(f"[VISION] Analysis complete: status={vision_result['status']}")

            # Inject vision context based on status
            if vision_result["status"] == "unknown":
                # Image not recognized as financial document
                user_message = f"""[Vision Analysis: Image not recognized as financial document]

{user_message}"""
                logger.info("[VISION] Image not recognized, context injected")

            elif vision_result["status"] == "success":
                # Financial document detected - inject structured data
                data_summary = format_vision_data(vision_result["data"])
                keywords_str = ", ".join(vision_result["keywords"])

                user_message = f"""[Vision Analysis: {vision_result["summary"]}
Keywords: {keywords_str}
{data_summary}]

{user_message}"""
                logger.info(
                    f"[VISION] Success - extracted {len(vision_result['data'])} fields"
                )

            elif vision_result["status"] == "error":
                # Vision API error - inject error context
                user_message = f"""[Vision Analysis: Failed - {vision_result["summary"]}]

{user_message}"""
                logger.warning(f"[VISION] Error: {vision_result['summary']}")

        except Exception as e:
            # Unexpected error in vision processing - fail gracefully
            logger.error(f"[VISION] Unexpected error: {e}", exc_info=True)
            user_message = f"""[Vision Analysis: System error during image processing]

{user_message}"""

    # Initialize memory
    region = get_region()
    memory_id = create_or_get_memory(region)

    # Configure LTM retrieval
    retrieval_config = {
        "finance-assistant/user/{actorId}/preferences": RetrievalConfig(
            top_k=5,
            relevance_score=0.7,
        ),
        "finance-assistant/user/{actorId}/facts": RetrievalConfig(
            top_k=10,
            relevance_score=0.5,
        ),
        "finance-assistant/user/{actorId}/summaries/{sessionId}": RetrievalConfig(
            top_k=3,
            relevance_score=0.6,
        ),
    }
    logger.info(
        "[*] LTM retrieval configured: 3 strategies (preferences, facts, summaries)"
    )

    # Create session manager
    try:
        session_manager = AgentCoreMemorySessionManager(
            agentcore_memory_config=AgentCoreMemoryConfig(
                memory_id=memory_id,
                session_id=session_id,
                actor_id=actor_id,
            ),
            retrieval_config=retrieval_config,
            region_name=region,
        )
        logger.info("[✓] Session manager created: STM + LTM enabled")
    except Exception as e:
        logger.error(f"[✗] Session manager creation failed: {type(e).__name__}")
        raise

    # Create orchestrator agent with memory
    orchestrator_agent = Agent(
        model=model,
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[budget_agent_tool, financial_analysis_agent_tool],
        conversation_manager=conversation_manager,
        session_manager=session_manager,
    )
    logger.info("[✓] Agent ready: Orchestrator with memory integration")

    # Stream response (user_message already set above, potentially with vision context)
    async for event in orchestrator_agent.stream_async(user_message):
        if "data" in event:
            yield event["data"]


if __name__ == "__main__":
    app.run()
