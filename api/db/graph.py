"""
Graph Database Operations
Helper functions for storing/retrieving graph nodes and edges.
"""
import json
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime


def store_graph_node(
    note_id: str,
    text: str,
    file_path: str,
    episodic_metadata: Dict[str, Any],
    db_connection: Optional[sqlite3.Connection] = None
) -> None:
    """Store a note as a graph node with episodic metadata.

    Args:
        note_id: Unique note identifier
        text: Full note text
        file_path: Path to the markdown file
        episodic_metadata: Dict with who/what/where/when/tags from episodic.py
        db_connection: Optional database connection (for transactions)
    """
    should_close = db_connection is None
    if db_connection is None:
        from ..config import get_db_connection
        con = get_db_connection()
    else:
        con = db_connection

    try:
        cur = con.cursor()

        # Extract metadata arrays
        entities_who = json.dumps(episodic_metadata.get("who", []))
        entities_what = json.dumps(episodic_metadata.get("what", []))
        entities_where = json.dumps(episodic_metadata.get("where", []))
        time_references = json.dumps(episodic_metadata.get("when", []))
        tags = json.dumps(episodic_metadata.get("tags", []))
        created = datetime.now().isoformat()

        # Insert or replace node
        cur.execute("""
            INSERT OR REPLACE INTO graph_nodes (
                id, text, created,
                entities_who, entities_what, entities_where,
                time_references, tags, file_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            note_id, text, created,
            entities_who, entities_what, entities_where,
            time_references, tags, file_path
        ))

        if should_close:
            con.commit()

    finally:
        if should_close:
            con.close()


def get_graph_node(note_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a graph node by ID.

    Returns:
        Dict with node data, or None if not found
    """
    from ..config import get_db_connection
    con = get_db_connection()

    try:
        cur = con.cursor()
        cur.execute("""
            SELECT id, text, created,
                   entities_who, entities_what, entities_where,
                   time_references, tags, file_path,
                   embedding, cluster_id
            FROM graph_nodes
            WHERE id = ?
        """, (note_id,))

        row = cur.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "text": row[1],
            "created": row[2],
            "who": json.loads(row[3]) if row[3] else [],
            "what": json.loads(row[4]) if row[4] else [],
            "where": json.loads(row[5]) if row[5] else [],
            "when": json.loads(row[6]) if row[6] else [],
            "tags": json.loads(row[7]) if row[7] else [],
            "file_path": row[8],
            "embedding": row[9],
            "cluster_id": row[10]
        }

    finally:
        con.close()


def get_all_nodes(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get all graph nodes, optionally limited.

    Args:
        limit: Maximum number of nodes to return

    Returns:
        List of node dictionaries
    """
    from ..config import get_db_connection
    con = get_db_connection()

    try:
        cur = con.cursor()

        query = """
            SELECT id, text, created,
                   entities_who, entities_what, entities_where,
                   time_references, tags, file_path,
                   cluster_id
            FROM graph_nodes
            ORDER BY created DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        cur.execute(query)
        rows = cur.fetchall()

        nodes = []
        for row in rows:
            nodes.append({
                "id": row[0],
                "text": row[1],
                "created": row[2],
                "who": json.loads(row[3]) if row[3] else [],
                "what": json.loads(row[4]) if row[4] else [],
                "where": json.loads(row[5]) if row[5] else [],
                "when": json.loads(row[6]) if row[6] else [],
                "tags": json.loads(row[7]) if row[7] else [],
                "file_path": row[8],
                "cluster_id": row[9]
            })

        return nodes

    finally:
        con.close()


def create_edge(
    src_node_id: str,
    dst_node_id: str,
    relation: str,
    weight: float = 1.0,
    metadata: Optional[Dict[str, Any]] = None,
    db_connection: Optional[sqlite3.Connection] = None
) -> None:
    """Create an edge between two nodes.

    Args:
        src_node_id: Source node ID
        dst_node_id: Destination node ID
        relation: Edge type (semantic, entity_link, tag_link, time_next, reminder)
        weight: Relationship strength (default 1.0)
        metadata: Additional edge metadata (JSON serializable)
        db_connection: Optional database connection (for transactions)
    """
    should_close = db_connection is None
    if db_connection is None:
        from ..config import get_db_connection
        con = get_db_connection()
    else:
        con = db_connection

    try:
        cur = con.cursor()
        created = datetime.now().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None

        # Insert or update edge
        cur.execute("""
            INSERT OR REPLACE INTO graph_edges (
                src_node_id, dst_node_id, relation, weight, metadata, created
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (src_node_id, dst_node_id, relation, weight, metadata_json, created))

        if should_close:
            con.commit()

    finally:
        if should_close:
            con.close()


def get_node_edges(node_id: str, relation: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all edges connected to a node.

    Args:
        node_id: Node ID to query
        relation: Optional filter by edge type

    Returns:
        List of edge dictionaries
    """
    from ..config import get_db_connection
    con = get_db_connection()

    try:
        cur = con.cursor()

        if relation:
            query = """
                SELECT src_node_id, dst_node_id, relation, weight, metadata, created
                FROM graph_edges
                WHERE (src_node_id = ? OR dst_node_id = ?) AND relation = ?
                ORDER BY created DESC
            """
            cur.execute(query, (node_id, node_id, relation))
        else:
            query = """
                SELECT src_node_id, dst_node_id, relation, weight, metadata, created
                FROM graph_edges
                WHERE src_node_id = ? OR dst_node_id = ?
                ORDER BY created DESC
            """
            cur.execute(query, (node_id, node_id))

        rows = cur.fetchall()

        edges = []
        for row in rows:
            edges.append({
                "src": row[0],
                "dst": row[1],
                "relation": row[2],
                "weight": row[3],
                "metadata": json.loads(row[4]) if row[4] else None,
                "created": row[5]
            })

        return edges

    finally:
        con.close()
