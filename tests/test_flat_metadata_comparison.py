"""
Test: Compare Folder Classification vs Flat Metadata Extraction

This test compares two approaches:
1. Current: Force LLM to pick ONE folder (tasks|meetings|ideas|reference|journal)
2. New: Extract multi-dimensional metadata (boolean dimensions + entities)

Metrics:
- LLM confidence (subjective reasoning quality)
- Accuracy (does output make sense?)
- Token usage
- Raw LLM responses (for human inspection)
"""

import asyncio
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.llm.client import get_llm
from api.llm.prompts import Prompts


# New metadata extraction prompt (flat approach)
EXTRACT_METADATA_FLAT = """## Identity

You are a metadata extraction agent. Extract factual, multi-dimensional metadata from notes.

Note content: {text}

---

## Extraction Guidelines

Extract the following dimensions independently. Multiple can be true simultaneously.

### Boolean Dimensions

**has_action_items**
- Does this note contain actionable todos, tasks, or deadlines?
- True if: "Need to...", "TODO:", deadlines, action items
- False if: pure reflection, discussion, learning

**is_social**
- Does this note involve conversations with other people?
- True if: meetings, discussions, "met with X", "talked to Y"
- False if: solo work, personal thoughts

**is_emotional**
- Does this note express feelings or emotions?
- True if: feeling words, emotional processing, reflections on mood
- False if: purely factual, no emotional content

**is_knowledge**
- Does this note contain learnings, how-tos, or reference material?
- True if: explanations, tutorials, "learned that...", "how to..."
- False if: just actions or feelings without learnings

**is_exploratory**
- Does this note contain brainstorming or "what if" thinking?
- True if: ideas, hypotheses, explorations, possibilities
- False if: concrete actions or facts

### Entity Extraction

- **people**: List of proper names mentioned
- **emotions**: List of feeling words expressed
- **entities**: List of concepts, tools, topics, projects mentioned
- **time_refs**: List of dates, deadlines, or time references

---

## Examples

**Example 1: Task with emotion**

Input:
"Need to fix the authentication bug by Friday. Feeling frustrated with this issue."

Output:
{{{{
  "has_action_items": true,
  "is_social": false,
  "is_emotional": true,
  "is_knowledge": false,
  "is_exploratory": false,
  "people": [],
  "emotions": ["frustrated"],
  "entities": ["authentication", "bug"],
  "time_refs": ["Friday"]
}}}}

**Example 2: Meeting with learnings**

Input:
"Met with Sarah to discuss memory consolidation research. She explained how hippocampus works during sleep. Very insightful!"

Output:
{{{{
  "has_action_items": false,
  "is_social": true,
  "is_emotional": false,
  "is_knowledge": true,
  "is_exploratory": false,
  "people": ["Sarah"],
  "emotions": [],
  "entities": ["memory consolidation", "hippocampus", "sleep"],
  "time_refs": []
}}}}

**Example 3: Idea brainstorm**

Input:
"What if we used Redis for caching API responses? Could improve performance significantly."

Output:
{{{{
  "has_action_items": false,
  "is_social": false,
  "is_emotional": false,
  "is_knowledge": false,
  "is_exploratory": true,
  "people": [],
  "emotions": [],
  "entities": ["Redis", "caching", "API", "performance"],
  "time_refs": []
}}}}

**Example 4: Journal entry**

Input:
"Feeling excited about the new project! Can't wait to get started."

Output:
{{{{
  "has_action_items": false,
  "is_social": false,
  "is_emotional": true,
  "is_knowledge": false,
  "is_exploratory": false,
  "people": [],
  "emotions": ["excited"],
  "entities": ["new project"],
  "time_refs": []
}}}}

**Example 5: Multi-dimensional note**

Input:
"Met with Alex to brainstorm ideas for the vector search project. Feeling overwhelmed by the scope but excited about possibilities. Need to research FAISS by next week."

Output:
{{{{
  "has_action_items": true,
  "is_social": true,
  "is_emotional": true,
  "is_knowledge": false,
  "is_exploratory": true,
  "people": ["Alex"],
  "emotions": ["overwhelmed", "excited"],
  "entities": ["vector search project", "FAISS"],
  "time_refs": ["next week"]
}}}}

---

## Important Notes

**All dimensions are independent:**
- A note can be social AND emotional AND have action items
- A note can be none of the dimensions (simple observation)
- Don't force single-category thinking

**Extract what's clearly present:**
- Don't infer or assume
- Empty arrays are fine
- Multiple true booleans are expected for complex notes

**Return format:**
Return ONLY the JSON object with all fields. No additional text.

JSON:"""


async def test_single_note_both_approaches(note_path: str) -> Dict:
    """Test both approaches on a single note."""

    # Read note content
    full_content = Path(note_path).read_text()
    note_name = Path(note_path).name
    actual_folder = Path(note_path).parent.name

    # Extract ONLY the actual note content (after YAML frontmatter)
    # This prevents LLM from seeing previously-enriched metadata
    if full_content.startswith('---'):
        parts = full_content.split('---', 2)
        if len(parts) >= 3:
            content = parts[2].strip()  # Content after second ---
        else:
            content = full_content
    else:
        content = full_content

    print(f"\n{'='*80}")
    print(f"NOTE: {note_name}")
    print(f"ACTUAL FOLDER: {actual_folder}")
    print(f"{'='*80}")
    print(f"CONTENT:\n{content[:300]}...")
    print(f"{'='*80}\n")

    llm = get_llm(format="json")

    # Approach 1: Current folder classification
    print("APPROACH 1: FOLDER CLASSIFICATION (Current)")
    print("-" * 80)

    start_time = time.time()
    classify_prompt = Prompts.CLASSIFY_NOTE.format(text=content)
    classify_response_obj = await llm.ainvoke(classify_prompt)
    classify_response = classify_response_obj.content
    classify_time = time.time() - start_time

    print(f"Raw LLM Response:\n{classify_response}\n")

    try:
        # Extract JSON from response
        classify_json_start = classify_response.find('{')
        classify_json_end = classify_response.rfind('}') + 1
        classify_json = json.loads(classify_response[classify_json_start:classify_json_end])
        print(f"Parsed JSON:\n{json.dumps(classify_json, indent=2)}\n")
        classify_success = True
        predicted_folder = classify_json.get('folder', 'unknown')
    except Exception as e:
        print(f"ERROR parsing JSON: {e}\n")
        classify_success = False
        classify_json = {}
        predicted_folder = 'error'

    print(f"Time: {classify_time:.2f}s")
    print(f"Predicted folder: {predicted_folder}")
    print(f"Actual folder: {actual_folder}")
    print(f"Match: {predicted_folder == actual_folder}")

    # Approach 2: Flat metadata extraction
    print("\n" + "=" * 80)
    print("APPROACH 2: FLAT METADATA EXTRACTION (New)")
    print("-" * 80)

    start_time = time.time()
    metadata_prompt = EXTRACT_METADATA_FLAT.format(text=content)
    metadata_response_obj = await llm.ainvoke(metadata_prompt)
    metadata_response = metadata_response_obj.content
    metadata_time = time.time() - start_time

    print(f"Raw LLM Response:\n{metadata_response}\n")

    try:
        # Extract JSON from response
        metadata_json_start = metadata_response.find('{')
        metadata_json_end = metadata_response.rfind('}') + 1
        metadata_json = json.loads(metadata_response[metadata_json_start:metadata_json_end])
        print(f"Parsed JSON:\n{json.dumps(metadata_json, indent=2)}\n")
        metadata_success = True
    except Exception as e:
        print(f"ERROR parsing JSON: {e}\n")
        metadata_success = False
        metadata_json = {}

    print(f"Time: {metadata_time:.2f}s")

    # Map metadata to expected folder
    if metadata_json:
        inferred_folders = []
        if metadata_json.get('has_action_items'): inferred_folders.append('tasks')
        if metadata_json.get('is_social'): inferred_folders.append('meetings')
        if metadata_json.get('is_emotional'): inferred_folders.append('journal')
        if metadata_json.get('is_knowledge'): inferred_folders.append('reference')
        if metadata_json.get('is_exploratory'): inferred_folders.append('ideas')

        print(f"Inferred folder(s) from metadata: {inferred_folders}")
        print(f"Actual folder: {actual_folder}")
        print(f"Match: {actual_folder in inferred_folders}")

    return {
        'note_name': note_name,
        'actual_folder': actual_folder,
        'content_preview': content[:200],
        'classify': {
            'success': classify_success,
            'time': classify_time,
            'raw_response': classify_response,
            'parsed': classify_json,
            'predicted_folder': predicted_folder,
            'match': predicted_folder == actual_folder
        },
        'metadata': {
            'success': metadata_success,
            'time': metadata_time,
            'raw_response': metadata_response,
            'parsed': metadata_json,
            'inferred_folders': inferred_folders if metadata_json else [],
            'match': actual_folder in inferred_folders if metadata_json else False
        }
    }


async def run_comparison_test(note_paths: List[str]):
    """Run comparison test on multiple notes."""

    print("\n" + "=" * 80)
    print("FOLDER CLASSIFICATION vs FLAT METADATA EXTRACTION")
    print("Comparison Test")
    print("=" * 80)

    results = []

    for note_path in note_paths:
        result = await test_single_note_both_approaches(note_path)
        results.append(result)

        # Small delay to avoid overwhelming LLM
        await asyncio.sleep(0.5)

    # Summary statistics
    print("\n\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    classify_matches = sum(1 for r in results if r['classify']['match'])
    metadata_matches = sum(1 for r in results if r['metadata']['match'])

    classify_success_rate = sum(1 for r in results if r['classify']['success']) / len(results)
    metadata_success_rate = sum(1 for r in results if r['metadata']['success']) / len(results)

    classify_avg_time = sum(r['classify']['time'] for r in results) / len(results)
    metadata_avg_time = sum(r['metadata']['time'] for r in results) / len(results)

    print(f"\nTotal notes tested: {len(results)}")
    print(f"\nAPPROACH 1 - Folder Classification:")
    print(f"  Success rate (valid JSON): {classify_success_rate:.1%}")
    print(f"  Accuracy (correct folder): {classify_matches}/{len(results)} ({classify_matches/len(results):.1%})")
    print(f"  Average time: {classify_avg_time:.2f}s")

    print(f"\nAPPROACH 2 - Flat Metadata:")
    print(f"  Success rate (valid JSON): {metadata_success_rate:.1%}")
    print(f"  Accuracy (folder in dimensions): {metadata_matches}/{len(results)} ({metadata_matches/len(results):.1%})")
    print(f"  Average time: {metadata_avg_time:.2f}s")

    # Search query analysis
    print(f"\n\nSEARCH QUERY FALLBACK ANALYSIS")
    print("=" * 80)
    await analyze_search_patterns()

    # Detailed comparison table
    print(f"\n\nDETAILED COMPARISON TABLE")
    print("=" * 80)
    print(f"{'Note':<40} {'Actual':<10} {'Classify':<10} {'Metadata Dims':<20}")
    print("-" * 80)

    for r in results:
        note_short = r['note_name'][:37] + "..." if len(r['note_name']) > 40 else r['note_name']
        actual = r['actual_folder']
        classify_pred = r['classify']['predicted_folder']

        # Get active dimensions
        meta_dims = []
        if r['metadata']['parsed']:
            if r['metadata']['parsed'].get('has_action_items'): meta_dims.append('T')
            if r['metadata']['parsed'].get('is_social'): meta_dims.append('M')
            if r['metadata']['parsed'].get('is_emotional'): meta_dims.append('J')
            if r['metadata']['parsed'].get('is_knowledge'): meta_dims.append('R')
            if r['metadata']['parsed'].get('is_exploratory'): meta_dims.append('I')
        meta_str = ','.join(meta_dims) if meta_dims else 'none'

        # Add checkmarks for matches
        classify_mark = '✓' if r['classify']['match'] else '✗'
        metadata_mark = '✓' if r['metadata']['match'] else '✗'

        print(f"{note_short:<40} {actual:<10} {classify_pred:<10}{classify_mark} {meta_str:<20}{metadata_mark}")

    print("\nLegend: T=tasks, M=meetings, J=journal, R=reference, I=ideas")

    # Save detailed results to file
    output_file = Path(__file__).parent / "flat_metadata_test_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n\nDetailed results saved to: {output_file}")

    return results


if __name__ == "__main__":
    # Test notes
    test_notes = [
        "/Users/weihuahuang/Notes/ideas/2025-10-11-brainstorming-vector-embeddings.md",
        "/Users/weihuahuang/Notes/ideas/2025-10-12-evaluate-vector-db-options-for-semantic-search.md",
        "/Users/weihuahuang/Notes/ideas/2025-10-12-memory-consolidation-for-background-tasks.md",
        "/Users/weihuahuang/Notes/inbox/2025-10-02-fix-aws-alb-cognito-integration-issue-need-to-check-vpc-e.md",
        "/Users/weihuahuang/Notes/inbox/2025-10-09-dodgers-win-and-advance.md",
        "/Users/weihuahuang/Notes/journal/2025-10-09-blue-jays-beat-yankees-in-alds.md",
        "/Users/weihuahuang/Notes/journal/2025-10-13-port-moody-park-and-korean-food.md",
        "/Users/weihuahuang/Notes/meetings/2025-10-11-meeting-with-sarah-about-memory-research.md",
        "/Users/weihuahuang/Notes/reference/2025-10-11-how-hippocampus-handles-memory-consolidation.md",
        "/Users/weihuahuang/Notes/reference/2025-10-12-fts5-full-text-search-in-sqlite.md",
    ]

    # Filter to only existing notes
    existing_notes = [n for n in test_notes if Path(n).exists()]

    print(f"Testing {len(existing_notes)} notes...")

    asyncio.run(run_comparison_test(existing_notes))
