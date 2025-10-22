#!/usr/bin/env python3
"""
Test the hybrid dateparser + parsedatetime fix for relative dates.

Tests the actual _extract_time_references function from episodic.py.
"""
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from api.services.episodic import _extract_time_references

# Test context: 2025-10-21 12:00 PST (Tuesday)
test_date = "2025-10-21 12:00 PST"

print("=" * 80)
print("Testing Hybrid dateparser + parsedatetime Fix")
print("=" * 80)
print(f"\nBASE DATE: {test_date} (Tuesday)")
print()

test_cases = [
    # From benchmark failures - these should now work
    ("Need to research by Friday", "2025-10-24T00:00:00", "Standalone Friday"),
    ("TODO: Call Mom tomorrow at 2pm", "2025-10-22T14:00:00", "Tomorrow with time"),
    ("Doctor appointment next Tuesday at 10am", "2025-10-28T10:00:00", "next Tuesday"),
    ("Dentist appointment next Tuesday at 10am", "2025-10-28T10:00:00", "next Tuesday variant"),
    ("Discussed OAuth2 implementation. Action: I'll implement it by Friday", "2025-10-24T00:00:00", "by Friday"),
    ("Set up meeting with Josh this Friday", "2025-10-24T00:00:00", "this Friday"),
    ("Planning to add features in Q2", "2025", "Q2 reference"),
    ("Meeting with Sarah today", "2025-10-21", "today"),
]

print("-" * 80)
print(f"{'Note Text':<50} {'Expected':<20} {'Result'}")
print("-" * 80)

for note_text, expected, description in test_cases:
    # Extract time references using the actual function
    time_refs = _extract_time_references(note_text, test_date)

    if time_refs:
        # Get the first parsed date
        parsed_str = time_refs[0].get('parsed', 'None')
        if parsed_str and parsed_str.startswith(expected[:10]):
            result = f"✓ {parsed_str}"
        else:
            result = f"✗ {parsed_str}"
    else:
        result = "✗ No time refs found"

    print(f"{description:<50} {expected:<20} {result}")

print()
print("=" * 80)
print("Detailed Results")
print("=" * 80)
print()

# Show detailed extraction for key cases
detailed_tests = [
    "Need to research by Friday",
    "Doctor appointment next Tuesday at 10am",
    "Set up meeting with Josh this Friday",
]

for note_text in detailed_tests:
    print(f"Input: {note_text}")
    time_refs = _extract_time_references(note_text, test_date)
    if time_refs:
        for ref in time_refs:
            print(f"  - original: '{ref['original']}'")
            print(f"    parsed: {ref['parsed']}")
            print(f"    type: {ref['type']}")
    else:
        print("  No time references extracted")
    print()
