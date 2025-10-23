"""
Rebuild all edges for existing notes.
Useful when background tasks didn't complete properly.
"""
from api.config import get_db_connection
from api.db.graph import get_all_nodes
from api.services.semantic import create_semantic_edges
from api.services.linking import create_entity_links, create_tag_links

def rebuild_all_edges():
    """Rebuild semantic, entity, and tag edges for all nodes."""

    print("=" * 80)
    print("REBUILDING ALL EDGES")
    print("=" * 80)
    print()

    con = get_db_connection()

    # Clear existing edges
    print("Clearing existing edges...")
    con.execute("DELETE FROM graph_edges")
    con.commit()
    print("✅ Edges cleared")
    print()

    # Get all nodes
    nodes = get_all_nodes()
    print(f"Found {len(nodes)} nodes to process")
    print()

    for i, node in enumerate(nodes, 1):
        note_id = node['id']
        print(f"[{i}/{len(nodes)}] Processing {note_id[:30]}...")

        try:
            # Create semantic edges
            create_semantic_edges(note_id, con)

            # Create entity links
            create_entity_links(note_id, con)

            # Create tag links
            create_tag_links(note_id, con)

            con.commit()
            print(f"  ✅ Done")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            con.rollback()

    # Show final counts
    print()
    print("=" * 80)
    print("EDGE STATISTICS")
    print("=" * 80)
    print()

    cursor = con.execute("""
        SELECT
          relation,
          COUNT(*) as count
        FROM graph_edges
        GROUP BY relation
        ORDER BY count DESC
    """)

    for row in cursor.fetchall():
        print(f"  {row[0]:20} {row[1]:4} edges")

    cursor = con.execute("SELECT COUNT(*) FROM graph_edges")
    total = cursor.fetchone()[0]
    print(f"  {'TOTAL':20} {total:4} edges")
    print()

    con.close()

if __name__ == "__main__":
    rebuild_all_edges()
    print("✅ Rebuild complete!")
