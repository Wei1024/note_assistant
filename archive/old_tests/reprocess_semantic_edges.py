#!/usr/bin/env python3
"""
Reprocess semantic edges for all existing notes with updated threshold.
This script will create semantic edges for the 30 test notes with threshold=0.5
"""
from api.config import get_db_connection
from api.db.graph import get_all_nodes
from api.services.semantic import create_semantic_edges

def reprocess_all_semantic_edges():
    """Reprocess semantic edges for all notes with new threshold"""
    print("=" * 80)
    print("REPROCESSING SEMANTIC EDGES (threshold=0.5)")
    print("=" * 80)
    print()

    con = get_db_connection()

    try:
        # Delete old semantic edges (if any)
        deleted = con.execute("DELETE FROM graph_edges WHERE relation = 'semantic'").rowcount
        con.commit()
        print(f"🗑️  Deleted {deleted} old semantic edges\n")

        # Get all nodes
        nodes = get_all_nodes()
        print(f"📊 Processing {len(nodes)} notes...\n")

        # Process each note
        for i, node in enumerate(nodes, 1):
            note_id = node['id']
            print(f"[{i}/{len(nodes)}] Creating semantic edges for {note_id[:30]}...")

            create_semantic_edges(note_id, con)

        con.commit()

        # Count created edges
        semantic_count = con.execute(
            "SELECT COUNT(*) FROM graph_edges WHERE relation = 'semantic'"
        ).fetchone()[0]

        print()
        print("=" * 80)
        print(f"✅ COMPLETE: Created {semantic_count} semantic edges")
        print("=" * 80)
        print()

        # Show sample edges
        if semantic_count > 0:
            print("Sample semantic edges:")
            edges = con.execute("""
                SELECT src_node_id, dst_node_id, weight
                FROM graph_edges
                WHERE relation = 'semantic'
                ORDER BY weight DESC
                LIMIT 5
            """).fetchall()

            for src, dst, weight in edges:
                print(f"  {src[:30]}... ↔ {dst[:30]}... (similarity={weight:.3f})")

    except Exception as e:
        con.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        con.close()

if __name__ == "__main__":
    reprocess_all_semantic_edges()
