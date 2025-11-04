# Create AgentCore-compatible deployment file with streaming endpoint

from __future__ import annotations

import logging

from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import (
    AgentCoreMemoryConfig,
    RetrievalConfig,
)
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from budget_agent import FinancialReport, budget_agent
from config import (
    BedrockModelCatalog,
    get_bedrock_model,
    get_guardrail_config,
    get_region,
)
from financial_analysis_agent import financial_analysis_agent
from memory_config import FINANCE_MEMORY_CONFIG, RETRIEVAL_CONFIG, Memory
from strands import Agent, tool
from strands.agent.conversation_manager import SummarizingConversationManager
from utils.gateway import create_mcp_client
from utils.memory_retrieval import retrieve_and_inject_memories
from utils.session_manager import extract_session_context
from utils.vision_analyzer import analyze_image
from utils.vision_context import inject_vision_context

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


app = BedrockAgentCoreApp()
agent = Agent()

ORCHESTRATOR_PROMPT = """You are a comprehensive financial advisor orchestrator that coordinates between specialized financial agents to provide complete financial guidance.

Your specialized agents are:
1. **budget_agent_tool**: Generates comprehensive financial reports with budget breakdowns and recommendations. Use for creating budgets, analyzing spending patterns, and providing savings advice. Note: This tool generates reports but does NOT track or store transactions.
2. **financial_analysis_agent_tool**: Handles investment analysis, stock research, portfolio creation, and performance comparisons.

<memory_behavior>
You have access to conversation history and user profile information.
Use the user's name and previous topics naturally in responses.
When users share personal details, financial goals, or budget info, remember them for future conversations.
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

<session_welcome_message>
If the user is greeting you, just return a very concise message using user's context (if exists).
</session_welcome_message>

Guidelines for using your agents:
- Use **budget_agent_tool** for questions about: budgets, spending analysis, savings goals, debt management
- Use **financial_analysis_agent_tool** for questions about: stocks, investments, portfolios, market analysis, investment recommendations
- You can use both agents together for comprehensive financial planning
- Always provide a cohesive summary that combines insights from multiple agents when applicable
- Maintain a helpful, professional tone and include appropriate disclaimers about financial advice

When a user asks a question:
1. Determine which agent(s) are most appropriate
2. Send friendly status to the user to avoid waiting for the response (e.g., "Yes, I'm working on it...\n" or "I'm thinking...\n" or "Just a moment! I'm on it...\n")
3. Call the relevant agent(s) with focused queries
4. Synthesize the responses into a coherent, comprehensive answer
5. Provide actionable next steps when possible

<tone_and_language>
- Use a friendly, professional, and engaging tone and language.
- Be randomly iterative between explanatory, formal, and ultra concise responses.
- Prefer line breaks and short sentences over mid-term/long-term sentences.
</tone_and_language>

<structured_options_format>
Only apply this format if you are requesting or asking a list of follow-up questions.
At the end of your response, add an XML formatted list of very concise options.
The user can click on the options to send back to you.
IMPORTANT: Only add options at the end of your response.

E.g.
<options>
<option>What is my current balance?</option>
<option>What is my spending trend?</option>
</options>

</structured_options_format>
"""

# Initialize region at module load
region = get_region()

# Lazy initialization - memory created on first request (prevents race conditions)
_memory_instance = None


def get_memory() -> Memory:
    """Get or create memory instance (lazy initialization to prevent parallel creation)"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = Memory(region_name=region, config=FINANCE_MEMORY_CONFIG)
    return _memory_instance

# Add conversation management to maintain context
conversation_manager = SummarizingConversationManager(
    summary_ratio=0.3,  # Summarize 30% of messages when context reduction is needed
    preserve_recent_messages=5,  # Always keep 5 most recent messages
)

model = get_bedrock_model(
    framework="strands",
    model=BedrockModelCatalog.CLAUDE_SONNET_45,
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


@app.entrypoint
async def invoke(payload, context):
    """Your AI agent function with memory and vision support"""
    logger.info(f"[VISION DEBUG] Received payload keys: {list(payload.keys())}")
    logger.info(f"[VISION DEBUG] image_base64 in payload: {'image_base64' in payload}")
    if "image_base64" in payload:
        logger.info(
            f"[VISION DEBUG] image_base64 type: {type(payload['image_base64'])}"
        )
        logger.info(
            f"[VISION DEBUG] image_base64 length: {len(payload.get('image_base64', ''))} chars"
        )

    # Extract session and actor context from AgentCore Runtime
    # Pass payload to extract actor_id (works for both OAuth and IAM)
    session_ctx = extract_session_context(context, payload)
    session_id = session_ctx.session_id
    actor_id = session_ctx.actor_id

    logger.info("[>] Finance Personal Assistant invoked")
    logger.info(
        f"    Session: {session_id} {'(generated)' if session_ctx.is_generated_session else ''}"
    )
    logger.info(f"    Actor: {actor_id}")

    # Get user message from payload
    user_message = payload["prompt"]

    # Check for document upload (PDF or CSV)
    document_base64 = payload.get("document_base64")
    filename = payload.get("filename", "").lower()

    if document_base64 and filename:
        logger.info(f"[DOCUMENT] Document detected: {filename}")

        # Handle PDF: Convert to image and process with vision
        if filename.endswith(".pdf"):
            from utils.pdf_processor import pdf_first_page_to_image

            logger.info("[DOCUMENT] Converting PDF to image...")
            converted_image = pdf_first_page_to_image(document_base64)

            if converted_image:
                # Set as image_base64 for vision processing
                payload["image_base64"] = converted_image
                logger.info("[DOCUMENT] PDF converted successfully, will process with vision")
            else:
                logger.warning("[DOCUMENT] PDF conversion failed")
                user_message = "[Document Error: Could not process PDF file]\n\n" + user_message

        # Handle CSV: Convert to text and inject into message
        elif filename.endswith(".csv"):
            from utils.csv_processor import csv_to_text

            logger.info("[DOCUMENT] Converting CSV to text...")
            csv_text = csv_to_text(document_base64)

            if csv_text:
                # Inject CSV content directly into user message
                user_message = f"""[CSV File Data]
{csv_text}

User Query: {user_message}"""
                logger.info(f"[DOCUMENT] CSV processed: {len(csv_text)} characters")
            else:
                logger.warning("[DOCUMENT] CSV processing failed")
                user_message = "[Document Error: Could not process CSV file]\n\n" + user_message

    # Check for image in payload (vision preprocessing)
    image_base64 = payload.get("image_base64")
    vision_result = None

    if image_base64:
        logger.info("[VISION] Image detected in payload, analyzing...")
        try:
            vision_result = analyze_image(image_base64=image_base64)
            logger.info(f"[VISION] Analysis complete: status={vision_result['status']}")
        except Exception as e:
            logger.error(f"[VISION] Unexpected error: {e}", exc_info=True)
            vision_result = {
                "status": "error",
                "summary": "System error during image processing",
                "data": {},
                "keywords": [],
            }

    # Inject vision context (handles all status cases)
    user_message = inject_vision_context(user_message, vision_result)

    # ========================================================================
    # GUARDRAIL PRE-CHECK: Validate user input BEFORE agent processing
    # This prevents blocked content from contaminating conversation history
    # ========================================================================
    guardrail_config = get_guardrail_config()
    if guardrail_config:
        from utils.guardrail_sanitize import apply_guardrail_text

        logger.info("=" * 70)
        logger.info("[GUARDRAIL PRE-CHECK] Validating user input before processing")
        logger.info(f"  • Guardrail ID: {guardrail_config.get('guardrail_id', 'N/A')}")
        logger.info(f"  • Guardrail Version: {guardrail_config.get('guardrail_version', 'N/A')}")

        pre_check_result = apply_guardrail_text(
            text=user_message,
            guardrail_id=guardrail_config.get("guardrail_id"),
            guardrail_arn=guardrail_config.get("guardrail_arn"),
            guardrail_version=guardrail_config.get("guardrail_version", "1"),
            source="INPUT",
            region_name=get_region(),
        )

        if not pre_check_result["is_safe"]:
            # User input blocked - return intervention message WITHOUT invoking agent
            logger.warning("=" * 70)
            logger.warning("[GUARDRAIL PRE-CHECK] ⚠️  User input BLOCKED")
            logger.warning(f"  • Actor ID: {actor_id}")
            logger.warning(f"  • Session ID: {session_id}")
            logger.warning(f"  • Action: {pre_check_result.get('action', 'UNKNOWN')}")
            if pre_check_result.get("action_reason"):
                logger.warning(f"  • Reason: {pre_check_result['action_reason']}")
            logger.warning("  • Agent invocation SKIPPED (prevents conversation history contamination)")
            logger.warning("=" * 70)

            # Return intervention message and stop (no agent invocation)
            # Use "final" type so Streamlit displays the message
            yield {
                "type": "final",
                "result": "I can't assist with that request.",
                "finish_reason": "guardrail_intervened",
            }
            return

        logger.info("[GUARDRAIL PRE-CHECK] ✅ User input ALLOWED - proceeding to agent")
        logger.info("=" * 70)

    # Get or create memory (lazy initialization)
    memory = get_memory()

    # Retrieve and inject LTM memories into user message
    user_message = retrieve_and_inject_memories(
        memory_client=memory._client,
        memory_id=memory.memory_id,
        actor_id=actor_id,
        user_message=user_message,
        namespaces={
            "finance-assistant/user/{actorId}/preferences": 5,
            "finance-assistant/user/{actorId}/facts": 10,
        },
    )

    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=AgentCoreMemoryConfig(
            memory_id=memory.memory_id,
            session_id=session_id,
            actor_id=actor_id,
        ),
        retrieval_config={
            namespace: RetrievalConfig(**config)
            for namespace, config in RETRIEVAL_CONFIG.items()
        },
        region_name=region,
    )

    # Initialize MCP client for Gateway tools
    mcp_client = create_mcp_client()

    # Build agent tools list (embedded tools + Gateway tools)
    agent_tools = [budget_agent_tool, financial_analysis_agent_tool]
    if mcp_client:
        agent_tools.append(mcp_client)

    # Create orchestrator agent
    orchestrator_agent = Agent(
        model=model,
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=agent_tools,  # All tools (embedded + Gateway)
        conversation_manager=conversation_manager,
        session_manager=session_manager,
    )

    logger.info(f"Agent invoked for session {session_id}, actor {actor_id}")

    async for event in orchestrator_agent.stream_async(user_message):
        if "data" in event:
            yield event["data"]


if __name__ == "__main__":
    app.run()
