#!/usr/bin/env python3
"""Quick health check for Finance Personal Assistant"""

import json
import os
import boto3
from config import get_region

def main():
    arn_file = ".agent_arn"
    if not os.path.exists(arn_file):
        print("❌ No .agent_arn file found. Deploy first.")
        return False

    with open(arn_file, "r") as f:
        runtime_arn = f.read().strip()

    print(f"Testing: {runtime_arn}")
    print("-" * 80)

    try:
        client = boto3.client("bedrock-agentcore", region_name=get_region())

        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            payload=json.dumps({"prompt": "Hello, are you operational?"})
        )

        if "response" in response:
            response_text = response["response"].read().decode("utf-8")
            print("✅ Finance Personal Assistant is HEALTHY")
            print(f"Response: {response_text[:300]}...")
            return True
        else:
            print(f"❌ Unexpected response format: {response}")
            return False

    except Exception as e:
        print(f"❌ Health check FAILED: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
