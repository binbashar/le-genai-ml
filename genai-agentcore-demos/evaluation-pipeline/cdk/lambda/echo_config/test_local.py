#!/usr/bin/env python3
"""
Local test for echo_config Lambda

Tests Lambda function locally before deploying to AWS
"""

import json
from lambda_function import lambda_handler


def test_valid_config():
    """Test with valid configuration"""
    print("Test 1: Valid configuration")
    print("=" * 60)

    event = {
        "agent_name": "finance-personal-assistant",
        "start_date": "2025-11-24",
        "end_date": "2025-11-24",
        "limit": 10,
        "metrics": ["Builtin.Correctness"]
    }

    response = lambda_handler(event, None)
    print(json.dumps(response, indent=2))

    assert response['statusCode'] == 200, "Expected status 200"
    assert response['config'] == event, "Config should match input"
    print("✅ Test passed\n")


def test_missing_fields():
    """Test with missing required fields"""
    print("Test 2: Missing required fields")
    print("=" * 60)

    event = {
        "agent_name": "finance-personal-assistant",
        # Missing other fields
    }

    response = lambda_handler(event, None)
    print(json.dumps(response, indent=2))

    assert response['statusCode'] == 400, "Expected status 400"
    assert 'error' in response, "Expected error field"
    print("✅ Test passed\n")


if __name__ == "__main__":
    print("Running local Lambda tests")
    print("=" * 60)
    print()

    test_valid_config()
    test_missing_fields()

    print("=" * 60)
    print("✅ All tests passed!")
