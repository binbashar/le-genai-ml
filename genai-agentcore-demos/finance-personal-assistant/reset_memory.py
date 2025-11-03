#!/usr/bin/env python3
"""
Reset AgentCore Memory data while preserving agent infrastructure.

This script deletes the AgentCore Memory instance, then the agent will
automatically recreate it on next invocation with fresh data.

Safer than full cleanup.py since it only affects memory data, not the agent runtime.
"""

import argparse
import logging
import sys

from config import get_region

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def reset_memory(dry_run: bool = False):
    """Delete and recreate the memory instance to clear all stored data."""

    logger.info("=" * 70)
    logger.info("Memory Reset Utility")
    logger.info("=" * 70)

    # Get region
    region = get_region()
    logger.info(f"Region: {region}")

    # Initialize memory client
    from bedrock_agentcore.memory import MemoryClient
    client = MemoryClient(region_name=region)

    # Find existing memory
    logger.info("\n🔍 Searching for existing memory instances...")
    try:
        memories = client.list_memories()
        finance_memories = [
            m for m in memories
            if m.get("id", "").startswith("finance_personal_assistant_mem")
        ]

        if not finance_memories:
            logger.info("✓ No memory instances found - nothing to reset")
            return

        logger.info(f"Found {len(finance_memories)} memory instance(s):")
        for mem in finance_memories:
            logger.info(f"  • {mem.get('id')} (status: {mem.get('status')})")

        if dry_run:
            logger.info("\n🔍 DRY RUN - Would delete these memories (but not actually deleting)")
            return

        # Confirm deletion
        print("\n⚠️  WARNING: This will delete ALL stored memories (preferences, facts, summaries)")
        print("   The agent will recreate the memory instance on next invocation with fresh data.")
        confirm = input("\nType 'yes' to confirm deletion: ")

        if confirm.lower() != "yes":
            logger.info("❌ Reset cancelled")
            return

        # Delete each memory instance
        logger.info("\n🗑️  Deleting memory instances...")
        for mem in finance_memories:
            memory_id = mem.get("id")
            try:
                logger.info(f"  Deleting: {memory_id}")
                client.delete_memory(memory_id)
                logger.info(f"  ✅ Deleted: {memory_id}")
            except Exception as e:
                logger.error(f"  ❌ Failed to delete {memory_id}: {e}")

        logger.info("\n✅ Memory reset complete!")
        logger.info("   Next agent invocation will create a fresh memory instance")

    except Exception as e:
        logger.error(f"❌ Error during memory reset: {e}", exc_info=True)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Reset AgentCore Memory data"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )

    args = parser.parse_args()

    reset_memory(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
