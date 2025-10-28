"""
Phase 4: Retrieval Layer Test Script
Tests hybrid search, graph expansion, and context assembly.

Run: python -m pytest tests/integration/test_phase4_retrieval.py -v
Or: python tests/integration/test_phase4_retrieval.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import requests
import json
from datetime import datetime
from typing import List, Dict, Any


# ==============================================================================
# Configuration
# ==============================================================================

API_BASE = "http://localhost:8000"
SEARCH_ENDPOINT = f"{API_BASE}/search"
CLUSTER_SEARCH_ENDPOINT = f"{API_BASE}/search/cluster"
SIMILAR_ENDPOINT = f"{API_BASE}/search/similar"

# Test queries (diverse to test different aspects)
TEST_QUERIES = [
    {
        "query": "meeting with Sarah about FAISS",
        "description": "Entity-focused query (WHO + WHAT)",
        "expected_entities": {"who": ["Sarah"], "what": ["FAISS"]}
    },
    {
        "query": "memory consolidation research",
        "description": "Semantic query (conceptual)",
        "expected_entities": {"what": ["memory", "consolidation"]}
    },
    {
        "query": "OAuth security implementation",
        "description": "Technical query (specific technology)",
        "expected_entities": {"what": ["OAuth", "security"]}
    },
    {
        "query": "tasks for next week",
        "description": "Temporal + prospective query",
        "expected_prospective": True
    },
    {
        "query": "feeling anxious about project",
        "description": "Emotional + knowledge query",
        "expected_tags": ["emotional"]
    }
]


# ==============================================================================
# Test Functions
# ==============================================================================

def test_hybrid_search():
    """Test basic hybrid search functionality"""
    print("\n" + "="*80)
    print("TEST 1: Hybrid Search")
    print("="*80)

    results = []

    for test_case in TEST_QUERIES:
        query = test_case['query']
        description = test_case['description']

        print(f"\n📝 Query: '{query}'")
        print(f"   Description: {description}")

        response = requests.post(
            SEARCH_ENDPOINT,
            params={
                "query": query,
                "top_k": 5,
                "expand_graph": False  # Test search only, no expansion
            }
        )

        if response.status_code != 200:
            print(f"   ❌ Failed: {response.status_code}")
            print(f"   Error: {response.text}")
            continue

        data = response.json()
        primary_results = data.get('primary_results', [])

        print(f"   ✅ Found {len(primary_results)} results")
        print(f"   ⏱️  Execution time: {data.get('execution_time_ms', 0)}ms")

        if primary_results:
            top_result = primary_results[0]
            print(f"   🏆 Top result:")
            print(f"      Title: {top_result['title'][:60]}")
            print(f"      Score: {top_result['score']:.3f} (FTS: {top_result['fts_score']:.3f}, Vector: {top_result['vector_score']:.3f})")
            print(f"      Snippet: {top_result['snippet'][:100]}...")

        results.append({
            'query': query,
            'num_results': len(primary_results),
            'execution_time_ms': data.get('execution_time_ms', 0),
            'top_score': primary_results[0]['score'] if primary_results else 0
        })

    # Summary statistics
    print("\n" + "-"*80)
    print("SUMMARY:")
    avg_time = sum(r['execution_time_ms'] for r in results) / len(results) if results else 0
    avg_results = sum(r['num_results'] for r in results) / len(results) if results else 0

    print(f"  Average execution time: {avg_time:.1f}ms")
    print(f"  Average results per query: {avg_results:.1f}")
    print(f"  Queries with results: {sum(1 for r in results if r['num_results'] > 0)}/{len(results)}")

    return results


def test_graph_expansion():
    """Test graph expansion functionality"""
    print("\n" + "="*80)
    print("TEST 2: Graph Expansion")
    print("="*80)

    query = "memory consolidation"  # Query likely to have related notes
    print(f"\n📝 Query: '{query}'")

    # Test without expansion
    response_no_expand = requests.post(
        SEARCH_ENDPOINT,
        params={"query": query, "top_k": 5, "expand_graph": False}
    )

    # Test with expansion
    response_with_expand = requests.post(
        SEARCH_ENDPOINT,
        params={"query": query, "top_k": 5, "expand_graph": True, "max_hops": 1}
    )

    if response_no_expand.status_code == 200 and response_with_expand.status_code == 200:
        data_no_expand = response_no_expand.json()
        data_with_expand = response_with_expand.json()

        primary_count = len(data_with_expand['primary_results'])
        expanded_count = len(data_with_expand['expanded_results'])

        print(f"\n   Primary results: {primary_count}")
        print(f"   Expanded results: {expanded_count}")
        print(f"   Total results: {data_with_expand['total_results']}")

        if expanded_count > 0:
            print(f"\n   ✅ Graph expansion working!")
            print(f"\n   Sample expanded results:")
            for i, node in enumerate(data_with_expand['expanded_results'][:3]):
                print(f"      {i+1}. {node['title'][:50]}")
                print(f"         Relation: {node['relation']}, Hop: {node['hop_distance']}, Score: {node['relevance_score']:.3f}")
                print(f"         Connected to: {len(node['connected_to'])} primary results")
        else:
            print(f"\n   ⚠️  No expanded results (might indicate sparse graph)")

        return {
            'primary_count': primary_count,
            'expanded_count': expanded_count,
            'expansion_ratio': expanded_count / primary_count if primary_count > 0 else 0
        }
    else:
        print(f"   ❌ Failed to test expansion")
        return None


def test_score_fusion():
    """Test score fusion between FTS and vector search"""
    print("\n" + "="*80)
    print("TEST 3: Score Fusion")
    print("="*80)

    # Test with different weight configurations
    weight_configs = [
        {"fts": 0.0, "vector": 1.0, "name": "Vector only"},
        {"fts": 0.4, "vector": 0.6, "name": "Default (60% vector)"},
        {"fts": 0.6, "vector": 0.4, "name": "FTS-heavy"},
        {"fts": 1.0, "vector": 0.0, "name": "FTS only"}
    ]

    query = "FAISS vector search implementation"
    print(f"\n📝 Query: '{query}'")

    results = []

    for config in weight_configs:
        response = requests.post(
            SEARCH_ENDPOINT,
            params={
                "query": query,
                "top_k": 3,
                "expand_graph": False,
                "fts_weight": config['fts'],
                "vector_weight": config['vector']
            }
        )

        if response.status_code == 200:
            data = response.json()
            primary = data.get('primary_results', [])

            print(f"\n   {config['name']} (FTS: {config['fts']}, Vector: {config['vector']})")
            if primary:
                for i, result in enumerate(primary[:3]):
                    print(f"      {i+1}. Score: {result['score']:.3f} (F={result['fts_score']:.3f}, V={result['vector_score']:.3f})")
                    print(f"         Title: {result['title'][:60]}")
            else:
                print(f"      No results")

            results.append({
                'config': config['name'],
                'top_score': primary[0]['score'] if primary else 0,
                'num_results': len(primary)
            })

    return results


def test_cluster_search():
    """Test cluster-aware search"""
    print("\n" + "="*80)
    print("TEST 4: Cluster-Aware Search")
    print("="*80)

    # First, get list of clusters
    clusters_response = requests.get(f"{API_BASE}/graph/clusters")

    if clusters_response.status_code != 200:
        print(f"   ❌ Failed to get clusters: {clusters_response.status_code}")
        return None

    clusters = clusters_response.json()['clusters']

    if not clusters:
        print(f"   ⚠️  No clusters found. Run clustering first: POST /graph/cluster")
        return None

    # Pick largest cluster
    largest_cluster = max(clusters, key=lambda c: c['size'])
    cluster_id = largest_cluster['id']

    print(f"\n   Testing with cluster {cluster_id}: '{largest_cluster['title']}'")
    print(f"   Cluster size: {largest_cluster['size']} notes")
    print(f"   Summary: {largest_cluster['summary']}")

    # Search within cluster
    query = "implementation"  # Generic query
    response = requests.post(
        f"{CLUSTER_SEARCH_ENDPOINT}/{cluster_id}",
        params={"query": query, "top_k": 5}
    )

    if response.status_code == 200:
        data = response.json()
        results = data.get('primary_results', [])

        print(f"\n   ✅ Found {len(results)} results in cluster")
        if results:
            print(f"   Top result: {results[0]['title'][:60]}")
            print(f"   Score: {results[0]['score']:.3f}")

        return {
            'cluster_id': cluster_id,
            'cluster_size': largest_cluster['size'],
            'results_found': len(results)
        }
    else:
        print(f"   ❌ Search failed: {response.status_code}")
        return None


def test_similarity_search():
    """Test similarity search (find similar notes)"""
    print("\n" + "="*80)
    print("TEST 5: Similarity Search")
    print("="*80)

    # First get a random note ID
    nodes_response = requests.get(f"{API_BASE}/graph/nodes")

    if nodes_response.status_code != 200:
        print(f"   ❌ Failed to get nodes: {nodes_response.status_code}")
        return None

    nodes = nodes_response.json()['nodes']

    if not nodes:
        print(f"   ⚠️  No notes found in database")
        return None

    # Pick first note
    seed_note = nodes[0]
    note_id = seed_note['id']

    print(f"\n   Seed note: {seed_note['id']}")
    print(f"   Text preview: {seed_note['text'][:100]}...")

    # Find similar notes
    response = requests.get(
        f"{SIMILAR_ENDPOINT}/{note_id}",
        params={"top_k": 5, "threshold": 0.3}
    )

    if response.status_code == 200:
        data = response.json()
        similar = data.get('similar_notes', [])

        print(f"\n   ✅ Found {len(similar)} similar notes")

        if similar:
            print(f"\n   Similar notes:")
            for i, note in enumerate(similar):
                print(f"      {i+1}. Similarity: {note['vector_score']:.3f}")
                print(f"         Title: {note['title'][:60]}")
                print(f"         Snippet: {note['snippet'][:80]}...")

        return {
            'seed_note_id': note_id,
            'similar_count': len(similar),
            'top_similarity': similar[0]['vector_score'] if similar else 0
        }
    else:
        print(f"   ❌ Similarity search failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None


def test_context_assembly():
    """Test context assembly with cluster summaries"""
    print("\n" + "="*80)
    print("TEST 6: Context Assembly")
    print("="*80)

    query = "research"
    print(f"\n📝 Query: '{query}'")

    response = requests.post(
        SEARCH_ENDPOINT,
        params={
            "query": query,
            "top_k": 5,
            "expand_graph": True,
            "max_hops": 1
        }
    )

    if response.status_code == 200:
        data = response.json()

        print(f"\n   Primary results: {len(data['primary_results'])}")
        print(f"   Expanded results: {len(data['expanded_results'])}")
        print(f"   Cluster summaries: {len(data['cluster_summaries'])}")

        if data['cluster_summaries']:
            print(f"\n   Cluster context:")
            for cluster in data['cluster_summaries']:
                print(f"      - Cluster {cluster['cluster_id']}: {cluster['title']}")
                print(f"        Size: {cluster['size']} notes")
                print(f"        Summary: {cluster['summary'][:100]}...")

        return {
            'primary_count': len(data['primary_results']),
            'expanded_count': len(data['expanded_results']),
            'cluster_count': len(data['cluster_summaries'])
        }
    else:
        print(f"   ❌ Context assembly failed: {response.status_code}")
        return None


# ==============================================================================
# Performance Benchmark
# ==============================================================================

def benchmark_search_performance():
    """Benchmark search performance with various configurations"""
    print("\n" + "="*80)
    print("BENCHMARK: Search Performance")
    print("="*80)

    queries = [
        "memory consolidation",
        "FAISS implementation",
        "meeting Sarah",
        "security OAuth",
        "research findings"
    ]

    results = []

    for query in queries:
        # Test hybrid search
        response = requests.post(
            SEARCH_ENDPOINT,
            params={"query": query, "top_k": 10, "expand_graph": False}
        )

        if response.status_code == 200:
            data = response.json()
            results.append({
                'query': query,
                'time_ms': data['execution_time_ms'],
                'results': len(data['primary_results'])
            })

    if results:
        avg_time = sum(r['time_ms'] for r in results) / len(results)
        max_time = max(r['time_ms'] for r in results)
        min_time = min(r['time_ms'] for r in results)

        print(f"\n   Queries tested: {len(results)}")
        print(f"   Average time: {avg_time:.1f}ms")
        print(f"   Min time: {min_time}ms")
        print(f"   Max time: {max_time}ms")

        # Check performance targets
        if avg_time < 200:
            print(f"   ✅ PASS: Average latency < 200ms target")
        else:
            print(f"   ⚠️  WARNING: Average latency {avg_time:.1f}ms exceeds 200ms target")

        return results

    return None


# ==============================================================================
# Main Test Runner
# ==============================================================================

def run_all_tests():
    """Run all Phase 4 tests"""
    print("\n" + "="*80)
    print("PHASE 4: RETRIEVAL LAYER TEST SUITE")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check API health
    try:
        health = requests.get(f"{API_BASE}/health")
        if health.status_code == 200:
            print(f"✅ API is running")
        else:
            print(f"❌ API health check failed")
            return
    except Exception as e:
        print(f"❌ Cannot connect to API at {API_BASE}")
        print(f"   Error: {e}")
        print(f"   Make sure the API is running: cd api && uvicorn main:app --port 8732")
        return

    # Run tests
    test_results = {}

    test_results['hybrid_search'] = test_hybrid_search()
    test_results['graph_expansion'] = test_graph_expansion()
    test_results['score_fusion'] = test_score_fusion()
    test_results['cluster_search'] = test_cluster_search()
    test_results['similarity_search'] = test_similarity_search()
    test_results['context_assembly'] = test_context_assembly()
    test_results['benchmark'] = benchmark_search_performance()

    # Final summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for k, v in test_results.items() if v is not None)
    total = len(test_results)

    print(f"\nTests completed: {passed}/{total}")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Save results
    output_file = f"test_data/phase4_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs('test_data', exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(test_results, f, indent=2, default=str)

    print(f"\n📄 Results saved to: {output_file}")


if __name__ == "__main__":
    run_all_tests()
