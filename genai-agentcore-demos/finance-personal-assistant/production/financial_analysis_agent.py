# Export financial analysis agent to standalone Python file

from typing import List

import yfinance as yf
from config import BedrockModelCatalog, get_bedrock_model
from strands import Agent, tool
from strands_tools.browser import AgentCoreBrowser

# Financial Analysis Agent System Prompt
FINANCIAL_ANALYSIS_PROMPT = """You are an elite financial portfolio manager with decades of institutional investment experience. Your expertise includes quantitative analysis, modern portfolio theory, sector rotation strategies, and risk-adjusted return optimization.

## Core Responsibilities

**Portfolio Construction**: Create sophisticated, data-driven investment portfolios using real market data, fundamental analysis, and modern portfolio theory principles. Always analyze actual stock metrics (P/E ratios, dividend yields, beta, sector exposure) rather than using generic templates.

**Client Discovery**: Before constructing any portfolio, gather comprehensive information about the client's investment profile:
- Investment time horizon (short: <3 years, medium: 3-10 years, long: 10+ years)
- Risk tolerance (conservative, moderate, aggressive)
- Investment goals (growth, income, capital preservation, balanced)
- Current portfolio holdings (if any)
- Sector preferences or restrictions
- ESG (Environmental, Social, Governance) considerations

**Professional Standards**: Communicate with precision and authority. Use quantitative metrics to support recommendations. Default to action—provide specific allocations with clear reasoning rather than vague suggestions. Frame recommendations as implementable portfolios with exact percentage allocations.

**Research Excellence**: When analyzing stocks, examine fundamental metrics including valuation ratios, growth rates, profitability margins, competitive positioning, and sector trends. Compare stocks within their peer groups.

**Risk Management**: Implement diversification across sectors, market capitalizations, and investment styles. Calculate and communicate expected volatility, maximum drawdown scenarios, and correlation risks.

## Output Format

Provide recommendations in structured formats with:
- Specific ticker symbols and percentage allocations
- Quantitative justification for each holding (P/E, dividend yield, beta, etc.)
- Expected risk/return profile
- Rebalancing guidance

## Critical Compliance Note

This analysis is for educational and informational purposes only. It does not constitute personalized investment advice. Markets involve substantial risk of loss. Clients should consult licensed financial advisors before making investment decisions, especially regarding suitability for their specific financial situation.

## Reasoning Approach

Before recommending portfolios, reflect on:
1. Does this allocation match the client's stated risk tolerance and time horizon?
2. Are the stocks selected based on current fundamentals, or am I relying on outdated assumptions?
3. Is the portfolio properly diversified across sectors and market caps?
4. Have I considered current market conditions and valuations?

Default to thoroughness. Gather all necessary information before constructing portfolios."""

# One-liner: Create Strands BedrockModelConverse
# Using Claude Sonnet 4.5 for superior reasoning and analysis capabilities
model = get_bedrock_model(
    model=BedrockModelCatalog.CLAUDE_HAIKU_45,
    framework="strands",
)

# Initialize AgentCore Browser for web research
browser_tool = AgentCoreBrowser(region="us-west-2")


# Tool 1: Get Comprehensive Stock Fundamentals
@tool
def get_stock_analysis(symbol: str) -> str:
    """Get comprehensive fundamental and technical analysis for a specific stock symbol including valuation metrics, profitability, growth rates, and risk metrics."""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="1y")

        # Price and performance metrics
        current_price = hist["Close"].iloc[-1]
        year_high = hist["High"].max()
        year_low = hist["Low"].min()
        avg_volume = hist["Volume"].mean()
        price_change = (
            (current_price - hist["Close"].iloc[0]) / hist["Close"].iloc[0]
        ) * 100

        # Fundamental metrics
        pe_ratio = info.get("forwardPE", info.get("trailingPE", "N/A"))
        pb_ratio = info.get("priceToBook", "N/A")
        dividend_yield = info.get("dividendYield", 0)
        if isinstance(dividend_yield, (int, float)) and dividend_yield > 0:
            dividend_yield_pct = dividend_yield * 100
        else:
            dividend_yield_pct = "N/A"

        # Growth and profitability
        revenue_growth = info.get("revenueGrowth", "N/A")
        if isinstance(revenue_growth, (int, float)):
            revenue_growth = f"{revenue_growth * 100:.1f}%"

        profit_margins = info.get("profitMargins", "N/A")
        if isinstance(profit_margins, (int, float)):
            profit_margins = f"{profit_margins * 100:.1f}%"

        # Risk metrics
        beta = info.get("beta", "N/A")
        if isinstance(beta, (int, float)):
            beta = f"{beta:.2f}"

        # Market cap categorization
        market_cap = info.get("marketCap", 0)
        if market_cap > 200_000_000_000:
            cap_category = "Mega Cap"
        elif market_cap > 10_000_000_000:
            cap_category = "Large Cap"
        elif market_cap > 2_000_000_000:
            cap_category = "Mid Cap"
        else:
            cap_category = "Small Cap"

        return f"""
📊 FUNDAMENTAL ANALYSIS: {symbol.upper()}

COMPANY PROFILE
• Name: {info.get("longName", "N/A")}
• Sector: {info.get("sector", "N/A")}
• Industry: {info.get("industry", "N/A")}
• Market Cap: ${market_cap:,.0f} ({cap_category})

VALUATION METRICS
• Current Price: ${current_price:.2f}
• P/E Ratio (Forward): {pe_ratio if pe_ratio != "N/A" else "N/A"}
• Price/Book Ratio: {pb_ratio if pb_ratio != "N/A" else "N/A"}
• Dividend Yield: {dividend_yield_pct if dividend_yield_pct != "N/A" else "N/A"}%

PERFORMANCE & GROWTH
• YTD Price Change: {price_change:+.2f}%
• 52-Week Range: ${year_low:.2f} - ${year_high:.2f}
• Revenue Growth: {revenue_growth}
• Profit Margin: {profit_margins}

RISK METRICS
• Beta (Market Sensitivity): {beta}
• Avg Daily Volume: {avg_volume:,.0f} shares

ANALYST CONSENSUS
• Target Price: ${info.get("targetMeanPrice", "N/A")}
• Recommendation: {info.get("recommendationKey", "N/A").upper() if info.get("recommendationKey") else "N/A"}
"""
    except Exception as e:
        return f"❌ Unable to retrieve data for {symbol}: {str(e)}"


# Tool 2: Create Diversified Portfolio
@tool
def create_diversified_portfolio(risk_level: str, investment_amount: float) -> str:
    """Create a diversified portfolio based on risk level (conservative, moderate, aggressive) and investment amount."""

    portfolios = {
        "conservative": {
            "stocks": ["AAPL", "MSFT", "JNJ", "PG", "KO"],
            "weights": [0.25, 0.25, 0.20, 0.15, 0.15],
            "description": "Focus on large-cap, dividend-paying stocks",
        },
        "moderate": {
            "stocks": ["AAPL", "GOOGL", "AMZN", "TSLA", "NVDA"],
            "weights": [0.30, 0.25, 0.20, 0.15, 0.10],
            "description": "Balanced mix of growth and stability",
        },
        "aggressive": {
            "stocks": ["TSLA", "NVDA", "AMZN", "GOOGL", "META"],
            "weights": [0.30, 0.25, 0.20, 0.15, 0.10],
            "description": "High-growth potential stocks",
        },
    }

    if risk_level.lower() not in portfolios:
        return "❌ Risk level must be: conservative, moderate, or aggressive"

    portfolio = portfolios[risk_level.lower()]

    result = f"""
🎯 {risk_level.upper()} Portfolio Recommendation (${investment_amount:,.0f}):
{portfolio["description"]}

Portfolio Allocation:
"""

    for stock, weight in zip(portfolio["stocks"], portfolio["weights"]):
        allocation = investment_amount * weight
        result += f"• {stock}: {weight * 100:.0f}% (${allocation:,.0f})\n"

    result += "\n⚠️ Disclaimer: This is for educational purposes only. Consult a financial advisor before investing."
    return result


# Tool 3: Compare Stock Performance
@tool
def compare_stock_performance(symbols: List[str], period: str = "1y") -> str:
    """Compare performance of multiple stocks over a specified period (1y, 6m, 3m, 1m)."""
    if len(symbols) > 5:
        return "❌ Please limit comparison to 5 stocks maximum"

    try:
        performance_data = {}

        for symbol in symbols:
            stock = yf.Ticker(symbol)
            hist = stock.history(period=period)
            if not hist.empty:
                start_price = hist["Close"].iloc[0]
                end_price = hist["Close"].iloc[-1]
                performance = ((end_price - start_price) / start_price) * 100
                performance_data[symbol] = performance

        result = f"📈 Stock Performance Comparison ({period}):\n"
        sorted_stocks = sorted(
            performance_data.items(), key=lambda x: x[1], reverse=True
        )

        for stock, performance in sorted_stocks:
            result += f"• {stock}: {performance:+.2f}%\n"

        return result

    except Exception as e:
        return f"❌ Error comparing stocks: {str(e)}"


# Create the Financial Analysis Agent
financial_analysis_agent = Agent(
    model=model,
    system_prompt=FINANCIAL_ANALYSIS_PROMPT,
    tools=[get_stock_analysis, create_diversified_portfolio, compare_stock_performance, browser_tool.browser],
    callback_handler=None,
)

if __name__ == "__main__":
    # Test the Financial Analysis Agent
    response = financial_analysis_agent(
        "Search on Bloomberg for the latest news on Apple"
    )
    print(response)
