#!/usr/bin/env python3
"""
Compare three WHEN extraction approaches:
1. Current: dateparser + parsedatetime hybrid
2. Option 1: Current + LLM validation (filter bad results)
3. Option 2: Improved LLM-only with better prompting

Uses the existing entity_extraction_comparison.csv benchmark
"""
import asyncio
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import sys

sys.path.insert(0, str(Path(__file__).parent))

from api.services.episodic import _extract_time_references
from api.llm import get_llm
from api.llm.audit import track_llm_call

# Test date context
CURRENT_DATE = "2025-10-20 14:00 PST"

async def approach1_current(text: str) -> List[Dict]:
    """Current approach: dateparser + parsedatetime hybrid"""
    return _extract_time_references(text, CURRENT_DATE)


async def approach2_llm_validation(text: str) -> List[Dict]:
    """Option 1: Current + LLM validation to filter bad results"""
    # Step 1: Extract with current approach
    time_refs = _extract_time_references(text, CURRENT_DATE)

    if not time_refs:
        return []

    # Step 2: LLM validates and filters
    prompt = f"""Review these extracted time references and remove any that are incorrect or not relevant for future planning.

NOTE TEXT: {text}
CURRENT DATE/TIME: {CURRENT_DATE}

EXTRACTED TIME REFERENCES:
{json.dumps(time_refs, indent=2)}

RULES:
1. Keep references that represent FUTURE events, deadlines, or scheduled times
2. Remove references that describe PAST duration ("after 3 hours" means past event)
3. Remove ambiguous standalone durations without clear future context
4. Remove incorrect parses (e.g., "3 hours" parsed as "3:00 AM")
5. Keep "tomorrow", "next week", specific dates/times even if approximate

TASK: Return ONLY the valid time references as a JSON array.
If all are invalid, return empty array [].

Return ONLY the JSON array, no explanation:"""

    llm = get_llm()

    try:
        with track_llm_call('when_validation', prompt) as tracker:
            response = await llm.ainvoke(prompt)
            tracker.set_response(response)

            validated = json.loads(response.content)
            tracker.set_parsed_output(validated)

        return validated if isinstance(validated, list) else []
    except Exception as e:
        # On error, return original (fallback to current approach)
        return time_refs


async def approach3_llm_only(text: str) -> List[Dict]:
    """Option 2: Improved LLM-only with better prompting and examples"""
    prompt = f"""Extract time references from this note for future planning and scheduling.

NOTE TEXT: {text}
CURRENT DATE/TIME: {CURRENT_DATE}

TASK: Extract time references that represent:
- Future events or deadlines
- Scheduled appointments
- Relative times (tomorrow, next week, etc.)
- Specific dates and times

DO NOT extract:
- Past durations describing completed events ("after 3 hours" = already happened)
- Ambiguous standalone numbers
- Current/ongoing states

For each time reference, provide:
1. "original": The exact phrase from the note
2. "parsed": ISO format timestamp (YYYY-MM-DDTHH:MM:SS) or date (YYYY-MM-DD)
3. "type": "absolute" (specific date/time) or "relative" (tomorrow, next week, etc.)

EXAMPLES:

Input: "Meeting tomorrow at 2pm"
Output: [{{"original": "tomorrow at 2pm", "parsed": "2025-10-21T14:00:00", "type": "relative"}}]

Input: "Appointment on October 25 at 5pm"
Output: [{{"original": "October 25 at 5pm", "parsed": "2025-10-25T17:00:00", "type": "absolute"}}]

Input: "Finally fixed bug after 3 hours"
Output: []  (past duration, not a future time reference)

Input: "Next week: improve testing"
Output: [{{"original": "Next week", "parsed": "2025-10-27", "type": "relative"}}]  (start of next week = Monday)

Return ONLY a JSON array of time references, or [] if none found:"""

    llm = get_llm()

    try:
        with track_llm_call('when_extraction_llm', prompt) as tracker:
            response = await llm.ainvoke(prompt)
            tracker.set_response(response)

            result = json.loads(response.content)
            tracker.set_parsed_output(result)

        return result if isinstance(result, list) else []
    except Exception as e:
        return []


def calculate_f1(expected: List[Dict], extracted: List[Dict]) -> float:
    """Calculate F1 score for time reference extraction"""
    if not expected and not extracted:
        return 1.0
    if not expected or not extracted:
        return 0.0

    # Match by parsed timestamps (allowing slight variations)
    expected_parsed = {ref.get('parsed', '')[:10] for ref in expected if ref.get('parsed')}  # Date only
    extracted_parsed = {ref.get('parsed', '')[:10] for ref in extracted if ref.get('parsed')}

    if not expected_parsed and not extracted_parsed:
        return 1.0
    if not expected_parsed or not extracted_parsed:
        return 0.0

    tp = len(expected_parsed & extracted_parsed)
    fp = len(extracted_parsed - expected_parsed)
    fn = len(expected_parsed - extracted_parsed)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0

    if precision + recall == 0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)


async def main():
    print("=" * 80)
    print("WHEN Extraction Comparison Test")
    print("=" * 80)
    print()
    print("Approaches:")
    print("  1. Current: dateparser + parsedatetime hybrid")
    print("  2. Option 1: Current + LLM validation")
    print("  3. Option 2: Improved LLM-only")
    print()

    # Load benchmark
    csv_path = Path(__file__).parent / "test_data" / "entity_extraction_comparison.csv"
    test_cases = []

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            expected_when = json.loads(row['expected_when']) if row['expected_when'] else []
            test_cases.append({
                'note_id': row['note_id'],
                'note_text': row['note_text'],
                'expected_when': expected_when
            })

    print(f"Loaded {len(test_cases)} test cases")
    print()
    print("Running extraction...")
    print()

    results = []

    for case in test_cases:
        text = case['note_text']
        expected = case['expected_when']

        # Run all three approaches
        current = await approach1_current(text)
        validated = await approach2_llm_validation(text)
        llm_only = await approach3_llm_only(text)

        # Calculate F1 scores
        f1_current = calculate_f1(expected, current)
        f1_validated = calculate_f1(expected, validated)
        f1_llm = calculate_f1(expected, llm_only)

        results.append({
            'note_id': case['note_id'],
            'expected': expected,
            'current': current,
            'validated': validated,
            'llm_only': llm_only,
            'f1_current': f1_current,
            'f1_validated': f1_validated,
            'f1_llm': f1_llm
        })

    # Calculate average F1 scores
    avg_f1_current = sum(r['f1_current'] for r in results) / len(results)
    avg_f1_validated = sum(r['f1_validated'] for r in results) / len(results)
    avg_f1_llm = sum(r['f1_llm'] for r in results) / len(results)

    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    print(f"{'Approach':<40} {'Average F1 Score':<20}")
    print("-" * 80)
    print(f"{'1. Current (dateparser+parsedatetime)':<40} {avg_f1_current:.3f}")
    print(f"{'2. Current + LLM Validation':<40} {avg_f1_validated:.3f}")
    print(f"{'3. Improved LLM-only':<40} {avg_f1_llm:.3f}")
    print()

    # Determine winner
    scores = {
        'Current': avg_f1_current,
        'LLM Validation': avg_f1_validated,
        'LLM Only': avg_f1_llm
    }
    winner = max(scores, key=scores.get)

    print(f"🏆 WINNER: {winner} ({scores[winner]:.3f} F1)")
    print()

    # Save detailed results to CSV
    output_path = Path(__file__).parent / "test_data" / "when_extraction_comparison_results.csv"

    with open(output_path, 'w', newline='') as f:
        fieldnames = [
            'note_id', 'note_text', 'expected_when',
            'current_extracted', 'current_f1',
            'validated_extracted', 'validated_f1',
            'llm_only_extracted', 'llm_only_f1',
            'winner'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, case in enumerate(test_cases):
            r = results[i]

            # Determine winner for this case
            case_scores = {
                'current': r['f1_current'],
                'validated': r['f1_validated'],
                'llm_only': r['f1_llm']
            }
            case_winner = max(case_scores, key=case_scores.get)

            writer.writerow({
                'note_id': r['note_id'],
                'note_text': case['note_text'],
                'expected_when': json.dumps(r['expected']),
                'current_extracted': json.dumps(r['current']),
                'current_f1': f"{r['f1_current']:.3f}",
                'validated_extracted': json.dumps(r['validated']),
                'validated_f1': f"{r['f1_validated']:.3f}",
                'llm_only_extracted': json.dumps(r['llm_only']),
                'llm_only_f1': f"{r['f1_llm']:.3f}",
                'winner': case_winner
            })

    print(f"✓ Detailed results saved to: {output_path}")
    print()

    # Show problem cases
    print("=" * 80)
    print("PROBLEM CASES (where all approaches failed)")
    print("=" * 80)
    print()

    for r in results:
        if r['f1_current'] < 1.0 and r['f1_validated'] < 1.0 and r['f1_llm'] < 1.0:
            print(f"Note {r['note_id']}:")
            print(f"  Expected: {r['expected']}")
            print(f"  Current: {r['current']} (F1={r['f1_current']:.2f})")
            print(f"  Validated: {r['validated']} (F1={r['f1_validated']:.2f})")
            print(f"  LLM: {r['llm_only']} (F1={r['f1_llm']:.2f})")
            print()


if __name__ == "__main__":
    asyncio.run(main())
