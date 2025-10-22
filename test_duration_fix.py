#!/usr/bin/env python3
"""
Test the duration pattern fix for past-context durations
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.services.episodic import _extract_time_references

test_date = "2025-10-20 14:00 PST"

test_cases = [
    # Past context (should have parsed: null)
    ("Frustrated with this bug for 3 hours. Finally found it", "for 3 hours", "past"),
    ("Waited 30 minutes for the meeting to start", "30 minutes", "past"),
    ("Took 2 hours to debug this issue", "2 hours", "past"),
    ("After 5 days of work, finally done", "5 days", "past"),

    # Future context (should have parsed timestamp)
    ("Meeting in 3 hours", "in 3 hours", "future"),
    ("Deadline in 2 days", "in 2 days", "future"),
    ("Will take 30 minutes", "30 minutes", "future - ambiguous"),
]

print("=" * 80)
print("Testing Duration Pattern Fix")
print("=" * 80)
print(f"\nBase date: {test_date}")
print()
print(f"{'Note Text':<60} {'Extracted':<30} {'Result'}")
print("-" * 80)

for note_text, duration, context_type in test_cases:
    refs = _extract_time_references(note_text, test_date)

    duration_refs = [r for r in refs if r['type'] == 'duration']

    if duration_refs:
        ref = duration_refs[0]
        parsed = ref.get('parsed')

        if context_type.startswith("past"):
            if parsed is None:
                result = "✓ Correctly null"
            else:
                result = f"✗ Should be null, got {parsed}"
        elif context_type.startswith("future"):
            if parsed is not None:
                result = f"✓ Has timestamp: {parsed}"
            else:
                result = "✗ Should have timestamp"
        else:
            result = f"Parsed: {parsed}"

        print(f"{note_text[:60]:<60} {ref['original']:<30} {result}")
    else:
        print(f"{note_text[:60]:<60} {'(not extracted)':<30} ✗ Missing")

print()
print("=" * 80)
print("Expected: Past-context durations have parsed=null")
print("=" * 80)
