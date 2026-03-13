#!/usr/bin/env python3
"""
Test script for Lambda transformation function.

Tests the transformation of CloudWatch logs to Bedrock evaluation format.
"""

import base64
import gzip
import json
import sys
from pathlib import Path

# Add the current directory to the path so we can import lambda_transform
sys.path.insert(0, str(Path(__file__).parent))

from lambda_transform import lambda_handler


def create_test_event():
    """Create a test event mimicking CloudWatch Logs subscription filter data"""

    # Sample log events simulating agent invocation
    log_events = [
        {
            "id": "1",
            "timestamp": 1700000000000,
            "message": json.dumps(
                {
                    "resource": {
                        "attributes": {
                            "service.name": "finance_personal_assistant.DEFAULT",
                            "cloud.region": "us-west-2",
                        }
                    },
                    "scope": {"name": "__main__"},
                    "body": json.dumps(
                        {
                            "prompt": "I make $6000/month and want to save $1000. Help me create a budget.",
                        }
                    ),
                    "attributes": {
                        "otelTraceID": "trace123",
                    },
                    "traceId": "trace123",
                    "spanId": "span123",
                }
            ),
        },
        {
            "id": "2",
            "timestamp": 1700000010000,
            "message": json.dumps(
                {
                    "resource": {
                        "attributes": {
                            "service.name": "finance_personal_assistant.DEFAULT",
                            "cloud.region": "us-west-2",
                        }
                    },
                    "scope": {"name": "__main__"},
                    "body": json.dumps(
                        {
                            "response": "Here's a budget plan for your $6000 monthly income with $1000 savings goal:\n\n1. Savings: $1000 (16.7%)\n2. Housing: $1800 (30%)\n3. Food: $600 (10%)\n4. Transportation: $600 (10%)\n5. Utilities: $300 (5%)\n6. Entertainment: $300 (5%)\n7. Other: $1400 (23.3%)\n\nTotal: $6000",
                        }
                    ),
                    "attributes": {
                        "otelTraceID": "trace123",
                    },
                    "traceId": "trace123",
                    "spanId": "span124",
                }
            ),
        },
        # Second conversation
        {
            "id": "3",
            "timestamp": 1700000020000,
            "message": json.dumps(
                {
                    "resource": {
                        "attributes": {
                            "service.name": "finance_personal_assistant.DEFAULT",
                        }
                    },
                    "scope": {"name": "__main__"},
                    "body": json.dumps(
                        {
                            "prompt": "Analyze Apple stock (AAPL) and tell me if it's a good investment.",
                        }
                    ),
                    "attributes": {
                        "otelTraceID": "trace456",
                    },
                    "traceId": "trace456",
                    "spanId": "span201",
                }
            ),
        },
        {
            "id": "4",
            "timestamp": 1700000030000,
            "message": json.dumps(
                {
                    "resource": {
                        "attributes": {
                            "service.name": "finance_personal_assistant.DEFAULT",
                        }
                    },
                    "scope": {"name": "__main__"},
                    "body": json.dumps(
                        {
                            "response": "Apple Inc. (AAPL) Analysis:\n\nCurrent Price: $182.45\nMarket Cap: $2.85T\nP/E Ratio: 28.5\n\nStrengths:\n- Strong brand loyalty\n- Growing services revenue\n- Solid balance sheet\n\nRisks:\n- High valuation\n- Market saturation\n- Regulatory concerns\n\nRecommendation: BUY for long-term investors seeking stable growth.",
                        }
                    ),
                    "attributes": {
                        "otelTraceID": "trace456",
                    },
                    "traceId": "trace456",
                    "spanId": "span202",
                }
            ),
        },
    ]

    # Create CloudWatch Logs subscription filter payload
    cloudwatch_payload = {
        "messageType": "DATA_MESSAGE",
        "owner": "905418344519",
        "logGroup": "/aws/bedrock-agentcore/runtimes/finance_personal_assistant-cjhbtj2mQE-DEFAULT",
        "logStream": "test-stream",
        "subscriptionFilters": ["finance_personal_assistant-to-firehose"],
        "logEvents": log_events,
    }

    # Compress and encode (as CloudWatch subscription filter does)
    json_data = json.dumps(cloudwatch_payload).encode("utf-8")
    compressed_data = gzip.compress(json_data)
    encoded_data = base64.b64encode(compressed_data).decode("utf-8")

    # Create Firehose event structure
    firehose_event = {
        "records": [
            {
                "recordId": "test-record-1",
                "data": encoded_data,
            }
        ]
    }

    return firehose_event


def main():
    print("=" * 80)
    print("Testing Lambda Transformation Function")
    print("=" * 80)
    print()

    # Create test event
    print("1. Creating test event with sample AgentCore logs...")
    event = create_test_event()
    print(f"   ✅ Test event created with {len(event['records'])} record(s)")
    print()

    # Invoke Lambda handler
    print("2. Invoking Lambda handler...")
    try:
        result = lambda_handler(event, None)
        print(f"   ✅ Handler returned successfully")
        print()
    except Exception as e:
        print(f"   ❌ Handler failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Check results
    print("3. Checking transformation results...")
    output_records = result.get("records", [])
    print(f"   Output records: {len(output_records)}")
    print()

    for i, record in enumerate(output_records):
        print(f"   Record {i + 1}:")
        print(f"      Record ID: {record['recordId']}")
        print(f"      Result: {record['result']}")

        if record["result"] == "Ok":
            # Decode and display transformed data
            decoded_data = base64.b64decode(record["data"]).decode("utf-8")
            print(f"      Transformed Data ({len(decoded_data)} bytes):")
            print()

            # Parse JSONL and pretty-print each line
            for line_num, line in enumerate(decoded_data.strip().split("\n"), 1):
                if line.strip():
                    try:
                        json_obj = json.loads(line)
                        print(f"      --- Evaluation Record {line_num} ---")
                        print(f"      Prompt: {json_obj.get('prompt', '')[:80]}...")
                        print(
                            f"      Model ID: {json_obj.get('modelResponses', [{}])[0].get('modelIdentifier', 'N/A')}"
                        )
                        response_text = json_obj.get("modelResponses", [{}])[0].get(
                            "response", ""
                        )
                        print(f"      Response: {response_text[:80]}...")
                        print()
                    except json.JSONDecodeError as e:
                        print(f"      ⚠️  Invalid JSON on line {line_num}: {e}")
                        print(f"         {line[:100]}...")
                        print()
        elif record["result"] == "Dropped":
            print(f"      ℹ️  Record was dropped (no conversation data found)")
            print()
        else:
            print(f"      ❌ Processing failed")
            print()

    # Validation
    print("4. Validating Bedrock evaluation format...")
    success_count = sum(1 for r in output_records if r["result"] == "Ok")

    if success_count > 0:
        # Decode first successful record
        for record in output_records:
            if record["result"] == "Ok":
                decoded_data = base64.b64decode(record["data"]).decode("utf-8")
                lines = [
                    line for line in decoded_data.strip().split("\n") if line.strip()
                ]

                if lines:
                    first_record = json.loads(lines[0])

                    # Check required fields for Bedrock evaluation
                    required_fields = ["prompt", "modelResponses"]
                    missing_fields = [
                        f for f in required_fields if f not in first_record
                    ]

                    if missing_fields:
                        print(f"   ❌ Missing required fields: {missing_fields}")
                        return 1

                    # Check modelResponses structure
                    if not isinstance(first_record["modelResponses"], list):
                        print(f"   ❌ modelResponses must be a list")
                        return 1

                    if len(first_record["modelResponses"]) == 0:
                        print(f"   ❌ modelResponses is empty")
                        return 1

                    model_response = first_record["modelResponses"][0]
                    if (
                        "response" not in model_response
                        or "modelIdentifier" not in model_response
                    ):
                        print(f"   ❌ modelResponses items missing required fields")
                        return 1

                    print(f"   ✅ Format validation passed")
                    print(
                        f"   ✅ Transformed {len(lines)} conversation(s) to Bedrock evaluation format"
                    )
                    break
    else:
        print(f"   ⚠️  No successful transformations")

    print()
    print("=" * 80)
    print("✅ Test Complete!")
    print("=" * 80)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
