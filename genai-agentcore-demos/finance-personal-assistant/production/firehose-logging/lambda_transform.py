"""
Firehose Lambda transformation function for AgentCore logs.

Transforms OpenTelemetry JSON logs into Bedrock Model Evaluation JSONL format.

Input: CloudWatch Logs subscription filter data (GZIP compressed, base64 encoded)
Output: JSONL format suitable for Bedrock LLM-as-a-judge evaluation

Bedrock Evaluation Format:
{
    "prompt": "The user's prompt/query",
    "modelResponses": [{
        "response": "The model's response",
        "modelIdentifier": "agent-name"
    }],
    "category": "optional category",
    "referenceResponse": "optional ground truth"
}
"""

import base64
import gzip
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Set to DEBUG for comprehensive logging


def extract_conversation_data(log_entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract prompt and response data from agent logs.

    Supports patterns:
    1. EVAL_PROMPT: <text> / EVAL_RESPONSE: <text> (simple format from agent)
    2. JSON body with "prompt" or "response" keys
    3. Plain text with markers

    Returns dict with 'prompt', 'response', 'agent', 'trace_id' if found,
    otherwise None.
    """
    try:
        message = log_entry.get("message", "")

        # Pattern 1: Simple EVAL_PROMPT/EVAL_RESPONSE markers (including logger prefix)
        if isinstance(message, str):
            # Handle both "EVAL_PROMPT:" and "INFO:__main__:EVAL_PROMPT:"
            if "EVAL_PROMPT:" in message:
                prompt_text = message.split("EVAL_PROMPT:", 1)[1].strip()
                return {
                    "type": "prompt",
                    "prompt": prompt_text,
                    "timestamp": log_entry.get("timestamp"),
                }
            elif "EVAL_RESPONSE:" in message:
                response_text = message.split("EVAL_RESPONSE:", 1)[1].strip()
                return {
                    "type": "response",
                    "response": response_text,
                    "timestamp": log_entry.get("timestamp"),
                }

        # Parse OTEL JSON format
        if isinstance(message, str):
            try:
                message_data = json.loads(message)
            except json.JSONDecodeError:
                return None
        else:
            message_data = message

        # Look for OTel format
        body = message_data.get("body", "")
        resource = message_data.get("resource", {}).get("attributes", {})
        agent_name = resource.get("service.name", "unknown-agent")
        trace_id = message_data.get("traceId", "")

        # Pattern 2: OTEL body with EVAL markers
        if isinstance(body, str):
            if body.startswith("EVAL_PROMPT:"):
                return {
                    "type": "prompt",
                    "prompt": body.replace("EVAL_PROMPT:", "").strip(),
                    "agent": agent_name,
                    "trace_id": trace_id,
                    "timestamp": log_entry.get("timestamp"),
                }
            elif body.startswith("EVAL_RESPONSE:"):
                return {
                    "type": "response",
                    "response": body.replace("EVAL_RESPONSE:", "").strip(),
                    "agent": agent_name,
                    "trace_id": trace_id,
                    "timestamp": log_entry.get("timestamp"),
                }

            # Pattern 3: JSON body with prompt/response
            try:
                body_json = json.loads(body)
                if "prompt" in body_json or "response" in body_json:
                    return {
                        "prompt": body_json.get("prompt"),
                        "response": body_json.get("response"),
                        "agent": agent_name,
                        "trace_id": trace_id,
                        "timestamp": log_entry.get("timestamp"),
                    }
            except json.JSONDecodeError:
                pass

            # Pattern 4: Look for structured logging patterns
            if "USER PROMPT:" in body or "User prompt:" in body:
                lines = body.split("\n")
                prompt = None
                for line in lines:
                    if "prompt:" in line.lower():
                        prompt = line.split(":", 1)[1].strip()
                        break

                if prompt:
                    return {
                        "prompt": prompt,
                        "response": None,  # Will be matched later
                        "agent": agent_name,
                        "trace_id": trace_id,
                        "timestamp": log_entry.get("timestamp"),
                    }

        # Pattern 3: Attributes contain structured data
        if "gen_ai.prompt" in attributes or "gen_ai.completion" in attributes:
            return {
                "prompt": attributes.get("gen_ai.prompt"),
                "response": attributes.get("gen_ai.completion"),
                "agent": agent_name,
                "trace_id": trace_id,
                "timestamp": log_entry.get("timestamp"),
            }

        return None

    except Exception as e:
        logger.warning(f"Error extracting conversation data: {e}")
        return None


def group_by_timestamp(conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group prompts and responses by timestamp proximity (within 60 seconds).

    Returns list of complete conversation records.
    """
    prompts = [c for c in conversations if c.get("type") == "prompt"]
    responses = [c for c in conversations if c.get("type") == "response"]

    # Sort by timestamp
    prompts.sort(key=lambda x: x.get("timestamp", 0))
    responses.sort(key=lambda x: x.get("timestamp", 0))

    complete = []
    for prompt in prompts:
        # Find the next response after this prompt (within 60 seconds)
        prompt_ts = prompt.get("timestamp", 0)
        for response in responses:
            response_ts = response.get("timestamp", 0)
            # Response should be after prompt and within 60 seconds
            if response_ts > prompt_ts and (response_ts - prompt_ts) < 60000:
                complete.append(
                    {
                        "prompt": prompt.get("prompt"),
                        "response": response.get("response"),
                        "agent": prompt.get("agent", "finance_personal_assistant"),
                        "timestamp": prompt_ts,
                    }
                )
                responses.remove(response)  # Don't reuse this response
                break

    return complete


def to_bedrock_evaluation_format(conversation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert conversation data to Bedrock Model Evaluation format.

    Format:
    {
        "prompt": "user prompt",
        "modelResponses": [{
            "response": "model response",
            "modelIdentifier": "agent-name"
        }],
        "category": "optional",
        "referenceResponse": "optional ground truth"
    }
    """
    return {
        "prompt": conversation["prompt"],
        "modelResponses": [
            {
                "response": conversation["response"],
                "modelIdentifier": conversation["agent"],
            }
        ],
        # Optional fields can be added here if available
        # "category": conversation.get("category"),
        # "referenceResponse": conversation.get("ground_truth"),
    }


def lambda_handler(event, context):
    """
    Firehose transformation handler.

    Expected event format:
    {
        "records": [
            {
                "recordId": "...",
                "data": "base64-encoded-gzipped-cloudwatch-logs"
            }
        ]
    }

    Returns:
    {
        "records": [
            {
                "recordId": "...",
                "result": "Ok|Dropped|ProcessingFailed",
                "data": "base64-encoded-transformed-data"
            }
        ]
    }
    """
    # DEBUG: Log complete incoming event
    logger.debug("=" * 80)
    logger.debug("LAMBDA INVOCATION - Complete Event Received")
    logger.debug("=" * 80)
    logger.debug(f"Event record count: {len(event.get('records', []))}")
    logger.debug(
        f"Complete event structure: {json.dumps(event, indent=2, default=str)}"
    )
    logger.debug("=" * 80)

    output_records = []

    for record in event["records"]:
        record_id = record["recordId"]

        try:
            # Decode and decompress CloudWatch Logs data
            compressed_data = base64.b64decode(record["data"])
            decompressed_data = gzip.decompress(compressed_data)
            log_data = json.loads(decompressed_data)

            # DEBUG: Log complete CloudWatch Logs data structure
            logger.debug("-" * 80)
            logger.debug(f"Record ID: {record_id}")
            logger.debug(
                f"CloudWatch Logs Data: {json.dumps(log_data, indent=2, default=str)}"
            )
            logger.debug("-" * 80)

            # CloudWatch subscription filter format
            log_events = log_data.get("logEvents", [])

            logger.info(
                f"Processing {len(log_events)} log events in record {record_id}"
            )

            # DEBUG: Log each individual log event
            for idx, log_event in enumerate(log_events):
                logger.debug(f"Log Event {idx + 1}/{len(log_events)}:")
                logger.debug(f"  Timestamp: {log_event.get('timestamp')}")
                logger.debug(
                    f"  Message: {log_event.get('message')[:500]}..."
                )  # First 500 chars
                logger.debug(
                    f"  Full event: {json.dumps(log_event, indent=2, default=str)}"
                )

            # Extract conversation data from all log events
            conversations = []
            for log_event in log_events:
                conv_data = extract_conversation_data(log_event)
                if conv_data:
                    conversations.append(conv_data)
                    # DEBUG: Log extracted conversation data
                    logger.debug(
                        f"Extracted conversation data: {json.dumps(conv_data, indent=2, default=str)}"
                    )
                else:
                    logger.debug(
                        f"No conversation data found in log event: {log_event.get('id', 'unknown')}"
                    )

            logger.info(f"Extracted {len(conversations)} conversation fragments")

            # Group by timestamp to match prompts with responses
            complete_conversations = group_by_timestamp(conversations)

            logger.info(f"Found {len(complete_conversations)} complete conversations")

            # DEBUG: Log complete conversations after grouping
            for idx, conv in enumerate(complete_conversations):
                logger.debug(
                    f"Complete Conversation {idx + 1}/{len(complete_conversations)}:"
                )
                logger.debug(f"  Trace ID: {conv.get('trace_id', 'N/A')}")
                logger.debug(f"  Agent: {conv.get('agent', 'N/A')}")
                logger.debug(
                    f"  Prompt: {conv.get('prompt', 'N/A')[:200]}..."
                )  # First 200 chars
                logger.debug(
                    f"  Response: {conv.get('response', 'N/A')[:200]}..."
                )  # First 200 chars

            # Transform to Bedrock evaluation format
            if complete_conversations:
                # Create JSONL output (one JSON object per line)
                jsonl_lines = []
                for conv in complete_conversations:
                    bedrock_format = to_bedrock_evaluation_format(conv)
                    jsonl_lines.append(json.dumps(bedrock_format))
                    # DEBUG: Log Bedrock evaluation format
                    logger.debug(
                        f"Bedrock Evaluation Format: {json.dumps(bedrock_format, indent=2, default=str)}"
                    )

                # Join with newlines
                output_data = "\n".join(jsonl_lines) + "\n"

                # DEBUG: Log final JSONL output
                logger.debug(f"Final JSONL Output ({len(output_data)} bytes):")
                logger.debug(output_data)

                # Encode for Firehose
                encoded_data = base64.b64encode(output_data.encode("utf-8")).decode(
                    "utf-8"
                )

                output_records.append(
                    {
                        "recordId": record_id,
                        "result": "Ok",
                        "data": encoded_data,
                    }
                )

                logger.info(
                    f"Successfully transformed {len(complete_conversations)} conversations"
                )
                logger.debug(
                    f"Output record result: Ok, data size: {len(encoded_data)} bytes"
                )
            else:
                # No conversation data found - drop this record
                logger.info(
                    f"No conversation data found in record {record_id}, dropping"
                )
                output_records.append(
                    {
                        "recordId": record_id,
                        "result": "Dropped",
                        "data": record["data"],  # Return original data
                    }
                )

        except Exception as e:
            logger.error(f"Error processing record {record_id}: {e}", exc_info=True)

            # Mark as processing failed
            output_records.append(
                {
                    "recordId": record_id,
                    "result": "ProcessingFailed",
                    "data": record["data"],
                }
            )

    return {"records": output_records}
