"""
MCP-compatible Lambda function for budget calculation.
Implements 50/30/20 budget rule.

This tool is exposed via AgentCore Gateway and follows the Model Context Protocol (MCP)
response format for seamless integration with Strands agents.
"""
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """
    Lambda handler for calculate_budget tool.

    Supports multiple invocation patterns:
    - Gateway MCP: {'monthly_income': 5000}
    - Direct/nested: {'arguments': {'monthly_income': 5000}}

    Args:
        event: Tool arguments (direct properties or nested under 'arguments')
        context: Lambda context (with bedrockAgentCore* fields when via Gateway)

    Returns:
        MCP-compatible response with content array
        Example: {'content': [{'type': 'text', 'text': 'Budget breakdown...'}]}
    """
    try:
        # Log incoming event for debugging
        logger.info(f"Received event: {json.dumps(event)}")

        # Extract tool arguments - handle multiple invocation patterns:
        # 1. Gateway MCP: {'monthly_income': 5000}
        # 2. Direct invocation: {'arguments': {'monthly_income': 5000}}
        # 3. Other patterns: check both locations
        if 'monthly_income' in event:
            # Gateway MCP format (direct properties)
            monthly_income = event.get('monthly_income')
        elif 'arguments' in event:
            # Nested arguments format
            monthly_income = event.get('arguments', {}).get('monthly_income')
        else:
            monthly_income = None

        # Validation
        if monthly_income is None:
            raise ValueError("monthly_income is required")

        if not isinstance(monthly_income, (int, float)):
            raise ValueError("monthly_income must be a number")

        if monthly_income < 0:
            raise ValueError("monthly_income must be non-negative")

        # Calculate budget
        result = calculate_budget(monthly_income)

        logger.info(f"Calculation successful for income: ${monthly_income}")

        # Return in MCP format
        # Gateway expects: {'content': [{'type': 'text', 'text': '...'}]}
        return {
            'content': [
                {
                    'type': 'text',
                    'text': result
                }
            ]
        }

    except ValueError as e:
        # Validation errors return 400 Bad Request via Gateway
        logger.error(f"Validation error: {e}")
        raise ValueError(str(e))

    except Exception as e:
        # Unexpected errors return 500 Internal Server Error via Gateway
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise RuntimeError(f"Budget calculation failed: {str(e)}")


def calculate_budget(monthly_income: float) -> str:
    """
    Calculate 50/30/20 budget breakdown.

    Rule:
    - 50% Needs (housing, food, utilities, transportation)
    - 30% Wants (entertainment, dining out, hobbies)
    - 20% Savings (emergency fund, investments, debt repayment)

    Args:
        monthly_income: Monthly income amount in dollars

    Returns:
        Formatted budget breakdown string with emoji icons
    """
    needs = monthly_income * 0.50
    wants = monthly_income * 0.30
    savings = monthly_income * 0.20

    return (
        f"💰 Budget for ${monthly_income:,.0f}/month:\n"
        f"• Needs: ${needs:,.0f} (50%)\n"
        f"• Wants: ${wants:,.0f} (30%)\n"
        f"• Savings: ${savings:,.0f} (20%)"
    )
