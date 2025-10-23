#!/usr/bin/env python3
"""
Debug the specific extraction case: "next Tuesday at 10am"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.services.episodic import _extract_time_references

test_date = "2025-10-21 12:00 PST"

test_cases = [
    "Doctor appointment next Tuesday at 10am",
    "next Tuesday at 10am",
    "next Tuesday",
]

print("=" * 80)
print("Detailed Extraction Analysis")
print("=" * 80)
print()

for text in test_cases:
    print(f"Input: '{text}'")
    print("-" * 80)

    refs = _extract_time_references(text, test_date)

    if refs:
        for i, ref in enumerate(refs, 1):
            print(f"  {i}. original: '{ref['original']}'")
            print(f"     parsed:   {ref['parsed']}")
            print(f"     type:     {ref['type']}")
            print()
    else:
        print("  No references extracted")
        print()
    print()
