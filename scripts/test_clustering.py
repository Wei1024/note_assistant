#!/usr/bin/env python
"""
Test clustering on existing graph data
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.clustering import run_clustering, get_all_clusters, get_cluster_details
from api.llm import initialize_llm, shutdown_llm


async def main():
    print("🔬 Testing Phase 2.5: Clustering Implementation\n")

    # Initialize LLM
    await initialize_llm()

    try:
        # Run clustering
        print("📊 Running Louvain community detection...")
        stats = await run_clustering(resolution=1.0)

        print(f"\n✅ Clustering Complete!")
        print(f"   Nodes: {stats['num_nodes']}")
        print(f"   Edges: {stats['num_edges']}")
        print(f"   Clusters: {stats['num_clusters']}")

        # Display cluster summaries
        print(f"\n🏷️  Cluster Summaries:\n")
        for cluster in stats['clusters']:
            print(f"   Cluster {cluster['id']}: \"{cluster['title']}\" ({cluster['size']} notes)")
            print(f"   └─ {cluster['summary']}")
            print()

        # Get detailed info for largest cluster
        if stats['clusters']:
            largest = max(stats['clusters'], key=lambda c: c['size'])
            print(f"🔍 Largest Cluster Details (Cluster {largest['id']}):\n")

            details = get_cluster_details(largest['id'])
            if details:
                print(f"   Title: {details['title']}")
                print(f"   Summary: {details['summary']}")
                print(f"   Size: {details['size']} notes")
                print(f"\n   Notes in this cluster:")
                for i, node in enumerate(details['nodes'][:5], 1):
                    preview = node['text'][:80].replace('\n', ' ')
                    print(f"   {i}. {preview}...")

                if len(details['nodes']) > 5:
                    print(f"   ... and {len(details['nodes']) - 5} more notes")

    finally:
        await shutdown_llm()


if __name__ == "__main__":
    asyncio.run(main())
