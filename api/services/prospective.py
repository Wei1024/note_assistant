"""
Prospective Memory Layer - Metadata-Only Approach

Extracts future-oriented items (actions, questions, plans) and links them to
WHEN timepoints from episodic memory for todo-list visualization.

Design Decision:
After testing edge-based approaches (time_next, reminder, intention_trigger),
we found they created too much noise (900+ edges for 60 notes). This simplified
approach stores prospective items as metadata only, keeping the graph clean for
semantic/entity relationships.

Based on user requirements:
- Identify prospective items (things to do, evaluate, discuss, decide, questions)
- Match items to WHEN timepoints from Phase 1
- Store as structured metadata (no graph edges)
- Display in todo-list view (frontend implementation)
"""
import json
from typing import Dict, List, Any
from ..llm import get_llm
from ..llm.audit import track_llm_call


async def extract_prospective_items(text: str, when_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract prospective items and link to WHEN timepoints.

    Runs AFTER episodic extraction to access parsed WHEN data.

    Args:
        text: Raw note content
        when_data: WHEN timepoints from episodic extraction
                   Format: [{"original": "Friday", "parsed": "2025-10-25T00:00:00", "type": "relative"}]

    Returns:
        {
            "contains_prospective": bool,
            "prospective_items": [
                {
                    "content": str,  # Brief action/question/plan description
                    "timedata": str | null  # ISO timestamp from when_data, or null
                }
            ]
        }

    Example:
        Input text: "Met with Sarah. Need to review proposal by Friday."
        Input when_data: [{"original": "Friday", "parsed": "2025-10-25T00:00:00", ...}]

        Output: {
            "contains_prospective": true,
            "prospective_items": [
                {
                    "content": "review proposal",
                    "timedata": "2025-10-25T00:00:00"
                }
            ]
        }
    """
    # Format WHEN data for LLM prompt
    when_str = json.dumps(when_data, indent=2) if when_data else "[]"

    prompt = f"""Extract future-oriented action items from this note.

NOTE TEXT:
{text}

TIMEPOINTS EXTRACTED:
{when_str}

TASK:
Identify any prospective items (things to do, evaluate, discuss, decide, or questions to answer).

For each prospective item:
1. Provide a brief description of the action/decision/question
2. If the item is associated with a specific timepoint, return the "parsed" timestamp from the TIMEPOINTS above
3. If no specific timepoint is mentioned with the item, use null

OUTPUT FORMAT (JSON only, no explanation):
{{
  "contains_prospective": true/false,
  "prospective_items": [
    {{
      "content": "<action description>",
      "timedata": "<ISO timestamp or null>"
    }}
  ]
}}

RULES:
- Only extract items requiring future action, decision, or answer
- Do NOT extract pure observations or completed past events
- For timedata: use the EXACT "parsed" value from TIMEPOINTS (e.g., "2025-10-25T00:00:00")
- Match prospective items to timepoints by reading the note carefully
- If no prospective items found, return {{"contains_prospective": false, "prospective_items": []}}

Return ONLY the JSON object:"""

    llm = get_llm()

    try:
        # Track LLM call for audit
        with track_llm_call('prospective_extraction', prompt) as tracker:
            response = await llm.ainvoke(prompt)
            tracker.set_response(response)

            result = json.loads(response.content)
            tracker.set_parsed_output(result)

        # Ensure required fields exist
        result.setdefault("contains_prospective", False)
        result.setdefault("prospective_items", [])

        # Validate item structure
        for item in result.get("prospective_items", []):
            item.setdefault("content", "")
            item.setdefault("timedata", None)

        return result

    except Exception as e:
        # Fallback on error
        return {
            "contains_prospective": False,
            "prospective_items": [],
            "error": str(e)
        }
