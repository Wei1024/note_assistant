"""
Entity Extraction Comparison Test
Compares pure LLM vs hybrid NLP extraction on labeled test dataset
"""
import asyncio
import csv
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.entity_extraction import extract_entities_llm, extract_entities_hybrid


def load_labeled_data(csv_path: str):
    """Load labeled test dataset"""
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def parse_json_field(field_value: str):
    """Parse JSON string from CSV"""
    try:
        return json.loads(field_value)
    except:
        return []


def calculate_metrics(expected: list, actual: list) -> dict:
    """Calculate precision, recall, F1 for a single field.

    For WHO/WHAT/WHERE: simple list comparison
    For WHEN: compare by 'original' text (not parsed dates)
    """
    # Check if this is WHEN field (contains dicts)
    expected_has_dicts = isinstance(expected, list) and len(expected) > 0 and isinstance(expected[0], dict)
    actual_has_dicts = isinstance(actual, list) and len(actual) > 0 and isinstance(actual[0], dict)

    if expected_has_dicts or actual_has_dicts:
        # WHEN field - compare original text
        expected_set = set(item.get('original', '') if isinstance(item, dict) else str(item) for item in expected)
        actual_set = set(item.get('original', '') if isinstance(item, dict) else str(item) for item in actual)
    else:
        # WHO/WHAT/WHERE - direct comparison
        expected_set = set(expected)
        actual_set = set(actual)

    if len(expected_set) == 0 and len(actual_set) == 0:
        # Both empty - perfect match
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "tp": 0, "fp": 0, "fn": 0}

    if len(expected_set) == 0:
        # Expected nothing but got something - all false positives
        return {"precision": 0.0, "recall": 1.0, "f1": 0.0, "tp": 0, "fp": len(actual_set), "fn": 0}

    if len(actual_set) == 0:
        # Expected something but got nothing - all false negatives
        return {"precision": 1.0, "recall": 0.0, "f1": 0.0, "tp": 0, "fp": 0, "fn": len(expected_set)}

    # Calculate metrics
    true_positives = len(expected_set & actual_set)
    false_positives = len(actual_set - expected_set)
    false_negatives = len(expected_set - actual_set)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "tp": true_positives,
        "fp": false_positives,
        "fn": false_negatives
    }


async def run_comparison_test(labeled_csv_path: str, output_csv_path: str):
    """Run comparison test on all notes"""

    print("Loading labeled dataset...")
    test_data = load_labeled_data(labeled_csv_path)
    print(f"Loaded {len(test_data)} test notes\n")

    current_date = "2025-10-20 00:00 PST"  # Fixed date for consistent testing

    results = []

    for i, row in enumerate(test_data, 1):
        note_id = row['note_id']
        note_text = row['note_text']

        # Parse expected entities
        expected = {
            "who": parse_json_field(row['expected_who']),
            "what": parse_json_field(row['expected_what']),
            "when": parse_json_field(row['expected_when']),
            "where": parse_json_field(row['expected_where'])
        }

        print(f"[{i}/{len(test_data)}] Testing note {note_id}...")
        print(f"  Text: {note_text[:80]}...")

        # Run LLM extraction
        print("  Running LLM extraction...")
        llm_result = await extract_entities_llm(note_text, current_date)

        # Run hybrid extraction
        print("  Running hybrid extraction...")
        hybrid_result = extract_entities_hybrid(note_text, current_date)

        # Calculate metrics for each field
        llm_metrics = {
            "who": calculate_metrics(expected["who"], llm_result.get("who", [])),
            "what": calculate_metrics(expected["what"], llm_result.get("what", [])),
            "when": calculate_metrics(expected["when"], llm_result.get("when", [])),
            "where": calculate_metrics(expected["where"], llm_result.get("where", []))
        }

        hybrid_metrics = {
            "who": calculate_metrics(expected["who"], hybrid_result.get("who", [])),
            "what": calculate_metrics(expected["what"], hybrid_result.get("what", [])),
            "when": calculate_metrics(expected["when"], hybrid_result.get("when", [])),
            "where": calculate_metrics(expected["where"], hybrid_result.get("where", []))
        }

        # Determine winners
        def get_winner(field):
            llm_f1 = llm_metrics[field]["f1"]
            hybrid_f1 = hybrid_metrics[field]["f1"]
            if llm_f1 > hybrid_f1:
                return "llm"
            elif hybrid_f1 > llm_f1:
                return "hybrid"
            else:
                return "tie"

        winners = {
            "who": get_winner("who"),
            "what": get_winner("what"),
            "when": get_winner("when"),
            "where": get_winner("where")
        }

        # Compile result row
        result_row = {
            "note_id": note_id,
            "note_text": note_text,

            # Expected
            "expected_who": json.dumps(expected["who"]),
            "expected_what": json.dumps(expected["what"]),
            "expected_when": json.dumps(expected["when"]),
            "expected_where": json.dumps(expected["where"]),

            # LLM results
            "llm_who": json.dumps(llm_result.get("who", [])),
            "llm_what": json.dumps(llm_result.get("what", [])),
            "llm_when": json.dumps(llm_result.get("when", [])),
            "llm_where": json.dumps(llm_result.get("where", [])),
            "llm_time_ms": llm_result.get("execution_time_ms", 0),
            "llm_who_f1": llm_metrics["who"]["f1"],
            "llm_what_f1": llm_metrics["what"]["f1"],
            "llm_when_f1": llm_metrics["when"]["f1"],
            "llm_where_f1": llm_metrics["where"]["f1"],

            # Hybrid results
            "hybrid_who": json.dumps(hybrid_result.get("who", [])),
            "hybrid_what": json.dumps(hybrid_result.get("what", [])),
            "hybrid_when": json.dumps(hybrid_result.get("when", [])),
            "hybrid_where": json.dumps(hybrid_result.get("where", [])),
            "hybrid_time_ms": hybrid_result.get("execution_time_ms", 0),
            "hybrid_who_f1": hybrid_metrics["who"]["f1"],
            "hybrid_what_f1": hybrid_metrics["what"]["f1"],
            "hybrid_when_f1": hybrid_metrics["when"]["f1"],
            "hybrid_where_f1": hybrid_metrics["where"]["f1"],

            # Winners
            "who_winner": winners["who"],
            "what_winner": winners["what"],
            "when_winner": winners["when"],
            "where_winner": winners["where"],
        }

        results.append(result_row)

        print(f"  LLM: WHO={llm_metrics['who']['f1']:.2f} WHAT={llm_metrics['what']['f1']:.2f} "
              f"WHEN={llm_metrics['when']['f1']:.2f} WHERE={llm_metrics['where']['f1']:.2f} ({llm_result.get('execution_time_ms', 0)}ms)")
        print(f"  Hybrid: WHO={hybrid_metrics['who']['f1']:.2f} WHAT={hybrid_metrics['what']['f1']:.2f} "
              f"WHEN={hybrid_metrics['when']['f1']:.2f} WHERE={hybrid_metrics['where']['f1']:.2f} ({hybrid_result.get('execution_time_ms', 0)}ms)")
        print()

    # Write results to CSV
    print(f"Writing results to {output_csv_path}...")
    with open(output_csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            "note_id", "note_text",
            "expected_who", "expected_what", "expected_when", "expected_where",
            "llm_who", "llm_what", "llm_when", "llm_where", "llm_time_ms",
            "llm_who_f1", "llm_what_f1", "llm_when_f1", "llm_where_f1",
            "hybrid_who", "hybrid_what", "hybrid_when", "hybrid_where", "hybrid_time_ms",
            "hybrid_who_f1", "hybrid_what_f1", "hybrid_when_f1", "hybrid_where_f1",
            "who_winner", "what_winner", "when_winner", "where_winner"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Calculate overall statistics
    print("\n" + "="*80)
    print("OVERALL RESULTS")
    print("="*80)

    # Average F1 scores
    avg_llm_f1 = {
        "who": sum(r["llm_who_f1"] for r in results) / len(results),
        "what": sum(r["llm_what_f1"] for r in results) / len(results),
        "when": sum(r["llm_when_f1"] for r in results) / len(results),
        "where": sum(r["llm_where_f1"] for r in results) / len(results),
    }

    avg_hybrid_f1 = {
        "who": sum(r["hybrid_who_f1"] for r in results) / len(results),
        "what": sum(r["hybrid_what_f1"] for r in results) / len(results),
        "when": sum(r["hybrid_when_f1"] for r in results) / len(results),
        "where": sum(r["hybrid_where_f1"] for r in results) / len(results),
    }

    print("\nAverage F1 Scores:")
    print(f"{'Field':<10} {'LLM':<10} {'Hybrid':<10} {'Winner'}")
    print("-" * 40)
    for field in ["who", "what", "when", "where"]:
        llm_score = avg_llm_f1[field]
        hybrid_score = avg_hybrid_f1[field]
        winner = "LLM" if llm_score > hybrid_score else ("Hybrid" if hybrid_score > llm_score else "Tie")
        print(f"{field.upper():<10} {llm_score:.3f}      {hybrid_score:.3f}      {winner}")

    # Average execution time
    avg_llm_time = sum(r["llm_time_ms"] for r in results) / len(results)
    avg_hybrid_time = sum(r["hybrid_time_ms"] for r in results) / len(results)

    print(f"\nAverage Execution Time:")
    print(f"  LLM:    {avg_llm_time:.0f}ms")
    print(f"  Hybrid: {avg_hybrid_time:.0f}ms")
    print(f"  Speedup: {avg_llm_time / avg_hybrid_time:.1f}x {'faster' if avg_hybrid_time < avg_llm_time else 'slower'}")

    # Winner counts
    who_wins = {"llm": 0, "hybrid": 0, "tie": 0}
    what_wins = {"llm": 0, "hybrid": 0, "tie": 0}
    when_wins = {"llm": 0, "hybrid": 0, "tie": 0}
    where_wins = {"llm": 0, "hybrid": 0, "tie": 0}

    for r in results:
        who_wins[r["who_winner"]] += 1
        what_wins[r["what_winner"]] += 1
        when_wins[r["when_winner"]] += 1
        where_wins[r["where_winner"]] += 1

    print(f"\nWin Counts (out of {len(results)} notes):")
    print(f"  WHO:   LLM={who_wins['llm']}, Hybrid={who_wins['hybrid']}, Tie={who_wins['tie']}")
    print(f"  WHAT:  LLM={what_wins['llm']}, Hybrid={what_wins['hybrid']}, Tie={what_wins['tie']}")
    print(f"  WHEN:  LLM={when_wins['llm']}, Hybrid={when_wins['hybrid']}, Tie={when_wins['tie']}")
    print(f"  WHERE: LLM={where_wins['llm']}, Hybrid={where_wins['hybrid']}, Tie={where_wins['tie']}")

    print(f"\nResults saved to: {output_csv_path}")
    print("="*80)


if __name__ == "__main__":
    labeled_csv = "test_data/test_notes_labeled.csv"
    output_csv = "test_data/entity_extraction_comparison.csv"

    asyncio.run(run_comparison_test(labeled_csv, output_csv))
