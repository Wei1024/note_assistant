#!/usr/bin/env python3
"""
Test what episodic extracts for "next week"
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.services.episodic import extract_episodic_metadata

async def test():
    test_date = "2025-10-21 12:00 PST"

    notes = [
        "Next week: improve time estimation.",
        "Meeting next week on Tuesday",
        "Planning to work on this next week",
    ]

    print("=" * 80)
    print("Testing 'next week' extraction in episodic layer")
    print("=" * 80)
    print(f"\nBase date: {test_date} (Tuesday, Oct 21)")
    print()

    for note_text in notes:
        print(f"Input: '{note_text}'")
        result = await extract_episodic_metadata(note_text, test_date)

        print(f"  WHEN extracted: {result['when']}")
        print()

if __name__ == "__main__":
    asyncio.run(test())
