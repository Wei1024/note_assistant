#!/usr/bin/env python3
"""
Quick test script for synthesis endpoint
"""
import asyncio
from api.services.synthesis import synthesize_search_results


async def test_synthesis():
    """Test the synthesis function directly"""
    print("Testing synthesis service...")
    print("-" * 60)

    query = "what projects have I been working on?"
    print(f"Query: {query}\n")

    result = await synthesize_search_results(query, limit=5)

    print(f"Query: {result['query']}")
    print(f"Notes Analyzed: {result['notes_analyzed']}")
    print(f"Total Results: {len(result['search_results'])}")
    print(f"\nSummary:\n{result['summary']}")
    print(f"\n{'='*60}")

    if result['search_results']:
        print("\nSearch Results:")
        for i, hit in enumerate(result['search_results'][:3], 1):
            print(f"\n{i}. {hit['path']}")
            print(f"   Score: {hit['score']}")
            print(f"   Snippet: {hit['snippet'][:100]}...")


if __name__ == "__main__":
    asyncio.run(test_synthesis())
