#!/usr/bin/env python3
"""
Test the agent locally before testing the deployed version
"""
from market_trends_agent import market_trends_agent_local
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test 1: Broker profile acknowledgment
logger.info("\n" + "="*60)
logger.info("TEST 1: Broker Profile Acknowledgment")
logger.info("="*60)
test1_payload = {
    "prompt": "Hi, I'm Sarah Chen from Morgan Stanley. I focus on growth investing and tech stocks for younger clients. Please remember my profile."
}
response1 = market_trends_agent_local(test1_payload)
logger.info(f"Response: {response1[:200]}...")

# Test 2: Memory recall
logger.info("\n" + "="*60)
logger.info("TEST 2: Memory Recall")
logger.info("="*60)
test2_payload = {
    "prompt": "Hi, I'm Sarah Chen from Morgan Stanley. What do you remember about my investment preferences?"
}
response2 = market_trends_agent_local(test2_payload)
logger.info(f"Response: {response2[:500]}...")

logger.info("\n✅ Local agent tests completed!")
