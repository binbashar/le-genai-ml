# Memory Test for Financial Personal Assistant

This directory contains the memory capability test for the Financial Personal Assistant agent using OAuth authentication.

## Overview

The test validates Short-Term Memory (STM) functionality and session isolation for the agent, ensuring:
- **Memory Persistence**: Information is retained within the same session
- **Session Isolation**: Different sessions don't share memory
- **OAuth Authentication**: Proper JWT token handling with Cognito

## Files

- **`test_memory_final_working.py`** - Main memory test that validates STM and session isolation
- **`test_memory.sh`** - Simple bash script to run the test
- **`README.md`** - This documentation

## Prerequisites

1. **Deployed Agent**: The Financial Personal Assistant must be deployed
   ```bash
   cd ../finance-personal-assistant
   ./launch.sh
   ```

2. **OAuth Configuration**: Agent must have OAuth configured (check `.bedrock_agentcore.yaml`)

3. **Cognito User**: The `broker_demo` user must exist in Cognito with password `DemoPass123!`

## Running the Test

```bash
# From tests directory
./test_memory.sh

# Or directly with Python
uv run test_memory_final_working.py

# Or from parent directory
cd /Users/alex/Developer/le-genai-ml/genai-agentcore-demos
uv run tests/test_memory_final_working.py
```

## What the Test Does

The test performs two key validations:

### 1. Memory Retention (STM)
- Teaches the agent a fact: "My lucky number is 7"
- Asks the agent to recall the fact in the same session
- Validates the agent remembers the information

### 2. Session Isolation
- Creates a new session with a different session ID
- Asks the same question in the new session
- Validates the new session doesn't have access to the previous session's data

## Expected Output

```
============================================================
🧠 FINAL MEMORY TEST
============================================================
Agent ARN: arn:aws:bedrock-agentcore:...
Region: us-west-2
✓ OAuth config loaded

Authenticating...
✓ Authenticated as broker_demo

Session ID: memory-test-[uuid]
Session length: 44 chars (AWS requires >= 33)

📝 TEST: Simple fact memory
----------------------------------------
Teaching: 'My lucky number is 7'
Response: I've noted that your lucky number is 7...

Recalling: 'What is my lucky number?'
Response: Your lucky number is 7!...
✅ Agent remembered the number!

🔒 TEST: Session isolation
----------------------------------------
New session: isolation-test-[uuid]
Asking same question in new session...
Response: I appreciate you reaching out...
✅ New session correctly doesn't know the number

============================================================
🎉 MEMORY TEST PASSED!
The agent successfully remembered information within the session.
============================================================
```

## Technical Details

### Authentication Flow
1. Loads OAuth config from `.bedrock_agentcore.yaml`
2. Authenticates using `authenticate()` function
3. Extracts token: `token = auth_result["AccessToken"]`
4. Uses token with `invoke_with_token()` for agent invocation

### Session Management
- Session IDs must be >= 33 characters (AWS requirement)
- Pattern: `memory-test-{uuid}` for main session
- Pattern: `isolation-test-{uuid}` for isolation test
- User ID is automatically extracted from JWT token

### Response Handling
- Agent returns Server-Sent Events (SSE) format
- Responses have `data:` prefix on each line
- Test includes SSE parser to extract actual text content

## Relationship to Streamlit

This test validates the same memory mechanisms used by the Streamlit demo:
- Same `invoke_with_token()` function
- Same OAuth authentication flow
- Same session-based memory isolation
- Same SSE response format

The test confirms that the underlying agent memory capabilities work correctly, which the Streamlit application relies on for user conversations.

## Troubleshooting

### Test Fails - Agent Doesn't Remember
- Check agent memory configuration in deployment
- Verify session ID is being passed correctly
- Ensure memory mode is set appropriately (STM_ONLY or STM_AND_LTM)

### OAuth Authentication Failed
- Verify `broker_demo` user exists in Cognito
- Check password is correct (`DemoPass123!`)
- Ensure OAuth config exists in `.bedrock_agentcore.yaml`

### Agent Not Available
- Verify agent is deployed: `cd ../finance-personal-assistant && ./health.sh`
- Check AWS credentials are configured
- Ensure agent ARN is correct in configuration