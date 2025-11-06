# Workshop Prompts - Example Queries

Copy-paste ready example queries for testing agents during the workshop.

## Table of Contents

1. [Basic Budget Queries](#basic-budget-queries)
2. [Financial Analysis Queries](#financial-analysis-queries)
3. [Multi-Agent Orchestration](#multi-agent-orchestration)
4. [Vision Analysis (Receipts/Invoices)](#vision-analysis-receiptsinvoices)
5. [Memory & Context Retention](#memory--context-retention)
6. [Advanced Scenarios](#advanced-scenarios)
7. [Error Testing](#error-testing)

---

## Basic Budget Queries

### Simple Budget Request
```
Can you help me create a simple monthly budget? My income is $5,000 per month.
```

### Detailed Budget with Categories
```
I need help creating a budget. Here are my details:
- Monthly income: $6,500
- Rent: $1,800
- Utilities: $200
- Groceries: $500
- Transportation: $300
- I want to save at least 20% of my income
```

### Budget Review
```
I spent $450 on dining out this month. My budget was $300. Can you help me understand if this is problematic and suggest adjustments?
```

### Expense Categorization
```
I have these expenses this month:
- $1,200 at Target
- $80 at Whole Foods
- $150 at Shell gas station
- $45 at Netflix
- $2,000 mortgage payment

Can you categorize these and tell me if I'm overspending in any category?
```

---

## Financial Analysis Queries

### Investment Advice
```
I have $10,000 to invest. I'm 30 years old with moderate risk tolerance. What investment strategy do you recommend?
```

### Retirement Planning
```
I'm 35 years old and want to retire at 65. I currently have $50,000 in my 401(k) and can contribute $1,000 per month. Will I have enough for retirement?
```

### Savings Goals
```
I want to save $30,000 for a down payment on a house in 3 years. How much should I save each month, and what's the best way to invest this money?
```

### Debt Management
```
I have:
- Credit card debt: $8,000 at 18% APR
- Student loan: $25,000 at 5% APR
- Car loan: $15,000 at 4% APR

Which debt should I prioritize paying off first?
```

---

## Multi-Agent Orchestration

These prompts require coordination between budget and financial analysis agents.

### Comprehensive Financial Plan
```
I need a complete financial plan. Here's my situation:
- Annual income: $85,000
- Monthly expenses: ~$4,000
- Current savings: $15,000
- Credit card debt: $5,000 at 16% APR
- Goals: Save for retirement and buy a house in 5 years

Can you help me create a budget, recommend investment strategies, and prioritize my debt payoff?
```

### Budget with Investment Allocation
```
I have a monthly income of $7,000 and expenses of $4,500. I want to invest the remaining $2,500. Where should I allocate this money for long-term growth?
```

### Emergency Fund Planning
```
I don't have an emergency fund yet. Can you help me create a budget that allows me to build a 6-month emergency fund while still investing for retirement? My monthly income is $5,500 and expenses are $3,800.
```

---

## Vision Analysis (Receipts/Invoices)

These prompts work with uploaded images of financial documents.

### Receipt Analysis
```
[Upload receipt image]
Can you analyze this receipt and tell me what I purchased, the total amount, and which budget category this should fall under?
```

### Invoice Processing
```
[Upload invoice image]
Please extract the invoice details including merchant, date, items, subtotal, tax, and total. Add this to my monthly expenses.
```

### Multiple Receipt Comparison
```
[Upload 3 grocery receipts]
I've uploaded my grocery receipts from the past 3 weeks. Can you analyze my spending pattern and suggest ways to reduce my grocery costs?
```

### Receipt with Budget Check
```
[Upload restaurant receipt]
I just had dinner and here's the receipt. My dining budget for this month is $400 and I've already spent $320. Should I be concerned?
```

---

## Memory & Context Retention

These prompts test the agent's ability to remember context across conversations.

### Set Preferences (First Message)
```
Hi! My name is Sarah. I'm 28 years old, work as a software engineer, and my financial goals are:
1. Save for a house down payment ($50,000 in 3 years)
2. Build retirement savings
3. Pay off my student loans ($30,000)

I'm risk-averse and prefer conservative investments.
```

### Reference Previous Context (Second Message)
```
Based on my goals we discussed earlier, what should be my top financial priority this month?
```

### Update Preferences (Third Message)
```
I just got a raise! My income increased from $6,000 to $7,000 per month. How should I adjust my budget and savings strategy?
```

### Memory Recall Test (Fourth Message)
```
Remind me what my financial goals are and how much I need to save for my house down payment.
```

---

## Advanced Scenarios

### Tax-Optimized Investing
```
I'm in the 24% tax bracket and want to invest $2,000 per month. Should I prioritize my 401(k), Roth IRA, or taxable brokerage account? Explain the tax implications.
```

### College Savings Plan
```
I have a newborn and want to start saving for college. I can invest $500 per month. Should I use a 529 plan, and what investment allocation do you recommend?
```

### Side Hustle Budget Integration
```
I'm starting a freelance business alongside my full-time job. I expect to earn $1,500/month from freelancing but will have expenses like equipment ($500 one-time), software subscriptions ($100/month), and taxes (~30%). How should I budget for this?
```

### Market Downturn Scenario
```
The stock market just dropped 20%. I have $100,000 invested in index funds and I'm 45 years old. Should I sell, hold, or buy more? I'm planning to retire at 65.
```

---

## Error Testing

Test error handling and edge cases.

### Invalid Numbers
```
I want to invest -$5,000 per month. [Should handle gracefully]
```

### Unrealistic Budget
```
My income is $3,000 per month but my expenses are $8,000. Can you help me create a budget? [Should identify the problem]
```

### Missing Critical Information
```
Can you create a retirement plan for me? [Should ask clarifying questions]
```

### Contradictory Goals
```
I want to pay off all my debt this year, save $50,000 for a house, and invest $2,000 per month for retirement. My income is $4,000 per month. [Should explain this isn't feasible]
```

---

## Progressive Complexity Examples

### Beginner Level
Start with simple, single-topic queries:
```
What's a budget?
How much should I save each month?
Is $200 a lot to spend on groceries?
```

### Intermediate Level
Multi-step queries with some context:
```
I earn $5,000/month and spend $3,500. I have $10,000 in credit card debt. What should I do first: save an emergency fund or pay off debt?
```

### Advanced Level
Complex scenarios requiring orchestration:
```
I'm 40 years old with $200,000 in retirement savings, earning $120,000/year. I have 2 kids (ages 5 and 8) and want to send them to college, retire at 60, and buy a vacation home in 10 years. My current savings rate is 15%. Create a comprehensive financial plan covering budgeting, investment allocation, tax optimization, and timeline for each goal.
```

---

## Streamlit Demo Flow

### Recommended Demo Sequence

**Step 1: Introduction**
```
Hi! I'm interested in improving my financial health. Can you help me?
```

**Step 2: Set Context**
```
I'm 32 years old, earn $6,000/month, and my main goal is to buy a house in 3 years. I need to save $40,000 for the down payment.
```

**Step 3: Budget Creation**
```
Here are my monthly expenses:
- Rent: $1,500
- Car payment: $400
- Insurance: $200
- Groceries: $500
- Dining out: $300
- Entertainment: $200
- Utilities: $150

Can you help me create a budget that maximizes my house savings?
```

**Step 4: Investment Strategy**
```
Where should I invest my monthly savings to reach my $40,000 goal in 3 years? I prefer low-risk options since I need the money soon.
```

**Step 5: Upload Receipt (if vision enabled)**
```
[Upload a receipt]
I just made this purchase. Can you tell me if it fits within my budget?
```

**Step 6: Memory Test**
```
What was my main financial goal again, and am I on track to achieve it?
```

---

## Workshop Testing Checklist

Use these prompts to validate agent functionality:

### ✅ Basic Functionality
- [ ] Simple budget request
- [ ] Expense categorization
- [ ] Savings calculation

### ✅ Agent Orchestration
- [ ] Query requiring both budget and investment advice
- [ ] Multi-step financial planning

### ✅ Vision Capabilities
- [ ] Receipt upload and analysis
- [ ] Invoice data extraction

### ✅ Memory & Context
- [ ] Set user preferences
- [ ] Reference previous conversation
- [ ] Update stored information

### ✅ Error Handling
- [ ] Invalid input handling
- [ ] Missing information prompts
- [ ] Unrealistic scenario detection

---

## Custom Prompt Templates

### Template: Budget Creation
```
I need help creating a budget. Here are my details:
- Monthly income: $[AMOUNT]
- Fixed expenses: [LIST]
- Variable expenses: [LIST]
- Financial goals: [GOALS]
- Savings target: [PERCENTAGE or AMOUNT]
```

### Template: Investment Planning
```
I have $[AMOUNT] to invest with [low/moderate/high] risk tolerance.
- Age: [AGE]
- Investment timeline: [YEARS]
- Goals: [RETIREMENT/HOUSE/OTHER]

What investment strategy do you recommend?
```

### Template: Debt Payoff
```
I have the following debts:
- [DEBT 1]: $[AMOUNT] at [APR]%
- [DEBT 2]: $[AMOUNT] at [APR]%

I can pay $[AMOUNT] extra per month toward debt. What's the optimal payoff strategy?
```

---

## Tips for Workshop Attendees

1. **Start simple**: Use beginner prompts first to understand agent behavior
2. **Build context**: Set preferences before asking complex questions
3. **Test memory**: Reference previous messages to validate context retention
4. **Upload images**: Try vision analysis with real receipts/invoices
5. **Experiment**: Modify prompts to see how the agent adapts
6. **Test errors**: Try invalid inputs to see error handling
7. **Multi-turn conversations**: Have natural back-and-forth dialogs

---

## Next Steps

After testing with these prompts:
1. Review agent responses in Streamlit UI
2. Check CloudWatch Logs for tool execution details
3. Examine memory storage in AgentCore Memory
4. Monitor token usage and response times
5. Iterate on prompts based on results

**Happy testing!** 🚀

---

**Last Updated:** 2025-01-06
