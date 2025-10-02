#!/usr/bin/env python3
"""
Test script to see detailed AI outputs for multi-tool queries
"""

import asyncio
import sys
import os

# Import from the main test file
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_litellm_agentic_loop import run_multi_tool, is_multi_tool_query

async def test_multi_tool_detailed():
    """Test multi-tool queries with detailed output"""

    # Test queries
    test_queries = [
        "What time is it in London and what's the weather there?",
        "Calculate 50 + 50 and tell me the current time"
    ]

    # Test with both models
    models = [
        ("ollama/gemma3:4b", "Gemma 3 (4B)"),
        ("ollama/qwen3:4b-instruct", "Qwen 3 (4B)")
    ]

    for query in test_queries:
        print("\n" + "="*80)
        print(f"TEST QUERY: {query}")
        print("="*80)

        for model_path, model_name in models:
            print(f"\n{'='*60}")
            print(f"MODEL: {model_name}")
            print(f"{'='*60}")

            # Check if it's detected as multi-tool
            is_multi = is_multi_tool_query(query)
            print(f"Detected as multi-tool query: {is_multi}")

            if is_multi:
                result = await run_multi_tool(query, model_path)
                print(f"\n🏁 FINAL RESULT: {result}")
            else:
                print("Not detected as multi-tool, skipping...")

            print("\n" + "-"*60)

if __name__ == "__main__":
    print("DETAILED MULTI-TOOL QUERY TESTING")
    print("="*80)
    asyncio.run(test_multi_tool_detailed())