"""
Graph Repository - Data access for dimensions, entities, and links
Wraps existing graph.py helpers with a clean repository interface
"""
from typing import List, Dict, Optional
from ..graph import (
    # Write operations
    add_dimension,
    add_entity,
    add_link,
    index_note_with_enrichment,

    # Read operations
    get_dimensions,
    get_entities,
    get_all_links_for_note,
    find_notes_by_dimension,
    find_notes_by_entity,
    find_notes_by_person,
    get_graph_neighborhood,
)


class GraphRepository:
    """Repository for graph-related data access (dimensions, entities, links)"""

    # ========================================================================
    # WRITE OPERATIONS
    # ========================================================================

    def add_dimension(self, note_id: str, dimension_type: str, dimension_value: str,
                     confidence: float = None, db_connection=None):
        """Add a dimension to a note

        Args:
            note_id: Note ID
            dimension_type: Type (context, emotion, time_reference)
            dimension_value: Value of the dimension
            confidence: Optional confidence score
            db_connection: Optional DB connection
        """
        return add_dimension(note_id, dimension_type, dimension_value, confidence, db_connection)

    def add_entity(self, note_id: str, entity_type: str, entity_value: str,
                  entity_metadata: str = None, confidence: float = None,
                  db_connection=None):
        """Add an entity to a note

        Args:
            note_id: Note ID
            entity_type: Type (person, topic, project, tech)
            entity_value: Value/name of entity
            entity_metadata: Optional JSON metadata
            confidence: Optional confidence score
            db_connection: Optional DB connection
        """
        return add_entity(note_id, entity_type, entity_value, entity_metadata, confidence, db_connection)

    def add_link(self, from_note_id: str, to_note_id: str, link_type: str,
                db_connection=None):
        """Create a link between two notes

        Args:
            from_note_id: Source note ID
            to_note_id: Target note ID
            link_type: Type of relationship
            db_connection: Optional DB connection
        """
        return add_link(from_note_id, to_note_id, link_type, db_connection)

    def store_enrichment(self, note_id: str, enrichment: dict, db_connection):
        """Store all enrichment metadata for a note

        Args:
            note_id: Note ID
            enrichment: Enrichment data from enrich_note_metadata()
            db_connection: DB connection
        """
        return index_note_with_enrichment(note_id, enrichment, db_connection)

    # ========================================================================
    # READ OPERATIONS
    # ========================================================================

    def get_dimensions(self, note_id: str) -> List[Dict]:
        """Get all dimensions for a note

        Args:
            note_id: Note ID

        Returns:
            List of dimension dicts with type and value
        """
        return get_dimensions(note_id)

    def get_entities(self, note_id: str) -> List[Dict]:
        """Get all entities for a note

        Args:
            note_id: Note ID

        Returns:
            List of entity dicts with type, value, metadata
        """
        return get_entities(note_id)

    def get_links(self, note_id: str) -> Dict:
        """Get all links for a note (both outgoing and incoming)

        Args:
            note_id: Note ID

        Returns:
            Dict with 'outgoing' and 'incoming' link lists
        """
        return get_all_links_for_note(note_id)

    def find_by_dimension(self, dimension_type: str, dimension_value: str) -> List[str]:
        """Find note IDs with a specific dimension

        Args:
            dimension_type: Type of dimension
            dimension_value: Value to search for

        Returns:
            List of note IDs
        """
        return find_notes_by_dimension(dimension_type, dimension_value)

    def find_by_entity(self, entity_type: str, entity_value: str) -> List[str]:
        """Find note IDs with a specific entity

        Args:
            entity_type: Type of entity
            entity_value: Value to search for

        Returns:
            List of note IDs
        """
        return find_notes_by_entity(entity_type, entity_value)

    def find_by_person(self, person_name: str) -> List[str]:
        """Find note IDs mentioning a person (case-insensitive)

        Args:
            person_name: Person's name

        Returns:
            List of note IDs
        """
        return find_notes_by_person(person_name)

    def get_graph_neighborhood(self, note_id: str, depth: int = 2) -> Dict:
        """Traverse graph from a starting note

        Args:
            note_id: Starting note ID
            depth: How many hops to traverse

        Returns:
            Dict with nodes and edges lists
        """
        return get_graph_neighborhood(note_id, depth)
