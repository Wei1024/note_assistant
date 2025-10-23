"""
Migrate existing database tags from old taxonomy to new taxonomy v2.

Re-extracts tags for all notes using the new tag extraction model.
Shows before/after comparison and impact on tag_link edges.
"""
import asyncio
import sqlite3
import json
from datetime import datetime
from collections import Counter
from api.config import get_db_connection
from api.services.episodic import _extract_tags_llm
from api.db.graph import get_all_nodes

async def migrate_tags():
    """Re-extract tags for all notes using new taxonomy v2."""

    print("=" * 80)
    print("TAG MIGRATION: Old Taxonomy → Taxonomy v2")
    print("=" * 80)
    print()

    # Get database connection
    conn = get_db_connection()

    # Get all nodes
    print("Loading all notes from database...")
    nodes = get_all_nodes()
    print(f"Found {len(nodes)} notes")
    print()

    # Collect statistics
    old_tags_all = []
    new_tags_all = []
    changes = []

    print("=" * 80)
    print("Re-extracting tags with new taxonomy...")
    print("=" * 80)
    print()

    for i, node in enumerate(nodes, 1):
        note_id = node['id']
        old_tags = node.get('tags', [])
        file_path = node.get('file_path')

        # Get note content from file
        if not file_path:
            print(f"[{i}/{len(nodes)}] Note {note_id}: No file path, skipping")
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"[{i}/{len(nodes)}] Note {note_id}: File not found at {file_path}, skipping")
            continue

        # Extract new tags
        print(f"[{i}/{len(nodes)}] Processing note {note_id}...")
        print(f"  Content preview: {content[:60]}...")
        print(f"  Old tags: {old_tags}")

        try:
            new_tags = await _extract_tags_llm(content)
            print(f"  New tags: {new_tags}")

            # Update database
            conn.execute(
                "UPDATE graph_nodes SET tags = ? WHERE id = ?",
                (json.dumps(new_tags), note_id)
            )

            # Track stats
            old_tags_all.extend(old_tags)
            new_tags_all.extend(new_tags)

            if set(old_tags) != set(new_tags):
                changes.append({
                    'note_id': note_id,
                    'old': old_tags,
                    'new': new_tags,
                    'content_preview': content[:80]
                })
                print(f"  ✓ CHANGED")
            else:
                print(f"  = Same")

        except Exception as e:
            print(f"  ✗ ERROR: {e}")

        print()

    conn.commit()

    # Print statistics
    print("=" * 80)
    print("MIGRATION STATISTICS")
    print("=" * 80)
    print()

    print(f"Total notes processed: {len(nodes)}")
    print(f"Notes with changed tags: {len(changes)}")
    print(f"Notes unchanged: {len(nodes) - len(changes)}")
    print()

    # Tag distribution comparison
    old_tag_counts = Counter(old_tags_all)
    new_tag_counts = Counter(new_tags_all)

    print("=" * 80)
    print("TAG DISTRIBUTION COMPARISON")
    print("=" * 80)
    print()

    print("OLD TAXONOMY - Top 20 tags:")
    for tag, count in old_tag_counts.most_common(20):
        print(f"  {tag:30} {count:3} notes")
    print()

    print("NEW TAXONOMY - Top 20 tags:")
    for tag, count in new_tag_counts.most_common(20):
        print(f"  {tag:30} {count:3} notes")
    print()

    # Specific changes
    print("=" * 80)
    print("SAMPLE CHANGES (First 10)")
    print("=" * 80)
    print()

    for i, change in enumerate(changes[:10], 1):
        print(f"{i}. Note {change['note_id']}")
        print(f"   Content: {change['content_preview']}...")
        print(f"   Old: {change['old']}")
        print(f"   New: {change['new']}")
        print()

    # Check tag_link edges impact
    print("=" * 80)
    print("TAG_LINK EDGES IMPACT")
    print("=" * 80)
    print()

    cursor = conn.execute(
        "SELECT COUNT(*) FROM graph_edges WHERE relation = 'tag_link'"
    )
    old_edge_count = cursor.fetchone()[0]

    print(f"Current tag_link edges (before rebuild): {old_edge_count}")
    print()
    print("⚠️  NOTE: Tag edges need to be rebuilt!")
    print("   Run: python rebuild_tag_edges.py")
    print()

    # Save detailed report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"test_data/tag_migration_report_{timestamp}.json"

    with open(report_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'total_notes': len(nodes),
            'notes_changed': len(changes),
            'old_tag_distribution': dict(old_tag_counts),
            'new_tag_distribution': dict(new_tag_counts),
            'changes': changes
        }, f, indent=2)

    print(f"Detailed report saved to: {report_file}")
    print()

    conn.close()

    return {
        'total_notes': len(nodes),
        'notes_changed': len(changes),
        'old_tags': len(old_tags_all),
        'new_tags': len(new_tags_all)
    }


if __name__ == "__main__":
    print()
    print("Starting tag migration to taxonomy v2...")
    print()

    summary = asyncio.run(migrate_tags())

    print()
    print("=" * 80)
    print("MIGRATION COMPLETE!")
    print("=" * 80)
    print(f"  Total notes: {summary['total_notes']}")
    print(f"  Notes changed: {summary['notes_changed']}")
    print(f"  Total old tags: {summary['old_tags']}")
    print(f"  Total new tags: {summary['new_tags']}")
    print()
    print("Next steps:")
    print("  1. Review the migration report")
    print("  2. Rebuild tag_link edges: python rebuild_tag_edges.py")
    print("  3. Check the graph view to see new tag clustering")
    print()
