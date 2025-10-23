#!/usr/bin/env python3
"""Quick test for search agent"""
import requests
import json

BACKEND_URL = "http://127.0.0.1:8787"

def test_search_agent():
    query = "what's the sport I recently watched?"

    print(f"Testing search agent with query: '{query}'")
    print("=" * 60)

    response = requests.post(
        f"{BACKEND_URL}/search_with_agent",
        json={"query": query, "limit": 10},
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()

        print("\n🔍 AGENT TRACE:")
        print("-" * 60)
        for i, step in enumerate(data.get("steps", []), 1):
            if step["type"] == "thought":
                content = step['content']
                if len(content) > 150:
                    content = content[:150] + "..."
                print(f"\n💭 Step {i}: {content}")
            elif step["type"] == "tool_call":
                print(f"\n🔧 Step {i}: Calling {step['name']}")
                if "args" in step:
                    print(f"   Args: {json.dumps(step['args'], indent=2)}")
            elif step["type"] == "tool_response":
                print(f"\n📥 Step {i}: Tool Response")
                content = step['content']
                if len(content) > 200:
                    content = content[:200] + "..."
                print(f"   {content}")

        print("\n" + "=" * 60)
        print("💬 AGENT'S ANSWER:")
        print("-" * 60)

        final_answer = data.get("final_answer")
        if final_answer:
            print(f"\n{final_answer}\n")

        print("=" * 60)
        print("📋 STRUCTURED RESULTS:")
        print("-" * 60)

        results = data.get("results", [])
        if results:
            print(f"Found {len(results)} results:\n")
            for i, r in enumerate(results, 1):
                print(f"{i}. {r['path']}")
                print(f"   Score: {r['score']:.6f}")
                print(f"   {r['snippet']}")
                print()
        else:
            print("No results found")
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_search_agent()
