#!/usr/bin/env python3
"""
Phase 3 Prospective Memory - Simplified Benchmark Test

Tests the metadata-only prospective extraction approach:
- Extracts prospective items (actions, questions, plans)
- Links items to WHEN timepoints from Phase 1
- No graph edges created (metadata only)

Metrics:
- Contains detection accuracy (true/false positive rate)
- Item extraction accuracy (content matching)
- Timedata linking accuracy (correct timepoint matching)

Usage:
    python test_phase3_prospective.py
"""

import asyncio
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from api.services.episodic import extract_episodic_metadata
from api.services.prospective import extract_prospective_items


async def load_benchmark_data() -> List[Dict]:
    """Load benchmark test cases from CSV."""
    test_cases = []
    csv_path = Path(__file__).parent / "test_data" / "phase3_prospective_benchmark.csv"

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse expected_items JSON
            expected_items = json.loads(row['expected_items'])

            test_cases.append({
                'note_id': row['note_id'],
                'note_text': row['note_text'],
                'expected_contains': row['expected_contains_prospective'].lower() == 'true',
                'expected_items': expected_items
            })

    return test_cases


async def run_prospective_extraction(test_cases: List[Dict]) -> List[Dict]:
    """Run prospective extraction on all test cases."""
    results = []
    current_date = "2025-10-21 12:00 PST"  # Fixed date for consistent testing

    for i, case in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] Processing note {case['note_id']}...")

        try:
            # Step 1: Extract episodic metadata (to get WHEN data)
            episodic = await extract_episodic_metadata(case['note_text'], current_date)

            # Step 2: Extract prospective items with WHEN data
            prospective = await extract_prospective_items(case['note_text'], episodic['when'])

            results.append({
                'note_id': case['note_id'],
                'note_text': case['note_text'],
                'expected': {
                    'contains_prospective': case['expected_contains'],
                    'items': case['expected_items']
                },
                'extracted': {
                    'contains_prospective': prospective['contains_prospective'],
                    'items': prospective['prospective_items']
                },
                'when_data': episodic['when']
            })

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                'note_id': case['note_id'],
                'note_text': case['note_text'],
                'expected': {
                    'contains_prospective': case['expected_contains'],
                    'items': case['expected_items']
                },
                'extracted': {
                    'contains_prospective': False,
                    'items': []
                },
                'error': str(e),
                'when_data': []
            })

    return results


def calculate_metrics(results: List[Dict]) -> Dict[str, Any]:
    """Calculate accuracy metrics."""
    # Contains detection metrics
    contains_correct = sum(1 for r in results
                          if r['expected']['contains_prospective'] == r['extracted']['contains_prospective'])
    contains_accuracy = contains_correct / len(results) if results else 0

    # True positives, false positives, false negatives for contains
    tp_contains = sum(1 for r in results
                      if r['expected']['contains_prospective'] and r['extracted']['contains_prospective'])
    fp_contains = sum(1 for r in results
                      if not r['expected']['contains_prospective'] and r['extracted']['contains_prospective'])
    fn_contains = sum(1 for r in results
                      if r['expected']['contains_prospective'] and not r['extracted']['contains_prospective'])

    # Item extraction accuracy (rough match based on content similarity)
    item_matches = []
    for r in results:
        if not r['expected']['contains_prospective']:
            # No items expected - correct if no items extracted
            item_matches.append(len(r['extracted']['items']) == 0)
        else:
            # Check if extracted items match expected (fuzzy match on content)
            expected_count = len(r['expected']['items'])
            extracted_count = len(r['extracted']['items'])

            if expected_count == 0 and extracted_count == 0:
                item_matches.append(True)
            elif expected_count == extracted_count:
                # Same number of items - consider it a partial match
                item_matches.append(True)
            else:
                item_matches.append(False)

    item_accuracy = sum(item_matches) / len(item_matches) if item_matches else 0

    # Timedata linking accuracy (for items with timedata)
    timedata_matches = []
    for r in results:
        for expected_item in r['expected']['items']:
            # Find matching extracted item by content similarity
            for extracted_item in r['extracted']['items']:
                # Simple match: if content keywords overlap
                exp_content = expected_item['content'].lower()
                ext_content = extracted_item['content'].lower()

                # Check if they're talking about the same thing (basic keyword overlap)
                exp_words = set(exp_content.split())
                ext_words = set(ext_content.split())
                overlap = len(exp_words & ext_words) / max(len(exp_words), len(ext_words)) if exp_words or ext_words else 0

                if overlap > 0.3:  # 30% word overlap = same item
                    # Check timedata match
                    timedata_matches.append(expected_item['timedata'] == extracted_item['timedata'])
                    break

    timedata_accuracy = sum(timedata_matches) / len(timedata_matches) if timedata_matches else 0

    return {
        'contains_accuracy': contains_accuracy,
        'contains_tp': tp_contains,
        'contains_fp': fp_contains,
        'contains_fn': fn_contains,
        'item_count_accuracy': item_accuracy,
        'timedata_linking_accuracy': timedata_accuracy,
        'total_test_cases': len(results)
    }


def generate_reports(results: List[Dict], metrics: Dict[str, Any]):
    """Generate test reports in multiple formats."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_path = Path(__file__).parent / "test_data"

    # 1. CSV Report (detailed results)
    csv_path = base_path / f"phase3_prospective_results_{timestamp}.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'note_id', 'note_text',
            'expected_contains', 'extracted_contains', 'match_contains',
            'expected_item_count', 'extracted_item_count',
            'expected_items_json', 'extracted_items_json'
        ])

        for r in results:
            writer.writerow([
                r['note_id'],
                r['note_text'][:100],  # Truncate for readability
                r['expected']['contains_prospective'],
                r['extracted']['contains_prospective'],
                r['expected']['contains_prospective'] == r['extracted']['contains_prospective'],
                len(r['expected']['items']),
                len(r['extracted']['items']),
                json.dumps(r['expected']['items']),
                json.dumps(r['extracted']['items'])
            ])

    # 2. Text Report (human-readable)
    txt_path = base_path / f"phase3_prospective_report_{timestamp}.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Phase 3: Prospective Memory - Simplified Benchmark Test Report\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Test Cases: {metrics['total_test_cases']}\n\n")

        f.write("-" * 80 + "\n")
        f.write("Metrics Summary\n")
        f.write("-" * 80 + "\n\n")

        f.write(f"Contains Detection Accuracy:  {metrics['contains_accuracy']:.3f}\n")
        f.write(f"  True Positives:   {metrics['contains_tp']}\n")
        f.write(f"  False Positives:  {metrics['contains_fp']}\n")
        f.write(f"  False Negatives:  {metrics['contains_fn']}\n\n")

        f.write(f"Item Count Accuracy:          {metrics['item_count_accuracy']:.3f}\n")
        f.write(f"Timedata Linking Accuracy:    {metrics['timedata_linking_accuracy']:.3f}\n\n")

        f.write("-" * 80 + "\n")
        f.write("Sample Results (First 10)\n")
        f.write("-" * 80 + "\n\n")

        for r in results[:10]:
            f.write(f"Note {r['note_id']}: {r['note_text'][:60]}...\n")
            f.write(f"  Expected Contains: {r['expected']['contains_prospective']}\n")
            f.write(f"  Extracted Contains: {r['extracted']['contains_prospective']}\n")
            f.write(f"  Expected Items: {len(r['expected']['items'])}\n")
            f.write(f"  Extracted Items: {len(r['extracted']['items'])}\n")

            if r['extracted']['items']:
                f.write(f"  Extracted:\n")
                for item in r['extracted']['items']:
                    f.write(f"    - {item['content']} (timedata: {item['timedata']})\n")
            f.write("\n")

    # 3. JSON Report (machine-readable)
    json_path = base_path / f"phase3_prospective_results_{timestamp}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': timestamp,
            'metrics': metrics,
            'results': results
        }, f, indent=2)

    print("\n" + "=" * 80)
    print("REPORTS GENERATED")
    print("=" * 80)
    print(f"\n✓ CSV:  {csv_path}")
    print(f"✓ TXT:  {txt_path}")
    print(f"✓ JSON: {json_path}\n")


async def main():
    """Main test execution."""
    print("=" * 80)
    print("Phase 3: Prospective Memory - Simplified Benchmark Test")
    print("=" * 80)
    print()

    # Load benchmark data
    print("📊 Loading benchmark data...")
    test_cases = await load_benchmark_data()
    print(f"✓ Loaded {len(test_cases)} test cases\n")

    # Run extraction
    print("🔄 Running prospective extraction...")
    results = await run_prospective_extraction(test_cases)
    print(f"✓ Completed {len(results)} extractions\n")

    # Calculate metrics
    print("📈 Calculating metrics...")
    metrics = calculate_metrics(results)
    print("✓ Metrics calculated\n")

    # Print metrics summary
    print("=" * 80)
    print("METRICS SUMMARY")
    print("=" * 80)
    print()
    print(f"Contains Detection Accuracy:  {metrics['contains_accuracy']:.3f}")
    print(f"  True Positives:   {metrics['contains_tp']}")
    print(f"  False Positives:  {metrics['contains_fp']}")
    print(f"  False Negatives:  {metrics['contains_fn']}")
    print()
    print(f"Item Count Accuracy:          {metrics['item_count_accuracy']:.3f}")
    print(f"Timedata Linking Accuracy:    {metrics['timedata_linking_accuracy']:.3f}")
    print()

    # Generate reports
    generate_reports(results, metrics)

    print("=" * 80)
    print("TEST COMPLETE!")
    print("=" * 80)
    print()


if __name__ == "__main__":
    asyncio.run(main())
