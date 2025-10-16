"""
Query Service for Multi-Dimensional Note Search
Provides high-level query functions that orchestrate graph.py helpers
"""
import sqlite3
from typing import List, Dict, Optional
from ..config import DB_PATH
from ..graph import (
    find_notes_by_dimension,
    find_notes_by_entity,
    find_notes_by_person,
    get_graph_neighborhood,
    get_entities,
    get_dimensions
)
from ..fts import search_notes


def search_by_dimension(dimension_type: str, dimension_value: str,
                       query_text: Optional[str] = None, limit: int = 20) -> List[Dict]:
    """Search notes by dimension (context, emotion, time_reference).

    Optionally combine with FTS5 text search for refined results.

    Args:
        dimension_type: Type of dimension (context, emotion, time_reference)
        dimension_value: Value to search for
        query_text: Optional text query to combine with dimension filter
        limit: Maximum results to return

    Returns:
        List of note dicts with path, snippet, score, metadata

    Examples:
        - search_by_dimension("emotion", "excited")
        - search_by_dimension("emotion", "excited", query_text="vector search")
    """
    # Get note IDs matching dimension
    note_ids = find_notes_by_dimension(dimension_type, dimension_value)

    if not query_text:
        # Return dimension results only
        return _format_results_from_ids(note_ids[:limit])

    # Combine with FTS5 search
    fts_results = search_notes(query_text, limit=100)  # Get larger set for filtering
    fts_paths = {r["path"] for r in fts_results}

    # Get paths for dimension note IDs and filter by FTS results
    note_paths = _get_paths_for_note_ids(note_ids)
    combined_ids = [nid for nid, path in note_paths.items() if path in fts_paths]

    return _format_results_from_ids(combined_ids[:limit])


def search_by_entity(entity_type: str, entity_value: str,
                    context: Optional[str] = None, limit: int = 20) -> List[Dict]:
    """Search notes by entity (person, topic, project, tech).

    Optionally filter by folder context.

    Args:
        entity_type: Type of entity (person, topic, project, tech)
        entity_value: Entity value to search for
        context: Optional folder to filter by (tasks, meetings, ideas, reference, journal)
        limit: Maximum results to return

    Returns:
        List of note dicts with path, snippet, score, metadata

    Examples:
        - search_by_entity("topic", "vector search")
        - search_by_entity("person", "Sarah", context="meetings")
    """
    # Get note IDs matching entity
    note_ids = find_notes_by_entity(entity_type, entity_value)

    # Filter by context if specified
    if context:
        note_ids = _filter_by_context(note_ids, context)

    return _format_results_from_ids(note_ids[:limit])


def search_by_person(person_name: str, context: Optional[str] = None,
                    limit: int = 20) -> List[Dict]:
    """Convenience function for person search with case-insensitive matching.

    Args:
        person_name: Person's name to search for
        context: Optional folder to filter by
        limit: Maximum results to return

    Returns:
        List of note dicts with path, snippet, score, metadata

    Examples:
        - search_by_person("Sarah")
        - search_by_person("sarah", context="meetings")  # Case-insensitive
    """
    # Get note IDs matching person
    note_ids = find_notes_by_person(person_name)

    # Filter by context if specified
    if context:
        note_ids = _filter_by_context(note_ids, context)

    return _format_results_from_ids(note_ids[:limit])


def search_graph(start_note_id: str, depth: int = 2,
                relationship_type: Optional[str] = None) -> Dict:
    """Traverse graph from starting note and return nodes + edges.

    Args:
        start_note_id: Note ID to start traversal from
        depth: How many hops to traverse (default: 2)
        relationship_type: Optional filter by link type (related, spawned, references, contradicts)

    Returns:
        Dict with:
            - nodes: List of note dicts
            - edges: List of link dicts with from/to/type

    Example:
        - search_graph("2025-10-12T09:00:00-07:00_a1b2", depth=2)
        - search_graph("...", depth=1, relationship_type="spawned")
    """
    # Note: get_graph_neighborhood doesn't support link_type_filter parameter
    # We'll get all links and filter after if needed
    graph = get_graph_neighborhood(start_note_id, depth=depth)

    # Filter edges by relationship type if specified
    edges = graph["edges"]
    if relationship_type:
        edges = [e for e in edges if e.get("type") == relationship_type]

    # Format for frontend (D3.js, Cytoscape, Vue Flow compatible)
    nodes = []
    for node in graph["nodes"]:
        # Enrich with metadata for visualization
        node_data = {
            "id": node["id"],
            "title": _get_title_for_note(node["path"]),
            "path": node["path"],
            "folder": node["folder"],
            "created": node["created"],
            "metadata": {
                "folder": node["folder"],  # For color coding
                "entity_count": 0,
                "dimension_count": 0
            }
        }

        # Add entity/dimension counts for visualization
        try:
            entities = get_entities(node["id"])
            dimensions = get_dimensions(node["id"])
            node_data["metadata"]["entity_count"] = len(entities)
            node_data["metadata"]["dimension_count"] = len(dimensions)

            # Group entities by type for tooltip/details
            entity_groups = {}
            for entity in entities:
                entity_type = entity["entity_type"]
                entity_value = entity["entity_value"]
                if entity_type not in entity_groups:
                    entity_groups[entity_type] = []
                entity_groups[entity_type].append(entity_value)
            node_data["metadata"]["has_entities"] = entity_groups

        except Exception:
            pass

        nodes.append(node_data)

    # Format edges (add source/target aliases for D3.js)
    formatted_edges = []
    for edge in edges:
        formatted_edges.append({
            "from": edge["from"],
            "to": edge["to"],
            "source": edge["from"],  # D3.js alias
            "target": edge["to"],    # D3.js alias
            "type": edge["type"]
        })

    return {
        "nodes": nodes,
        "edges": formatted_edges
    }


def get_graph_visualization(note_id: str, depth: int = 2) -> Dict:
    """Get graph data formatted for visualization.

    Convenience wrapper around search_graph for the GET endpoint.

    Args:
        note_id: Center note ID
        depth: Traversal depth

    Returns:
        Graph data with nodes and edges
    """
    return search_graph(note_id, depth=depth)


def _get_paths_for_note_ids(note_ids: List[str]) -> Dict[str, str]:
    """Get file paths for a list of note IDs.

    Args:
        note_ids: List of note IDs

    Returns:
        Dict mapping note_id -> path
    """
    import sqlite3
    from ..config import DB_PATH

    if not note_ids:
        return {}

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    placeholders = ','.join(['?' for _ in note_ids])
    cur.execute(
        f"SELECT id, path FROM notes_meta WHERE id IN ({placeholders})",
        note_ids
    )

    result = {row[0]: row[1] for row in cur.fetchall()}
    con.close()
    return result


def _filter_by_context(note_ids: List[str], context: str) -> List[str]:
    """Filter note IDs by folder context.

    Args:
        note_ids: List of note IDs
        context: Folder name (tasks, meetings, ideas, reference, journal)

    Returns:
        Filtered list of note IDs
    """
    import sqlite3
    from ..config import DB_PATH

    if not note_ids:
        return []

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    placeholders = ','.join(['?' for _ in note_ids])

    # Map context to dimension column (Phase 2: folder → dimensions)
    dimension_map = {
        "tasks": "has_action_items",
        "meetings": "is_social",
        "ideas": "is_exploratory",
        "reference": "is_knowledge",
        "journal": "is_emotional"
    }

    dimension_col = dimension_map.get(context)
    if dimension_col:
        cur.execute(
            f"SELECT id FROM notes_meta WHERE id IN ({placeholders}) AND {dimension_col} = 1",
            note_ids
        )
    else:
        # No filtering if context not recognized
        cur.execute(
            f"SELECT id FROM notes_meta WHERE id IN ({placeholders})",
            note_ids
        )

    result = [row[0] for row in cur.fetchall()]
    con.close()
    return result


def _get_title_for_note(file_path: str) -> str:
    """Extract title from a note file.

    Args:
        file_path: Path to note file

    Returns:
        Title or "Untitled"
    """
    import yaml

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 2:
                    frontmatter = yaml.safe_load(parts[1])
                    return frontmatter.get("title", "Untitled")
    except Exception:
        pass
    return "Untitled"


def _format_results_from_ids(note_ids: List[str]) -> List[Dict]:
    """Format note IDs into API response format with paths and snippets.

    Args:
        note_ids: List of note IDs

    Returns:
        Formatted results with path, snippet, score, metadata
    """
    import sqlite3
    import yaml
    from ..config import DB_PATH

    if not note_ids:
        return []

    # Get note metadata from DB
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    placeholders = ','.join(['?' for _ in note_ids])
    cur.execute(
        f"SELECT id, path, folder, created FROM notes_meta WHERE id IN ({placeholders})",
        note_ids
    )

    notes = {}
    for row in cur.fetchall():
        notes[row[0]] = {
            "id": row[0],
            "path": row[1],
            "folder": row[2],
            "created": row[3]
        }

    con.close()

    # Format results in original order
    formatted = []
    for note_id in note_ids:
        if note_id not in notes:
            continue

        note = notes[note_id]

        # Read snippet and title from file
        snippet = ""
        title = "Untitled"
        try:
            with open(note["path"], 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract title and body after frontmatter
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 2:
                        frontmatter = yaml.safe_load(parts[1])
                        title = frontmatter.get("title", "Untitled")
                    body = parts[2].strip() if len(parts) >= 3 else content
                else:
                    body = content
                snippet = body[:200] + ("..." if len(body) > 200 else "")
        except Exception:
            snippet = "[Could not read file]"

        formatted.append({
            "path": note["path"],
            "snippet": snippet,
            "score": 1.0,  # All results are exact matches for metadata queries
            "metadata": {
                "folder": note["folder"],
                "created": note["created"],
                "title": title
            }
        })

    return formatted
