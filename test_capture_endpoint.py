"""
Test the new /capture_note endpoint
"""
import asyncio
import httpx
from api.db.graph import get_graph_node, get_all_nodes


async def test_capture_endpoint():
    """Test single note capture through new endpoint"""

    # Test note with rich episodic content
    test_note = """Met with Sarah at Café Awesome today at 2pm to discuss FAISS vector search implementation.

Key takeaways:
- Use FAISS for similarity search instead of naive NumPy approach
- Consider using HNSW index for better performance
- Need to implement batch embedding generation

Next steps:
- Research FAISS Python API documentation
- Prototype FAISS integration by Friday
- Schedule follow-up meeting next Tuesday at 3pm
"""

    print("=" * 80)
    print("TESTING /capture_note ENDPOINT")
    print("=" * 80)
    print(f"\nTest note:\n{test_note[:200]}...\n")

    # Call the endpoint
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/capture_note",
            json={"text": test_note},
            timeout=30.0
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}\n")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Note saved successfully!")
            print(f"   Note ID: {result['note_id']}")
            print(f"   Title: {result['title']}")
            print(f"   Path: {result['path']}")
            print(f"\n📊 Episodic Metadata:")
            episodic = result['episodic']
            print(f"   WHO:   {episodic['who']}")
            print(f"   WHAT:  {episodic['what']}")
            print(f"   WHERE: {episodic['where']}")
            print(f"   WHEN:  {[t['original'] for t in episodic['when']]}")
            print(f"   Tags:  {episodic['tags']}")

            # Verify graph node was created
            print("\n" + "=" * 80)
            print("VERIFYING GRAPH NODE")
            print("=" * 80)

            # Get all nodes and find the latest one
            nodes = get_all_nodes(limit=1)
            if nodes:
                node = nodes[0]
                print(f"\n✅ Graph node created:")
                print(f"   ID: {node['id']}")
                print(f"   WHO: {node['who']}")
                print(f"   WHAT: {node['what']}")
                print(f"   WHERE: {node['where']}")
                print(f"   WHEN: {[t['original'] for t in node['when']]}")
                print(f"   Tags: {node['tags']}")
                print(f"   Created: {node['created']}")
            else:
                print("❌ No graph nodes found!")

        else:
            print(f"❌ Request failed: {response.text}")


if __name__ == "__main__":
    print("\n🚀 Starting API server test...")
    print("⚠️  Make sure the API server is running on http://localhost:8000\n")

    try:
        asyncio.run(test_capture_endpoint())
    except httpx.ConnectError:
        print("\n❌ Could not connect to API server!")
        print("   Start the server with: uvicorn api.main:app --reload")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
