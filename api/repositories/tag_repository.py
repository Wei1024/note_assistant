"""
Tag Repository - Database operations for user tag system

Handles:
- CRUD operations for tags table
- Note-tag relationship management (note_tags junction table)
- Tag hierarchy parsing and storage
- Fuzzy search and autocomplete
- Tag analytics and usage stats

Design for batch compatibility:
- UUID-based tag references (renaming safe)
- Bulk insert/delete support for note_tags
- Transaction support for multi-note operations
"""
import uuid
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from ..config import get_db_connection


class TagRepository:
    """Repository for tag database operations."""

    @staticmethod
    def _parse_tag_hierarchy(tag_name: str) -> Tuple[str, Optional[str], int]:
        """Parse tag name into components.

        Args:
            tag_name: Full tag name (e.g., "project/alpha" or "personal")

        Returns:
            (full_name, parent_name, level)
            Examples:
                "personal" → ("personal", None, 0)
                "project/alpha" → ("project/alpha", "project", 1)
                "work/project/alpha" → ("work/project/alpha", "work/project", 2)
        """
        parts = tag_name.split('/')
        level = len(parts) - 1

        if level == 0:
            return (tag_name, None, 0)
        else:
            parent_name = '/'.join(parts[:-1])
            return (tag_name, parent_name, level)

    @staticmethod
    def get_or_create_tag(tag_name: str) -> str:
        """Get existing tag ID or create new tag.

        Handles hierarchy:
        - If parent doesn't exist, creates it first
        - Returns tag UUID

        Args:
            tag_name: Full tag name (e.g., "project/alpha")

        Returns:
            Tag UUID

        Example:
            >>> tag_id = TagRepository.get_or_create_tag("project/alpha")
            >>> # If "project" doesn't exist, creates it first
            >>> # Then creates "project/alpha" with parent_id pointing to "project"
        """
        conn = get_db_connection()
        tag_name = tag_name.lower()  # Normalize to lowercase

        try:
            # Check if tag already exists
            cursor = conn.execute(
                "SELECT id FROM tags WHERE name = ?",
                (tag_name,)
            )
            existing = cursor.fetchone()
            if existing:
                return existing[0]

            # Parse hierarchy
            full_name, parent_name, level = TagRepository._parse_tag_hierarchy(tag_name)

            # Get or create parent if hierarchical
            parent_id = None
            if parent_name:
                parent_id = TagRepository.get_or_create_tag(parent_name)

            # Create new tag
            tag_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            conn.execute(
                """
                INSERT INTO tags (id, name, parent_id, level, use_count, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
                """,
                (tag_id, full_name, parent_id, level, now)
            )
            conn.commit()

            return tag_id

        finally:
            conn.close()

    @staticmethod
    def add_tag_to_note(note_id: str, tag_name: str, source: str = 'user') -> None:
        """Add tag to a note.

        Args:
            note_id: Note UUID
            tag_name: Tag name (e.g., "project/alpha")
            source: 'user' | 'detected' | 'suggested'

        Batch-compatible: Can be called in loop for multiple tags
        """
        tag_id = TagRepository.get_or_create_tag(tag_name)
        conn = get_db_connection()

        try:
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT OR IGNORE INTO note_tags (note_id, tag_id, created_at, source)
                VALUES (?, ?, ?, ?)
                """,
                (note_id, tag_id, now, source)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def add_tags_to_note_bulk(note_id: str, tag_names: List[str], source: str = 'user') -> None:
        """Add multiple tags to a note (optimized for bulk operations).

        Args:
            note_id: Note UUID
            tag_names: List of tag names
            source: 'user' | 'detected' | 'suggested'

        Batch-compatible: Single transaction for multiple tags
        """
        # Get or create all tag IDs first (separate connections)
        tag_ids = []
        for tag_name in tag_names:
            tag_id = TagRepository.get_or_create_tag(tag_name)
            tag_ids.append(tag_id)

        # Then insert all note_tags in single transaction
        conn = get_db_connection()
        try:
            now = datetime.now().isoformat()

            for tag_id in tag_ids:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO note_tags (note_id, tag_id, created_at, source)
                    VALUES (?, ?, ?, ?)
                    """,
                    (note_id, tag_id, now, source)
                )

            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def remove_tag_from_note(note_id: str, tag_id: str) -> None:
        """Remove tag from a note.

        Args:
            note_id: Note UUID
            tag_id: Tag UUID

        Batch-compatible: Can be called in loop
        """
        conn = get_db_connection()
        try:
            conn.execute(
                "DELETE FROM note_tags WHERE note_id = ? AND tag_id = ?",
                (note_id, tag_id)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_note_tags(note_id: str) -> List[Dict[str, Any]]:
        """Get all tags for a note.

        Returns:
            List of tag dicts with id, name, level, use_count
        """
        conn = get_db_connection()
        try:
            cursor = conn.execute(
                """
                SELECT t.id, t.name, t.level, t.use_count, nt.source, nt.created_at
                FROM note_tags nt
                JOIN tags t ON nt.tag_id = t.id
                WHERE nt.note_id = ?
                ORDER BY t.name
                """,
                (note_id,)
            )

            tags = []
            for row in cursor.fetchall():
                tags.append({
                    'id': row[0],
                    'name': row[1],
                    'level': row[2],
                    'use_count': row[3],
                    'source': row[4],
                    'added_at': row[5]
                })

            return tags
        finally:
            conn.close()

    @staticmethod
    def get_all_tags(include_unused: bool = True) -> List[Dict[str, Any]]:
        """Get all tags with hierarchy information.

        Args:
            include_unused: If False, only return tags with use_count > 0

        Returns:
            List of tag dicts with full metadata
        """
        conn = get_db_connection()
        try:
            query = """
                SELECT
                    id, name, parent_id, level, use_count,
                    created_at, last_used_at
                FROM tags
            """

            if not include_unused:
                query += " WHERE use_count > 0"

            query += " ORDER BY name"

            cursor = conn.execute(query)

            tags = []
            for row in cursor.fetchall():
                tags.append({
                    'id': row[0],
                    'name': row[1],
                    'parent_id': row[2],
                    'level': row[3],
                    'use_count': row[4],
                    'created_at': row[5],
                    'last_used_at': row[6]
                })

            return tags
        finally:
            conn.close()

    @staticmethod
    def search_tags(query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fuzzy search tags by name (for autocomplete).

        Matching strategy:
        1. Exact prefix match (highest priority)
        2. Contains match
        3. Ordered by use_count (most used first)

        Args:
            query: Search string (e.g., "proj" matches "project", "project/alpha")
            limit: Max results to return

        Returns:
            List of matching tags, ordered by relevance

        Example:
            >>> search_tags("proj")
            [
                {"name": "project/alpha", "use_count": 12},
                {"name": "project/beta", "use_count": 8},
                {"name": "side-project", "use_count": 3}
            ]
        """
        conn = get_db_connection()
        query_lower = query.lower()

        try:
            # Search with prefix and contains matching
            cursor = conn.execute(
                """
                SELECT id, name, level, use_count, last_used_at
                FROM tags
                WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?
                ORDER BY
                    CASE
                        WHEN LOWER(name) = ? THEN 1           -- Exact match
                        WHEN LOWER(name) LIKE ? THEN 2        -- Prefix match
                        ELSE 3                                 -- Contains match
                    END,
                    use_count DESC,                            -- Most used first
                    name ASC                                   -- Alphabetical
                LIMIT ?
                """,
                (
                    f"{query_lower}%",     # Prefix match
                    f"%{query_lower}%",    # Contains match
                    query_lower,           # Exact match check
                    f"{query_lower}%",     # Prefix match check
                    limit
                )
            )

            tags = []
            for row in cursor.fetchall():
                tags.append({
                    'id': row[0],
                    'name': row[1],
                    'level': row[2],
                    'use_count': row[3],
                    'last_used_at': row[4]
                })

            return tags
        finally:
            conn.close()

    @staticmethod
    def get_tag_children(tag_name: str) -> List[Dict[str, Any]]:
        """Get all child tags for a parent tag.

        Args:
            tag_name: Parent tag name (e.g., "project")

        Returns:
            List of child tags (e.g., ["project/alpha", "project/beta"])

        Example:
            >>> get_tag_children("project")
            [
                {"name": "project/alpha", "use_count": 12},
                {"name": "project/beta", "use_count": 8}
            ]
        """
        conn = get_db_connection()
        try:
            # Get parent tag ID
            cursor = conn.execute(
                "SELECT id FROM tags WHERE name = ?",
                (tag_name.lower(),)
            )
            parent = cursor.fetchone()
            if not parent:
                return []

            parent_id = parent[0]

            # Get all children
            cursor = conn.execute(
                """
                SELECT id, name, level, use_count
                FROM tags
                WHERE parent_id = ?
                ORDER BY use_count DESC, name ASC
                """,
                (parent_id,)
            )

            children = []
            for row in cursor.fetchall():
                children.append({
                    'id': row[0],
                    'name': row[1],
                    'level': row[2],
                    'use_count': row[3]
                })

            return children
        finally:
            conn.close()

    @staticmethod
    def rename_tag(tag_id: str, new_name: str) -> None:
        """Rename a tag (updates all note_tags references automatically).

        Design: UUID-based references mean renaming doesn't break relationships.

        Args:
            tag_id: Tag UUID
            new_name: New tag name

        Batch-compatible: Safe for bulk rename operations
        """
        conn = get_db_connection()
        new_name = new_name.lower()

        try:
            # Parse new hierarchy
            full_name, parent_name, level = TagRepository._parse_tag_hierarchy(new_name)

            # Get or create new parent if needed
            parent_id = None
            if parent_name:
                parent_id = TagRepository.get_or_create_tag(parent_name)

            # Update tag
            conn.execute(
                """
                UPDATE tags
                SET name = ?, parent_id = ?, level = ?
                WHERE id = ?
                """,
                (full_name, parent_id, level, tag_id)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def merge_tags(source_tag_ids: List[str], target_tag_name: str) -> str:
        """Merge multiple tags into one.

        All notes tagged with source tags will be re-tagged with target tag.
        Source tags are deleted after merge.

        Args:
            source_tag_ids: List of tag UUIDs to merge from
            target_tag_name: Name of target tag (created if doesn't exist)

        Returns:
            Target tag UUID

        Batch-compatible: Designed for cleanup operations

        Example:
            >>> merge_tags(
            ...     ["uuid-work", "uuid-Work", "uuid-WORK"],
            ...     "work"
            ... )
            # All notes with any variant of "work" now have canonical "work" tag
        """
        target_tag_id = TagRepository.get_or_create_tag(target_tag_name)
        conn = get_db_connection()

        try:
            for source_id in source_tag_ids:
                # Get all notes with source tag
                cursor = conn.execute(
                    "SELECT note_id, created_at, source FROM note_tags WHERE tag_id = ?",
                    (source_id,)
                )
                note_associations = cursor.fetchall()

                # Re-tag all notes with target tag
                for note_id, created_at, source in note_associations:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO note_tags (note_id, tag_id, created_at, source)
                        VALUES (?, ?, ?, ?)
                        """,
                        (note_id, target_tag_id, created_at, source)
                    )

                # Delete source tag (CASCADE will remove note_tags entries)
                conn.execute("DELETE FROM tags WHERE id = ?", (source_id,))

            conn.commit()
            return target_tag_id

        finally:
            conn.close()

    @staticmethod
    def get_tag_usage_stats() -> List[Dict[str, Any]]:
        """Get tag usage statistics for analytics.

        Returns:
            List of tags with usage metrics (from tag_usage_stats view)

        Useful for:
        - Identifying dormant tags (unused >90 days)
        - Finding duplicate candidates (#work, #Work)
        - Tag cleanup recommendations
        """
        conn = get_db_connection()
        try:
            cursor = conn.execute(
                """
                SELECT
                    id, name, use_count, last_used_at,
                    days_since_last_use, status
                FROM tag_usage_stats
                ORDER BY use_count DESC
                """
            )

            stats = []
            for row in cursor.fetchall():
                stats.append({
                    'id': row[0],
                    'name': row[1],
                    'use_count': row[2],
                    'last_used_at': row[3],
                    'days_since_last_use': row[4],
                    'status': row[5]  # never_used | active | recent | stale | dormant
                })

            return stats
        finally:
            conn.close()

    @staticmethod
    def get_notes_by_tag(tag_id: str, include_children: bool = True) -> List[str]:
        """Get all note IDs with a specific tag.

        Args:
            tag_id: Tag UUID
            include_children: If True, also return notes with child tags
                             (e.g., "project" includes "project/alpha" notes)

        Returns:
            List of note IDs

        Batch-compatible: Used for batch tagging operations
        """
        conn = get_db_connection()
        try:
            if not include_children:
                # Simple query - just this tag
                cursor = conn.execute(
                    "SELECT note_id FROM note_tags WHERE tag_id = ?",
                    (tag_id,)
                )
            else:
                # Complex query - this tag + all descendants
                cursor = conn.execute(
                    """
                    WITH RECURSIVE tag_tree AS (
                        SELECT id FROM tags WHERE id = ?
                        UNION ALL
                        SELECT t.id FROM tags t
                        JOIN tag_tree tt ON t.parent_id = tt.id
                    )
                    SELECT DISTINCT nt.note_id
                    FROM note_tags nt
                    WHERE nt.tag_id IN (SELECT id FROM tag_tree)
                    """,
                    (tag_id,)
                )

            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()
