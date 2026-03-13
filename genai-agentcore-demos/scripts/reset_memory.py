#!/usr/bin/env python3
"""
Reset memory for AWS Bedrock AgentCore agents.

Deletes ONLY runtime-created memories (LTM strategies or runtime STM).
Preserves the configured STM memory defined in .bedrock_agentcore.yaml.

Usage:
    # Preview what will be deleted
    uv run reset_memory.py --dry-run

    # Delete memory (requires confirmation)
    uv run reset_memory.py

    # Force delete without confirmation
    uv run reset_memory.py --force

    # Target specific agent
    uv run reset_memory.py --agent finance-personal-assistant
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml
from bedrock_agentcore.memory import MemoryClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def load_memory_config(agent_name: str) -> dict:
    """Load memory configuration from agent's .bedrock_agentcore.yaml."""
    agent_dir = Path(__file__).parent / agent_name
    config_file = agent_dir / ".bedrock_agentcore.yaml"

    if not config_file.exists():
        raise FileNotFoundError(f"Agent not configured: {config_file}")

    with open(config_file) as f:
        config = yaml.safe_load(f)

    agent_key = agent_name.replace("-", "_")
    agent_config = config["agents"][agent_key]
    memory_config = agent_config["memory"]

    return {
        "memory_id": memory_config["memory_id"],
        "memory_name": memory_config.get("memory_name", "unknown"),
        "region": agent_config["aws"]["region"],
    }


def reset_memory(agent_name: str, dry_run: bool, force: bool) -> bool:
    """Reset runtime-created memories for the specified agent.

    Preserves the configured STM memory from .bedrock_agentcore.yaml.
    Only deletes LTM and runtime-created STM memories.
    """
    try:
        # Load configuration
        logger.info(f"🎯 Agent: {agent_name}")
        config = load_memory_config(agent_name)

        configured_memory_id = config["memory_id"]
        configured_memory_name = config["memory_name"]
        region = config["region"]

        logger.info(f"🌍 Region: {region}")
        logger.info(
            f"🔒 Configured STM memory (will be preserved): {configured_memory_id}"
        )

        # Initialize client
        client = MemoryClient(region_name=region)

        # Find all memories for this agent
        all_memories = client.list_memories()

        # Map agent name to runtime memory name prefixes
        # These are the names used by create_memory() / create_or_get_memory() at runtime
        runtime_prefixes = {
            "finance-personal-assistant": "FinancePersonalAssistantMemory",
        }

        memories_to_delete = []

        # Find runtime-created memories (exclude configured STM memory)
        prefix = runtime_prefixes.get(agent_name)
        if prefix:
            for mem in all_memories:
                mem_id = mem.get("id", "")
                # Only delete runtime memories, not the configured one
                if mem_id.startswith(prefix) and mem_id != configured_memory_id:
                    memories_to_delete.append(
                        {"id": mem_id, "name": mem_id, "type": "runtime"}
                    )

        # Show what will be deleted
        if memories_to_delete:
            logger.info(
                f"\n📋 Found {len(memories_to_delete)} runtime memory instance(s) to delete:"
            )
            for mem in memories_to_delete:
                logger.info(f"   • {mem['id']} ({mem['type']})")
        else:
            logger.info("\n📋 No runtime memories found to delete")
            logger.info(
                "💡 All runtime memories have already been cleared or never existed"
            )
            return True

        if dry_run:
            logger.info(
                "\n✅ [DRY RUN] Runtime memories would be deleted (no changes made)"
            )
            logger.info(
                f"🔒 Configured memory will be preserved: {configured_memory_id}"
            )
            logger.info(
                "💡 Next agent invocation will auto-create fresh runtime memory"
            )
            return True

        # Confirmation
        if not force:
            print("\n⚠️  WARNING: This will PERMANENTLY DELETE runtime memory")
            print(f"   Agent: {agent_name}")
            print(f"   Runtime instances to delete: {len(memories_to_delete)}")
            print(f"   Configured STM (preserved): {configured_memory_id}")
            print("   Affects: ALL users and sessions (runtime data only)")
            print()
            response = input("Type 'DELETE' to confirm: ")
            if response != "DELETE":
                logger.info("❌ Cancelled")
                return False

        # Delete runtime memories
        logger.info(
            f"\n🗑️  Deleting {len(memories_to_delete)} runtime memory instance(s)..."
        )
        for mem in memories_to_delete:
            try:
                logger.info(f"   Deleting: {mem['id']}")
                client.delete_memory(mem["id"])
                logger.info(f"   ✅ Deleted: {mem['id']}")
            except Exception as e:
                logger.error(f"   ❌ Failed: {e}")

        logger.info("\n✅ Runtime memory reset complete")
        logger.info(f"🔒 Configured memory preserved: {configured_memory_id}")
        logger.info("💡 Next agent invocation will auto-create fresh runtime memory")

        return True

    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Reset memory for AWS Bedrock AgentCore agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--agent",
        default="finance-personal-assistant",
        help="Agent name (default: finance-personal-assistant)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without making changes",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    try:
        success = reset_memory(args.agent, args.dry_run, args.force)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Cancelled")
        sys.exit(130)


if __name__ == "__main__":
    main()
