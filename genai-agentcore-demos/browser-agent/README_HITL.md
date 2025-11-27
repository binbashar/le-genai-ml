# Human-in-the-Loop (HITL) Browser Agent

Secure browser automation with the ability to pause automation and allow human intervention via AWS Bedrock AgentCore Browser Live View.

## Overview

This implementation demonstrates how to build a production-ready browser agent that:
- **Pauses automation** when sensitive operations are detected (login, CAPTCHA, etc.)
- **Allows human control** via Live View (real-time browser session viewing)
- **Resumes automation** after human completes manual steps
- **Never logs credentials** - secure by design

## Architecture

```
┌──────────────┐
│    User      │
│  (Streamlit) │
└──────┬───────┘
       │ 1. "Login to my bank"
       ▼
┌────────────────────────┐
│  HITL Browser Agent    │
│  (Claude Sonnet 4.5)   │
└──────┬─────────────────┘
       │ 2. Detects login form
       ▼
┌────────────────────────┐
│  UpdateBrowserStream   │
│  streamStatus:DISABLED │
└──────┬─────────────────┘
       │ 3. Returns Live View URL
       ▼
┌────────────────────────┐
│   Live View (DCV)      │
│  Human enters creds    │
└──────┬─────────────────┘
       │ 4. Signals "done"
       ▼
┌────────────────────────┐
│  UpdateBrowserStream   │
│  streamStatus:ENABLED  │
└──────┬─────────────────┘
       │ 5. Continues task
       ▼
┌────────────────────────┐
│  Agent completes task  │
└────────────────────────┘
```

## Key Components

### 1. `browser_agent_hitl.py` - Core HITL Logic

**HITLBrowserSession:**
- Manages browser session lifecycle
- Calls `UpdateBrowserStream` API
- Generates Live View URLs
- Tracks automation state (paused/active)

**HITLBrowserAgent:**
- Strands agent with browser tool
- Auto-detects when human intervention needed
- Orchestrates pause → wait → resume flow

### 2. `main_hitl.py` - AgentCore Entrypoint

**Features:**
- Streaming responses (`AsyncIterator`)
- Session state management
- Callback endpoints for continuation
- Error handling and logging

**Event types:**
- `status` - Progress updates
- `thinking` - Agent reasoning
- `awaiting_human` - Paused, needs intervention
- `final` - Task completed
- `error` - Error occurred

### 3. `test_hitl_local.py` - Testing Suite

**Tests:**
- Full HITL flow with banking scenario
- Session state management
- UpdateBrowserStream API structure

## Quick Start

### Local Testing

```bash
# Run interactive test suite
uv run python test_hitl_local.py

# Select option 1 for full HITL flow
```

**What happens:**
1. Agent navigates to banking website
2. Detects login form
3. Pauses automation
4. Shows Live View URL
5. You login manually via Live View
6. Press Enter to continue
7. Agent resumes and completes task

### Deploy to AgentCore

```bash
# Configure
uv run agentcore configure -e main_hitl.py

# Deploy
uv run agentcore launch

# Test deployed agent
curl -X POST https://{runtime-url}/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Login to my bank account"}'
```

## Usage Examples

### Example 1: Banking Login with HITL

```python
from browser_agent_hitl import HITLBrowserAgent

agent = HITLBrowserAgent()

# Start task
result = agent.execute(
    user_message="Navigate to https://mybank.com and check my balance",
    session_id="user-123"
)

if result["status"] == "awaiting_human":
    # Human intervention needed
    print(f"Please login at: {result['live_view_url']}")

    # Wait for user signal...
    input("Press Enter when done...")

    # Continue
    final_result = agent.continue_after_human(
        "Check my account balance"
    )

    print(final_result["agent_response"])
```

### Example 2: Streamlit Integration

```python
import streamlit as st
import boto3

bedrock = boto3.client('bedrock-agentcore-runtime')

# Session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# User input
message = st.chat_input("What do you want to do?")

if message:
    # Invoke agent
    response = bedrock.invoke_agent_runtime(
        agentRuntimeArn='arn:aws:bedrock-agentcore:...',
        sessionId=st.session_state.session_id,
        payload={'prompt': message}
    )

    # Parse streaming response
    for event in response['responseStream']:
        event_type = event.get('type')

        if event_type == 'awaiting_human':
            # Show Live View URL
            live_view_url = event['live_view_url']

            st.warning("🚨 Manual intervention required")
            st.markdown(f"[Open Live View]({live_view_url})")

            # Button to continue
            if st.button("I've completed the login"):
                # Continue agent
                continue_response = bedrock.invoke_agent_runtime(
                    agentRuntimeArn='arn:aws:bedrock-agentcore:...',
                    sessionId=st.session_state.session_id,
                    payload={'action': 'continue'}
                )

        elif event_type == 'final':
            st.write(event['result'])
```

### Example 3: API Callback Pattern

```python
# Client initiates task
POST /invocations
{
    "prompt": "Login to my bank and transfer $100"
}

# Response: awaiting_human
{
    "type": "awaiting_human",
    "session_id": "abc-123",
    "live_view_url": "https://console.aws.amazon.com/...",
    "message": "Please complete login via Live View"
}

# User completes login in Live View

# Client signals completion
POST /sessions/abc-123/continue
{
    "next_instruction": "Now transfer $100 to savings"
}

# Response: completed
{
    "status": "continued",
    "result": "Transfer completed successfully"
}
```

## UpdateBrowserStream API

### Pause Automation

```python
import boto3

client = boto3.client('bedrock-agentcore')

response = client.update_browser_stream(
    browserIdentifier='browser-abc123',
    sessionId='session-xyz789',
    streamUpdate={
        'automationStreamUpdate': {
            'streamStatus': 'DISABLED'
        }
    }
)

# Automation paused - human can take control
```

### Resume Automation

```python
response = client.update_browser_stream(
    browserIdentifier='browser-abc123',
    sessionId='session-xyz789',
    streamUpdate={
        'automationStreamUpdate': {
            'streamStatus': 'ENABLED'
        }
    }
)

# Automation resumed - agent continues
```

## Live View Access

### AWS Console

1. Navigate to: **AWS Console → Bedrock → AgentCore → Browser → Sessions**
2. Find your session in the list
3. Click "Live view" link in the table
4. Browser session opens in new window (DCV streaming)
5. You can see real-time video and interact with mouse/keyboard

### Programmatic Access

```python
def generate_live_view_url(session_id: str, region: str = "us-west-2") -> str:
    """Generate Live View URL for browser session"""
    base_url = "https://console.aws.amazon.com/bedrock"
    return f"{base_url}/agentcore/browser/sessions/{session_id}?region={region}"

# Example
url = generate_live_view_url("my-session-123")
print(f"Open in browser: {url}")
```

### Live View Features

- **Real-time video** - See exactly what the browser is doing
- **Interactive control** - Click, type, scroll in real-time
- **Take control / Release control** - Toggle between automated and manual
- **Session info** - Status, connection, identifiers
- **Terminate session** - Kill browser session if needed

## Security Considerations

### ✅ What's Secure

**Credentials never logged:**
- Human enters credentials directly in Live View
- Browser sends credentials to bank (not through agent)
- Agent resumes after login (no access to credentials)

**Encryption:**
- Live View uses DCV (NICE DCV) with TLS
- All data encrypted in transit
- Session isolated per user (actor_id scoping)

**Authentication:**
- Live View requires AWS Console login
- IAM permissions required: `bedrock-agentcore:UpdateBrowserStream`
- No public access to sessions

**Ephemeral sessions:**
- Sessions timeout after inactivity (default: 15 min, max: 8 hours)
- No persistent storage of credentials
- Clean slate on each run

### ⚠️ Security Risks

**Session recording:**
- If enabled, credentials visible in S3 recordings
- **Recommendation:** Disable recording for banking sessions

```yaml
# .bedrock_agentcore.yaml
agents:
  browser_agent:
    browser_recording:
      enabled: false  # Disable for sensitive operations
```

**CloudWatch Logs:**
- Agent prompts/responses logged
- **Mitigation:** Never include credentials in prompts
- **Pattern:** Pause before credentials, resume after

**Network monitoring:**
- Traffic between browser and bank is visible to VPC
- **Mitigation:** Use VPC endpoints, PrivateLink
- **Best practice:** Deploy in private subnet

### 🔐 Best Practices

1. **Disable recording for banking sessions**
2. **Use VPC private subnets**
3. **Minimize IAM permissions** (principle of least privilege)
4. **Rotate session IDs** frequently
5. **Set short session timeouts** (15 minutes for banking)
6. **Audit CloudTrail logs** for UpdateBrowserStream calls
7. **Use MFA** for AWS Console access (Live View)

## IAM Permissions

### Required for Agent Execution Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateBrowser",
        "bedrock-agentcore:StartBrowserSession",
        "bedrock-agentcore:UpdateBrowserStream",
        "bedrock-agentcore:ConnectBrowserAutomationStream"
      ],
      "Resource": "arn:aws:bedrock-agentcore:*:*:browser/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    }
  ]
}
```

### Required for Live View Users

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:GetBrowserSession",
        "bedrock-agentcore:ListBrowserSessions"
      ],
      "Resource": "*"
    }
  ]
}
```

## Troubleshooting

### Issue: "Browser identifier not found"

**Cause:** Browser session not properly initialized

**Solution:**
```python
# Ensure browser tool is used before pause
agent.execute("Navigate to example.com")  # Creates browser
# NOW you can pause
agent.session_manager.pause_automation()
```

### Issue: "Live View URL returns 404"

**Cause:** Session ID or region mismatch

**Solution:**
```python
# Verify session exists
aws bedrock-agentcore list-browser-sessions --region us-west-2

# Check session status
aws bedrock-agentcore get-browser-session \
    --session-id <session_id> \
    --region us-west-2
```

### Issue: "UpdateBrowserStream fails with AccessDenied"

**Cause:** Missing IAM permissions

**Solution:**
```bash
# Add required permission
aws iam put-role-policy \
    --role-name <execution-role> \
    --policy-name BrowserStreamUpdate \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": "bedrock-agentcore:UpdateBrowserStream",
            "Resource": "*"
        }]
    }'
```

### Issue: "Agent doesn't detect login form"

**Cause:** Detection logic needs tuning

**Solution:**
```python
# Customize detection in browser_agent_hitl.py
def _needs_human_intervention(self, response: str) -> bool:
    # Add more keywords
    intervention_signals = [
        "pause_for_human",
        "login_required",
        "credentials",
        "password",
        "sign in",           # Add
        "authenticate",      # Add
        "verification",      # Add
    ]
    ...
```

## Monitoring

### CloudWatch Logs

```bash
# View agent logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow

# Filter for HITL events
aws logs filter-log-events \
    --log-group-name /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT \
    --filter-pattern "awaiting_human"
```

### CloudTrail Auditing

```bash
# Audit UpdateBrowserStream calls
aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=UpdateBrowserStream \
    --max-results 50
```

### Session Metrics

```python
# Custom metrics
import boto3

cloudwatch = boto3.client('cloudwatch')

cloudwatch.put_metric_data(
    Namespace='BrowserAgent/HITL',
    MetricData=[
        {
            'MetricName': 'HumanInterventions',
            'Value': 1,
            'Unit': 'Count',
            'Dimensions': [
                {'Name': 'SessionId', 'Value': session_id},
                {'Name': 'Reason', 'Value': 'login_required'}
            ]
        }
    ]
)
```

## Comparison with Other Approaches

| Feature | HITL (UpdateBrowserStream) | AgentCore Identity (OAuth) | Secrets Manager | Return of Control |
|---------|---------------------------|---------------------------|-----------------|-------------------|
| **Use Case** | Legacy web login | Modern APIs (OAuth) | Stored credentials | Bedrock Agents only |
| **Security** | ⭐⭐⭐⭐⭐ (creds never touch agent) | ⭐⭐⭐⭐⭐ (token vault) | ⭐⭐⭐⭐ (encrypted) | ⭐⭐⭐⭐⭐ |
| **UX** | ⭐⭐⭐ (manual step) | ⭐⭐⭐⭐⭐ (automatic) | ⭐⭐⭐⭐ (once configured) | ⭐⭐⭐ (custom) |
| **Complexity** | ⭐⭐⭐ (moderate) | ⭐⭐⭐⭐ (requires OAuth) | ⭐⭐ (simple) | ⭐⭐⭐⭐ (complex) |
| **Credentials stored?** | ❌ No | ✅ Yes (encrypted tokens) | ✅ Yes (encrypted) | ❌ No |
| **Works with AgentCore Runtime?** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No (Agents only) |

## References

- [AWS Bedrock AgentCore Browser Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-onboarding.html)
- [UpdateBrowserStream API Reference](https://docs.aws.amazon.com/cli/latest/reference/bedrock-agentcore/update-browser-stream.html)
- [Live View Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-observability.html)
- [GitHub: amazon-bedrock-agentcore-samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- [Web Bot Auth for CAPTCHAs](https://aws.amazon.com/blogs/machine-learning/reduce-captchas-for-ai-agents-browsing-the-web-with-web-bot-auth-preview-in-amazon-bedrock-agentcore-browser/)

## License

Apache License 2.0 - See LICENSE file for details.
