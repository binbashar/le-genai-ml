#!/usr/bin/env python3
"""
Tests market-trends-agent and finance-personal-assistant
"""

import os
import subprocess
import sys
from pathlib import Path


def test_agent(name: str, agent_dir: Path) -> dict:
    """Test a single agent by running its health_check.py script.
    Returns a dictionary with the agent name, status, ARN, output, and error.
    """
    result = {
        "name": name,
        "status": "unknown",
        "arn": None,
        "output": None,
        "error": None,
    }

    health_check_script = agent_dir / "health.py"
    arn_file = agent_dir / ".agent_arn"

    if not health_check_script.exists():
        result["status"] = "missing_script"
        result["error"] = f"No health_check.py found in {agent_dir}"
        return result

    if not arn_file.exists():
        result["status"] = "not_deployed"
        result["error"] = "No .agent_arn file found. Use agentcore status"
        return result

    result["arn"] = arn_file.read_text().strip()

    try:
        env = os.environ.copy()
        proc = subprocess.run(
            ["uv", "run", "python", "health.py"],
            cwd=agent_dir,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )

        result["output"] = proc.stdout

        if proc.returncode == 0:
            result["status"] = "healthy"
        else:
            result["status"] = "error"
            result["error"] = proc.stderr or "Health check failed"

    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        result["error"] = "Health check timed out after 120s"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def main():
    """Run health check for all agents"""
    print("=" * 80)
    print("AGENTCORE DEMOS - HEALTH CHECK ALL")
    print("=" * 80)
    print()

    base_dir = Path(__file__).parent

    agents = [
        {
            "name": "Market Trends Agent",
            "dir": base_dir / "market-trends-agent",
        },
        {
            "name": "Finance Personal Assistant",
            "dir": base_dir / "finance-personal-assistant",
        },
    ]

    results = []
    for agent_config in agents:
        print(f"Testing: {agent_config['name']}")
        print("-" * 80)

        result = test_agent(agent_config["name"], agent_config["dir"])
        results.append(result)

        if result["status"] == "healthy":
            print(result["output"])
        elif result["status"] == "not_deployed":
            print("⚠️  Status: NOT DEPLOYED")
            print(f"   {result['error']}")
        elif result["status"] == "missing_script":
            print("⚠️  Status: MISSING HEALTH CHECK")
            print(f"   {result['error']}")
        else:
            print(f"❌ Status: {result['status'].upper()}")
            if result["arn"]:
                print(f"   ARN: {result['arn']}")
            print(f"   Error: {result['error']}")

        print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    healthy_count = sum(1 for r in results if r["status"] == "healthy")
    total_count = len(results)

    print(f"Total Agents: {total_count}")
    print(f"Healthy: {healthy_count}")
    print(f"Errors: {total_count - healthy_count}")
    print()

    if healthy_count == total_count:
        print("✅ ALL SYSTEMS HEALTHY!")
        return 0
    elif healthy_count > 0:
        print("⚠️  PARTIAL SYSTEM HEALTH")
        return 1
    else:
        print("❌ ALL SYSTEMS DOWN")
        return 2


if __name__ == "__main__":
    sys.exit(main())
