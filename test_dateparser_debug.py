#!/usr/bin/env python3
"""
Debug dateparser behavior for relative dates.

Test cases from Phase 3 benchmark that failed timedata linking.
"""
import dateparser
from datetime import datetime

# Test context: 2025-10-21 (Tuesday)
test_date = "2025-10-21 12:00 PST"
base_date = datetime.fromisoformat("2025-10-21")

print("=" * 80)
print("Dateparser Debug - Relative Date Parsing")
print("=" * 80)
print(f"\nBASE DATE: {test_date} (Tuesday)")
print()

test_cases = [
    # From benchmark failures
    ("Friday", "2025-10-25T00:00:00", "Should be this Friday (4 days ahead)"),
    ("by Friday", "2025-10-25T00:00:00", "Should be this Friday"),
    ("this Friday", "2025-10-25T00:00:00", "Should be this Friday"),
    ("next Tuesday", "2025-10-28T00:00:00", "Should be next week Tuesday (7 days ahead)"),
    ("next Tuesday at 10am", "2025-10-28T10:00:00", "Should be next week Tuesday"),
    ("tomorrow at 2pm", "2025-10-22T14:00:00", "Should be Wednesday"),
    ("in Q2", "Should parse Q2 2026", "Q2 parsing"),
]

print("-" * 80)
print(f"{'Input':<30} {'Expected':<25} {'Parsed':<25} {'Match'}")
print("-" * 80)

for time_text, expected, note in test_cases:
    parsed = dateparser.parse(
        time_text,
        settings={
            'RELATIVE_BASE': base_date,
            'TIMEZONE': 'America/Los_Angeles',
            'RETURN_AS_TIMEZONE_AWARE': False,
            'PREFER_DATES_FROM': 'future'  # This might help
        }
    )

    parsed_str = parsed.isoformat() if parsed else "FAILED"
    match = "✓" if parsed and parsed_str.startswith(expected[:10]) else "✗"

    print(f"{time_text:<30} {expected:<25} {parsed_str:<25} {match}")

print()
print("=" * 80)
print("Analysis")
print("=" * 80)
print()

# Test different settings
print("Testing 'Friday' with different settings:")
print()

settings_variants = [
    {"RELATIVE_BASE": base_date},
    {"RELATIVE_BASE": base_date, "PREFER_DATES_FROM": "future"},
    {"RELATIVE_BASE": base_date, "PREFER_DATES_FROM": "current_period"},
    {"RELATIVE_BASE": base_date, "STRICT_PARSING": True},
]

for i, settings in enumerate(settings_variants, 1):
    parsed = dateparser.parse("Friday", settings=settings)
    print(f"  Settings {i}: {settings}")
    print(f"  Result: {parsed.isoformat() if parsed else 'FAILED'}")
    print()

print("Testing 'next Tuesday' with different settings:")
print()

for i, settings in enumerate(settings_variants, 1):
    parsed = dateparser.parse("next Tuesday", settings=settings)
    print(f"  Settings {i}: {settings}")
    print(f"  Result: {parsed.isoformat() if parsed else 'FAILED'}")
    print()
