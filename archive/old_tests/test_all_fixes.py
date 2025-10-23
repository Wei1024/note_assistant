#!/usr/bin/env python3
"""
Comprehensive test of all dateparser + parsedatetime fixes
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.services.episodic import _extract_time_references

test_date = "2025-10-21 12:00 PST"

print("=" * 80)
print("Comprehensive Test: All Dateparser Fixes")
print("=" * 80)
print(f"\nBase date: {test_date} (Tuesday, Oct 21, 2025)")
print()

test_cases = [
    # Original failures from Phase 3 benchmark
    ("Need to research by Friday", "2025-10-24", "Standalone Friday"),
    ("TODO: Call Mom tomorrow at 2pm", "2025-10-22T14:00", "Tomorrow with time"),
    ("Doctor appointment next Tuesday at 10am", "2025-10-28T10:00", "next Tuesday at 10am"),
    ("Dentist appointment next Tuesday at 10am", "2025-10-28T10:00", "next Tuesday at 10am variant"),
    ("I'll implement it by Friday", "2025-10-24", "by Friday"),
    ("Set up meeting with Josh this Friday", "2025-10-24", "this Friday"),
    ("Meeting with Sarah today", "2025-10-21", "today"),

    # Additional edge cases
    ("next Monday", "2025-10-27", "next Monday"),
    ("this Wednesday", "2025-10-22", "this Wednesday"),
    ("last Friday", "2025-10-17", "last Friday"),
    ("tomorrow", "2025-10-22", "tomorrow"),
]

print("-" * 80)
print(f"{'Description':<40} {'Expected':<20} {'Result'}")
print("-" * 80)

all_passed = True

for note_text, expected, description in test_cases:
    time_refs = _extract_time_references(note_text, test_date)

    if time_refs:
        parsed_str = time_refs[0].get('parsed', 'None')
        if parsed_str and parsed_str.startswith(expected):
            result = f"✓ {parsed_str}"
        else:
            result = f"✗ {parsed_str} (expected {expected})"
            all_passed = False
    else:
        result = "✗ No time refs found"
        all_passed = False

    print(f"{description:<40} {expected:<20} {result}")

print()
print("=" * 80)
if all_passed:
    print("✅ ALL TESTS PASSED!")
else:
    print("⚠️  Some tests failed - see details above")
print("=" * 80)
print()

# Show detailed extraction for key combined patterns
print("Detailed Extraction for Combined Patterns:")
print("-" * 80)

combined_tests = [
    "next Tuesday at 10am",
    "this Friday at 2pm",
    "tomorrow at 9:30am",
]

for text in combined_tests:
    print(f"\nInput: '{text}'")
    refs = _extract_time_references(text, test_date)
    if refs:
        for ref in refs:
            print(f"  - original: '{ref['original']}'")
            print(f"    parsed: {ref['parsed']}")
            print(f"    type: {ref['type']}")
    else:
        print("  No references extracted")
