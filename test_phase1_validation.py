"""
Phase 1 Validation: Compare production /capture_note endpoint against labeled test data

Similar to scripts/test_entity_extraction.py but tests the actual API endpoint
"""
import asyncio
import httpx
import csv
import json
from datetime import datetime
from typing import Dict, List, Any


def parse_expected(field_value: str) -> Any:
    """Parse expected value from CSV (JSON string)"""
    try:
        return json.loads(field_value)
    except:
        return []


def calculate_f1(expected: List[str], actual: List[str]) -> Dict[str, float]:
    """Calculate precision, recall, F1 for a field"""
    if not expected and not actual:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}

    if not expected:
        return {"precision": 0.0, "recall": 1.0, "f1": 0.0}

    if not actual:
        return {"precision": 1.0, "recall": 0.0, "f1": 0.0}

    # Normalize for comparison (lowercase, strip)
    expected_norm = {str(e).lower().strip() for e in expected}
    actual_norm = {str(a).lower().strip() for a in actual}

    true_positives = len(expected_norm & actual_norm)
    false_positives = len(actual_norm - expected_norm)
    false_negatives = len(expected_norm - actual_norm)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": true_positives,
        "fp": false_positives,
        "fn": false_negatives
    }


async def validate_phase1():
    """Test all 30 notes and calculate accuracy metrics"""

    print("=" * 80)
    print("PHASE 1 VALIDATION - Production Endpoint vs Labeled Data")
    print("=" * 80)
    print()

    # Read labeled test data
    with open('test_data/test_notes_labeled.csv', 'r') as f:
        reader = csv.DictReader(f)
        test_notes = list(reader)

    print(f"📊 Loaded {len(test_notes)} labeled test notes\n")

    # Track results
    results = []
    field_scores = {
        "who": [],
        "what": [],
        "when": [],
        "where": []
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, note in enumerate(test_notes, 1):
            note_id = note['note_id']
            note_text = note['note_text']

            # Parse expected values
            expected_who = parse_expected(note['expected_who'])
            expected_what = parse_expected(note['expected_what'])
            expected_when = parse_expected(note['expected_when'])
            expected_where = parse_expected(note['expected_where'])

            print(f"[{i}/{len(test_notes)}] Note {note_id}")
            print(f"   Text: {note_text[:60]}...")

            try:
                # Call production endpoint
                response = await client.post(
                    "http://localhost:8000/capture_note",
                    json={"text": note_text}
                )

                if response.status_code != 200:
                    print(f"   ❌ API Error: {response.status_code}")
                    continue

                result = response.json()
                episodic = result['episodic']

                # Extract actual values
                actual_who = episodic['who']
                actual_what = episodic['what']
                actual_when = [t['original'] for t in episodic['when']]
                actual_where = episodic['where']

                # Calculate F1 scores for each field
                who_score = calculate_f1(expected_who, actual_who)
                what_score = calculate_f1(expected_what, actual_what)
                # For WHEN, just check if time references were found (not exact match)
                when_score = calculate_f1(
                    [t['original'] for t in expected_when],
                    actual_when
                )
                where_score = calculate_f1(expected_where, actual_where)

                # Store scores
                field_scores["who"].append(who_score["f1"])
                field_scores["what"].append(what_score["f1"])
                field_scores["when"].append(when_score["f1"])
                field_scores["where"].append(where_score["f1"])

                # Print comparison
                print(f"   WHO:")
                print(f"      Expected: {expected_who}")
                print(f"      Actual:   {actual_who}")
                print(f"      F1: {who_score['f1']:.3f} (TP:{who_score['tp']}, FP:{who_score['fp']}, FN:{who_score['fn']})")

                print(f"   WHAT:")
                print(f"      Expected: {expected_what[:3]}{'...' if len(expected_what) > 3 else ''}")
                print(f"      Actual:   {actual_what[:3]}{'...' if len(actual_what) > 3 else ''}")
                print(f"      F1: {what_score['f1']:.3f} (TP:{what_score['tp']}, FP:{what_score['fp']}, FN:{what_score['fn']})")

                print(f"   WHEN:")
                print(f"      Expected: {[t['original'] for t in expected_when]}")
                print(f"      Actual:   {actual_when}")
                print(f"      F1: {when_score['f1']:.3f} (TP:{when_score['tp']}, FP:{when_score['fp']}, FN:{when_score['fn']})")

                print(f"   WHERE:")
                print(f"      Expected: {expected_where}")
                print(f"      Actual:   {actual_where}")
                print(f"      F1: {where_score['f1']:.3f} (TP:{where_score['tp']}, FP:{where_score['fp']}, FN:{where_score['fn']})")

                print()

                # Store result
                results.append({
                    'note_id': note_id,
                    'note_text': note_text,
                    'expected': {
                        'who': expected_who,
                        'what': expected_what,
                        'when': [t['original'] for t in expected_when],
                        'where': expected_where
                    },
                    'actual': {
                        'who': actual_who,
                        'what': actual_what,
                        'when': actual_when,
                        'where': actual_where,
                        'tags': episodic['tags']
                    },
                    'scores': {
                        'who': who_score['f1'],
                        'what': what_score['f1'],
                        'when': when_score['f1'],
                        'where': where_score['f1']
                    }
                })

            except Exception as e:
                print(f"   ❌ Error: {e}")
                print()
                continue

    # Calculate aggregate metrics
    print("=" * 80)
    print("AGGREGATE RESULTS")
    print("=" * 80)
    print()

    for field in ["who", "what", "when", "where"]:
        scores = field_scores[field]
        if scores:
            avg_f1 = sum(scores) / len(scores)
            print(f"{field.upper():6} - Average F1: {avg_f1:.3f} (n={len(scores)})")
            print(f"         Range: {min(scores):.3f} - {max(scores):.3f}")
            print()

    # Overall average
    all_scores = []
    for field_list in field_scores.values():
        all_scores.extend(field_list)

    if all_scores:
        overall_f1 = sum(all_scores) / len(all_scores)
        print(f"📊 OVERALL AVERAGE F1: {overall_f1:.3f}")
        print()

    # Save detailed results
    output_file = 'test_data/phase1_validation_results.json'
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_notes': len(test_notes),
            'results': results,
            'aggregate_scores': {
                field: {
                    'average_f1': sum(scores) / len(scores) if scores else 0,
                    'min_f1': min(scores) if scores else 0,
                    'max_f1': max(scores) if scores else 0,
                    'count': len(scores)
                }
                for field, scores in field_scores.items()
            },
            'overall_f1': sum(all_scores) / len(all_scores) if all_scores else 0
        }, f, indent=2)

    print(f"💾 Detailed results saved to {output_file}")
    print()

    # Comparison to research baseline
    print("=" * 80)
    print("COMPARISON TO RESEARCH BASELINE")
    print("=" * 80)
    print()
    print("Research Results (from entity_extraction_research.md):")
    print("  WHO:   0.691 F1 (LLM)")
    print("  WHAT:  0.933 F1 (LLM)")
    print("  WHEN:  0.944 F1 (dateparser)")
    print("  WHERE: 0.844 F1 (LLM)")
    print()

    if field_scores["who"]:
        who_f1 = sum(field_scores["who"]) / len(field_scores["who"])
        what_f1 = sum(field_scores["what"]) / len(field_scores["what"])
        when_f1 = sum(field_scores["when"]) / len(field_scores["when"])
        where_f1 = sum(field_scores["where"]) / len(field_scores["where"])

        print("Phase 1 Production Results:")
        print(f"  WHO:   {who_f1:.3f} F1 {'✅' if who_f1 >= 0.69 else '⚠️'}")
        print(f"  WHAT:  {what_f1:.3f} F1 {'✅' if what_f1 >= 0.93 else '⚠️'}")
        print(f"  WHEN:  {when_f1:.3f} F1 {'✅' if when_f1 >= 0.94 else '⚠️'}")
        print(f"  WHERE: {where_f1:.3f} F1 {'✅' if where_f1 >= 0.84 else '⚠️'}")

    print()
    print("=" * 80)


if __name__ == "__main__":
    print("\n🚀 Starting Phase 1 Validation...")
    print("⚠️  Make sure the API server is running on http://localhost:8000\n")

    try:
        asyncio.run(validate_phase1())
    except httpx.ConnectError:
        print("\n❌ Could not connect to API server!")
        print("   Start the server with: uvicorn api.main:app --reload")
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
