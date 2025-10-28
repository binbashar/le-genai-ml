# Export financial analysis agent to standalone Python file

from typing import List

import yfinance as yf
from config import BedrockModelCatalog, get_bedrock_model
from strands import Agent, tool

# Financial Analysis Agent System Prompt
FINANCIAL_ANALYSIS_PROMPT = """You are a specialized financial analysis agent focused on investment research and portfolio recommendations. Your role is to:

1. Research and analyze stock performance data
2. Create diversified investment portfolios
3. Provide data-driven investment recommendations

You do not provide specific investment advice but rather present analytical data to help users make informed decisions. Always include disclaimers about market risks and the importance of consulting financial advisors."""

# One-liner: Create Strands BedrockModelConverse
model = get_bedrock_model(
    model=BedrockModelCatalog.CLAUDE_SONNET_45,
    framework="strands",
)


# Tool 1: Get Stock Analysis
@tool
def get_stock_analysis(symbol: str) -> str:
    """Get comprehensive analysis for a specific stock symbol."""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="1y")

        # Calculate key metrics
        current_price = hist["Close"].iloc[-1]
        year_high = hist["High"].max()
        year_low = hist["Low"].min()
        avg_volume = hist["Volume"].mean()
        price_change = (
            (current_price - hist["Close"].iloc[0]) / hist["Close"].iloc[0]
        ) * 100

        return f"""
📊 Stock Analysis for {symbol.upper()}:
• Current Price: ${current_price:.2f}
• 52-Week High: ${year_high:.2f}
• 52-Week Low: ${year_low:.2f}
• Year-to-Date Change: {price_change:.2f}%
• Average Daily Volume: {avg_volume:,.0f} shares
• Company: {info.get("longName", "N/A")}
• Sector: {info.get("sector", "N/A")}
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
    tools=[get_stock_analysis, create_diversified_portfolio, compare_stock_performance],
    callback_handler=None,
)

if __name__ == "__main__":
    # Test the Financial Analysis Agent
    response = financial_analysis_agent(
        "Create a moderate risk portfolio for $10,000 and analyze Apple stock"
    )
    print(response)
