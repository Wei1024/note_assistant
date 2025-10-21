"""
Test batch import of all 30 test notes through /capture_note endpoint
"""
import asyncio
import httpx
import csv
import json
from datetime import datetime


async def import_test_notes():
    """Import all notes from test_notes_labeled.csv"""

    print("=" * 80)
    print("BATCH IMPORT TEST - 30 Notes")
    print("=" * 80)

    # Read test notes
    notes = []
    with open('test_data/test_notes_labeled.csv', 'r') as f:
        reader = csv.DictReader(f)
        notes = list(reader)

    print(f"\n📝 Found {len(notes)} test notes to import\n")

    success_count = 0
    error_count = 0
    results = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, note in enumerate(notes, 1):
            note_text = note['note_text']
            note_id = note['note_id']

            print(f"[{i}/{len(notes)}] Importing note {note_id}...")
            print(f"   Text: {note_text[:60]}...")

            try:
                response = await client.post(
                    "http://localhost:8000/capture_note",
                    json={"text": note_text}
                )

                if response.status_code == 200:
                    result = response.json()
                    episodic = result['episodic']

                    print(f"   ✅ Success!")
                    print(f"      Title: {result['title']}")
                    print(f"      WHO: {episodic['who']}")
                    print(f"      WHAT: {episodic['what'][:3] if len(episodic['what']) > 3 else episodic['what']}")
                    print(f"      WHEN: {[t['original'] for t in episodic['when']][:2]}")
                    print(f"      Tags: {episodic['tags']}")

                    success_count += 1
                    results.append({
                        'note_id': note_id,
                        'status': 'success',
                        'extracted': episodic
                    })
                else:
                    print(f"   ❌ Failed: HTTP {response.status_code}")
                    error_count += 1
                    results.append({
                        'note_id': note_id,
                        'status': 'error',
                        'error': f"HTTP {response.status_code}"
                    })

            except Exception as e:
                print(f"   ❌ Error: {e}")
                error_count += 1
                results.append({
                    'note_id': note_id,
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

    # Save results
    with open('test_data/batch_import_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to test_data/batch_import_results.json")

    return success_count, error_count


if __name__ == "__main__":
    print("\n🚀 Starting batch import test...")
    print("⚠️  Make sure the API server is running on http://localhost:8000\n")

    try:
        success, errors = asyncio.run(import_test_notes())
        exit(0 if errors == 0 else 1)
    except httpx.ConnectError:
        print("\n❌ Could not connect to API server!")
        print("   Start the server with: uvicorn api.main:app --reload")
        exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
