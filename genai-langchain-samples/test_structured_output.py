#!/usr/bin/env python3
"""
Test script for Bedrock structured output approaches.
"""

from config import Model
from structured_output import get_llm


def test_approaches():
    prompt = "Should we use containers in production?"

    print("\n" + "=" * 60)
    print("Testing ChatBedrockConverse (native support)")
    print("=" * 60)

    # Native structured output
    llm = get_llm(Model.NOVA_MICRO, use_bedrock_converse=True)
    result = llm.invoke(prompt)
    print(f"Type: {type(result).__name__} (Pydantic model)")
    print(f"Answer: {result.answer[:50]}...")

    print("\n" + "=" * 60)
    print("Testing ChatBedrock (JsonOutputParser)")
    print("=" * 60)

    # JsonOutputParser workaround
    llm = get_llm(Model.NOVA_MICRO, use_bedrock_converse=False)
    result = llm.invoke({"query": prompt})
    print(f"Type: {type(result).__name__} (dictionary)")
    print(f"Answer: {result['answer'][:50]}...")


if __name__ == "__main__":
    test_approaches()
    print("\n[SUCCESS] Both approaches work")
