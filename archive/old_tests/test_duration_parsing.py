#!/usr/bin/env python3
"""
Test how dateparser handles duration patterns
"""
import dateparser
from datetime import datetime

base_date = datetime.fromisoformat("2025-10-21")

test_cases = [
    "3 hours",           # Standalone
    "in 3 hours",        # Future
    "after 3 hours",     # Past context
    "3 hours ago",       # Past
    "next 3 hours",      # Future range
    "5 minutes",         # Another duration
    "in 5 minutes",      # Future
]

print("=" * 80)
print("Testing dateparser with duration patterns")
print("=" * 80)
print(f"\nBase date: {base_date} (2025-10-21 00:00:00)")
print()
print(f"{'Input':<20} {'Parsed Result':<30} {'Notes'}")
print("-" * 80)

for text in test_cases:
    result = dateparser.parse(
        text,
        settings={
            'RELATIVE_BASE': base_date,
            'TIMEZONE': 'America/Los_Angeles',
            'RETURN_AS_TIMEZONE_AWARE': False,
            'PREFER_DATES_FROM': 'future'
        }
    )

    if result:
        notes = ""
        if "3 hours" in text and result.hour == 3:
            notes = "⚠️ Interpreted as 3:00 AM!"
        elif "ago" in text and result < base_date:
            notes = "✓ Correctly past"
        elif "in" in text and result > base_date:
            notes = "✓ Correctly future"

        print(f"{text:<20} {result.isoformat():<30} {notes}")
    else:
        print(f"{text:<20} FAILED TO PARSE")

print()
print("=" * 80)
print("PROBLEM: '3 hours' and 'after 3 hours' parse as 3:00 AM")
print("SOLUTION: Filter out duration patterns in past context")
print("=" * 80)
