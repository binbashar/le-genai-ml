# Instructor Guide - AgentCore Workshop

**Workshop Title:** Building Multi-Agent Financial Advisory Systems with AWS Bedrock AgentCore
**Duration:** 90-120 minutes
**Level:** Intermediate (requires basic AWS and Python knowledge)
**Format:** Hands-on workshop with live coding

---

## Table of Contents

1. [Workshop Overview](#workshop-overview)
2. [Preparation Checklist](#preparation-checklist)
3. [Presentation Flow](#presentation-flow)
4. [Timing & Pacing](#timing--pacing)
5. [Talking Points by Section](#talking-points-by-section)
6. [Common Questions & Answers](#common-questions--answers)
7. [Troubleshooting During Workshop](#troubleshooting-during-workshop)
8. [Backup Plans](#backup-plans)
9. [Post-Workshop Resources](#post-workshop-resources)

---

## Workshop Overview

### Learning Objectives

By the end of this workshop, attendees will be able to:
1. **Understand** multi-agent orchestration patterns using Strands framework
2. **Build** specialized agents (budget planning, investment analysis)
3. **Deploy** agents to AWS Bedrock AgentCore Runtime
4. **Integrate** OAuth2/Cognito authentication
5. **Test** deployed agents via Streamlit UI with real-time streaming

### Workshop Architecture

```
Lab 1: Single Agent (Budget Assistant)
  ↓
Lab 2: Multi-Agent Orchestration (Budget + Investment)
  ↓
Lab 3: Deploy to AWS AgentCore Runtime
  ↓
Demo: Interactive Streamlit UI
```

### Target Audience

- **Software engineers** building AI applications
- **Solution architects** designing agentic systems
- **ML engineers** exploring production deployment patterns
- **Assumes familiarity with:** AWS basics, Python, APIs, Docker concepts

---

## Preparation Checklist

### One Week Before Workshop

- [ ] **Configure AWS access for participants (CRITICAL)**:
  - **Recommended:** Create IAM users with access keys - See [AWS_SETUP.md - For Administrators](./AWS_SETUP.md#for-workshop-administrators-creating-iam-users)
    - Fast setup (2 minutes per user)
    - No organizational dependencies
    - Works reliably during workshops
  - **Alternative (NOT recommended):** AWS SSO - Only if organization already has IAM Identity Center fully configured
  - Distribute access keys securely to participants before workshop day
- [ ] **Test complete workshop flow** in clean AWS account
- [ ] **Record backup demo** of entire system working (in case of live failures)
- [ ] **Prepare demo users** in `.demo_users.json` with memorable passwords
- [ ] **Enable Bedrock model access** in demo AWS account (all Nova + Claude models)
- [ ] **Verify CDK bootstrap** completed in demo account
- [ ] **Create workshop Slack channel** (or communication method) for attendee support

### One Day Before Workshop

- [ ] **Deploy finance assistant** to your demo account (`cd production && ./launch.sh`)
- [ ] **Test Streamlit UI** connects and streams correctly (`./demo.sh`)
- [ ] **Verify health checks** pass (`./health.sh`)
- [ ] **Print emergency cheat sheet** (deployment commands, common errors)
- [ ] **Test screen sharing** and zoom/presentation setup
- [ ] **Prepare backup AWS account** (in case primary account has issues)

### One Hour Before Workshop

- [ ] **Open all terminal windows** (1 for root, 1 for production, 1 for UI)
- [ ] **Test AWS credentials** (`aws sts get-caller-identity`)
- [ ] **Clear memory** for clean demo (`uv run reset_memory.py`)
- [ ] **Open all required files** in IDE (main.py, budget_agent.py, config.py)
- [ ] **Start screen recording** (for post-workshop reference)
- [ ] **Have TROUBLESHOOTING.md** open in browser tab

### Materials Checklist

- [ ] **Presentation slides** (architecture diagrams, workshop flow)
- [ ] **Code snippets** ready to copy-paste (from workshop_prompts.md)
- [ ] **Backup demo recording** (in case live demo fails)
- [ ] **Emergency contact** (AWS support, colleague who can help)

---

## Presentation Flow

### Introduction (10 minutes)

**Slide 1: Welcome**
- Workshop title, your name, role
- Logistics: duration, breaks, Q&A format
- Communication channel (Slack, chat)

**Slide 2: Learning Objectives**
- What attendees will build today
- Show final demo video (2-minute preview)

**Slide 3: Prerequisites Check**
- "Has everyone run `./quickstart.sh`?"
- Quick poll: Who has AWS credentials working?
- Share troubleshooting link: `TROUBLESHOOTING.md`

**Slide 4: Architecture Overview**
- Draw multi-agent architecture diagram
- Explain orchestrator pattern
- Show service discovery via SSM

---

### Lab 1: Budget Assistant Agent (30 minutes)

**⏱️ 00:10 - 00:40**

#### Introduction (5 min)

**Key concepts to cover:**
- What is Strands? (Agent framework for AWS Bedrock)
- Tools vs Agents vs Orchestrators
- Structured outputs with Pydantic

**Live demo:**
```python
# Show budget_agent.py structure
# Highlight: model, tools, system_prompt, structured_output
```

#### Hands-On Activity (20 min)

**Instruct attendees:**
1. Open `workshop/lab1-develop_a_personal_budget_assistant_strands_agent.ipynb`
2. Run cells sequentially
3. Test agent with example prompts from `workshop_prompts.md`

**Walk around and help attendees who are stuck**

**Key teaching moments:**
- "@tool decorator" - How tools are registered
- "structured_output()" - Type-safe Pydantic responses
- "50/30/20 rule" - Financial planning best practice

#### Checkpoint (5 min)

**Ask attendees:**
- "Who successfully created a budget agent?"
- "What structured output did you receive?"

**Show expected output:**
```json
{
  "monthly_income": 5000,
  "budget_categories": [
    {"name": "Needs", "amount": 2500, "percentage": 50},
    {"name": "Wants", "amount": 1500, "percentage": 30},
    {"name": "Savings", "amount": 1000, "percentage": 20}
  ],
  "recommendations": ["..."],
  "financial_health_score": 8
}
```

---

### Lab 2: Multi-Agent Orchestration (30 minutes)

**⏱️ 00:40 - 01:10**

#### Introduction (5 min)

**Key concepts:**
- Why multiple specialized agents? (Separation of concerns, expertise)
- Orchestrator pattern (router agent delegates to specialists)
- Tool composition (wrapping agents as tools)

**Architecture diagram:**
```
User Query
    ↓
Orchestrator (decides which agent to use)
    ↓
Budget Agent  OR  Financial Analysis Agent
    ↓
Structured Response
```

#### Hands-On Activity (20 min)

**Instruct attendees:**
1. Open `workshop/lab2-build_multi_agent_workflows_with_strands.ipynb`
2. Create financial analysis agent (yfinance tool)
3. Create orchestrator agent (wraps both specialists)
4. Test with multi-agent queries

**Key teaching moments:**
- "Tool wrapping pattern" - `@tool def budget_agent_tool(query) -> FinancialReport`
- "LangGraph integration" - Financial analysis uses LangGraph for workflows
- "Orchestrator system prompt" - How to write routing logic

#### Checkpoint (5 min)

**Test query:**
```
I make $5000/month and want to invest $1000.
Help me budget and suggest a portfolio.
```

**Expected behavior:**
1. Orchestrator analyzes query
2. Calls budget_agent_tool first
3. Then calls financial_analysis_agent_tool
4. Synthesizes both responses

**Ask attendees:**
- "Did your orchestrator call both agents?"
- "What investment recommendations did you receive?"

---

### Lab 3: Deploy to AgentCore Runtime (30 minutes)

**⏱️ 01:10 - 01:40**

#### Introduction (5 min)

**Key concepts:**
- What is AgentCore Runtime? (Managed serverless agent execution)
- Deployment workflow (Docker → ECR → AgentCore)
- Service discovery (SSM Parameter Store)
- Authentication modes (IAM vs OAuth/Cognito)

**Deployment flow diagram:**
```
configure.sh → launch.sh → health.sh
     ↓            ↓           ↓
  .yaml file   Docker    AWS test
               build
```

#### Hands-On Activity (20 min)

**Step-by-step deployment:**

**1. Deploy OAuth infrastructure (optional, 5 min)**
```bash
cd production/cdk
./deploy.sh  # Creates Cognito, publishes OAuth to SSM
```

**Teaching point:** "This creates Cognito User Pool and stores OAuth config in SSM. The agent will read this automatically."

**2. Configure agent (2 min)**
```bash
cd ..
./configure.sh  # Reads OAuth from SSM, creates .bedrock_agentcore.yaml
```

**Teaching point:** "This reads your SSM config and prepares .bedrock_agentcore.yaml for deployment."

**3. Launch to AWS (10 min)**
```bash
./launch.sh  # Builds Docker, deploys to AgentCore, publishes ARN to SSM
```

**Teaching point:** "This builds your Docker container, pushes to ECR, and creates AgentCore Runtime. Watch for the agent ARN in the output."

**Common issues during deployment:**
- Docker build timeout (show CloudWatch Logs)
- ECR authentication failure (show fix: `aws ecr get-login-password`)
- Cold start delay (explain 30-60s first invocation)

**4. Verify deployment (3 min)**
```bash
./health.sh  # Tests deployed agent
```

**Expected output:**
```
✓ AWS health check passed!
Agent ARN: arn:aws:bedrock-agentcore:us-west-2:...
Response time: 2.5 seconds
```

#### Checkpoint (5 min)

**Ask attendees:**
- "Who successfully deployed their agent?"
- "Who can see their agent ARN in `.bedrock_agentcore.yaml`?"
- "Who got a healthy response from `./health.sh`?"

**Troubleshooting time:** Help attendees who are stuck

---

### Demo: Streamlit UI (20 minutes)

**⏱️ 01:40 - 02:00**

#### Introduction (3 min)

**Key features:**
- SSM-based agent discovery (no manual config!)
- Real-time SSE streaming
- OAuth2/Cognito authentication
- Vision analysis (receipts, invoices)
- Session-based conversation history

#### Live Demo (12 min)

**Demo flow:**

**1. Launch UI (2 min)**
```bash
cd ../../  # Back to project root
./demo.sh  # Auto-discovers agents from SSM
```

**Open browser:** `http://localhost:8501`

**2. Show agent discovery (2 min)**
- Point out agent selector in sidebar
- Show OAuth icon (🔐) for Cognito agents vs IAM icon (🔑)

**3. Login demo (2 min)**
- Use demo_user / DemoPass123! (from .demo_users.json)
- Show authentication flow

**4. Chat interaction (3 min)**

**Example 1: Budget query**
```
I make $6000/month. Help me create a budget.
```

**Show:**
- Real-time token streaming
- Tool execution feedback ("🔧 Using budget_agent_tool...")
- Structured output rendering

**Example 2: Multi-agent query**
```
I make $5000/month and want to invest $1000.
Help me budget and recommend stocks.
```

**Show:**
- Orchestrator calling both agents
- Synthesized response

**Example 3: Vision analysis (if time)**
- Upload sample receipt image
- Show vision extraction
- Budget categorization

#### Hands-On (5 min)

**Instruct attendees:**
- Launch Streamlit: `cd genai-agentcore-demos && ./demo.sh`
- Test agent with queries from `workshop_prompts.md`
- Try uploading a receipt (if vision enabled)

---

### Wrap-Up & Q&A (10 minutes)

**⏱️ 02:00 - 02:10**

#### Key Takeaways

**Recap what attendees learned:**
1. ✅ Built single-agent system (budget assistant)
2. ✅ Created multi-agent orchestration
3. ✅ Deployed to AWS AgentCore Runtime
4. ✅ Tested via Streamlit UI

#### Next Steps

**Resources to share:**
- Workshop GitHub repo: [link]
- AWS AgentCore Docs: https://docs.aws.amazon.com/bedrock-agentcore/
- Strands Agents Docs: https://strandsagents.com/latest/
- AgentCore Starter Toolkit: https://aws.github.io/bedrock-agentcore-starter-toolkit/

**Homework/Extension ideas:**
- Add custom tools (database lookup, API calls)
- Implement guardrails (content filtering, PII redaction)
- Deploy multiple agents (market trends, tax planning)
- Build custom UI with your branding

#### Q&A

**Open floor for questions** (remaining time)

**Common questions** (see next section)

---

## Timing & Pacing

### Recommended Schedule

| Time | Activity | Duration | Type |
|------|----------|----------|------|
| 00:00-00:10 | Introduction & Prerequisites | 10 min | Presentation |
| 00:10-00:40 | Lab 1: Budget Assistant | 30 min | Hands-on |
| 00:40-01:10 | Lab 2: Multi-Agent Orchestration | 30 min | Hands-on |
| 01:10-01:15 | **Break** | 5 min | Break |
| 01:15-01:45 | Lab 3: Deploy to AgentCore | 30 min | Hands-on |
| 01:45-02:05 | Streamlit UI Demo | 20 min | Demo |
| 02:05-02:15 | Wrap-Up & Q&A | 10 min | Discussion |

**Total: 135 minutes (2 hours 15 minutes)**

### Pacing Tips

**If running behind schedule:**
- **Skip Lab 1** - Jump directly to Lab 2 (use pre-built budget agent)
- **Skip OAuth deployment** - Use IAM authentication only (faster)
- **Pre-deploy agent** - Have agent already deployed, skip Lab 3 deployment steps
- **Shorten Q&A** - Answer top 3 questions, share documentation links

**If ahead of schedule:**
- **Deep dive on guardrails** - Show `deploy_guardrails.py` and testing
- **Show production code** - Compare workshop vs production implementations
- **Live coding** - Add a custom tool together
- **Advanced memory** - Explain LTM vs STM retrieval strategies

---

## Talking Points by Section

### Introduction

**Key messages:**
- "Today we're building a production-ready multi-agent financial advisory system"
- "You'll learn patterns applicable to any domain (not just finance)"
- "Everything we deploy today runs on your AWS account - you own it"

**Hook:** "By the end of today, you'll have a working AI financial advisor that you can demo to your team or clients."

### Lab 1: Budget Assistant

**Key messages:**
- "Strands makes it easy to add tools - just use @tool decorator"
- "Structured outputs ensure type safety - no parsing LLM text"
- "The 50/30/20 rule is a proven budgeting framework - 50% needs, 30% wants, 20% savings"

**Analogy:** "Think of an agent like a specialized consultant. You wouldn't hire one consultant to do everything - you want experts."

### Lab 2: Orchestration

**Key messages:**
- "Orchestration is just delegation - the orchestrator decides WHO should handle WHAT"
- "You can wrap entire agents as tools - powerful composition pattern"
- "LangGraph gives you workflow primitives - parallel execution, conditionals, loops"

**Analogy:** "The orchestrator is like a project manager who assigns tasks to specialists based on their expertise."

### Lab 3: Deployment

**Key messages:**
- "AgentCore Runtime handles all the infrastructure - no Kubernetes, no ECS config"
- "Immutable versioning means you can rollback instantly if needed"
- "SSM Parameter Store enables service discovery - agents find each other automatically"

**Analogy:** "AgentCore is like AWS Lambda for AI agents - you focus on code, AWS manages execution."

### Streamlit Demo

**Key messages:**
- "Real-time streaming improves UX - users see progress, not a spinner"
- "OAuth2/Cognito adds enterprise-grade auth with minimal code"
- "Vision analysis enables document processing - receipts, invoices, charts"

**Analogy:** "The Streamlit UI is like ChatGPT, but connected to YOUR agents with YOUR business logic."

---

## Common Questions & Answers

### General Questions

**Q: Can I use this for non-financial use cases?**
**A:** Absolutely! The patterns (orchestration, tools, structured outputs) apply to any domain. Just swap the financial tools for your domain-specific tools.

**Q: How much does this cost to run?**
**A:** Costs are pay-per-use:
- Bedrock model invocation: $0.003-0.03 per 1K tokens (model-dependent)
- AgentCore Runtime: $0.00003 per invocation + compute time
- Typical chat session: $0.01-0.10

**Q: Can this handle production traffic?**
**A:** Yes! AgentCore Runtime auto-scales. The production code includes:
- Guardrails (content filtering, PII)
- Memory management (LTM/STM)
- Error handling and logging
- OAuth2 authentication

### Technical Questions

**Q: Why use Strands instead of LangChain?**
**A:** Strands is AWS-native, optimized for Bedrock models, and has cleaner abstractions for tools/agents. LangChain is more feature-rich but complex. You can use both (we do in financial_analysis_agent).

**Q: How does memory work?**
**A:** AgentCore Memory uses vector embeddings for semantic search. Three strategies:
- USER_PREFERENCE (profile, goals)
- SEMANTIC (facts, data)
- SUMMARY (conversation history)

**Q: Can I deploy this in my VPC?**
**A:** Not directly - AgentCore Runtime is fully managed. But you CAN:
- Use VPC endpoints for Bedrock API calls
- Connect to VPC resources via Lambda integration
- Use AWS PrivateLink for secure connectivity

**Q: What about PII and sensitive data?**
**A:** Use Bedrock Guardrails for:
- PII detection and redaction (SSN, email, phone)
- Content filtering (profanity, violence)
- Pre-check validation (before conversation history)

### Troubleshooting Questions

**Q: My agent deployment is taking forever (10+ minutes)**
**A:** Docker build can be slow. Check:
- Is Docker Desktop running?
- Check CloudWatch Logs: https://console.aws.amazon.com/codesuite/codebuild/
- Try: `docker system prune -f` to clean cache

**Q: Health check fails with timeout**
**A:** Cold start can take 30-60 seconds. Try:
- `./health.sh --timeout 120` (increase timeout)
- Check agent ARN exists: `grep agent_arn .bedrock_agentcore.yaml`
- View logs: `aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow`

**Q: Streamlit shows "No agents available"**
**A:** SSM parameter missing. Fix:
- Verify parameter exists: `aws ssm get-parameter --name "/agentcore/finance-personal-assistant/config"`
- Redeploy agent: `./launch.sh` (publishes ARN to SSM automatically)

---

## Troubleshooting During Workshop

### Real-Time Monitoring

**Have these open during workshop:**
1. **CloudWatch Logs console** (for agent logs)
2. **TROUBLESHOOTING.md** (common errors with solutions)
3. **Slack/chat window** (monitor attendee questions)

### Quick Fixes

| Problem | Quick Fix | Time |
|---------|-----------|------|
| AWS credentials not working | Verify `export AWS_PROFILE=workshop` is set; re-run `aws configure --profile workshop` if needed | 1 min |
| Docker not running | Open Docker Desktop app | 2 min |
| Agent deployment failed | Show CloudWatch logs, explain error | 3 min |
| Bedrock model access denied | Verify Administrator access granted; rare after Oct 2025 (models auto-enabled) | 2 min |
| Health check timeout | Increase timeout, explain cold start | 1 min |

### Escalation Path

**If multiple attendees have the same issue:**
1. **Pause workshop** - Don't leave people behind
2. **Screen share solution** - Show fix for everyone
3. **Update TROUBLESHOOTING.md** - Document new issue
4. **Continue** - Resume when resolved

**If individual issue:**
1. **Ask for screenshot** - Share in Slack/chat
2. **Assign helper** - If you have co-instructor/TA
3. **Defer to break** - Help during break time
4. **Provide workaround** - "Use my deployed agent for now"

---

## Backup Plans

### Plan A: Live Deployment (Ideal)

Attendees deploy agents to their own AWS accounts during workshop.

**Requirements:**
- Attendees have **AWS Administrator access** to their AWS accounts
- AWS CLI configured with valid credentials
- Docker Desktop running
- Python 3.13+ and `uv` installed
- AWS CDK CLI installed and bootstrapped

**Why Administrator access?**
Workshop involves deploying CDK infrastructure (IAM roles, Cognito), building Docker images, creating AgentCore Runtime instances, and managing AWS resources.

**Risk:** Individual account issues, timing variability, permission troubleshooting

---

### Plan B: Shared Demo Account

Use your AWS account, attendees follow along without deploying.

**Preparation:**
- Deploy finance assistant before workshop
- Share read-only credentials for viewing logs
- Attendees run notebooks locally (no AWS deployment)

**Advantage:** No AWS account dependency
**Disadvantage:** Less hands-on experience

---

### Plan C: Pre-Recorded Demo + Explanation

Show pre-recorded deployment video, explain concepts.

**Use when:**
- Internet connectivity issues
- AWS service outage
- Major deployment failures

**Have ready:**
- 15-minute demo recording showing full workflow
- Annotated slides explaining each step
- Q&A session after video

---

### Plan D: Local Development Only

Skip AgentCore deployment, focus on agent development.

**Modified schedule:**
- Lab 1: Budget assistant (local)
- Lab 2: Multi-agent orchestration (local)
- Skip Lab 3: Deployment
- Demo: Show pre-deployed Streamlit UI

**Advantage:** No AWS dependency
**Disadvantage:** Misses production deployment patterns

---

## Post-Workshop Resources

### Attendee Takeaways

**Share these links after workshop:**

1. **Workshop GitHub Repo:**
   - All code from today
   - Setup instructions
   - Additional examples

2. **Documentation:**
   - AWS AgentCore Docs: https://docs.aws.amazon.com/bedrock-agentcore/
   - Strands Agents: https://strandsagents.com/latest/
   - AgentCore Toolkit: https://aws.github.io/bedrock-agentcore-starter-toolkit/

3. **Workshop Recording:**
   - Link to video recording (if recorded)
   - Slides PDF

4. **Support:**
   - Slack community channel
   - GitHub Issues for questions
   - AWS support forums

### Follow-Up Email Template

```
Subject: Thank you for attending the AgentCore Workshop!

Hi everyone,

Thank you for attending today's workshop on building multi-agent financial advisory systems with AWS Bedrock AgentCore.

Resources:
📦 Workshop code: [GitHub link]
📚 Documentation: [Docs link]
🎥 Recording: [Video link]
💬 Community: [Slack/Discord link]

Next steps:
1. Deploy the agent to your AWS account (if you haven't already)
2. Experiment with custom tools and queries
3. Share your creations in the community channel!

Questions? Reply to this email or post in the community.

Best regards,
[Your name]
```

---

## Instructor Checklist - Day Of

### Pre-Workshop (1 hour before)

- [ ] Test screen sharing and audio
- [ ] Open all required terminal windows
- [ ] Clear browser cache and cookies
- [ ] Test AWS credentials (`aws sts get-caller-identity`)
- [ ] Verify agent deployed and healthy (`./health.sh`)
- [ ] Start screen recording
- [ ] Have TROUBLESHOOTING.md open
- [ ] Share Slack/chat link with attendees

### During Workshop

- [ ] Record attendance (for follow-up)
- [ ] Monitor Slack/chat for questions
- [ ] Take screenshots of interesting questions/errors
- [ ] Note timing (are we ahead/behind?)
- [ ] Call out break times

### Post-Workshop

- [ ] Stop screen recording
- [ ] Upload recording to shared drive
- [ ] Send follow-up email with resources
- [ ] Document new troubleshooting issues
- [ ] Update workshop materials based on feedback
- [ ] Thank co-instructors/helpers

---

## Emergency Contacts

**Have these ready before workshop:**

- **AWS Support:** 1-XXX-XXX-XXXX (or support.aws.amazon.com)
- **Backup instructor:** [Name, phone]
- **IT support:** [Contact for Zoom/connectivity issues]
- **Workshop admin:** [Contact for logistics]

---

## Workshop Feedback

### Questions to ask attendees (post-workshop survey):

1. Was the workshop duration appropriate? (Too short / Just right / Too long)
2. What was the most valuable part of the workshop?
3. What was the most confusing part?
4. Did you successfully deploy an agent to AWS? (Yes / No / Partial)
5. Would you recommend this workshop to colleagues? (1-10 scale)
6. What topics should we add to future workshops?
7. Any other feedback?

---

## Version History

- **v1.0** (2025-01-06): Initial instructor guide
  - Created for AgentCore workshop series
  - Based on 3-lab structure (Budget → Multi-Agent → Deployment)
  - Includes backup plans and troubleshooting

---

**Good luck with the workshop! You've got this!** 🚀

**Last Updated:** 2025-01-06
