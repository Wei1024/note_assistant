#!/usr/bin/env python3
"""Test full flow: capture note -> search for it"""
import requests
import time

BACKEND_URL = "http://127.0.0.1:8787"

def capture_note():
    note_text = "I watched the Toronto Blue Jays baseball game yesterday. They won 5-3!"

    print("=" * 60)
    print("STEP 1: CAPTURING NOTE")
    print("=" * 60)
    print(f"Note: {note_text}\n")

    response = requests.post(
        f"{BACKEND_URL}/classify_with_trace",
        json={"text": note_text},
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()

        print("🔍 Classification Agent Trace:")
        for step in data.get("steps", []):
            if step["type"] == "tool_call":
                print(f"  🔧 Called: {step['name']}")

        final = data.get("final", {})
        print(f"\n✅ Saved:")
        print(f"  Title: {final.get('title')}")
        print(f"  Folder: {final.get('folder')}")
        print(f"  Path: {final.get('path')}")
        print()
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        return False


def search_notes():
    query = "what's the sport I recently watched?"

    print("=" * 60)
    print("STEP 2: SEARCHING WITH AGENT")
    print("=" * 60)
    print(f"Query: {query}\n")

    response = requests.post(
        f"{BACKEND_URL}/search_with_agent",
        json={"query": query, "limit": 10},
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()

        print("🔍 Search Agent Trace:")
        for step in data.get("steps", []):
            if step["type"] == "tool_call":
                print(f"  🔧 Called: {step['name']}")
                if step["name"] == "rewrite_natural_query":
                    print(f"      Input: {step['args'].get('natural_query')}")
                elif step["name"] == "search_notes_tool":
                    print(f"      Optimized query: {step['args'].get('query')}")

        results = data.get("results", [])
        print(f"\n✅ Found {len(results)} results:")
        for r in results:
            print(f"\n  📄 {r['path'].split('/')[-1]}")
            print(f"     {r['snippet']}")
    else:
        print(f"❌ Failed: {response.status_code}")


if __name__ == "__main__":
    if capture_note():
        # Give FTS5 a moment to index
        print("\n⏳ Waiting for FTS5 indexing...")
        time.sleep(2)
        search_notes()
