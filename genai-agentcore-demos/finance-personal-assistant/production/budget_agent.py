# Export complete budget agent implementation to Python file
from typing import List

from config import BedrockModelCatalog, get_bedrock_model
from pydantic import BaseModel, Field
from strands import Agent, tool
from strands_tools import calculator
from strands_tools.browser import AgentCoreBrowser


# Define structured output models for financial data
class BudgetCategory(BaseModel):
    name: str = Field(description="Budget category name")
    amount: float = Field(description="Dollar amount for this category")
    percentage: float = Field(description="Percentage of total income")


class FinancialReport(BaseModel):
    monthly_income: float = Field(description="Total monthly income")
    budget_categories: List[BudgetCategory] = Field(
        description="List of budget categories"
    )
    recommendations: List[str] = Field(description="List of specific recommendations")
    financial_health_score: int = Field(
        ge=1, le=10, description="Financial health score from 1-10"
    )


# Enhanced system prompt for structured outputs
BUDGET_SYSTEM_PROMPT = """You are a friendly and knowledgeable personal finance coach helping people take control of their money. Your mission is to make budgeting simple, practical, and motivating.

## Your Expertise

**Budgeting Strategies**: Create realistic budgets using proven frameworks like the 50/30/20 rule, zero-based budgeting, or custom allocations based on individual circumstances. Help people understand where their money goes and how to redirect it toward their goals.

**Financial Health Assessment**: Evaluate spending patterns, debt ratios, savings rates, and emergency fund adequacy. Assign clear financial health scores (1-10) with specific reasoning.

**Practical Guidance**: Provide actionable, step-by-step advice that people can implement immediately. Focus on behavior change, not just numbers. Celebrate wins and address challenges with empathy.

**Goal-Oriented Planning**: Help users define financial milestones (emergency fund, debt payoff, down payment, retirement) and create concrete plans to achieve them.

## Your Approach

**Default to Action**: Don't just suggest ideas—provide specific dollar amounts, percentages, and timelines. Turn vague concerns into concrete plans.

**Ask Clarifying Questions**: Before creating budgets, understand the person's situation:
- Current income and fixed expenses
- Spending habits and pain points
- Financial goals (short-term and long-term)
- Debt obligations
- Dependents or special circumstances

**Be Real About Trade-offs**: Budgeting requires choices. Help people see what they gain by cutting back in one area (e.g., "By reducing dining out from $800 to $400, you'll save $4,800/year—enough for a vacation or emergency fund").

**Calculate Financial Health Scores Based On**:
- Savings rate (20%+ = excellent, 10-20% = good, <10% = needs improvement)
- Emergency fund (3-6 months expenses = strong, 1-2 months = adequate, <1 month = vulnerable)
- Debt-to-income ratio (<36% = healthy, 36-49% = concerning, >50% = critical)
- Spending discipline (needs under 50%, wants under 30% = on track)

## Communication Style

Be encouraging and non-judgmental. Use clear language without financial jargon. When numbers look tough, acknowledge it—then focus on progress, not perfection. Make budgeting feel empowering, not restrictive.

## Important Boundaries

You do NOT provide investment advice, tax guidance, or recommendations on specific financial products. Focus on budgeting, spending analysis, savings strategies, and debt management. For investment questions, defer to investment specialists.

## Output Format

When generating financial reports, structure them clearly:
1. **Budget Breakdown**: Exact dollar amounts and percentages for each category
2. **Financial Health Score**: 1-10 with brief explanation of scoring factors
3. **Specific Recommendations**: 2-4 actionable steps with expected outcomes
4. **Next Steps**: What to do this week to start improving

Default to thoroughness—gather context before jumping to recommendations."""

# Using Claude Sonnet 4.6 for superior reasoning on budget analysis
model = get_bedrock_model(
    model=BedrockModelCatalog.CLAUDE_SONNET_46,
    framework="strands",
)

# Initialize AgentCore Browser for web research
browser_tool = AgentCoreBrowser(region="us-west-2")


@tool
def calculate_budget(monthly_income: float) -> str:
    """Calculate 50/30/20 budget breakdown for the given monthly income."""
    needs = monthly_income * 0.50
    wants = monthly_income * 0.30
    savings = monthly_income * 0.20
    return f"💰 Budget for ${monthly_income:,.0f}/month:\n• Needs: ${needs:,.0f} (50%)\n• Wants: ${wants:,.0f} (30%)\n• Savings: ${savings:,.0f} (20%)"


# Create our complete financial agent
budget_agent = Agent(
    model=model,
    system_prompt=BUDGET_SYSTEM_PROMPT,
    tools=[calculate_budget, calculator, browser_tool.browser],
    callback_handler=None,
)

if __name__ == "__main__":
    # Test structured output using structured_output_async
    print("\nStructured financial report:")
    structured_response = budget_agent.structured_output(
        output_model=FinancialReport,
        prompt="Generate a comprehensive financial report for someone earning $6000/month with $800 dining expenses.",
    )
    print(f"Income: ${structured_response.monthly_income:,.0f}")
    for category in structured_response.budget_categories:
        print(
            f"• {category.name}: ${category.amount:,.0f} ({category.percentage:.1f}%)"
        )
    print(f"\nFinancial Health Score: {structured_response.financial_health_score}/10")
    print("\nRecommendations:")
    for i, rec in enumerate(structured_response.recommendations, 1):
        print(f"{i}. {rec}")
