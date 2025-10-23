#!/usr/bin/env python3
"""
Phase 2 Linking Test
1. Import all 30 test notes via /capture_note
2. Wait for background tasks to complete
3. Query and analyze all edges
4. Generate review reports (CSV/TXT/JSON)
"""
import asyncio
import httpx
import csv
import json
import time
from pathlib import Path
from datetime import datetime


async def import_test_notes():
    """Import 30 test notes via API"""
    print("=" * 80)
    print("PHASE 2 LINKING TEST - Importing Notes")
    print("=" * 80)
    print()

    test_file = Path('test_data/test_notes_labeled.csv')
    if not test_file.exists():
        print(f"❌ Test data file not found: {test_file}")
        print("   Please ensure test_data/test_notes_labeled.csv exists")
        return []

    with open(test_file, 'r') as f:
        reader = csv.DictReader(f)
        test_notes = list(reader)

    print(f"📊 Loaded {len(test_notes)} test notes\n")

    note_ids = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, note in enumerate(test_notes, 1):
            note_id = note.get('note_id', f'note_{i}')
            note_text = note['note_text']

            print(f"[{i}/{len(test_notes)}] Importing: {note_text[:50]}...")

            try:
                response = await client.post(
                    "http://localhost:8000/capture_note",
                    json={"text": note_text}
                )

                if response.status_code == 200:
                    result = response.json()
                    note_ids.append(result['note_id'])
                    print(f"   ✅ Saved as {result['note_id'][:30]}...")
                else:
                    print(f"   ❌ Error: {response.status_code}")
                    print(f"   {response.text}")

            except Exception as e:
                print(f"   ❌ Exception: {e}")

    print(f"\n✅ Imported {len(note_ids)}/{len(test_notes)} notes")
    print("\n⏳ Waiting 90 seconds for background tasks to complete...")
    print("   (Generating embeddings + creating edges for all notes)")

    # Show progress while waiting
    for i in range(90, 0, -10):
        print(f"   {i} seconds remaining...")
        time.sleep(10)

    print("\n✅ Background processing complete\n")

    return note_ids


def analyze_edges():
    """Query and analyze all edges"""
    from api.config import get_db_connection

    print("=" * 80)
    print("EDGE ANALYSIS")
    print("=" * 80)
    print()

    con = get_db_connection()

    # Get all edges with metadata
    edges = con.execute("""
        SELECT src_node_id, dst_node_id, relation, weight, metadata
        FROM graph_edges
        ORDER BY relation, weight DESC
    """).fetchall()

    con.close()

    if not edges:
        print("⚠️  No edges found in database!")
        print("   Possible reasons:")
        print("   - Background tasks haven't completed yet")
        print("   - Notes don't have sufficient similarity/shared entities")
        print("   - Check server logs for errors")
        return [], {}

    # Group by relation type
    by_relation = {}
    for edge in edges:
        relation = edge[2]
        if relation not in by_relation:
            by_relation[relation] = []
        by_relation[relation].append(edge)

    # Print summary
    print(f"📊 Total edges: {len(edges)}\n")

    for relation, rel_edges in sorted(by_relation.items()):
        print(f"🔗 {relation.upper()}: {len(rel_edges)} edges")

        # Calculate weight statistics
        weights = [e[3] for e in rel_edges]
        avg_weight = sum(weights) / len(weights)
        min_weight = min(weights)
        max_weight = max(weights)

        print(f"   Weight: avg={avg_weight:.3f}, min={min_weight:.3f}, max={max_weight:.3f}")

        # Show top 5 strongest
        print(f"   Top 5 strongest:")
        for edge in rel_edges[:5]:
            src, dst, _, weight, metadata_json = edge
            meta_dict = json.loads(metadata_json) if metadata_json else {}

            src_short = src[:20] + "..." if len(src) > 20 else src
            dst_short = dst[:20] + "..." if len(dst) > 20 else dst

            print(f"      {src_short} ↔ {dst_short} (weight={weight:.3f})")

            # Show relevant metadata
            if relation == 'semantic':
                sim = meta_dict.get('similarity', weight)
                print(f"        Similarity: {sim:.3f}")
            elif relation == 'entity_link':
                entity_type = meta_dict.get('entity_type', '?')
                shared = meta_dict.get(f'shared_{entity_type}', [])
                print(f"        Type: {entity_type}, Shared: {shared}")
            elif relation == 'tag_link':
                jaccard = meta_dict.get('jaccard', weight)
                shared_tags = meta_dict.get('shared_tags', [])
                print(f"        Jaccard: {jaccard:.3f}, Tags: {shared_tags}")

        print()

    return edges, by_relation


def generate_reports(edges, by_relation):
    """Generate CSV, TXT, and JSON reports for manual review"""
    output_dir = Path('test_data')
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    print("=" * 80)
    print("GENERATING REPORTS")
    print("=" * 80)
    print()

    # 1. CSV export (all edges with flattened metadata)
    csv_path = output_dir / f'phase2_edges_{timestamp}.csv'
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['src_node_id', 'dst_node_id', 'relation', 'weight', 'metadata_json'])

        for edge in edges:
            writer.writerow(edge)

    print(f"📄 CSV report: {csv_path}")

    # 2. Human-readable report
    txt_path = output_dir / f'phase2_linking_report_{timestamp}.txt'
    with open(txt_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 2 LINKING REPORT\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Total edges: {len(edges)}\n\n")

        for relation, rel_edges in sorted(by_relation.items()):
            f.write(f"\n{'=' * 80}\n")
            f.write(f"{relation.upper()} EDGES ({len(rel_edges)} total)\n")
            f.write(f"{'=' * 80}\n\n")

            for edge in rel_edges:
                src, dst, _, weight, metadata_json = edge
                meta_dict = json.loads(metadata_json) if metadata_json else {}

                f.write(f"{src}\n")
                f.write(f"  ↔\n")
                f.write(f"{dst}\n")
                f.write(f"  Weight: {weight:.3f}\n")

                if meta_dict:
                    f.write(f"  Metadata:\n")
                    for key, value in meta_dict.items():
                        f.write(f"    {key}: {value}\n")

                f.write("\n" + "-" * 80 + "\n\n")

    print(f"📄 Text report: {txt_path}")

    # 3. JSON export (structured data)
    json_path = output_dir / f'phase2_linking_results_{timestamp}.json'
    results = {
        'generated_at': datetime.now().isoformat(),
        'total_edges': len(edges),
        'edges_by_relation': {
            relation: {
                'count': len(rel_edges),
                'edges': [
                    {
                        'src': e[0],
                        'dst': e[1],
                        'weight': e[3],
                        'metadata': json.loads(e[4]) if e[4] else None
                    }
                    for e in rel_edges
                ]
            }
            for relation, rel_edges in by_relation.items()
        }
    }

    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"📄 JSON report: {json_path}")
    print()


async def main():
    """Main test flow"""
    print("\n🧪 PHASE 2 LINKING INTEGRATION TEST\n")
    print("This test will:")
    print("  1. Import 30 test notes via /capture_note")
    print("  2. Wait for background tasks (embeddings + linking)")
    print("  3. Analyze created edges")
    print("  4. Generate reports for manual review\n")

    # Step 1: Import notes
    note_ids = await import_test_notes()

    if not note_ids:
        print("\n❌ No notes were imported. Aborting test.")
        return

    # Step 2: Analyze edges
    edges, by_relation = analyze_edges()

    # Step 3: Generate reports
    if edges:
        generate_reports(edges, by_relation)

        print("=" * 80)
        print("✅ PHASE 2 LINKING TEST COMPLETE")
        print("=" * 80)
        print("\n📋 Next steps:")
        print("  1. Review the generated reports in test_data/")
        print("  2. Check edge quality (are similar notes linked?)")
        print("  3. Validate entity/tag matching with normalization")
        print("  4. Look for any unexpected edges or missing links")
        print()
    else:
        print("=" * 80)
        print("⚠️  TEST COMPLETE (but no edges found)")
        print("=" * 80)
        print()


if __name__ == "__main__":
    print("\n⚠️  Prerequisites:")
    print("  - API server running on http://localhost:8000")
    print("  - test_data/test_notes_labeled.csv exists")
    print("  - Database cleared (optional, for clean test)\n")

    input("Press Enter to continue...")

    try:
        asyncio.run(main())
    except httpx.ConnectError:
        print("\n❌ Could not connect to API server!")
        print("   Start the server with: uvicorn api.main:app --reload --port 8000")
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
