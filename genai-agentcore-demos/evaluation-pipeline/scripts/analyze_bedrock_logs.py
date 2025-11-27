#!/usr/bin/env python3
"""
Bedrock Model Invocation Log Analyzer

This script helps you understand and retrieve data from Bedrock model invocation logs stored in S3.
It can:
1. Parse JSONL log files (gzipped or plain)
2. Search for specific prompts/responses
3. Extract conversation flows
4. Analyze token usage and performance metrics
"""

import json
import gzip
import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import argparse
from pathlib import Path
import sys


class BedrockLogAnalyzer:
    """Analyzer for Bedrock model invocation logs"""

    def __init__(
        self, bucket_name: str, profile: str = "binbash", region: str = "us-west-2"
    ):
        """
        Initialize the log analyzer

        Args:
            bucket_name: S3 bucket containing Bedrock logs
            profile: AWS profile to use
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.session = boto3.Session(profile_name=profile, region_name=region)
        self.s3 = self.session.client("s3")

    def list_log_files(
        self, prefix: str = "invocation-logging/", hours_back: int = 24
    ) -> List[str]:
        """
        List log files in the S3 bucket

        Args:
            prefix: S3 prefix to search under
            hours_back: How many hours back to search (default: 24)

        Returns:
            List of S3 keys for log files
        """
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        paginator = self.s3.get_paginator("list_objects_v2")
        log_files = []

        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                key = obj["Key"]
                # Skip permission check files
                if "permission-check" in key or obj["Size"] == 0:
                    continue

                # Check if file is recent enough
                if obj["LastModified"].replace(tzinfo=None) >= cutoff_time:
                    log_files.append(key)

        return sorted(log_files, reverse=True)  # Most recent first

    def download_and_parse_log(self, s3_key: str) -> List[Dict[str, Any]]:
        """
        Download and parse a log file from S3

        Args:
            s3_key: S3 key of the log file

        Returns:
            List of parsed log records
        """
        # Download file
        response = self.s3.get_object(Bucket=self.bucket_name, Key=s3_key)
        content = response["Body"].read()

        # Decompress if gzipped
        if s3_key.endswith(".gz"):
            content = gzip.decompress(content)

        # Parse JSONL (each line is a separate JSON object)
        records = []
        for line in content.decode("utf-8").strip().split("\n"):
            if line:
                records.append(json.loads(line))

        return records

    def extract_user_prompt(self, record: Dict[str, Any]) -> Optional[str]:
        """
        Extract the actual user prompt from a log record

        Args:
            record: Bedrock log record

        Returns:
            User prompt text or None
        """
        try:
            messages = record["input"]["inputBodyJson"]["messages"]

            # Find the last user message
            for msg in reversed(messages):
                if msg["role"] == "user":
                    # Extract text from content
                    for content in msg["content"]:
                        if "text" in content:
                            text = content["text"]

                            # Remove memory context if present
                            if "<retrieved_memories>" in text:
                                # Extract just the user prompt after memories
                                parts = text.split("User:")
                                if len(parts) > 1:
                                    return parts[-1].strip()

                            return text.strip()

            return None
        except (KeyError, IndexError):
            return None

    def extract_assistant_response(self, record: Dict[str, Any]) -> Optional[str]:
        """
        Extract the assistant's response from a log record

        Args:
            record: Bedrock log record

        Returns:
            Assistant response text or None
        """
        try:
            output = record["output"]["outputBodyJson"]["output"]

            # Handle different response structures
            if "message" in output:
                message = output["message"]
                if "content" in message:
                    text_parts = []
                    for content in message["content"]:
                        if "text" in content:
                            text_parts.append(content["text"])
                        elif "toolUse" in content:
                            tool_use = content["toolUse"]
                            text_parts.append(f"[Tool Call: {tool_use['name']}]")

                    return "\n".join(text_parts)

            return None
        except (KeyError, IndexError):
            return None

    def get_token_stats(self, record: Dict[str, Any]) -> Dict[str, int]:
        """
        Extract token usage statistics

        Args:
            record: Bedrock log record

        Returns:
            Dict with inputTokens, outputTokens, totalTokens
        """
        try:
            usage = record["output"]["outputBodyJson"]["usage"]
            return {
                "inputTokens": usage.get("inputTokens", 0),
                "outputTokens": usage.get("outputTokens", 0),
                "totalTokens": usage.get("totalTokens", 0),
                "latencyMs": record["output"]["outputBodyJson"]["metrics"].get(
                    "latencyMs", 0
                ),
            }
        except (KeyError, IndexError):
            return {
                "inputTokens": 0,
                "outputTokens": 0,
                "totalTokens": 0,
                "latencyMs": 0,
            }

    def search_prompts(
        self, search_term: str, hours_back: int = 24, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for prompts containing a specific term

        Args:
            search_term: Term to search for (case-insensitive)
            hours_back: How many hours back to search
            max_results: Maximum number of results to return

        Returns:
            List of matching records with extracted data
        """
        log_files = self.list_log_files(hours_back=hours_back)
        results = []

        for log_file in log_files:
            if len(results) >= max_results:
                break

            print(f"Searching {log_file}...", file=sys.stderr)
            records = self.download_and_parse_log(log_file)

            for record in records:
                if len(results) >= max_results:
                    break

                prompt = self.extract_user_prompt(record)
                if prompt and search_term.lower() in prompt.lower():
                    response = self.extract_assistant_response(record)
                    tokens = self.get_token_stats(record)

                    results.append(
                        {
                            "timestamp": record["timestamp"],
                            "requestId": record["requestId"],
                            "modelId": record["modelId"],
                            "operation": record["operation"],
                            "prompt": prompt,
                            "response": response,
                            "tokens": tokens,
                            "raw_record": record,
                        }
                    )

        return results

    def analyze_conversation_flow(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Analyze conversation flow by grouping related requests

        Args:
            hours_back: How many hours back to analyze

        Returns:
            List of conversation turns with full context
        """
        log_files = self.list_log_files(hours_back=hours_back)
        conversations = []

        for log_file in log_files:
            print(f"Analyzing {log_file}...", file=sys.stderr)
            records = self.download_and_parse_log(log_file)

            for record in records:
                prompt = self.extract_user_prompt(record)
                response = self.extract_assistant_response(record)
                tokens = self.get_token_stats(record)

                # Extract conversation history from input
                messages = record["input"]["inputBodyJson"].get("messages", [])
                history = []

                for msg in messages[:-1]:  # Exclude the current user message
                    role = msg["role"]
                    text_parts = []
                    for content in msg.get("content", []):
                        if "text" in content:
                            text_parts.append(content["text"])

                    if text_parts:
                        history.append({"role": role, "content": "\n".join(text_parts)})

                conversations.append(
                    {
                        "timestamp": record["timestamp"],
                        "requestId": record["requestId"],
                        "modelId": record["modelId"],
                        "history": history,
                        "current_prompt": prompt,
                        "current_response": response,
                        "tokens": tokens,
                    }
                )

        return sorted(conversations, key=lambda x: x["timestamp"])

    def print_log_structure(self, hours_back: int = 1):
        """
        Print the structure of a sample log record for documentation

        Args:
            hours_back: How many hours back to search for sample
        """
        log_files = self.list_log_files(hours_back=hours_back)

        if not log_files:
            print("No log files found!", file=sys.stderr)
            return

        records = self.download_and_parse_log(log_files[0])

        if not records:
            print("No records found in log file!", file=sys.stderr)
            return

        sample = records[0]

        print("=" * 80)
        print("BEDROCK MODEL INVOCATION LOG STRUCTURE")
        print("=" * 80)
        print()
        print("Top-level fields:")
        for key in sample.keys():
            print(f"  - {key}: {type(sample[key]).__name__}")
        print()

        print("Input structure:")
        print(f"  - inputContentType: {sample['input']['inputContentType']}")
        print(f"  - inputBodyJson.messages: List of message objects")
        print(f"  - inputBodyJson.system: List of system prompts")
        print(f"  - inputBodyJson.inferenceConfig: Model parameters")
        print(f"  - inputBodyJson.toolConfig: Tool definitions (if applicable)")
        print()

        print("Output structure:")
        print(f"  - outputContentType: {sample['output']['outputContentType']}")
        print(f"  - outputBodyJson.output.message: Assistant response")
        print(f"  - outputBodyJson.stopReason: Why generation stopped")
        print(f"  - outputBodyJson.usage: Token counts")
        print(f"  - outputBodyJson.metrics: Performance metrics")
        print()

        print("Full sample record (formatted JSON):")
        print(json.dumps(sample, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Bedrock model invocation logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for "Hello world" prompt in last 24 hours
  python analyze_bedrock_logs.py search "Hello world" --bucket bb-bedrock-invocations-ab4d1c24

  # Analyze conversation flow in last 6 hours
  python analyze_bedrock_logs.py conversation --hours 6 --bucket bb-bedrock-invocations-ab4d1c24

  # Print log structure documentation
  python analyze_bedrock_logs.py structure --bucket bb-bedrock-invocations-ab4d1c24
        """,
    )

    parser.add_argument(
        "command",
        choices=["search", "conversation", "structure"],
        help="Command to execute",
    )
    parser.add_argument(
        "search_term", nargs="?", help="Search term (for search command)"
    )
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument(
        "--profile", default="binbash", help="AWS profile (default: binbash)"
    )
    parser.add_argument(
        "--region", default="us-west-2", help="AWS region (default: us-west-2)"
    )
    parser.add_argument(
        "--hours", type=int, default=24, help="Hours back to search (default: 24)"
    )
    parser.add_argument(
        "--max-results", type=int, default=10, help="Max search results (default: 10)"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.command == "search" and not args.search_term:
        parser.error("search command requires search_term argument")

    # Initialize analyzer
    analyzer = BedrockLogAnalyzer(
        bucket_name=args.bucket, profile=args.profile, region=args.region
    )

    # Execute command
    if args.command == "search":
        print(
            f"Searching for: '{args.search_term}' in last {args.hours} hours...\n",
            file=sys.stderr,
        )
        results = analyzer.search_prompts(
            args.search_term, hours_back=args.hours, max_results=args.max_results
        )

        if not results:
            print("No matching prompts found!", file=sys.stderr)
            sys.exit(1)

        print(f"\nFound {len(results)} matching prompts:\n")
        for i, result in enumerate(results, 1):
            print(f"{'=' * 80}")
            print(f"Result {i}/{len(results)}")
            print(f"{'=' * 80}")
            print(f"Timestamp: {result['timestamp']}")
            print(f"Model: {result['modelId']}")
            print(f"Request ID: {result['requestId']}")
            print()
            print(f"USER PROMPT:")
            print(f"{result['prompt']}")
            print()
            print(f"ASSISTANT RESPONSE:")
            print(f"{result['response']}")
            print()
            print(
                f"TOKENS: Input={result['tokens']['inputTokens']}, "
                f"Output={result['tokens']['outputTokens']}, "
                f"Total={result['tokens']['totalTokens']}, "
                f"Latency={result['tokens']['latencyMs']}ms"
            )
            print()

    elif args.command == "conversation":
        print(
            f"Analyzing conversation flow in last {args.hours} hours...\n",
            file=sys.stderr,
        )
        conversations = analyzer.analyze_conversation_flow(hours_back=args.hours)

        if not conversations:
            print("No conversations found!", file=sys.stderr)
            sys.exit(1)

        print(f"\nFound {len(conversations)} conversation turns:\n")
        for i, conv in enumerate(conversations, 1):
            print(f"{'=' * 80}")
            print(f"Turn {i}/{len(conversations)} - {conv['timestamp']}")
            print(f"{'=' * 80}")

            if conv["history"]:
                print("CONVERSATION HISTORY:")
                for msg in conv["history"]:
                    role_label = "USER" if msg["role"] == "user" else "ASSISTANT"
                    content = msg["content"]
                    # Truncate long content
                    if len(content) > 200:
                        content = content[:200] + "... [truncated]"
                    print(f"  [{role_label}]: {content}")
                print()

            print(f"CURRENT PROMPT:")
            print(f"{conv['current_prompt']}")
            print()
            print(f"CURRENT RESPONSE:")
            print(f"{conv['current_response']}")
            print()
            print(
                f"TOKENS: Input={conv['tokens']['inputTokens']}, "
                f"Output={conv['tokens']['outputTokens']}, "
                f"Total={conv['tokens']['totalTokens']}, "
                f"Latency={conv['tokens']['latencyMs']}ms"
            )
            print()

    elif args.command == "structure":
        analyzer.print_log_structure(hours_back=args.hours)


if __name__ == "__main__":
    main()
