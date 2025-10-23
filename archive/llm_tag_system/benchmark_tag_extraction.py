"""
Tag Extraction Benchmark - Three-Axis Taxonomy Evaluation

Similar to entity_extraction_research.md methodology:
1. Load benchmark dataset with gold-standard labels
2. Run LLM tag extraction on each note
3. Calculate precision, recall, F1 scores
4. Output detailed CSV for manual debugging

Based on: docs/entity_extraction_research.md
"""
import asyncio
import csv
import json
import time
from datetime import datetime
from typing import List, Dict, Set
from api.services.episodic import _extract_tags_llm

# =====================================================
# Evaluation Metrics
# =====================================================

def calculate_metrics(expected: Set[str], predicted: Set[str]) -> Dict[str, float]:
    """Calculate precision, recall, and F1 score.

    Args:
        expected: Set of expected tags
        predicted: Set of predicted tags

    Returns:
        Dictionary with precision, recall, f1, exact_match
    """
    if not expected and not predicted:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "exact_match": 1.0}

    if not expected:
        return {"precision": 0.0, "recall": 1.0, "f1": 0.0, "exact_match": 0.0}

    if not predicted:
        return {"precision": 1.0, "recall": 0.0, "f1": 0.0, "exact_match": 0.0}

    true_positives = len(expected & predicted)
    false_positives = len(predicted - expected)
    false_negatives = len(expected - predicted)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    exact_match = 1.0 if expected == predicted else 0.0

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "exact_match": exact_match
    }


# =====================================================
# Benchmark Execution
# =====================================================

async def run_benchmark():
    """Run tag extraction benchmark on test dataset."""

    # Load benchmark dataset
    print("=" * 80)
    print("TAG EXTRACTION BENCHMARK - Three-Axis Taxonomy v2")
    print("=" * 80)
    print()
    print("TAXONOMY v2 CHANGES:")
    print("  - NATURE: record, decision, question, reference, task, plan (removed: idea, insight, memory)")
    print("  - PROCESS: discussion, learning, creating, solving, feedback (merged: meeting+conversation)")
    print("  - DOMAIN: work, project, people, health, finance, home, event (added: work)")
    print()
    print("Loading benchmark dataset...")

    benchmark_file = "test_data/tag_taxonomy_benchmark_v2.csv"
    results = []

    with open(benchmark_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        test_cases = list(reader)

    print(f"Loaded {len(test_cases)} test cases")
    print()

    # Run extraction on each test case
    total_time = 0
    for i, test_case in enumerate(test_cases, 1):
        note_id = test_case['note_id']
        note_text = test_case['note_text']
        expected_tags_str = test_case['expected_tags']
        rationale = test_case['rationale']

        # Parse expected tags
        expected_tags = set(json.loads(expected_tags_str))

        print(f"[{i}/{len(test_cases)}] Testing note {note_id}...")
        print(f"  Text: {note_text[:60]}...")
        print(f"  Expected: {sorted(expected_tags)}")

        # Extract tags with timing
        start_time = time.time()
        try:
            predicted_tags_list = await _extract_tags_llm(note_text)
            predicted_tags = set(predicted_tags_list)
            error = None
        except Exception as e:
            predicted_tags = set()
            error = str(e)
            print(f"  ERROR: {error}")

        elapsed_ms = int((time.time() - start_time) * 1000)
        total_time += elapsed_ms

        print(f"  Predicted: {sorted(predicted_tags)}")
        print(f"  Time: {elapsed_ms}ms")

        # Calculate metrics
        metrics = calculate_metrics(expected_tags, predicted_tags)

        print(f"  F1: {metrics['f1']:.3f} | Precision: {metrics['precision']:.3f} | Recall: {metrics['recall']:.3f} | Exact: {metrics['exact_match']}")

        # Store result
        results.append({
            'note_id': note_id,
            'note_text': note_text,
            'expected_tags': expected_tags_str,
            'predicted_tags': json.dumps(sorted(predicted_tags)),
            'rationale': rationale,
            'time_ms': elapsed_ms,
            'precision': metrics['precision'],
            'recall': metrics['recall'],
            'f1': metrics['f1'],
            'exact_match': metrics['exact_match'],
            'error': error or ''
        })

        print()

    # =====================================================
    # Summary Statistics
    # =====================================================

    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print()

    avg_precision = sum(r['precision'] for r in results) / len(results)
    avg_recall = sum(r['recall'] for r in results) / len(results)
    avg_f1 = sum(r['f1'] for r in results) / len(results)
    exact_match_rate = sum(r['exact_match'] for r in results) / len(results)
    avg_time = total_time / len(results)

    print(f"Total test cases: {len(results)}")
    print(f"Average precision: {avg_precision:.3f}")
    print(f"Average recall: {avg_recall:.3f}")
    print(f"Average F1 score: {avg_f1:.3f}")
    print(f"Exact match rate: {exact_match_rate:.1%} ({int(exact_match_rate * len(results))}/{len(results)})")
    print(f"Average extraction time: {avg_time:.0f}ms")
    print(f"Total time: {total_time/1000:.1f}s")
    print()

    # =====================================================
    # Error Analysis
    # =====================================================

    print("=" * 80)
    print("ERROR ANALYSIS")
    print("=" * 80)
    print()

    errors = [r for r in results if r['f1'] < 1.0]
    if errors:
        print(f"Found {len(errors)} cases with errors:")
        print()
        for err in errors:
            print(f"Note {err['note_id']}: F1={err['f1']:.3f}")
            print(f"  Text: {err['note_text'][:60]}...")
            print(f"  Expected: {err['expected_tags']}")
            print(f"  Predicted: {err['predicted_tags']}")
            print()
    else:
        print("Perfect! No errors found.")
        print()

    # =====================================================
    # Save Results CSV
    # =====================================================

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_data/tag_extraction_results_{timestamp}.csv"

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['note_id', 'note_text', 'expected_tags', 'predicted_tags',
                     'rationale', 'time_ms', 'precision', 'recall', 'f1',
                     'exact_match', 'error']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print("=" * 80)
    print(f"Results saved to: {output_file}")
    print("=" * 80)
    print()

    # =====================================================
    # Return summary for further analysis
    # =====================================================

    return {
        'avg_precision': avg_precision,
        'avg_recall': avg_recall,
        'avg_f1': avg_f1,
        'exact_match_rate': exact_match_rate,
        'avg_time_ms': avg_time,
        'total_cases': len(results),
        'perfect_matches': int(exact_match_rate * len(results)),
        'output_file': output_file
    }


# =====================================================
# Main Execution
# =====================================================

if __name__ == "__main__":
    print()
    print("Starting Tag Extraction Benchmark...")
    print()

    summary = asyncio.run(run_benchmark())

    print()
    print("FINAL SUMMARY:")
    print(f"  Average F1: {summary['avg_f1']:.3f}")
    print(f"  Exact matches: {summary['perfect_matches']}/{summary['total_cases']} ({summary['exact_match_rate']:.1%})")
    print(f"  Average time: {summary['avg_time_ms']:.0f}ms")
    print()
    print("Benchmark complete!")
    print()
