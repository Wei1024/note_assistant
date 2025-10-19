"""
Cluster Detection Service
Uses Louvain algorithm to detect communities in the knowledge graph
"""
import sqlite3
from typing import Dict, List, Set
import networkx as nx
import community as community_louvain
from ..config import DB_PATH


# Link type weights for clustering
LINK_WEIGHTS = {
    'spawned': 1.0,      # Strongest - direct causal relationship
    'references': 0.8,   # Strong - builds on ideas
    'related': 0.6,      # Medium - same topic
    'contradicts': 0.4   # Weaker - opposite views but still connected
}


def detect_clusters(min_links: int = 1, limit: int = 100) -> Dict[int, List[str]]:
    """Detect clusters in the knowledge graph using Louvain algorithm.

    Args:
        min_links: Minimum number of links a note must have to be included
        limit: Maximum number of notes to include in clustering

    Returns:
        Dictionary mapping cluster_id -> list of note_ids
        Example: {0: ['note1', 'note2'], 1: ['note3', 'note4']}
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Get all notes with sufficient links
    cur.execute("""
        SELECT DISTINCT n.id, n.path, n.created
        FROM notes_meta n
        INNER JOIN (
            SELECT from_note_id as note_id, COUNT(*) as link_count
            FROM notes_links
            GROUP BY from_note_id
            UNION ALL
            SELECT to_note_id as note_id, COUNT(*) as link_count
            FROM notes_links
            GROUP BY to_note_id
        ) link_counts ON n.id = link_counts.note_id
        GROUP BY n.id
        HAVING SUM(link_count) >= ?
        ORDER BY n.created DESC
        LIMIT ?
    """, (min_links, limit))

    nodes = cur.fetchall()
    valid_node_ids = {row[0] for row in nodes}

    # Get all links between these nodes
    cur.execute("""
        SELECT from_note_id, to_note_id, link_type
        FROM notes_links
        WHERE from_note_id IN ({})
          AND to_note_id IN ({})
    """.format(
        ','.join('?' * len(valid_node_ids)),
        ','.join('?' * len(valid_node_ids))
    ), list(valid_node_ids) * 2)

    links = cur.fetchall()
    con.close()

    # Build NetworkX graph
    G = nx.Graph()

    # Add nodes
    for node_id in valid_node_ids:
        G.add_node(node_id)

    # Add weighted edges
    for from_id, to_id, link_type in links:
        weight = LINK_WEIGHTS.get(link_type, 0.5)
        # If edge already exists, add to weight (multiple link types possible)
        if G.has_edge(from_id, to_id):
            G[from_id][to_id]['weight'] += weight
        else:
            G.add_edge(from_id, to_id, weight=weight)

    # Run Louvain clustering
    # Returns: {node_id: cluster_id}
    partition = community_louvain.best_partition(G, weight='weight')

    # Invert to get {cluster_id: [node_ids]}
    clusters: Dict[int, List[str]] = {}
    for node_id, cluster_id in partition.items():
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(node_id)

    return clusters


def get_cluster_stats(clusters: Dict[int, List[str]]) -> Dict[int, Dict]:
    """Get statistics for each cluster.

    Args:
        clusters: Output from detect_clusters()

    Returns:
        Dictionary with cluster statistics
        Example: {
            0: {
                'size': 5,
                'node_ids': ['note1', 'note2', ...],
                'avg_links': 3.2
            }
        }
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    stats = {}

    for cluster_id, node_ids in clusters.items():
        # Get link counts for nodes in this cluster
        placeholders = ','.join('?' * len(node_ids))
        cur.execute(f"""
            SELECT COUNT(*) as total_links
            FROM notes_links
            WHERE from_note_id IN ({placeholders})
               OR to_note_id IN ({placeholders})
        """, node_ids * 2)

        total_links = cur.fetchone()[0]

        stats[cluster_id] = {
            'size': len(node_ids),
            'node_ids': node_ids,
            'total_links': total_links,
            'avg_links': round(total_links / len(node_ids), 2) if node_ids else 0
        }

    con.close()
    return stats
