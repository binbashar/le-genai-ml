# Streaming and Async Tasks with AgentCore Runtime

Demo implementation of multi-node agents with streaming intermediate updates and long-running asynchronous tasks using Amazon Bedrock AgentCore Runtime and LangGraph.

## Architecture

### Multi-Node Streaming Agent

```
User Request → analyze_with_streaming()
                      ↓
    ┌─────────────────────────┐
    │   Processing Node       │ → yield "Thinking: Processing request..."
    └─────────────────────────┘
                      ↓
    ┌─────────────────────────┐
    │   Data Fetch Node       │ → yield "Thinking: Fetching data..."
    └─────────────────────────┘
                      ↓
    ┌─────────────────────────┐
    │   Transform Node        │ → yield "Thinking: Transforming output..."
    └─────────────────────────┘
                      ↓
    ┌─────────────────────────┐
    │   Response Node         │ → yield final response + metadata
    └─────────────────────────┘
```

## Core Concepts

### Streaming vs Async Tasks

| Feature | Streaming | Async Tasks |
|---------|-----------|-------------|
| **Connection** | Remains open | Closes immediately |
| **Updates** | Real-time yields | Client polls for status |
| **Typical Duration** | Seconds to minutes | Minutes to hours (up to 8h) |
| **Use Case** | Intermediate progress updates | Long-running batch jobs |

### Implementation Patterns

#### 1. Intermediate Message Streaming

Send progress updates as the agent processes through nodes:

```python
import asyncio

@app.entrypoint
async def analyze_with_streaming(payload, context):  # Must be async
    user_input = payload.get("prompt")
    
    # Yield intermediate update - sent immediately
    yield {"type": "thinking", "message": "Thinking: Processing request..."}
    state = await asyncio.to_thread(agent.nodes["analysis"].invoke, initial_state)
    
    # Yield data fetch update
    yield {"type": "thinking", "message": "Thinking: Fetching data from sources..."}
    state = await asyncio.to_thread(agent.nodes["data_query"].invoke, state)
    
    # Yield transformation update
    yield {"type": "thinking", "message": "Thinking: Determining output format..."}
    state = await asyncio.to_thread(agent.nodes["visualization"].invoke, state)
    
    # Final response
    final_state = await asyncio.to_thread(agent.nodes["response"].invoke, state)
    yield {"type": "final", "result": final_state["messages"][-1].content}
```

**⚠️ Critical:** Function must be `async def` for real-time streaming.

#### 2. Token-by-Token Streaming

Stream LLM responses as they are generated:

```python
@app.entrypoint
async def analyze_with_llm_streaming(payload, context):  # Must be async
    llm = ChatBedrock(model_id="us.amazon.nova-micro-v1:0", streaming=True)
    
    # Use astream for async streaming
    async for chunk in llm.astream(messages):
        yield {"type": "stream_token", "token": chunk.content}
    
    yield {"type": "done"}
```

**⚠️ Critical:** Use `astream()` not `stream()` for async contexts.

#### 3. Long-Running Async Tasks

For operations that take minutes or hours:

```python
@app.async_task
def generate_report(task_id: str, payload: dict):
    """Background task with up to 8-hour execution time"""
    # Process large dataset
    # Generate comprehensive report
    return {"task_id": task_id, "result": report}

@app.entrypoint
def start_report(payload, context):
    """Returns immediately with task_id"""
    task_id = generate_unique_id()
    
    context.add_async_task(
        task_function=generate_report,
        task_id=task_id,
        payload=payload
    )
    
    return {"task_id": task_id, "status": "initiated"}

@app.entrypoint
def check_status(payload, context):
    """Poll for task progress"""
    task_id = payload.get("task_id")
    task = TASK_STORAGE.get(task_id)
    
    return {
        "status": task["status"],
        "progress": task["progress"],
        "result": task.get("result")
    }
```

## Installation

### Prerequisites

- Python 3.12+
- AWS credentials configured
- `uv` package manager

### Setup

```bash
cd 02_async_streaming

# Install dependencies
uv sync

# Test locally (no AWS deployment required)
uv run python streaming_agent_local.py
```

### Local Testing Output

```
============================================================
STREAMING AGENT - LOCAL TEST
============================================================

User Request: Process dataset with comprehensive analysis

🤔 Thinking: Processing your request to understand requirements...
📊 Thinking: Fetching relevant data from external sources...
📊 Thinking: Retrieved data. Retrieved 1,247 records matching criteria...
📈 Thinking: Determining the best output format for your request...
📈 Thinking: Recommended format is structured

============================================================
FINAL RESPONSE
============================================================

Based on your request, here is the processed output...
[Complete LLM response]
```

## Deployment

### 1. Configure AgentCore

```bash
# Set AWS profile
export AWS_PROFILE=your-profile

# Configure agent (generates .bedrock_agentcore.yaml)
uv run agentcore configure -e streaming_agent.py

```

### 2. Deploy to AgentCore Runtime

```bash
# Build container, push to ECR, create runtime
uv run agentcore launch
```

## Invocation

> 💰 **Cost Note**: Streaming does NOT increase costs. During streaming (I/O wait), CPU is not charged.

### CLI Invocation

```bash
# Events shown together at completion
agentcore invoke '{"query": "Your question here"}'
```

### Real-Time Streaming

For **real-time streaming** where events appear as they occur, use the provided client:

```bash
# First, get your agent ARN from the deployment
agentcore status

# Option 1: Set as environment variable
export AGENT_RUNTIME_ARN='arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/streaming_agent-xxx'
uv run invoke_streaming.py "How does AWS Lambda work with Bedrock?"

# Option 2: Pass ARN as argument
uv run invoke_streaming.py "How does AWS Lambda work?" "arn:aws:bedrock-agentcore:..."
```

Output:
- Progress updates in real-time (`🔄 Classifying request...`)
- Token-by-token streaming
- Final metadata summary


### Boto3 Streaming Pattern

Based on [AWS Official Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-invoke-agent.html):

```python
import boto3
import json

# Initialize the Bedrock AgentCore client
agent_core_client = boto3.client('bedrock-agentcore')

# Prepare the payload
payload = json.dumps({"query": "Your question"}).encode()

# Invoke the agent
response = agent_core_client.invoke_agent_runtime(
    agentRuntimeArn=agent_arn,
    runtimeSessionId=session_id,
    payload=payload
)

# Process streaming response
if "text/event-stream" in response.get("contentType", ""):
    for line in response["response"].iter_lines(chunk_size=10):
        if line:
            line = line.decode("utf-8")
            if line.startswith("data: "):
                line = line[6:]
                print(line)

elif response.get("contentType") == "application/json":
    content = []
    for chunk in response.get("response", []):
        content.append(chunk.decode('utf-8'))
    print(json.loads(''.join(content)))
```

**Key Points:**
- Method: `invoke_agent_runtime` 
- Response: `text/event-stream` for streaming
- Pattern: `iter_lines(chunk_size=10)`
- Format: Each line prefixed with `data: `

### Async Tasks with Polling

```python
# Start long-running task
response = client.invoke_agent_runtime(
    agentRuntimeArn='arn:aws:bedrock:us-east-1:ACCOUNT:agent-runtime/ID',
    entrypoint='start_report',
    payload={'query': 'Process comprehensive dataset with full analysis'}
)

task_id = response['task_id']

# Poll for completion
while True:
    status = client.invoke_agent_runtime(
        agentRuntimeArn='arn:aws:bedrock:us-east-1:ACCOUNT:agent-runtime/ID',
        entrypoint='check_status',
        payload={'task_id': task_id}
    )
    
    if status['status'] == 'completed':
        print(f"Processing complete: {status['result']}")
        break
    
    time.sleep(5)
```

## Components

### `streaming_agent.py`

Production agent with two entrypoints:
- `analyze_with_streaming`: Multi-node workflow with intermediate updates
- `analyze_with_llm_streaming`: Token-by-token LLM streaming

### `async_task_agent.py`

Long-running task agent with three patterns:
- `start_report`: Fire-and-forget task initiation
- `check_status`: Status polling endpoint
- `start_report_with_polling`: Streaming + polling hybrid

### `streaming_agent_local.py`

Local testing harness that runs agents without AWS deployment.

## Session Management

AgentCore automatically manages session state:

```python
# Client maintains session across multiple calls
client.invoke_agent_runtime(
    agentRuntimeArn='...',
    sessionId='user-123-session-456',  # Unique per conversation
    payload={'prompt': 'First query'}
)

# Subsequent call with same sessionId maintains context
client.invoke_agent_runtime(
    agentRuntimeArn='...',
    sessionId='user-123-session-456',  # Same session
    payload={'prompt': 'Follow-up question'}
)
```

### Error Handling

```python
@app.entrypoint
async def analyze_with_streaming(payload, context):  # Must be async
    try:
        yield {"type": "thinking", "message": "Processing..."}
        result = await asyncio.to_thread(process_data)
        yield {"type": "final", "result": result}
    except Exception as e:
        yield {"type": "error", "message": str(e)}
```

## Cost Considerations

AgentCore Runtime uses consumption-based pricing:
- **CPU**: $0.0895 per vCPU-hour (only during active processing)
- **Memory**: $0.00945 per GB-hour

**Key**: During streaming (I/O wait for LLM responses), CPU is NOT charged.

## References

- [AgentCore Runtime Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AgentCore Pricing](https://aws.amazon.com/bedrock/agentcore/pricing/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Long-Running Tasks Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-long-run.html)
