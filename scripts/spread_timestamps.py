#!/usr/bin/env python3
"""
Timestamp Spreading Experiment

Spreads 60 test notes across 45 days (Sept 6 - Oct 21, 2025) with realistic
distribution to test how time_next edges behave with proper temporal spacing.

Usage:
    python scripts/spread_timestamps.py
"""

import sqlite3
import os
from datetime import datetime, timedelta
import random
from pathlib import Path

# Configuration
DB_PATH = os.path.expanduser("~/Notes/.index/notes.sqlite")
BASE_DATE = datetime(2025, 9, 6, 8, 0, 0)  # Sept 6, 2025, 8am PDT
TIMEZONE = "-07:00"

# Distribution: week_number -> note_count
# Mimics realistic note-taking pattern (busy weeks vs slow weeks)
DISTRIBUTION = {
    1: 15,  # Week 1 (Sept 6-12): Active project phase
    2: 8,   # Week 2 (Sept 13-19): Normal week
    3: 5,   # Week 3 (Sept 20-26): Slow week
    4: 10,  # Week 4 (Sept 27-Oct 3): Sprint/deadline week
    5: 7,   # Week 5 (Oct 4-10): Wind-down
    6: 8,   # Week 6 (Oct 11-17): New project start
    7: 7,   # Week 7 (Oct 18-21): Recent notes (partial week)
}

def generate_timestamps():
    """Generate 60 timestamps spread across 45 days with realistic distribution."""
    timestamps = []

    for week_num, note_count in DISTRIBUTION.items():
        # Calculate week start date
        week_start = BASE_DATE + timedelta(weeks=week_num - 1)

        # Determine week duration (Week 7 is partial: only 4 days)
        week_duration_days = 4 if week_num == 7 else 7

        for i in range(note_count):
            # Random day within the week
            day_offset = random.uniform(0, week_duration_days)

            # Random time of day (8am - 10pm, 14 hour window)
            hour_offset = random.uniform(0, 14)

            # Combine to get random timestamp
            total_offset = timedelta(days=day_offset, hours=hour_offset)
            timestamp = week_start + total_offset

            timestamps.append(timestamp)

    # Sort chronologically
    timestamps.sort()

    return timestamps


def update_database(timestamps):
    """Update graph_nodes.created with new timestamps."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Get all node IDs in current order (oldest to newest)
        cursor.execute("SELECT id FROM graph_nodes ORDER BY created")
        node_ids = [row[0] for row in cursor.fetchall()]

        if len(node_ids) != len(timestamps):
            raise ValueError(f"Mismatch: {len(node_ids)} nodes but {len(timestamps)} timestamps")

        print(f"Updating {len(node_ids)} nodes with new timestamps...")
        print(f"Date range: {timestamps[0].date()} to {timestamps[-1].date()}")
        print()

        # Update each node
        update_count = 0
        for node_id, timestamp in zip(node_ids, timestamps):
            # Format timestamp as ISO8601 with timezone
            timestamp_str = timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f") + TIMEZONE

            cursor.execute(
                "UPDATE graph_nodes SET created = ? WHERE id = ?",
                (timestamp_str, node_id)
            )
            update_count += 1

            if update_count % 10 == 0:
                print(f"  Updated {update_count}/{len(node_ids)} nodes...")

        conn.commit()
        print(f"\n✓ Successfully updated {update_count} node timestamps")

        # Show distribution summary
        print("\nTimestamp Distribution Summary:")
        for week_num, note_count in DISTRIBUTION.items():
            week_start = BASE_DATE + timedelta(weeks=week_num - 1)
            week_end = week_start + timedelta(days=6 if week_num != 7 else 3)
            print(f"  Week {week_num} ({week_start.date()} to {week_end.date()}): {note_count} notes")

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error: {e}")
        print("Database rolled back - no changes made")
        raise
    finally:
        conn.close()


def main():
    """Main execution."""
    print("=" * 60)
    print("Timestamp Spreading Experiment")
    print("=" * 60)
    print()

    # Check database exists
    if not os.path.exists(DB_PATH):
        print(f"✗ Database not found: {DB_PATH}")
        return

    # Generate timestamps
    print("Generating realistic timestamp distribution...")
    timestamps = generate_timestamps()

    # Verify total
    expected_total = sum(DISTRIBUTION.values())
    if len(timestamps) != expected_total:
        print(f"✗ Error: Expected {expected_total} timestamps, got {len(timestamps)}")
        return

    print(f"✓ Generated {len(timestamps)} timestamps")
    print()

    # Update database
    update_database(timestamps)

    print()
    print("=" * 60)
    print("Experiment Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Refresh your browser to reload the graph view")
    print("2. Observe if the visual is still a tangled mess")
    print("3. Note that time_next edges are still based on OLD timestamps")
    print("   (we didn't regenerate edges - per Option C)")
    print()
    print("To rollback:")
    print(f"  cp ~/Notes/.index/notes.sqlite.backup_before_timestamp_experiment \\")
    print(f"     ~/Notes/.index/notes.sqlite")


if __name__ == "__main__":
    main()
