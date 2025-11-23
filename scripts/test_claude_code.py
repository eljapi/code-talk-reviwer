#!/usr/bin/env python3
"""Test script for Claude Code tool integration.

This script tests the ClaudeCodeTool to verify it can:
1. Initialize properly with repository path
2. Execute coding tasks
3. Return meaningful results
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, will use system env vars
    pass

from src.voice_ai_assistant.agent.tools import ClaudeCodeTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_claude_code_tool():
    """Test the ClaudeCodeTool functionality."""

    # Get repository path from env or use current directory
    repository_path = os.getenv("REPOSITORY_BASE_PATH")
    if not repository_path:
        repository_path = os.getcwd()
        logger.info(f"No REPOSITORY_BASE_PATH set, using current directory: {repository_path}")
    else:
        logger.info(f"Using repository base path: {repository_path}")

    # Initialize tool
    logger.info("=" * 60)
    logger.info("Initializing ClaudeCodeTool...")
    logger.info("=" * 60)

    try:
        tool = ClaudeCodeTool(repository_path=repository_path)
        logger.info("✓ ClaudeCodeTool initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize ClaudeCodeTool: {e}")
        return False

    # Start the tool
    logger.info("\nStarting Claude Code SDK client...")
    try:
        await tool.start()
        logger.info("✓ Claude Code SDK client started successfully")
    except Exception as e:
        logger.error(f"✗ Failed to start Claude Code SDK client: {e}")
        return False

    # Test cases
    test_cases = [
        {
            "name": "List files in current project",
            "task": "List all Python files in the src directory of the code-talk-reviwer project"
        },
        {
            "name": "Read specific file",
            "task": "Read the file src/voice_ai_assistant/agent/tools.py and explain what it does"
        },
        {
            "name": "Search for pattern",
            "task": "Find all occurrences of 'ClaudeCodeTool' in the codebase"
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        logger.info("\n" + "=" * 60)
        logger.info(f"Test {i}/{len(test_cases)}: {test_case['name']}")
        logger.info("=" * 60)
        logger.info(f"Task: {test_case['task']}")
        logger.info("-" * 60)

        try:
            # Run the task
            result = await tool.run_coding_task(test_case['task'])

            # Log result
            logger.info("Result:")
            logger.info(result)
            logger.info("-" * 60)
            logger.info(f"✓ Test passed (result length: {len(result)} chars)")

            results.append({
                "test": test_case['name'],
                "status": "PASS",
                "result_length": len(result)
            })

        except Exception as e:
            logger.error(f"✗ Test failed with error: {e}")
            results.append({
                "test": test_case['name'],
                "status": "FAIL",
                "error": str(e)
            })

    # Stop the tool
    logger.info("\n" + "=" * 60)
    logger.info("Stopping Claude Code SDK client...")
    try:
        await tool.stop()
        logger.info("✓ Claude Code SDK client stopped successfully")
    except Exception as e:
        logger.error(f"✗ Failed to stop Claude Code SDK client: {e}")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')

    for result in results:
        status_symbol = "✓" if result['status'] == 'PASS' else "✗"
        logger.info(f"{status_symbol} {result['test']}: {result['status']}")
        if result['status'] == 'FAIL':
            logger.info(f"  Error: {result.get('error', 'Unknown')}")

    logger.info(f"\nTotal: {len(results)} tests")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info("=" * 60)

    return failed == 0


async def main():
    """Main entry point."""
    logger.info("Claude Code Tool Test Script")
    logger.info("=" * 60)

    # Check required env vars
    claude_api_key = os.getenv("CLAUDE_API_KEY")
    if not claude_api_key:
        logger.error("✗ CLAUDE_API_KEY environment variable not set")
        logger.error("Please set CLAUDE_API_KEY in your .env file")
        return 1

    logger.info("✓ CLAUDE_API_KEY is set")

    # Run tests
    success = await test_claude_code_tool()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
