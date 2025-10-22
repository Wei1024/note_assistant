#!/usr/bin/env python3
"""
Debug Note #22: Where did '2025-10-21T03:00:00' come from?
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.services.episodic import extract_episodic_metadata
from api.services.prospective import extract_prospective_items

async def test():
    test_date = "2025-10-21 12:00 PST"
    note_text = "Finally found the bug after 3 hours - typo in config file. Remember to add linting."

    print("=" * 80)
    print("Debug Note #22: Hallucinated Timestamp")
    print("=" * 80)
    print(f"\nBase date: {test_date}")
    print(f"Note text: {note_text}")
    print()

    # Step 1: Check episodic extraction
    print("-" * 80)
    print("STEP 1: Episodic Extraction (WHEN data)")
    print("-" * 80)
    episodic = await extract_episodic_metadata(note_text, test_date)
    print(f"WHEN extracted: {episodic['when']}")
    print()

    # Step 2: Check prospective extraction
    print("-" * 80)
    print("STEP 2: Prospective Extraction (with WHEN data from Step 1)")
    print("-" * 80)
    prospective = await extract_prospective_items(note_text, episodic['when'])
    print(f"Prospective data: {prospective}")
    print()

    # Analysis
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()
    if episodic['when']:
        print("✓ Episodic extracted WHEN data:")
        for ref in episodic['when']:
            print(f"  - '{ref['original']}' → {ref['parsed']}")
        print()
        print("The hallucinated timestamp came from episodic layer!")
        print("Episodic incorrectly parsed '3 hours' as a timestamp.")
    else:
        print("✗ Episodic did NOT extract any WHEN data")
        print("The hallucinated timestamp came from prospective LLM!")
        print("The LLM invented a timestamp without any WHEN data.")

if __name__ == "__main__":
    asyncio.run(test())
