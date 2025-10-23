#!/usr/bin/env python3
"""
Test how parsedatetime interprets "next week" from different base days
"""
import parsedatetime as pdt
from datetime import datetime

cal = pdt.Calendar()

# Test from different days of the week
test_cases = [
    ("2025-10-20", "Monday"),    # Monday
    ("2025-10-21", "Tuesday"),   # Tuesday
    ("2025-10-22", "Wednesday"), # Wednesday
    ("2025-10-23", "Thursday"),  # Thursday
    ("2025-10-24", "Friday"),    # Friday
    ("2025-10-25", "Saturday"),  # Saturday
    ("2025-10-26", "Sunday"),    # Sunday
]

print("=" * 80)
print("How parsedatetime interprets 'next week' from different days")
print("=" * 80)
print()
print(f"{'Base Date':<20} {'Day':<12} {'Parsed Result':<20} {'Target Day'}")
print("-" * 80)

for date_str, day_name in test_cases:
    base = datetime.fromisoformat(date_str)
    dt, status = cal.parseDT("next week", sourceTime=base)

    if dt:
        target_day = dt.strftime("%A")
        print(f"{date_str:<20} {day_name:<12} {dt.date():<20} {target_day}")
    else:
        print(f"{date_str:<20} {day_name:<12} FAILED")

print()
print("=" * 80)
print("PATTERN:")
print("  Does 'next week' always resolve to the SAME DAY OF WEEK, one week ahead?")
print("=" * 80)
