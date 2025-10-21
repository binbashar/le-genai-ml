#!/usr/bin/env python3
"""
Test Nova Micro's native structured output capability.
"""

from enum import Enum
from typing import List

from langchain_aws import ChatBedrockConverse
from pydantic import BaseModel, Field

from config import Model, get_bedrock_client_kwargs


# Test 1: Simple Response
class SimpleResponse(BaseModel):
    answer: str = Field(description="The answer")
    confidence: float = Field(description="Confidence level (0-1)", ge=0, le=1)


# Test 2: Complex nested structure
class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Task(BaseModel):
    title: str = Field(description="Task title")
    description: str = Field(description="Task description")
    priority: Priority = Field(description="Task priority")
    estimated_hours: float = Field(description="Estimated hours to complete")


class ProjectPlan(BaseModel):
    project_name: str = Field(description="Project name")
    summary: str = Field(description="Project summary")
    tasks: List[Task] = Field(description="List of tasks")
    total_hours: float = Field(description="Total estimated hours")
    risks: List[str] = Field(description="Potential risks")


def test_simple_structure():
    """Test Nova Micro with simple structured output."""
    print("\n" + "=" * 60)
    print("TEST 1: Simple Structured Output")
    print("=" * 60)

    model = Model.NOVA_MICRO
    llm = ChatBedrockConverse(
        model=model.value.id, **model.value.get_params(), **get_bedrock_client_kwargs()
    )

    try:
        structured_llm = llm.with_structured_output(SimpleResponse)
        result = structured_llm.invoke("Is Python good for data science?")

        print("SUCCESS: Nova Micro works with native structured output!")
        print(f"Result type: {type(result)}")
        print(f"Answer: {result.answer}")
        print(f"Confidence: {result.confidence:.2%}")
        return True
    except Exception as e:
        print("FAILED: Nova Micro doesn't support native structured output")
        print(f"Error: {e}")
        return False


def test_complex_structure():
    """Test Nova Micro with complex nested structured output."""
    print("\n" + "=" * 60)
    print("TEST 2: Complex Nested Structured Output")
    print("=" * 60)

    model = Model.NOVA_MICRO
    llm = ChatBedrockConverse(
        model=model.value.id, **model.value.get_params(), **get_bedrock_client_kwargs()
    )

    try:
        structured_llm = llm.with_structured_output(ProjectPlan)
        result = structured_llm.invoke(
            "Create a project plan for building a simple e-commerce website. "
            "Include at least 3 tasks with priorities and time estimates."
        )

        print("SUCCESS: Nova Micro handles complex structures!")
        print(f"\nProject: {result.project_name}")
        print(f"Summary: {result.summary}")
        print(f"Total Hours: {result.total_hours}")
        print(f"\nTasks ({len(result.tasks)}):")
        for i, task in enumerate(result.tasks, 1):
            print(f"  {i}. {task.title}")
            print(f"     Priority: {task.priority}")
            print(f"     Hours: {task.estimated_hours}")
        print(f"\nRisks ({len(result.risks)}):")
        for risk in result.risks:
            print(f"  - {risk}")
        return True
    except Exception as e:
        print("FAILED: Nova Micro can't handle complex structures")
        print(f"Error: {e}")
        return False


def compare_with_claude():
    """Compare Nova Micro with Claude Haiku."""
    print("\n" + "=" * 60)
    print("COMPARISON: Nova Micro vs Claude Haiku")
    print("=" * 60)

    for model_enum in [Model.NOVA_MICRO, Model.CLAUDE_HAIKU]:
        print(f"\nTesting {model_enum.value.name}...")

        llm = ChatBedrockConverse(
            model=model_enum.value.id,
            **model_enum.value.get_params(),
            **get_bedrock_client_kwargs(),
        )

        try:
            structured_llm = llm.with_structured_output(SimpleResponse)
            result = structured_llm.invoke("Is TypeScript better than JavaScript?")
            print(
                f"  SUCCESS: {model_enum.value.name} supports native structured output"
            )
            print(f"     Answer: {result.answer[:50]}...")
        except Exception as e:
            print(f"  FAILED: {model_enum.value.name} failed: {str(e)[:100]}...")


if __name__ == "__main__":
    # Run all tests
    simple_works = test_simple_structure()
    complex_works = test_complex_structure()
    compare_with_claude()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if simple_works and complex_works:
        print("Nova Micro FULLY supports native structured output")
    elif simple_works:
        print("WARNING: Nova Micro partially supports structured output")
        print("Works for simple cases but fails on complex structures")
    else:
        print("Nova Micro does NOT support native structured output")
        print("JsonOutputParser is needed")
