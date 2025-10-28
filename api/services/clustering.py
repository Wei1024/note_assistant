"""
Clustering Service - Community Detection for GraphRAG
Uses NetworkX Louvain algorithm to detect thematic clusters in the note graph.

Phase 2.5 Implementation:
- Builds NetworkX graph from edges
- Runs community detection (Louvain algorithm)
- Assigns cluster_id to graph_nodes
- Generates LLM summaries for each cluster
"""
import networkx as nx
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from ..db.graph import get_all_nodes
from ..config import get_db_connection
from ..llm import get_llm
from ..llm.audit import track_llm_call


def build_networkx_graph() -> nx.Graph:
    """Build NetworkX graph from database edges.

    Returns:
        Undirected graph with nodes and weighted edges
    """
    G = nx.Graph()

    # Add all nodes
    nodes = get_all_nodes()
    for node in nodes:
        G.add_node(node['id'], **node)

    # Add all edges
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT src_node_id, dst_node_id, relation, weight
            FROM graph_edges
            ORDER BY weight DESC
        """)

        for row in cursor.fetchall():
            src_id, dst_id, relation, weight = row

            # Add edge (undirected, so A-B same as B-A)
            if G.has_edge(src_id, dst_id):
                # Accumulate weights if multiple edge types exist
                G[src_id][dst_id]['weight'] += weight
            else:
                G.add_edge(src_id, dst_id, weight=weight, relation=relation)

        return G

    finally:
        conn.close()


def detect_communities(G: nx.Graph, resolution: float = 1.0) -> Dict[str, int]:
    """Run Louvain community detection algorithm.

    Args:
        G: NetworkX graph
        resolution: Higher values create more, smaller clusters (default 1.0)

    Returns:
        Dict mapping node_id -> cluster_id

    Example:
        {
            "note-uuid-1": 0,
            "note-uuid-2": 0,
            "note-uuid-3": 1
        }
    """
    # Use Louvain algorithm (best modularity)
    communities = nx.community.louvain_communities(G, weight='weight', resolution=resolution)

    # Convert to node_id -> cluster_id mapping
    node_to_cluster = {}
    for cluster_id, community in enumerate(communities):
        for node_id in community:
            node_to_cluster[node_id] = cluster_id

    return node_to_cluster


def assign_cluster_ids(node_to_cluster: Dict[str, int]) -> None:
    """Update graph_nodes table with cluster assignments.

    Args:
        node_to_cluster: Mapping of node_id -> cluster_id
    """
    conn = get_db_connection()
    try:
        for node_id, cluster_id in node_to_cluster.items():
            conn.execute(
                "UPDATE graph_nodes SET cluster_id = ? WHERE id = ?",
                (cluster_id, node_id)
            )
        conn.commit()
    finally:
        conn.close()


def get_cluster_nodes(cluster_id: int) -> List[Dict[str, Any]]:
    """Get all nodes in a cluster.

    Args:
        cluster_id: Cluster ID

    Returns:
        List of node dicts with episodic metadata
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT id, text, entities_who, entities_what, entities_where, tags
            FROM graph_nodes
            WHERE cluster_id = ?
            ORDER BY created DESC
        """, (cluster_id,))

        nodes = []
        for row in cursor.fetchall():
            nodes.append({
                'id': row[0],
                'text': row[1],
                'who': json.loads(row[2]) if row[2] else [],
                'what': json.loads(row[3]) if row[3] else [],
                'where': json.loads(row[4]) if row[4] else [],
                'tags': json.loads(row[5]) if row[5] else []
            })

        return nodes

    finally:
        conn.close()


async def generate_cluster_summary(nodes: List[Dict[str, Any]]) -> Dict[str, str]:
    """Generate LLM summary and title for a cluster.

    Args:
        nodes: List of nodes in the cluster

    Returns:
        Dict with 'title' (3-5 words) and 'summary' (1-2 sentences)
    """
    # Extract common entities and tags
    all_who = set()
    all_what = set()
    all_where = set()
    all_tags = set()

    for node in nodes:
        all_who.update(node.get('who', []))
        all_what.update(node.get('what', []))
        all_where.update(node.get('where', []))
        all_tags.update(node.get('tags', []))

    # Sample note texts (first 3 for context)
    sample_texts = [node['text'][:200] for node in nodes[:3]]

    # Build prompt for JSON output with title + summary
    prompt = f"""Generate a title and summary for this cluster of {len(nodes)} related notes.

CLUSTER ENTITIES:
- People/Orgs: {', '.join(list(all_who)[:5]) if all_who else 'None'}
- Topics: {', '.join(list(all_what)[:8]) if all_what else 'None'}
- Locations: {', '.join(list(all_where)[:5]) if all_where else 'None'}
- Tags: {', '.join(list(all_tags)[:5]) if all_tags else 'None'}

SAMPLE NOTES:
{chr(10).join(f"{i+1}. {text}..." for i, text in enumerate(sample_texts))}

OUTPUT FORMAT (JSON):
{{
  "title": "3-5 word cluster title",
  "summary": "1-2 sentence description of what these notes are about"
}}

Your JSON response:"""

    # Request JSON format for structured output
    llm = get_llm(format="json")

    try:
        with track_llm_call('cluster_summary', prompt) as tracker:
            response = await llm.ainvoke(prompt)
            tracker.set_response(response)

            result = json.loads(response.content)
            tracker.set_parsed_output(result)

            return {
                'title': result.get('title', 'Untitled Cluster'),
                'summary': result.get('summary', '')
            }

    except Exception:
        # Fallback summary on LLM error
        top_topics = list(all_what)[:3]
        if top_topics:
            title = ', '.join(top_topics[:2])
            summary = f"Notes about {', '.join(top_topics)}"
        else:
            title = f"Cluster {len(nodes)} notes"
            summary = f"Cluster of {len(nodes)} related notes"

        return {
            'title': title,
            'summary': summary
        }


def store_cluster_summary(cluster_id: int, title: str, summary: str, size: int) -> None:
    """Store cluster metadata in database.

    Args:
        cluster_id: Cluster ID
        title: Short cluster title (3-5 words)
        summary: LLM-generated summary
        size: Number of nodes in cluster
    """
    conn = get_db_connection()
    now = datetime.now().isoformat()

    try:
        conn.execute("""
            INSERT OR REPLACE INTO graph_clusters (id, title, summary, size, created, updated)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (cluster_id, title, summary, size, now, now))

        conn.commit()
    finally:
        conn.close()


async def run_clustering(resolution: float = 1.0) -> Dict[str, Any]:
    """Run full clustering pipeline.

    Steps:
    1. Build NetworkX graph from edges
    2. Run Louvain community detection
    3. Assign cluster IDs to nodes
    4. Generate summaries for each cluster
    5. Store cluster metadata

    Args:
        resolution: Clustering resolution (higher = more clusters)

    Returns:
        Stats dict with cluster counts and info
    """
    # Step 1: Build graph
    G = build_networkx_graph()

    if G.number_of_nodes() == 0:
        return {
            'num_nodes': 0,
            'num_edges': 0,
            'num_clusters': 0,
            'clusters': []
        }

    # Step 2: Detect communities
    node_to_cluster = detect_communities(G, resolution=resolution)

    # Step 3: Assign cluster IDs to database
    assign_cluster_ids(node_to_cluster)

    # Step 4: Generate summaries for each cluster
    cluster_stats = {}
    unique_clusters = set(node_to_cluster.values())

    for cluster_id in unique_clusters:
        nodes = get_cluster_nodes(cluster_id)
        cluster_info = await generate_cluster_summary(nodes)
        store_cluster_summary(cluster_id, cluster_info['title'], cluster_info['summary'], len(nodes))

        cluster_stats[cluster_id] = {
            'id': cluster_id,
            'size': len(nodes),
            'title': cluster_info['title'],
            'summary': cluster_info['summary']
        }

    return {
        'num_nodes': G.number_of_nodes(),
        'num_edges': G.number_of_edges(),
        'num_clusters': len(unique_clusters),
        'clusters': list(cluster_stats.values())
    }


def get_all_clusters() -> List[Dict[str, Any]]:
    """Get all clusters with metadata.

    Returns:
        List of cluster dicts with id, title, summary, size
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT id, title, summary, size, created, updated
            FROM graph_clusters
            ORDER BY size DESC
        """)

        clusters = []
        for row in cursor.fetchall():
            clusters.append({
                'id': row[0],
                'title': row[1],
                'summary': row[2],
                'size': row[3],
                'created': row[4],
                'updated': row[5]
            })

        return clusters

    finally:
        conn.close()


def get_cluster_details(cluster_id: int) -> Optional[Dict[str, Any]]:
    """Get detailed cluster information including all nodes.

    Args:
        cluster_id: Cluster ID

    Returns:
        Dict with cluster metadata and list of nodes
    """
    conn = get_db_connection()
    try:
        # Get cluster metadata
        cursor = conn.execute(
            "SELECT id, title, summary, size, created, updated FROM graph_clusters WHERE id = ?",
            (cluster_id,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        # Get cluster nodes
        nodes = get_cluster_nodes(cluster_id)

        return {
            'id': row[0],
            'title': row[1],
            'summary': row[2],
            'size': row[3],
            'created': row[4],
            'updated': row[5],
            'nodes': nodes
        }

    finally:
        conn.close()
