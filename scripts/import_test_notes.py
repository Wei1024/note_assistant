#!/usr/bin/env python3
"""
Import Test Notes from CSV
===========================

Reads test notes from CSV and creates them via the API,
allowing full LLM processing and audit logging.
"""
import csv
import asyncio
import httpx
from pathlib import Path

# Test data path
TEST_CSV = Path(__file__).parent.parent / "test_data" / "test_notes.csv"

# API endpoint
API_URL = "http://127.0.0.1:8734"


async def import_notes():
    """Import all test notes from CSV"""

    if not TEST_CSV.exists():
        print(f"❌ Test CSV not found: {TEST_CSV}")
        return

    # Read CSV
    with open(TEST_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        notes = list(reader)

    print(f"📝 Found {len(notes)} test notes in CSV")
    print(f"🚀 Starting import (this will take a few minutes)...\n")

    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, row in enumerate(notes, 1):
            note_text = row['note_text']
            expected_dims = row['expected_dimensions']
            description = row['notes']

            print(f"[{i}/{len(notes)}] Importing: {description}")
            print(f"  Text: {note_text[:60]}...")
            print(f"  Expected: {expected_dims}")

            try:
                # Call the classification endpoint
                response = await client.post(
                    f"{API_URL}/classify_and_save",
                    json={"text": note_text},
                    timeout=120.0
                )

                if response.status_code == 200:
                    result = response.json()
                    dims = result.get('dimensions', {})

                    # Show which dimensions were detected
                    detected = []
                    if dims.get('has_action_items'): detected.append('action')
                    if dims.get('is_social'): detected.append('social')
                    if dims.get('is_emotional'): detected.append('emotional')
                    if dims.get('is_knowledge'): detected.append('knowledge')
                    if dims.get('is_exploratory'): detected.append('exploratory')

                    detected_str = ','.join(detected) if detected else 'none'
                    print(f"  ✓ Detected: {detected_str}")
                    print(f"  Title: {result.get('title', 'N/A')}")
                else:
                    print(f"  ❌ API error: {response.status_code}")

            except Exception as e:
                print(f"  ❌ Error: {type(e).__name__}: {str(e)[:100]}")

            print()

            # Small delay to avoid overwhelming the API
            await asyncio.sleep(0.5)

    print(f"✅ Import complete! {len(notes)} notes processed")
    print(f"\nNext steps:")
    print(f"1. Run: python scripts/analyze_llm_decisions.py")
    print(f"2. Check: sqlite3 ~/Notes/.index/notes.sqlite 'SELECT * FROM llm_operations'")


if __name__ == "__main__":
    asyncio.run(import_notes())
