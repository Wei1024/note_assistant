#!/usr/bin/env python3
"""
Test parsedatetime with combined date+time patterns
"""
import parsedatetime as pdt
from datetime import datetime

base_date = datetime.fromisoformat("2025-10-21")
cal = pdt.Calendar()

print("=" * 80)
print("Testing parsedatetime with Combined Date+Time Patterns")
print("=" * 80)
print(f"\nBase date: {base_date} (Tuesday, Oct 21)")
print()

test_cases = [
    "next Tuesday at 10am",
    "next Tuesday 10am",
    "10am next Tuesday",
    "next Tuesday",
    "10am",
]

print("-" * 80)
print(f"{'Input':<30} {'Status':<10} {'Result'}")
print("-" * 80)

for text in test_cases:
    dt, status = cal.parseDT(text, sourceTime=base_date)
    print(f"{text:<30} {status:<10} {dt.isoformat() if dt else 'FAILED'}")

print()
print("=" * 80)
print("Status Codes:")
print("  1 = date only")
print("  2 = time only")
print("  3 = datetime (combined)")
print("=" * 80)
