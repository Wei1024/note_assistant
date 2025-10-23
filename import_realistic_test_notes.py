"""
Import realistic test dataset (50 notes) with thematic clusters.
"""
import asyncio
import httpx
import csv
import json
from datetime import datetime

async def import_notes():
    """Import all notes from realistic_test_notes.csv"""

    print("=" * 80)
    print("IMPORTING REALISTIC TEST DATASET - 50 Notes")
    print("=" * 80)
    print()

    # Read test notes
    notes = []
    with open('test_data/realistic_test_notes.csv', 'r') as f:
        reader = csv.DictReader(f)
        notes = list(reader)

    print(f"📝 Found {len(notes)} test notes to import")
    print()
    print("THEMATIC CLUSTERS:")
    themes = {}
    for note in notes:
        theme = note['theme_cluster']
        themes[theme] = themes.get(theme, 0) + 1

    for theme, count in sorted(themes.items(), key=lambda x: x[1], reverse=True):
        print(f"  {theme:25} {count:2} notes")
    print()

    success_count = 0
    error_count = 0
    results = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, note in enumerate(notes, 1):
            note_text = note['note_text']
            note_id = note['note_id']
            theme = note['theme_cluster']

            print(f"[{i}/{len(notes)}] Importing note {note_id} ({theme})...")
            print(f"   Text: {note_text[:70]}...")

            try:
                response = await client.post(
                    "http://localhost:8000/capture_note",
                    json={"text": note_text}
                )

                if response.status_code == 200:
                    result = response.json()
                    episodic = result['episodic']

                    print(f"   ✅ Success!")
                    print(f"      Tags: {episodic['tags']}")
                    print(f"      WHO: {episodic['who']}")
                    print(f"      WHAT: {episodic['what'][:2] if len(episodic['what']) > 2 else episodic['what']}")

                    success_count += 1
                    results.append({
                        'note_id': note_id,
                        'theme': theme,
                        'status': 'success',
                        'extracted_tags': episodic['tags'],
                        'expected_tags': json.loads(note['expected_tags'])
                    })
                else:
                    print(f"   ❌ Failed: HTTP {response.status_code}")
                    error_count += 1
                    results.append({
                        'note_id': note_id,
                        'theme': theme,
                        'status': 'error',
                        'error': f"HTTP {response.status_code}"
                    })

            except Exception as e:
                print(f"   ❌ Error: {e}")
                error_count += 1
                results.append({
                    'note_id': note_id,
                    'theme': theme,
                    'status': 'error',
                    'error': str(e)
                })

            print()

    # Summary
    print("=" * 80)
    print("IMPORT SUMMARY")
    print("=" * 80)
    print(f"✅ Successful: {success_count}/{len(notes)}")
    print(f"❌ Errors: {error_count}/{len(notes)}")
    print(f"Success Rate: {success_count/len(notes)*100:.1f}%")
    print()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f'test_data/realistic_import_results_{timestamp}.json'

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"💾 Results saved to {results_file}")
    print()

    return success_count, error_count

if __name__ == "__main__":
    print()
    print("🚀 Starting realistic dataset import...")
    print("⚠️  Make sure the API server is running on http://localhost:8000")
    print("⚠️  Database should be empty or you'll have duplicates!")
    print()

    input("Press Enter to continue or Ctrl+C to cancel...")
    print()

    try:
        success, errors = asyncio.run(import_notes())
        print()
        print("✅ Import complete!")
        print()
        print("Next steps:")
        print("  1. Check edge distribution: sqlite3 ~/Notes/.index/notes.sqlite")
        print("  2. View the graph in the web UI")
        print("  3. Compare 'All' vs 'Semantic' vs 'Entity' vs 'Tags' views")
        print()
        exit(0 if errors == 0 else 1)
    except httpx.ConnectError:
        print("\n❌ Could not connect to API server!")
        print("   Start the server with: uvicorn api.main:app --reload")
        exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Import cancelled by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
