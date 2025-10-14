"""
Notes Repository - Data access for note CRUD operations
Wraps existing notes.py functions with a clean repository interface
"""
from typing import Tuple, Optional, List
from ..notes import write_markdown, update_note_status, get_notes_created_today


class NotesRepository:
    """Repository for note CRUD operations"""

    def create(self, folder: str, title: str, tags: list, body: str,
              related_ids: Optional[list] = None, status: Optional[str] = None,
              needs_review: bool = False, reasoning: Optional[str] = None,
              enrichment: Optional[dict] = None) -> Tuple[str, str, str, str]:
        """Create a new note

        Args:
            folder: Primary folder
            title: Note title
            tags: List of tags
            body: Note content
            related_ids: List of related note IDs
            status: Optional status (only for tasks)
            needs_review: Whether note needs review
            reasoning: Review reasoning
            enrichment: Optional enrichment metadata

        Returns:
            Tuple of (note_id, path, title, folder)
        """
        return write_markdown(
            folder, title, tags, body, related_ids, status,
            needs_review, reasoning, enrichment
        )

    def update_status(self, path: str, new_status: str):
        """Update note status

        Args:
            path: Note file path
            new_status: New status value
        """
        return update_note_status(path, new_status)

    def get_created_today(self) -> List[dict]:
        """Get all notes created today

        Returns:
            List of note dicts with id, path, entities, dimensions
        """
        return get_notes_created_today()
