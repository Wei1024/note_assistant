#!/usr/bin/env python3
"""
Analyze LLM Decisions from Existing Database
============================================

This script extracts all available LLM decision data from the current database
to help determine what's missing for debugging and optimization.

Queries:
1. Classification decisions (dimension patterns)
2. Entity extraction patterns (what gets extracted most)
3. Link creation patterns (consolidation effectiveness)
4. Review flags (when LLM is uncertain)
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict

# Database path
NOTES_DIR = Path.home() / "Notes"
DB_PATH = NOTES_DIR / ".index" / "notes.sqlite"


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def analyze_classification_decisions(con):
    """Analyze how notes are being classified into dimensions"""
    print_section("1. CLASSIFICATION DECISIONS")

    cur = con.cursor()

    # Get total notes
    cur.execute("SELECT COUNT(*) FROM notes_meta")
    total_notes = cur.fetchone()[0]
    print(f"📊 Total Notes: {total_notes}\n")

    # Dimension distribution
    print("🏷️  Dimension Distribution:")
    print("-" * 80)

    cur.execute("""
        SELECT
            SUM(has_action_items) as action_items,
            SUM(is_social) as social,
            SUM(is_emotional) as emotional,
            SUM(is_knowledge) as knowledge,
            SUM(is_exploratory) as exploratory
        FROM notes_meta
    """)

    row = cur.fetchone()
    dimensions = [
        ("has_action_items", row[0]),
        ("is_social", row[1]),
        ("is_emotional", row[2]),
        ("is_knowledge", row[3]),
        ("is_exploratory", row[4])
    ]

    for dim_name, count in dimensions:
        pct = (count / total_notes * 100) if total_notes > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {dim_name:20} {count:4} ({pct:5.1f}%) {bar}")

    # Multi-dimensional notes
    print(f"\n📐 Multi-Dimensional Analysis:")
    print("-" * 80)

    cur.execute("""
        SELECT
            (has_action_items + is_social + is_emotional + is_knowledge + is_exploratory) as dim_count,
            COUNT(*) as note_count
        FROM notes_meta
        GROUP BY dim_count
        ORDER BY dim_count
    """)

    for dim_count, note_count in cur.fetchall():
        pct = (note_count / total_notes * 100) if total_notes > 0 else 0
        print(f"  {dim_count} dimensions: {note_count:4} notes ({pct:5.1f}%)")

    # Common dimension combinations
    print(f"\n🔀 Most Common Dimension Combinations:")
    print("-" * 80)

    cur.execute("""
        SELECT
            has_action_items, is_social, is_emotional, is_knowledge, is_exploratory,
            COUNT(*) as count
        FROM notes_meta
        GROUP BY has_action_items, is_social, is_emotional, is_knowledge, is_exploratory
        ORDER BY count DESC
        LIMIT 10
    """)

    for row in cur.fetchall():
        dims = []
        if row[0]: dims.append("action")
        if row[1]: dims.append("social")
        if row[2]: dims.append("emotional")
        if row[3]: dims.append("knowledge")
        if row[4]: dims.append("exploratory")

        dim_str = ", ".join(dims) if dims else "none"
        print(f"  [{dim_str:40}] {row[5]:4} notes")

    # Review flags (uncertainty indicators)
    print(f"\n⚠️  Review Flags (LLM Uncertainty):")
    print("-" * 80)

    cur.execute("""
        SELECT
            COUNT(*) as total_needs_review,
            COUNT(DISTINCT review_reason) as unique_reasons
        FROM notes_meta
        WHERE needs_review = 1
    """)

    total_review, unique_reasons = cur.fetchone()
    print(f"  Notes needing review: {total_review} ({(total_review/total_notes*100):.1f}%)")
    print(f"  Unique review reasons: {unique_reasons}")

    if total_review > 0:
        print(f"\n  Top review reasons:")
        cur.execute("""
            SELECT review_reason, COUNT(*) as count
            FROM notes_meta
            WHERE needs_review = 1 AND review_reason IS NOT NULL
            GROUP BY review_reason
            ORDER BY count DESC
            LIMIT 5
        """)

        for reason, count in cur.fetchall():
            print(f"    - {reason}: {count} notes")


def analyze_entity_extraction(con):
    """Analyze what entities are being extracted"""
    print_section("2. ENTITY EXTRACTION PATTERNS")

    cur = con.cursor()

    # Total entities
    cur.execute("SELECT COUNT(*) FROM notes_entities")
    total_entities = cur.fetchone()[0]
    print(f"📊 Total Entities Extracted: {total_entities}\n")

    # Entity type distribution
    print("🏷️  Entity Types:")
    print("-" * 80)

    cur.execute("""
        SELECT entity_type, COUNT(*) as count
        FROM notes_entities
        GROUP BY entity_type
        ORDER BY count DESC
    """)

    for entity_type, count in cur.fetchall():
        pct = (count / total_entities * 100) if total_entities > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {entity_type:15} {count:5} ({pct:5.1f}%) {bar}")

    # Most common people
    print(f"\n👥 Most Mentioned People:")
    print("-" * 80)

    cur.execute("""
        SELECT entity_value, COUNT(*) as count
        FROM notes_entities
        WHERE entity_type = 'person'
        GROUP BY entity_value
        ORDER BY count DESC
        LIMIT 10
    """)

    people = cur.fetchall()
    if people:
        for person, count in people:
            print(f"  {person:30} {count:3} notes")
    else:
        print("  (No people extracted yet)")

    # Most common entities (topics/projects/tech)
    print(f"\n🔖 Most Common Entities (Topics/Projects):")
    print("-" * 80)

    cur.execute("""
        SELECT entity_value, COUNT(*) as count
        FROM notes_entities
        WHERE entity_type = 'entity'
        GROUP BY entity_value
        ORDER BY count DESC
        LIMIT 15
    """)

    entities = cur.fetchall()
    if entities:
        for entity, count in entities:
            print(f"  {entity:40} {count:3} notes")
    else:
        print("  (No entities extracted yet)")

    # Confidence scores (if populated)
    print(f"\n🎯 Extraction Confidence (if available):")
    print("-" * 80)

    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(extraction_confidence) as with_confidence,
            AVG(extraction_confidence) as avg_confidence,
            MIN(extraction_confidence) as min_confidence,
            MAX(extraction_confidence) as max_confidence
        FROM notes_entities
    """)

    total, with_conf, avg_conf, min_conf, max_conf = cur.fetchone()

    if with_conf > 0:
        print(f"  Entities with confidence scores: {with_conf}/{total}")
        print(f"  Average confidence: {avg_conf:.2f}")
        print(f"  Min/Max confidence: {min_conf:.2f} / {max_conf:.2f}")
    else:
        print(f"  ⚠️  No confidence scores found (extraction_confidence is NULL)")
        print(f"  💡 This means we're not tracking LLM uncertainty on extractions!")


def analyze_dimensions_metadata(con):
    """Analyze dimension metadata (emotions, time references)"""
    print_section("3. DIMENSION METADATA (Emotions, Time References)")

    cur = con.cursor()

    # Total dimensions
    cur.execute("SELECT COUNT(*) FROM notes_dimensions")
    total_dims = cur.fetchone()[0]
    print(f"📊 Total Dimension Records: {total_dims}\n")

    # Dimension type breakdown
    print("🏷️  Dimension Types:")
    print("-" * 80)

    cur.execute("""
        SELECT dimension_type, COUNT(*) as count
        FROM notes_dimensions
        GROUP BY dimension_type
        ORDER BY count DESC
    """)

    for dim_type, count in cur.fetchall():
        pct = (count / total_dims * 100) if total_dims > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {dim_type:20} {count:5} ({pct:5.1f}%) {bar}")

    # Most common emotions
    print(f"\n😊 Most Common Emotions:")
    print("-" * 80)

    cur.execute("""
        SELECT dimension_value, COUNT(*) as count
        FROM notes_dimensions
        WHERE dimension_type = 'emotion'
        GROUP BY dimension_value
        ORDER BY count DESC
        LIMIT 10
    """)

    emotions = cur.fetchall()
    if emotions:
        for emotion, count in emotions:
            print(f"  {emotion:30} {count:3} notes")
    else:
        print("  (No emotions extracted yet)")

    # Time references
    print(f"\n📅 Time Reference Patterns:")
    print("-" * 80)

    cur.execute("""
        SELECT COUNT(*) as count
        FROM notes_dimensions
        WHERE dimension_type = 'time_reference'
    """)

    time_refs = cur.fetchone()[0]
    print(f"  Notes with time references: {time_refs}")

    if time_refs > 0:
        cur.execute("""
            SELECT dimension_value
            FROM notes_dimensions
            WHERE dimension_type = 'time_reference'
            ORDER BY created DESC
            LIMIT 5
        """)

        print(f"\n  Recent time references:")
        for (time_ref,) in cur.fetchall():
            print(f"    - {time_ref}")


def analyze_consolidation_links(con):
    """Analyze link creation patterns from consolidation"""
    print_section("4. CONSOLIDATION & LINK PATTERNS")

    cur = con.cursor()

    # Total links
    cur.execute("SELECT COUNT(*) FROM notes_links")
    total_links = cur.fetchone()[0]
    print(f"📊 Total Links Created: {total_links}\n")

    if total_links == 0:
        print("  ⚠️  No links found. Consolidation hasn't run yet or found no connections.\n")
        return

    # Link type distribution
    print("🔗 Link Type Distribution:")
    print("-" * 80)

    cur.execute("""
        SELECT link_type, COUNT(*) as count
        FROM notes_links
        GROUP BY link_type
        ORDER BY count DESC
    """)

    for link_type, count in cur.fetchall():
        pct = (count / total_links * 100) if total_links > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {link_type:15} {count:5} ({pct:5.1f}%) {bar}")

    # Most linked notes
    print(f"\n🌟 Most Connected Notes (Hubs):")
    print("-" * 80)

    cur.execute("""
        SELECT
            n.id,
            n.path,
            COUNT(*) as link_count
        FROM (
            SELECT from_note_id as note_id FROM notes_links
            UNION ALL
            SELECT to_note_id as note_id FROM notes_links
        ) l
        JOIN notes_meta n ON n.id = l.note_id
        GROUP BY n.id
        ORDER BY link_count DESC
        LIMIT 10
    """)

    for note_id, path, link_count in cur.fetchall():
        # Extract title from path
        title = Path(path).stem
        print(f"  {link_count:3} links - {title[:60]}")

    # Consolidation timestamps
    print(f"\n⏱️  Consolidation Activity:")
    print("-" * 80)

    cur.execute("""
        SELECT COUNT(*) as consolidated_count
        FROM notes_meta
        WHERE consolidated_at IS NOT NULL
    """)

    consolidated_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM notes_meta")
    total_notes = cur.fetchone()[0]

    pct = (consolidated_count / total_notes * 100) if total_notes > 0 else 0
    print(f"  Notes consolidated: {consolidated_count}/{total_notes} ({pct:.1f}%)")

    if consolidated_count > 0:
        cur.execute("""
            SELECT
                DATE(consolidated_at) as date,
                COUNT(*) as count
            FROM notes_meta
            WHERE consolidated_at IS NOT NULL
            GROUP BY date
            ORDER BY date DESC
            LIMIT 7
        """)

        print(f"\n  Recent consolidation activity:")
        for date, count in cur.fetchall():
            print(f"    {date}: {count} notes consolidated")


def analyze_data_gaps(con):
    """Identify what data is missing for debugging"""
    print_section("5. DATA GAPS FOR DEBUGGING")

    print("❌ What We're Missing:")
    print("-" * 80)

    gaps = [
        ("LLM Raw Responses", "Can't see what LLM actually returned (JSON)"),
        ("LLM Reasoning Text", "Can't see WHY LLM made decisions"),
        ("Token Usage", "Can't measure cost per operation"),
        ("Latency Metrics", "Can't measure LLM call duration"),
        ("Prompt Versions", "Can't track if prompt changes affect quality"),
        ("Rejected Entities", "Can't see what entities were extracted but filtered"),
        ("Rejected Links", "Can't see which link suggestions were rejected during consolidation"),
        ("Confidence Scores", "extraction_confidence column exists but is NULL"),
    ]

    for gap_name, gap_desc in gaps:
        print(f"  • {gap_name:25} - {gap_desc}")

    print(f"\n✅ What We Have:")
    print("-" * 80)

    have = [
        ("Final Classifications", "Boolean dimensions in notes_meta"),
        ("Extracted Entities", "People, entities in notes_entities"),
        ("Extracted Dimensions", "Emotions, time_refs in notes_dimensions"),
        ("Created Links", "Link type and timestamp in notes_links"),
        ("Review Flags", "needs_review, review_reason in notes_meta"),
        ("Consolidation Timestamps", "consolidated_at in notes_meta"),
    ]

    for have_name, have_desc in have:
        print(f"  • {have_name:25} - {have_desc}")

    print(f"\n💡 Recommendations:")
    print("-" * 80)
    print("  1. Start populating extraction_confidence from LLM responses")
    print("  2. Consider adding llm_operations audit table for:")
    print("     - Raw LLM responses (debugging)")
    print("     - Token usage (cost tracking)")
    print("     - Latency (performance optimization)")
    print("     - Rejected candidates (understanding filtering)")


def main():
    """Run all analyses"""
    if not DB_PATH.exists():
        print(f"❌ Database not found at: {DB_PATH}")
        print(f"   Make sure you've created some notes first!")
        return

    con = sqlite3.connect(DB_PATH)

    try:
        analyze_classification_decisions(con)
        analyze_entity_extraction(con)
        analyze_dimensions_metadata(con)
        analyze_consolidation_links(con)
        analyze_data_gaps(con)

        print("\n" + "="*80)
        print("  Analysis Complete!")
        print("="*80 + "\n")

    finally:
        con.close()


if __name__ == "__main__":
    main()
