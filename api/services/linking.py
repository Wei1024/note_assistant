"""
Entity & Tag Linking Service
Creates edges between notes sharing entities or tags.
Includes normalization for fuzzy matching.

Links on:
- WHO: People, organizations
- WHAT: Concepts, topics, entities
- WHERE: Locations (physical/virtual/contextual)
- TAGS: Thematic categories

Philosophy: "A link is a link" - create edges for ANY shared entity/tag,
but weight by strength (1 shared = weak, 5 shared = strong).
"""
import json
from typing import List, Dict, Any, Set, Tuple, Optional
from ..db.graph import create_edge, get_all_nodes, get_graph_node


def normalize_entity(entity: str) -> str:
    """Normalize entity for comparison (case-insensitive)

    Args:
        entity: Entity string (e.g., "Sarah", "FAISS")

    Returns:
        Normalized string for comparison
    """
    return entity.lower().strip()


def normalize_tag(tag: str) -> str:
    """Normalize tag for comparison

    Handles: "ai-research" = "AI Research" = "ai_research"

    Args:
        tag: Tag string

    Returns:
        Normalized string for comparison
    """
    return tag.lower().replace("-", "_").replace(" ", "_").strip()


def find_shared_entities(
    entities_a: List[str],
    entities_b: List[str]
) -> List[str]:
    """Find shared entities with normalization

    Returns original casing from entities_a

    Args:
        entities_a: First entity list
        entities_b: Second entity list

    Returns:
        List of shared entities (original casing from entities_a)
    """
    if not entities_a or not entities_b:
        return []

    # Build normalized → original mapping
    norm_a = {normalize_entity(e): e for e in entities_a}
    norm_b = {normalize_entity(e) for e in entities_b}

    # Find intersection
    shared_normalized = set(norm_a.keys()) & norm_b

    # Return original casing
    return [norm_a[norm] for norm in shared_normalized]


def calculate_tag_similarity(
    tags_a: List[str],
    tags_b: List[str]
) -> Tuple[float, List[str]]:
    """Calculate Jaccard similarity between tag sets

    Args:
        tags_a: First tag list
        tags_b: Second tag list

    Returns:
        (similarity, shared_tags) tuple
        similarity: Jaccard coefficient (0.0 to 1.0)
        shared_tags: List of shared tags (original casing from tags_a)
    """
    if not tags_a or not tags_b:
        return 0.0, []

    # Normalize
    norm_a = {normalize_tag(t): t for t in tags_a}
    norm_b = {normalize_tag(t) for t in tags_b}

    # Jaccard similarity
    intersection = set(norm_a.keys()) & norm_b
    union = set(norm_a.keys()) | norm_b

    similarity = len(intersection) / len(union) if union else 0.0
    shared_tags = [norm_a[tag] for tag in intersection]

    return similarity, shared_tags


def create_entity_links(note_id: str, db_connection):
    """Create entity_link edges for notes sharing WHO/WHAT/WHERE entities

    Creates separate edges for each entity type.
    Weight = number of shared entities.
    Edge stored unidirectionally (A→B where A.id < B.id).

    Args:
        note_id: Note ID to create links for
        db_connection: SQLite connection
    """
    # Get current note's entities
    current_node = get_graph_node(note_id)
    if not current_node:
        return

    current_who = current_node.get('who', [])
    current_what = current_node.get('what', [])
    current_where = current_node.get('where', [])

    # Get all other nodes
    all_nodes = get_all_nodes()

    for other_node in all_nodes:
        other_id = other_node['id']

        if other_id == note_id:
            continue  # Skip self

        other_who = other_node.get('who', [])
        other_what = other_node.get('what', [])
        other_where = other_node.get('where', [])

        # Check WHO overlap
        shared_who = find_shared_entities(current_who, other_who)
        if shared_who:
            create_entity_link_edge(
                note_id,
                other_id,
                'who',
                shared_who,
                db_connection
            )

        # Check WHAT overlap
        shared_what = find_shared_entities(current_what, other_what)
        if shared_what:
            create_entity_link_edge(
                note_id,
                other_id,
                'what',
                shared_what,
                db_connection
            )

        # Check WHERE overlap
        shared_where = find_shared_entities(current_where, other_where)
        if shared_where:
            create_entity_link_edge(
                note_id,
                other_id,
                'where',
                shared_where,
                db_connection
            )


def create_entity_link_edge(
    note_id: str,
    other_id: str,
    entity_type: str,  # 'who', 'what', or 'where'
    shared_entities: List[str],
    db_connection
):
    """Helper to create entity_link edge with metadata

    Args:
        note_id: First note ID
        other_id: Second note ID
        entity_type: Type of entity ('who', 'what', 'where')
        shared_entities: List of shared entity values
        db_connection: SQLite connection
    """
    # Normalize direction (lexicographically smaller ID first)
    src_id = min(note_id, other_id)
    dst_id = max(note_id, other_id)

    # Weight = number of shared entities (human brain: more connections = stronger)
    weight = len(shared_entities)

    # Metadata for debugging/analysis
    metadata = {
        'entity_type': entity_type,
        f'shared_{entity_type}': shared_entities,
        'count': len(shared_entities)
    }

    create_edge(
        src_node_id=src_id,
        dst_node_id=dst_id,
        relation='entity_link',
        weight=weight,
        metadata=metadata,
        db_connection=db_connection
    )


def create_tag_links(note_id: str, db_connection):
    """Create tag_link edges for notes sharing tags

    Weight = Jaccard similarity (0.0 to 1.0)
    Only creates edge if similarity >= 0.3

    Args:
        note_id: Note ID to create tag links for
        db_connection: SQLite connection
    """
    # Get current note's tags
    current_node = get_graph_node(note_id)
    if not current_node:
        return

    current_tags = current_node.get('tags', [])
    if not current_tags:
        return  # No tags to link

    # Get all other nodes
    all_nodes = get_all_nodes()

    for other_node in all_nodes:
        other_id = other_node['id']

        if other_id == note_id:
            continue  # Skip self

        other_tags = other_node.get('tags', [])
        if not other_tags:
            continue

        # Calculate similarity
        similarity, shared_tags = calculate_tag_similarity(current_tags, other_tags)

        # Threshold: only create edge if similarity >= 0.3
        if similarity >= 0.3:
            # Normalize direction (lexicographically smaller ID first)
            src_id = min(note_id, other_id)
            dst_id = max(note_id, other_id)

            metadata = {
                'shared_tags': shared_tags,
                'jaccard': similarity
            }

            create_edge(
                src_node_id=src_id,
                dst_node_id=dst_id,
                relation='tag_link',
                weight=similarity,  # Weight = Jaccard similarity
                metadata=metadata,
                db_connection=db_connection
            )
