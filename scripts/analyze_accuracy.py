#!/usr/bin/env python3
"""
Analyze Classification Accuracy
================================

Compares expected dimensions (from test CSV) with actual LLM classifications
to calculate accuracy and identify patterns in errors.
"""
import csv
import sqlite3
from pathlib import Path
from collections import defaultdict

# Paths
TEST_CSV = Path(__file__).parent.parent / "test_data" / "test_notes.csv"
NOTES_DIR = Path.home() / "Notes"
DB_PATH = NOTES_DIR / ".index" / "notes.sqlite"


def parse_expected_dimensions(dim_string):
    """Parse expected dimensions from CSV"""
    if not dim_string or dim_string == "":
        return set()

    # Map CSV format to database column names
    mapping = {
        "has_action_items": "has_action_items",
        "is_social": "is_social",
        "is_emotional": "is_emotional",
        "is_knowledge": "is_knowledge",
        "is_exploratory": "is_exploratory"
    }

    dims = set()
    for part in dim_string.split(','):
        part = part.strip()
        if part in mapping:
            dims.add(mapping[part])

    return dims


def get_actual_dimensions(note_path):
    """Get actual dimensions from database by note path"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        SELECT has_action_items, is_social, is_emotional, is_knowledge, is_exploratory
        FROM notes_meta
        WHERE path = ?
    """, (note_path,))

    row = cur.fetchone()
    con.close()

    if not row:
        return None

    dims = set()
    if row[0]: dims.add("has_action_items")
    if row[1]: dims.add("is_social")
    if row[2]: dims.add("is_emotional")
    if row[3]: dims.add("is_knowledge")
    if row[4]: dims.add("is_exploratory")

    return dims


def calculate_accuracy():
    """Calculate classification accuracy"""

    print("="*80)
    print("  CLASSIFICATION ACCURACY ANALYSIS")
    print("="*80)
    print()

    # Read test CSV
    with open(TEST_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        test_cases = list(reader)

    print(f"📊 Analyzing {len(test_cases)} test cases...\n")

    # Get all note paths from database
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT path FROM notes_meta ORDER BY created")
    note_paths = [row[0] for row in cur.fetchall()]
    con.close()

    if len(note_paths) != len(test_cases):
        print(f"⚠️  Warning: Found {len(note_paths)} notes but expected {len(test_cases)}")
        print()

    # Compare each test case
    results = []
    dimension_stats = defaultdict(lambda: {"tp": 0, "fp": 0, "tn": 0, "fn": 0})

    for i, (test_case, note_path) in enumerate(zip(test_cases, note_paths), 1):
        expected = parse_expected_dimensions(test_case['expected_dimensions'])
        actual = get_actual_dimensions(note_path)

        if actual is None:
            print(f"❌ Could not find note {i} in database")
            continue

        # Calculate per-note accuracy
        if expected == actual:
            match = "✅ PERFECT"
            correct = True
        else:
            missing = expected - actual
            extra = actual - expected
            match_parts = []
            if missing:
                match_parts.append(f"Missing: {', '.join(missing)}")
            if extra:
                match_parts.append(f"Extra: {', '.join(extra)}")
            match = "❌ " + " | ".join(match_parts)
            correct = False

        results.append({
            "test_case": i,
            "text": test_case['note_text'][:60] + "...",
            "expected": expected,
            "actual": actual,
            "correct": correct,
            "match": match
        })

        # Update per-dimension stats
        all_dims = {"has_action_items", "is_social", "is_emotional", "is_knowledge", "is_exploratory"}
        for dim in all_dims:
            if dim in expected and dim in actual:
                dimension_stats[dim]["tp"] += 1  # True Positive
            elif dim not in expected and dim in actual:
                dimension_stats[dim]["fp"] += 1  # False Positive
            elif dim in expected and dim not in actual:
                dimension_stats[dim]["fn"] += 1  # False Negative
            elif dim not in expected and dim not in actual:
                dimension_stats[dim]["tn"] += 1  # True Negative

    # Calculate overall accuracy
    perfect_matches = sum(1 for r in results if r["correct"])
    overall_accuracy = (perfect_matches / len(results) * 100) if results else 0

    print(f"📈 Overall Accuracy: {perfect_matches}/{len(results)} ({overall_accuracy:.1f}%)")
    print()

    # Per-dimension accuracy
    print("📊 Per-Dimension Performance:")
    print("-" * 80)
    print(f"{'Dimension':<20} {'Precision':>10} {'Recall':>10} {'F1-Score':>10}")
    print("-" * 80)

    for dim in ["has_action_items", "is_social", "is_emotional", "is_knowledge", "is_exploratory"]:
        stats = dimension_stats[dim]
        tp, fp, fn, tn = stats["tp"], stats["fp"], stats["fn"], stats["tn"]

        # Precision = TP / (TP + FP)
        precision = (tp / (tp + fp) * 100) if (tp + fp) > 0 else 0

        # Recall = TP / (TP + FN)
        recall = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0

        # F1 = 2 * (Precision * Recall) / (Precision + Recall)
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0

        dim_name = dim.replace("has_", "").replace("is_", "")
        print(f"{dim_name:<20} {precision:>9.1f}% {recall:>9.1f}% {f1:>9.1f}%")

    print()

    # Show failures
    failures = [r for r in results if not r["correct"]]
    if failures:
        print(f"❌ Failures ({len(failures)}/{len(results)}):")
        print("-" * 80)
        for r in failures:
            print(f"\n{r['test_case']}. {r['text']}")
            print(f"   Expected: {', '.join(sorted(r['expected'])) if r['expected'] else 'none'}")
            print(f"   Actual:   {', '.join(sorted(r['actual'])) if r['actual'] else 'none'}")
            print(f"   {r['match']}")
    else:
        print("✅ Perfect! All test cases classified correctly!")

    print()

    # Error patterns
    print("🔍 Common Error Patterns:")
    print("-" * 80)

    # Most commonly missed dimensions
    missed_dims = defaultdict(int)
    extra_dims = defaultdict(int)

    for r in failures:
        for dim in r['expected'] - r['actual']:
            missed_dims[dim] += 1
        for dim in r['actual'] - r['expected']:
            extra_dims[dim] += 1

    if missed_dims:
        print("\nMost commonly MISSED dimensions:")
        for dim, count in sorted(missed_dims.items(), key=lambda x: x[1], reverse=True):
            print(f"  {dim.replace('has_', '').replace('is_', ''):<20} {count} times")

    if extra_dims:
        print("\nMost commonly EXTRA dimensions (false positives):")
        for dim, count in sorted(extra_dims.items(), key=lambda x: x[1], reverse=True):
            print(f"  {dim.replace('has_', '').replace('is_', ''):<20} {count} times")

    if not missed_dims and not extra_dims:
        print("  None - perfect classification!")

    print()
    print("="*80)
    print("  Analysis Complete!")
    print("="*80)
    print()

    # Recommendations
    print("💡 Recommendations:")
    print("-" * 80)

    if overall_accuracy >= 90:
        print("✅ Excellent! LLM classification is highly accurate (≥90%)")
        print("   → Keep current LLM-based approach")
        print("   → No need for traditional NLP")
    elif overall_accuracy >= 75:
        print("⚠️  Good but could improve (75-90%)")
        print("   → Consider these optimizations:")
        if missed_dims.get("has_action_items", 0) > 2:
            print("      • Action items detection could improve")
            print("        Try: Adding keyword matching for 'TODO', 'call', 'buy', 'fix'")
        if extra_dims.get("is_knowledge", 0) > 2:
            print("      • Too many false positives for knowledge")
            print("        Try: Stricter prompt or post-processing filter")
        print("   → Still usable, minor tweaks needed")
    else:
        print("❌ Below target accuracy (<75%)")
        print("   → Consider hybrid approach:")
        print("      1. Use spaCy NER for entity extraction (people)")
        print("      2. Use dateparser for time references")
        print("      3. Use KeyBERT for tag generation")
        print("      4. Keep LLM for dimension classification")

    return overall_accuracy, dimension_stats, results


if __name__ == "__main__":
    if not TEST_CSV.exists():
        print(f"❌ Test CSV not found: {TEST_CSV}")
        exit(1)

    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("   Run import_test_notes.py first!")
        exit(1)

    calculate_accuracy()
