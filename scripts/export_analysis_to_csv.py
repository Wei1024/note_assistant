#!/usr/bin/env python3
"""
Export LLM Analysis to CSV
===========================

Exports analysis results to CSV files for easy viewing in spreadsheet apps.
"""
import sqlite3
import csv
import json
from pathlib import Path
from datetime import datetime

# Database path
NOTES_DIR = Path.home() / "Notes"
DB_PATH = NOTES_DIR / ".index" / "notes.sqlite"

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "analysis_output"
OUTPUT_DIR.mkdir(exist_ok=True)


def export_llm_operations():
    """Export all LLM operations to CSV"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        SELECT
            id,
            note_id,
            operation_type,
            created,
            model,
            duration_ms,
            tokens_input,
            tokens_output,
            cost_usd,
            success,
            error
        FROM llm_operations
        ORDER BY created
    """)

    output_file = OUTPUT_DIR / "llm_operations.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'operation_id', 'note_id', 'operation_type', 'created',
            'model', 'duration_ms', 'tokens_input', 'tokens_output',
            'cost_usd', 'success', 'error'
        ])

        for row in cur.fetchall():
            writer.writerow(row)

    con.close()
    print(f"✓ Exported LLM operations to: {output_file}")


def export_classification_results():
    """Export classification results with expected vs actual dimensions"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        SELECT
            m.id,
            m.path,
            m.created,
            m.has_action_items,
            m.is_social,
            m.is_emotional,
            m.is_knowledge,
            m.is_exploratory,
            o.parsed_output
        FROM notes_meta m
        LEFT JOIN llm_operations o ON o.note_id = m.id AND o.operation_type = 'classification'
        ORDER BY m.created
    """)

    output_file = OUTPUT_DIR / "classification_results.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'note_id', 'filename', 'created',
            'has_action_items', 'is_social', 'is_emotional', 'is_knowledge', 'is_exploratory',
            'title', 'tags', 'reasoning'
        ])

        for row in cur.fetchall():
            note_id, path, created = row[0], row[1], row[2]
            has_action, is_social, is_emotional, is_knowledge, is_exploratory = row[3:8]
            parsed_json = row[8]

            filename = Path(path).stem if path else "Unknown"
            title = ""
            tags = ""
            reasoning = ""

            if parsed_json:
                try:
                    parsed = json.loads(parsed_json)
                    title = parsed.get('title', '')
                    tags = ', '.join(parsed.get('tags', []))
                    reasoning = parsed.get('reasoning', '')
                except json.JSONDecodeError:
                    pass

            writer.writerow([
                note_id, filename, created,
                has_action, is_social, is_emotional, is_knowledge, is_exploratory,
                title, tags, reasoning
            ])

    con.close()
    print(f"✓ Exported classification results to: {output_file}")


def export_entity_extractions():
    """Export all extracted entities"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        SELECT
            e.note_id,
            m.path,
            e.entity_type,
            e.entity_value,
            e.extraction_confidence,
            e.created
        FROM notes_entities e
        LEFT JOIN notes_meta m ON m.id = e.note_id
        ORDER BY e.created
    """)

    output_file = OUTPUT_DIR / "entity_extractions.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'note_id', 'filename', 'entity_type', 'entity_value',
            'confidence', 'created'
        ])

        for row in cur.fetchall():
            note_id, path, entity_type, entity_value, confidence, created = row
            filename = Path(path).stem if path else "Unknown"
            writer.writerow([
                note_id, filename, entity_type, entity_value,
                confidence, created
            ])

    con.close()
    print(f"✓ Exported entity extractions to: {output_file}")


def export_dimension_metadata():
    """Export dimension metadata (emotions, time references)"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        SELECT
            d.note_id,
            m.path,
            d.dimension_type,
            d.dimension_value,
            d.extraction_confidence,
            d.created
        FROM notes_dimensions d
        LEFT JOIN notes_meta m ON m.id = d.note_id
        ORDER BY d.created
    """)

    output_file = OUTPUT_DIR / "dimension_metadata.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'note_id', 'filename', 'dimension_type', 'dimension_value',
            'confidence', 'created'
        ])

        for row in cur.fetchall():
            note_id, path, dim_type, dim_value, confidence, created = row
            filename = Path(path).stem if path else "Unknown"
            writer.writerow([
                note_id, filename, dim_type, dim_value,
                confidence, created
            ])

    con.close()
    print(f"✓ Exported dimension metadata to: {output_file}")


def export_performance_summary():
    """Export performance summary statistics"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        SELECT
            operation_type,
            COUNT(*) as total,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
            AVG(duration_ms) as avg_duration,
            MIN(duration_ms) as min_duration,
            MAX(duration_ms) as max_duration,
            SUM(tokens_input) as total_input,
            SUM(tokens_output) as total_output,
            AVG(tokens_input) as avg_input,
            AVG(tokens_output) as avg_output,
            SUM(cost_usd) as total_cost,
            AVG(cost_usd) as avg_cost
        FROM llm_operations
        GROUP BY operation_type
    """)

    output_file = OUTPUT_DIR / "performance_summary.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'operation_type', 'total_operations', 'successful',
            'avg_duration_ms', 'min_duration_ms', 'max_duration_ms',
            'total_tokens_input', 'total_tokens_output',
            'avg_tokens_input', 'avg_tokens_output',
            'total_cost_usd', 'avg_cost_usd'
        ])

        for row in cur.fetchall():
            writer.writerow(row)

    con.close()
    print(f"✓ Exported performance summary to: {output_file}")


def main():
    """Export all analysis data to CSV"""
    if not DB_PATH.exists():
        print(f"❌ Database not found at: {DB_PATH}")
        print(f"   Import test notes first!")
        return

    print(f"📊 Exporting analysis data to CSV...\n")

    export_llm_operations()
    export_classification_results()
    export_entity_extractions()
    export_dimension_metadata()
    export_performance_summary()

    print(f"\n✅ All exports complete!")
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"\nFiles created:")
    print(f"  1. llm_operations.csv       - All LLM calls with tokens/costs")
    print(f"  2. classification_results.csv - Dimension classifications")
    print(f"  3. entity_extractions.csv   - Extracted entities/people")
    print(f"  4. dimension_metadata.csv   - Emotions/time references")
    print(f"  5. performance_summary.csv  - Aggregated statistics")
    print(f"\nOpen in Excel, Google Sheets, or any spreadsheet app!")


if __name__ == "__main__":
    main()
