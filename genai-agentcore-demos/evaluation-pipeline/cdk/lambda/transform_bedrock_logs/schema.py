"""
Parquet Schema Definition for Bedrock Invocation Logs

Defines the structured schema for storing Bedrock agent conversations
in a queryable Parquet format.

17 columns total:
- Metadata (5): timestamp, request_id, agent_name, model_id, region
- Input (2): prompt, system_prompt
- Output (3): response, stop_reason, finish_reason
- Token Metrics (4): input_tokens, output_tokens, total_tokens, latency_ms
- Error Handling (1): error_message
- Partitioning (2): _agent_name, _date (for Athena efficiency)
"""

import re
from typing import Dict, Any, Optional
import pyarrow as pa


# Parquet schema definition
BEDROCK_LOG_SCHEMA = pa.schema([
    # Metadata fields
    ('timestamp', pa.timestamp('ms', tz='UTC')),
    ('request_id', pa.string()),
    ('agent_name', pa.string()),
    ('model_id', pa.string()),
    ('region', pa.string()),

    # Input fields
    ('prompt', pa.string()),
    ('system_prompt', pa.string()),

    # Output fields
    ('response', pa.string()),
    ('stop_reason', pa.string()),
    ('finish_reason', pa.string()),

    # Token metrics
    ('input_tokens', pa.int64()),
    ('output_tokens', pa.int64()),
    ('total_tokens', pa.int64()),
    ('latency_ms', pa.int64()),

    # Error handling
    ('error_message', pa.string()),

    # Partition keys (for Athena efficiency)
    ('_agent_name', pa.string()),
    ('_date', pa.string()),  # Format: YYYY-MM-DD
])


def extract_structured_record(bedrock_log: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured data from Bedrock invocation log.

    Transforms raw Bedrock log format into flat Parquet-compatible record.

    Args:
        bedrock_log: Raw Bedrock invocation log from CloudWatch

    Returns:
        Flat dictionary matching BEDROCK_LOG_SCHEMA
    """
    # Extract metadata
    timestamp = bedrock_log.get('timestamp')
    request_id = bedrock_log.get('requestId', '')
    model_id = bedrock_log.get('modelId', '')
    region = bedrock_log.get('region', '')

    # Extract agent name from identity ARN (AgentCore Runtime pattern)
    # Format: arn:aws:sts::ACCOUNT:assumed-role/BedrockAgentCore-{agent_name}-execution-role/...
    identity_arn = bedrock_log.get('identity', {}).get('arn', '')

    # Extract input
    input_data = bedrock_log.get('input', {})
    input_body = input_data.get('inputBodyJson', {})

    # Extract prompt from messages array (Converse API format)
    prompt = ''
    messages = input_body.get('messages', [])
    if messages and isinstance(messages, list):
        # Get last user message
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                content = msg.get('content', [])
                if isinstance(content, list):
                    text_blocks = [
                        block.get('text', '')
                        for block in content
                        if block.get('text')
                    ]
                    prompt = ' '.join(text_blocks)
                    break

    # Extract system prompt if available
    system_prompt = ''
    system_data = input_body.get('system', [])
    if isinstance(system_data, list):
        system_blocks = [
            block.get('text', '')
            for block in system_data
            if block.get('text')
        ]
        system_prompt = ' '.join(system_blocks)

    # Extract output
    output_data = bedrock_log.get('output', {})
    output_body = output_data.get('outputBodyJson', {})
    output_obj = output_body.get('output', {})
    message = output_obj.get('message', {})

    # Extract response text from content blocks
    response = ''
    content = message.get('content', [])
    if isinstance(content, list):
        text_blocks = [
            block.get('text', '')
            for block in content
            if block.get('text')
        ]
        response = ' '.join(text_blocks)

    stop_reason = output_data.get('stopReason', '')
    finish_reason = message.get('finishReason', '')

    # Extract token metrics
    usage = output_data.get('usage', {})
    input_tokens = usage.get('inputTokens', 0)
    output_tokens = usage.get('outputTokens', 0)
    total_tokens = usage.get('totalTokens', 0)

    # Calculate latency if available
    latency_ms = 0
    if 'metrics' in bedrock_log:
        latency_ms = bedrock_log['metrics'].get('latencyMs', 0)

    # Extract error if available
    error_message = bedrock_log.get('error', {}).get('message', '')

    # Partition keys
    # Agent name extracted from identity ARN (AgentCore Runtime)
    # Falls back to model family if no identity ARN
    agent_name = _extract_agent_name_from_identity(identity_arn) or _extract_model_family(model_id)
    date_partition = timestamp[:10] if timestamp else ''  # YYYY-MM-DD

    return {
        'timestamp': timestamp,
        'request_id': request_id,
        'agent_name': agent_name,
        'model_id': model_id,
        'region': region,
        'prompt': prompt,
        'system_prompt': system_prompt,
        'response': response,
        'stop_reason': stop_reason,
        'finish_reason': finish_reason,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'total_tokens': total_tokens,
        'latency_ms': latency_ms,
        'error_message': error_message,
        '_agent_name': agent_name,
        '_date': date_partition,
    }


def _extract_agent_name_from_identity(identity_arn: str) -> Optional[str]:
    """
    Extract AgentCore Runtime agent name from identity ARN.

    IAM role ARN format:
    arn:aws:sts::ACCOUNT:assumed-role/BedrockAgentCore-{agent_name}-execution-role/...

    Args:
        identity_arn: IAM role ARN from Bedrock invocation identity

    Returns:
        Agent name if found, None otherwise
    """
    if not identity_arn:
        return None

    # Pattern: BedrockAgentCore-{agent_name}-execution-role
    match = re.search(r'BedrockAgentCore-(.+?)-execution-role', identity_arn)
    if match:
        return match.group(1)

    return None


def _extract_model_family(model_id: str) -> str:
    """
    Extract model family from model ID.

    Fallback for non-AgentCore invocations or direct model calls.

    Args:
        model_id: Bedrock model ID (ARN or inference profile)

    Returns:
        Model family name for partitioning
    """
    if not model_id:
        return 'unknown'

    # Extract model family from common patterns
    # amazon.nova-lite-v1:0 → nova-lite
    # us.anthropic.claude-3-5-sonnet-20241022-v2:0 → claude-sonnet
    model_lower = model_id.lower()

    if 'nova-lite' in model_lower:
        return 'nova-lite'
    elif 'nova-pro' in model_lower:
        return 'nova-pro'
    elif 'nova-micro' in model_lower:
        return 'nova-micro'
    elif 'nova-premier' in model_lower:
        return 'nova-premier'
    elif 'claude-3-5-sonnet' in model_lower or 'claude-sonnet' in model_lower:
        return 'claude-sonnet'
    elif 'claude-3-5-haiku' in model_lower or 'claude-haiku' in model_lower:
        return 'claude-haiku'
    elif 'claude-3-opus' in model_lower:
        return 'claude-opus'
    else:
        return 'unknown'
