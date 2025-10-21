"""
Search Repository - Data access for FTS5 full-text search
Wraps existing fts.py functions with a clean repository interface
"""
from typing import List, Dict, Optional
from ..fts import search_notes, index_note


class SearchRepository:
    """Repository for full-text search operations"""

    def search_text(self, query: str, limit: int = 20, status: Optional[str] = None) -> List[Dict]:
        """Search notes using FTS5

        Args:
            query: FTS5 query string
            limit: Maximum results to return
            status: Optional status filter (todo, in_progress, done)

        Returns:
            List of search result dicts with path, snippet, score
        """
        return search_notes(query, limit, status)

    def index_note(self, note_id: str, title: str, body: str, tags: list,
                  path: str, created: str, status: str = None,
                  needs_review: bool = False, review_reason: str = None,
                  has_action_items: bool = False, is_social: bool = False,
                  is_emotional: bool = False, is_knowledge: bool = False,
                  is_exploratory: bool = False):
        """Add or update note in FTS5 index

        Args:
            note_id: Note ID
            title: Note title
            body: Note body text
            tags: List of tags
            path: File path
            created: Creation timestamp
            status: Optional status
            needs_review: Whether note needs review
            review_reason: Review reason if needed
            has_action_items: Boolean dimension - contains actionable todos
            is_social: Boolean dimension - involves conversations
            is_emotional: Boolean dimension - expresses feelings
            is_knowledge: Boolean dimension - contains learnings
            is_exploratory: Boolean dimension - brainstorming/ideas
        """
        return index_note(
            note_id, title, body, tags, path, created,
            status, needs_review, review_reason,
            has_action_items, is_social, is_emotional, is_knowledge, is_exploratory
        )
