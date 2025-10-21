#!/usr/bin/env python3
"""
Analyze LLM Audit Logs
======================

Query the llm_operations table to understand LLM performance,
costs, and decision quality.
"""
import sqlite3
import json
from pathlib import Path
from collections import Counter

# Database path
NOTES_DIR = Path.home() / "Notes"
DB_PATH = NOTES_DIR / ".index" / "notes.sqlite"


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def analyze_operation_overview(con):
    """Overview of all LLM operations"""
    print_section("LLM OPERATIONS OVERVIEW")

    cur = con.cursor()

    cur.execute("""
        SELECT
            operation_type,
            COUNT(*) as total,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
            SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
            AVG(duration_ms) as avg_duration,
            MAX(duration_ms) as max_duration,
            SUM(tokens_input) as total_input,
            SUM(tokens_output) as total_output,
            SUM(cost_usd) as total_cost
        FROM llm_operations
        GROUP BY operation_type
        ORDER BY total DESC
    """)

    print(f"{'Operation':<20} {'Count':>6} {'Success':>7} {'Avg ms':>8} {'Max ms':>8} {'Tokens In':>10} {'Tokens Out':>11} {'Cost $':>10}")
    print("-" * 95)

    total_cost = 0
    for row in cur.fetchall():
        op_type, total, success, failed, avg_dur, max_dur, tok_in, tok_out, cost = row
        total_cost += cost or 0
        print(f"{op_type:<20} {total:>6} {success:>7} {avg_dur:>8.0f} {max_dur:>8.0f} {tok_in or 0:>10} {tok_out or 0:>11} ${cost or 0:>9.4f}")

    print("-" * 95)
    print(f"{'TOTAL':<20} {'':<14} {'':<15} {'':<17} {'':<22} ${total_cost:>9.4f}")


def analyze_classification_patterns(con):
    """Analyze classification decision patterns"""
    print_section("CLASSIFICATION PATTERNS")

    cur = con.cursor()

    cur.execute("""
        SELECT parsed_output
        FROM llm_operations
        WHERE operation_type = 'classification' AND success = 1
    """)

    dimension_counts = Counter()
    total_notes = 0

    for (parsed_json,) in cur.fetchall():
        if not parsed_json:
            continue

        try:
            result = json.loads(parsed_json)
            dims = result.get('dimensions', {})

            # Count each dimension
            for dim, value in dims.items():
                if value:
                    dimension_counts[dim] += 1

            total_notes += 1
        except json.JSONDecodeError:
            continue

    if total_notes == 0:
        print("  No classification data found yet.")
        return

    print(f"Total notes classified: {total_notes}\n")
    print(f"{'Dimension':<20} {'Count':>6} {'%':>6}")
    print("-" * 35)

    for dim, count in dimension_counts.most_common():
        pct = (count / total_notes * 100) if total_notes > 0 else 0
        print(f"{dim:<20} {count:>6} {pct:>5.1f}%")


def analyze_entity_extraction(con):
    """Analyze entity extraction patterns from enrichment"""
    print_section("ENTITY EXTRACTION QUALITY")

    cur = con.cursor()

    cur.execute("""
        SELECT parsed_output
        FROM llm_operations
        WHERE operation_type = 'enrichment' AND success = 1
    """)

    entity_counts = Counter()
    people_extracted = 0
    emotions_extracted = 0
    time_refs_extracted = 0
    total_enrichments = 0

    for (parsed_json,) in cur.fetchall():
        if not parsed_json:
            continue

        try:
            result = json.loads(parsed_json)

            # Count entities
            entities = result.get('entities', [])
            for entity in entities:
                entity_counts[entity] += 1

            # Count people
            people = result.get('people', [])
            if people:
                people_extracted += 1

            # Count emotions
            emotions = result.get('emotions', [])
            if emotions:
                emotions_extracted += 1

            # Count time references
            time_refs = result.get('time_references', [])
            if time_refs:
                time_refs_extracted += 1

            total_enrichments += 1
        except json.JSONDecodeError:
            continue

    if total_enrichments == 0:
        print("  No enrichment data found yet.")
        return

    print(f"Total enrichments: {total_enrichments}\n")

    print(f"Extraction success rates:")
    print(f"  People:          {people_extracted}/{total_enrichments} ({people_extracted/total_enrichments*100:.1f}%)")
    print(f"  Emotions:        {emotions_extracted}/{total_enrichments} ({emotions_extracted/total_enrichments*100:.1f}%)")
    print(f"  Time references: {time_refs_extracted}/{total_enrichments} ({time_refs_extracted/total_enrichments*100:.1f}%)")

    print(f"\nMost common entities:")
    for entity, count in entity_counts.most_common(10):
        print(f"  {entity:<40} {count:>3} notes")


def analyze_cost_breakdown(con):
    """Detailed cost analysis"""
    print_section("COST ANALYSIS")

    cur = con.cursor()

    # Cost by operation type
    cur.execute("""
        SELECT
            operation_type,
            COUNT(*) as count,
            AVG(cost_usd) as avg_cost,
            SUM(cost_usd) as total_cost
        FROM llm_operations
        WHERE cost_usd IS NOT NULL
        GROUP BY operation_type
    """)

    print(f"{'Operation':<20} {'Count':>6} {'Avg Cost':>12} {'Total Cost':>12}")
    print("-" * 55)

    for op_type, count, avg_cost, total_cost in cur.fetchall():
        print(f"{op_type:<20} {count:>6} ${avg_cost:>11.6f} ${total_cost:>11.4f}")

    # Projected costs
    print(f"\nProjected costs:")

    cur.execute("SELECT AVG(cost_usd) FROM llm_operations WHERE cost_usd IS NOT NULL")
    avg_cost_per_op = cur.fetchone()[0] or 0

    # Assume 2 operations per note (classification + enrichment)
    cost_per_note = avg_cost_per_op * 2

    print(f"  Per note (classification + enrichment): ${cost_per_note:.4f}")
    print(f"  100 notes:  ${cost_per_note * 100:.2f}")
    print(f"  1000 notes: ${cost_per_note * 1000:.2f}")


def analyze_performance(con):
    """Performance analysis"""
    print_section("PERFORMANCE METRICS")

    cur = con.cursor()

    cur.execute("""
        SELECT
            operation_type,
            MIN(duration_ms) as min_dur,
            AVG(duration_ms) as avg_dur,
            MAX(duration_ms) as max_dur,
            COUNT(*) as count
        FROM llm_operations
        WHERE success = 1
        GROUP BY operation_type
    """)

    print(f"{'Operation':<20} {'Min (ms)':>9} {'Avg (ms)':>9} {'Max (ms)':>9} {'Count':>6}")
    print("-" * 60)

    for op_type, min_dur, avg_dur, max_dur, count in cur.fetchall():
        print(f"{op_type:<20} {min_dur:>9.0f} {avg_dur:>9.0f} {max_dur:>9.0f} {count:>6}")


def show_sample_decisions(con):
    """Show a few sample LLM decisions for manual review"""
    print_section("SAMPLE LLM DECISIONS (Manual Review)")

    cur = con.cursor()

    cur.execute("""
        SELECT
            o.operation_type,
            m.path,
            o.parsed_output
        FROM llm_operations o
        LEFT JOIN notes_meta m ON m.id = o.note_id
        WHERE o.operation_type = 'classification'
          AND o.success = 1
        LIMIT 3
    """)

    for i, (op_type, path, parsed_json) in enumerate(cur.fetchall(), 1):
        if not parsed_json:
            continue

        try:
            result = json.loads(parsed_json)
            filename = Path(path).stem if path else "Unknown"

            print(f"{i}. {filename}")
            print(f"   Title: {result.get('title', 'N/A')}")

            dims = result.get('dimensions', {})
            detected = [k.replace('is_', '').replace('has_', '') for k, v in dims.items() if v]
            print(f"   Dimensions: {', '.join(detected) if detected else 'none'}")

            if result.get('reasoning'):
                print(f"   Reasoning: {result['reasoning'][:100]}...")

            print()
        except json.JSONDecodeError:
            continue


def main():
    """Run all audit analyses"""
    if not DB_PATH.exists():
        print(f"❌ Database not found at: {DB_PATH}")
        print(f"   Run import_test_notes.py first!")
        return

    con = sqlite3.connect(DB_PATH)

    try:
        # Check if any operations exist
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM llm_operations")
        count = cur.fetchone()[0]

        if count == 0:
            print("❌ No LLM operations found yet!")
            print("\nNext steps:")
            print("1. Make sure backend is running: python api/main.py")
            print("2. Import test notes: python scripts/import_test_notes.py")
            return

        analyze_operation_overview(con)
        analyze_classification_patterns(con)
        analyze_entity_extraction(con)
        analyze_cost_breakdown(con)
        analyze_performance(con)
        show_sample_decisions(con)

        print("\n" + "="*80)
        print("  Analysis Complete!")
        print("="*80)
        print("\nNext steps:")
        print("1. Review the metrics above")
        print("2. Check specific decisions: sqlite3 ~/Notes/.index/notes.sqlite")
        print("3. Decide: Keep LLM-only, or add traditional NLP?")

    finally:
        con.close()


if __name__ == "__main__":
    main()
