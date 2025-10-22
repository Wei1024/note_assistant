#!/usr/bin/env python3
"""
Debug timezone handling in dateparser vs parsedatetime
"""
import dateparser
import parsedatetime as pdt
from datetime import datetime

# Test context: 2025-10-21 12:00 PST (Tuesday)
test_date_str = "2025-10-21 12:00 PST"
base_date = datetime.fromisoformat("2025-10-21")

print("=" * 80)
print("Timezone Debug - dateparser vs parsedatetime")
print("=" * 80)
print(f"\nBASE DATE: {base_date}")
print(f"BASE DATE STR: {test_date_str}")
print()

# Test "10am" parsing with both libraries
test_time = "10am"
print(f"Testing: '{test_time}'")
print("-" * 80)

# dateparser
dp_result = dateparser.parse(
    test_time,
    settings={
        'RELATIVE_BASE': base_date,
        'TIMEZONE': 'America/Los_Angeles',
        'RETURN_AS_TIMEZONE_AWARE': False,
        'PREFER_DATES_FROM': 'future'
    }
)
print(f"dateparser result: {dp_result}")
print(f"  ISO: {dp_result.isoformat() if dp_result else 'None'}")

# parsedatetime
cal = pdt.Calendar()
pdt_result, status = cal.parseDT(test_time, sourceTime=base_date)
print(f"\nparsedatetime result: {pdt_result}")
print(f"  status: {status}")
print(f"  ISO: {pdt_result.isoformat() if pdt_result else 'None'}")

print()
print("=" * 80)
print("Testing 'next Tuesday at 10am'")
print("=" * 80)

test_text = "next Tuesday at 10am"

# dateparser
dp_result = dateparser.parse(
    test_text,
    settings={
        'RELATIVE_BASE': base_date,
        'TIMEZONE': 'America/Los_Angeles',
        'RETURN_AS_TIMEZONE_AWARE': False,
        'PREFER_DATES_FROM': 'future'
    }
)
print(f"dateparser result: {dp_result}")
print(f"  ISO: {dp_result.isoformat() if dp_result else 'None'}")

# parsedatetime
pdt_result, status = cal.parseDT(test_text, sourceTime=base_date)
print(f"\nparsedatetime result: {pdt_result}")
print(f"  status: {status}")
print(f"  ISO: {pdt_result.isoformat() if pdt_result else 'None'}")

print()
print("=" * 80)
print("Just 'next Tuesday' (no time)")
print("=" * 80)

test_text = "next Tuesday"

# dateparser
dp_result = dateparser.parse(
    test_text,
    settings={
        'RELATIVE_BASE': base_date,
        'TIMEZONE': 'America/Los_Angeles',
        'RETURN_AS_TIMEZONE_AWARE': False,
        'PREFER_DATES_FROM': 'future'
    }
)
print(f"dateparser result: {dp_result}")
print(f"  ISO: {dp_result.isoformat() if dp_result else 'None'}")

# parsedatetime
pdt_result, status = cal.parseDT(test_text, sourceTime=base_date)
print(f"\nparsedatetime result: {pdt_result}")
print(f"  status: {status}")
print(f"  ISO: {pdt_result.isoformat() if pdt_result else 'None'}")

print()
print("=" * 80)
print("Analysis")
print("=" * 80)
print()
print("The issue: parsedatetime might be using system local time")
print("while our base_date is naive (no timezone info)")
print()
print(f"System timezone info:")
import time
print(f"  time.tzname: {time.tzname}")
print(f"  time.timezone: {time.timezone} seconds offset")
print(f"  time.daylight: {time.daylight}")
