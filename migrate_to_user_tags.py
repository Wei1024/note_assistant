#!/usr/bin/env python3
"""
Migration: LLM Tags → User Hashtag System

Steps:
1. Create new tables (tags, note_tags)
2. Clear old LLM-generated tags from graph_nodes
3. Parse any existing #hashtags from note content
4. Display statistics

Usage:
    source .venv/bin/activate
    python migrate_to_user_tags.py
"""

import os
import sqlite3
import sys
from pathlib import Path

# Add api to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from api.config import get_db_connection
from api.repositories.tag_repository import TagRepository
from api.services.episodic import extract_hashtags_from_text


def migrate():
    """Run migration from LLM tags to user hashtag system."""

    print("=" * 80)
    print("MIGRATING TO USER TAG SYSTEM")
    print("=" * 80)
    print()

    # Step 1: Create new tables
    print("Step 1: Creating tag tables...")
    schema_path = Path(__file__).parent / 'api' / 'db' / 'schema_tags.sql'

    if not schema_path.exists():
        print(f"  ❌ Schema file not found: {schema_path}")
        return

    conn = get_db_connection()
    try:
        with open(schema_path, 'r') as f:
            schema = f.read()
            conn.executescript(schema)
        print("  ✅ Tables created (tags, note_tags)")
        print("  ✅ Triggers created (auto-update use_count)")
        print("  ✅ Views created (tags_with_hierarchy, tag_usage_stats)")
    except Exception as e:
        print(f"  ❌ Error creating tables: {e}")
        return
    finally:
        conn.close()

    print()

    # Step 2: Clear old LLM-generated tags
    print("Step 2: Clearing old LLM-generated tags from graph_nodes...")
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM graph_nodes WHERE tags != '[]'")
        old_tag_count = cursor.fetchone()[0]

        conn.execute("UPDATE graph_nodes SET tags = '[]'")
        conn.commit()

        print(f"  ✅ Cleared tags from {old_tag_count} nodes")
    except Exception as e:
        print(f"  ⚠️  Warning: {e}")
    finally:
        conn.close()

    print()

    # Step 3: Parse hashtags from existing note content
    print("Step 3: Parsing #hashtags from note content...")
    conn = get_db_connection()

    try:
        cursor = conn.execute("SELECT id, file_path FROM graph_nodes")
        notes = cursor.fetchall()

        print(f"  Found {len(notes)} notes to scan")
        print()

        tags_found = 0
        notes_with_tags = 0

        for i, (note_id, file_path) in enumerate(notes, 1):
            # Check if file exists
            if not os.path.exists(file_path):
                continue

            # Read note content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"  ⚠️  [{i}/{len(notes)}] Could not read {file_path}: {e}")
                continue

            # Extract hashtags
            tags = extract_hashtags_from_text(content)

            if tags:
                # Add to database
                TagRepository.add_tags_to_note_bulk(note_id, tags, source='detected')

                # Get note title for display
                title = Path(file_path).stem[:40]
                print(f"  [{i}/{len(notes)}] {title}")
                print(f"    Tags: {', '.join(['#' + t for t in tags])}")

                tags_found += len(tags)
                notes_with_tags += 1

        print()
        print(f"  ✅ Found {tags_found} hashtags in {notes_with_tags} notes")

    except Exception as e:
        print(f"  ❌ Error parsing hashtags: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

    print()

    # Step 4: Display statistics
    print("=" * 80)
    print("MIGRATION COMPLETE - STATISTICS")
    print("=" * 80)
    print()

    conn = get_db_connection()
    try:
        # Count unique tags
        cursor = conn.execute("SELECT COUNT(*) FROM tags")
        unique_tags = cursor.fetchone()[0]

        # Count note-tag relationships
        cursor = conn.execute("SELECT COUNT(*) FROM note_tags")
        total_relationships = cursor.fetchone()[0]

        # Get top tags
        cursor = conn.execute("""
            SELECT name, use_count, level
            FROM tags
            ORDER BY use_count DESC
            LIMIT 10
        """)
        top_tags = cursor.fetchall()

        # Count by level
        cursor = conn.execute("""
            SELECT level, COUNT(*)
            FROM tags
            GROUP BY level
            ORDER BY level
        """)
        level_counts = cursor.fetchall()

        print(f"Unique tags created:       {unique_tags}")
        print(f"Total note-tag links:      {total_relationships}")
        print()

        print("Tags by hierarchy level:")
        for level, count in level_counts:
            level_name = {0: 'Root', 1: 'Child', 2: 'Grandchild'}.get(level, f'Level {level}')
            print(f"  {level_name} (level {level}): {count} tags")
        print()

        if top_tags:
            print("Top 10 most used tags:")
            for name, use_count, level in top_tags:
                indent = "  " * level
                print(f"  {indent}#{name:<30} ({use_count} notes)")

    finally:
        conn.close()

    print()
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Manually add hashtags to notes:")
    print("   - Edit note files in ~/Notes/")
    print("   - Add tags like: #project/alpha, #personal, #urgent")
    print()
    print("2. Reimport notes to detect new hashtags:")
    print("   - Re-run this script, OR")
    print("   - Use API to create new notes with hashtags")
    print()
    print("3. Test in graph view:")
    print("   - Start backend: cd api && uvicorn main:app --reload")
    print("   - Start frontend: cd frontend && npm run dev")
    print("   - Check graph view for tag-based edges")
    print()


if __name__ == "__main__":
    migrate()
