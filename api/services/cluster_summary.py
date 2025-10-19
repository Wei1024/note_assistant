"""
Cluster Summary Service
Aggregates metadata across cluster nodes and generates semantic summaries
"""
import sqlite3
import json
from typing import Dict, List
from ..config import DB_PATH
from ..llm import get_llm
from ..llm.prompts import Prompts


async def get_cluster_summary(cluster_id: int, node_ids: List[str]) -> Dict:
    """Generate a comprehensive summary for a cluster of notes.

    Aggregates:
    - People mentioned across all notes
    - Key concepts/entities
    - Emotions expressed
    - Time references (deadlines, meetings)
    - Dimension flags (action items, knowledge, etc.)

    Then uses LLM to generate a thematic summary.

    Args:
        cluster_id: Unique identifier for the cluster
        node_ids: List of note IDs in this cluster

    Returns:
        Dictionary with aggregated metadata and LLM-generated theme
    """
    if not node_ids:
        return {
            'cluster_id': cluster_id,
            'size': 0,
            'theme': 'Empty cluster',
            'people': [],
            'key_concepts': [],
            'emotions': [],
            'time_references': [],
            'dimensions': {
                'has_action_items': False,
                'is_social': False,
                'is_emotional': False,
                'is_knowledge': False,
                'is_exploratory': False
            }
        }

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    placeholders = ','.join('?' * len(node_ids))

    # Aggregate people
    cur.execute(f"""
        SELECT DISTINCT entity_value, entity_metadata
        FROM notes_entities
        WHERE note_id IN ({placeholders})
          AND entity_type = 'person'
    """, node_ids)

    people = []
    for entity_value, metadata_json in cur.fetchall():
        if metadata_json:
            try:
                metadata = json.loads(metadata_json)
                people.append({
                    'name': entity_value,
                    'role': metadata.get('role'),
                    'relation': metadata.get('relation')
                })
            except json.JSONDecodeError:
                people.append({'name': entity_value})
        else:
            people.append({'name': entity_value})

    # Aggregate entities/concepts (top 10 by frequency)
    cur.execute(f"""
        SELECT entity_value, COUNT(*) as freq
        FROM notes_entities
        WHERE note_id IN ({placeholders})
          AND entity_type = 'entity'
        GROUP BY entity_value
        ORDER BY freq DESC
        LIMIT 10
    """, node_ids)

    key_concepts = [{'concept': row[0], 'frequency': row[1]} for row in cur.fetchall()]

    # Aggregate emotions
    cur.execute(f"""
        SELECT DISTINCT dimension_value
        FROM notes_dimensions
        WHERE note_id IN ({placeholders})
          AND dimension_type = 'emotion'
    """, node_ids)

    emotions = [row[0] for row in cur.fetchall()]

    # Aggregate time references
    cur.execute(f"""
        SELECT dimension_value
        FROM notes_dimensions
        WHERE note_id IN ({placeholders})
          AND dimension_type = 'time_reference'
    """, node_ids)

    time_references = []
    for (dimension_value,) in cur.fetchall():
        try:
            time_ref = json.loads(dimension_value)
            time_references.append(time_ref)
        except json.JSONDecodeError:
            pass

    # Aggregate dimensions (boolean flags - true if ANY note has it)
    cur.execute(f"""
        SELECT
            MAX(has_action_items) as has_action_items,
            MAX(is_social) as is_social,
            MAX(is_emotional) as is_emotional,
            MAX(is_knowledge) as is_knowledge,
            MAX(is_exploratory) as is_exploratory,
            SUM(CASE WHEN has_action_items = 1 THEN 1 ELSE 0 END) as action_count
        FROM notes_meta
        WHERE id IN ({placeholders})
    """, node_ids)

    row = cur.fetchone()
    dimensions = {
        'has_action_items': bool(row[0]),
        'is_social': bool(row[1]),
        'is_emotional': bool(row[2]),
        'is_knowledge': bool(row[3]),
        'is_exploratory': bool(row[4])
    }
    action_count = row[5] or 0

    # Get sample note titles for context
    cur.execute(f"""
        SELECT path
        FROM notes_meta
        WHERE id IN ({placeholders})
        LIMIT 5
    """, node_ids)

    sample_titles = []
    for (path,) in cur.fetchall():
        # Extract filename from path
        filename = path.split('/')[-1]
        # Remove date prefix and .md extension
        title = filename.replace('.md', '').split('_', 1)[-1] if '_' in filename else filename
        sample_titles.append(title)

    con.close()

    # Generate LLM theme summary
    theme = await _generate_cluster_theme(
        node_count=len(node_ids),
        people=[p['name'] for p in people],
        concepts=[c['concept'] for c in key_concepts[:5]],  # Top 5 concepts
        emotions=emotions,
        time_refs=time_references,
        dimensions=dimensions,
        sample_titles=sample_titles
    )

    return {
        'cluster_id': cluster_id,
        'size': len(node_ids),
        'theme': theme,
        'people': people,
        'key_concepts': key_concepts,
        'emotions': emotions,
        'time_references': time_references,
        'dimensions': dimensions,
        'action_count': action_count
    }


async def _generate_cluster_theme(
    node_count: int,
    people: List[str],
    concepts: List[str],
    emotions: List[str],
    time_refs: List[Dict],
    dimensions: Dict[str, bool],
    sample_titles: List[str]
) -> str:
    """Use LLM to generate a thematic summary for a cluster.

    Args:
        node_count: Number of notes in cluster
        people: List of person names
        concepts: List of key concepts/entities
        emotions: List of emotions
        time_refs: List of time reference objects
        dimensions: Boolean dimension flags
        sample_titles: Sample note titles for context

    Returns:
        1-2 sentence theme summary
    """
    llm = get_llm()

    # Build context string
    context_parts = []

    if people:
        context_parts.append(f"People: {', '.join(people)}")

    if concepts:
        context_parts.append(f"Key concepts: {', '.join(concepts)}")

    if emotions:
        context_parts.append(f"Emotions: {', '.join(emotions)}")

    if time_refs:
        time_descriptions = [ref.get('description', '') for ref in time_refs if ref.get('description')]
        if time_descriptions:
            context_parts.append(f"Time references: {', '.join(time_descriptions[:3])}")

    # Dimension context
    active_dims = [dim.replace('_', ' ').replace('is ', '').replace('has ', '')
                   for dim, val in dimensions.items() if val]
    if active_dims:
        context_parts.append(f"Dimensions: {', '.join(active_dims)}")

    if sample_titles:
        context_parts.append(f"Sample notes: {', '.join(sample_titles[:3])}")

    context = '\n'.join(context_parts)

    prompt = f"""You are summarizing a cluster of {node_count} interconnected notes from a knowledge graph.

Context:
{context}

Task: Generate a concise 1-2 sentence theme that captures what this cluster is about. Focus on the main topic, people involved, and purpose.

Theme:"""

    try:
        response = await llm.ainvoke(prompt)
        theme = response.content.strip()
        # Clean up common LLM artifacts
        theme = theme.replace('"', '').replace('Theme:', '').strip()
        return theme
    except Exception as e:
        # Fallback to heuristic summary
        if concepts:
            return f"Notes about {concepts[0]}" + (f" involving {people[0]}" if people else "")
        elif people:
            return f"Notes involving {people[0]}"
        else:
            return f"Cluster of {node_count} related notes"
