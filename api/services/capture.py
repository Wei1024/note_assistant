"""
Note Classification Service
Direct LLM-based classification (no agent overhead for fast performance)
"""
import json
from langchain_core.tools import tool
from ..config import VALID_FOLDERS, WORKING_FOLDERS, CLASSIFICATION_CONFIDENCE_THRESHOLD
from ..llm import get_llm
from ..llm.prompts import Prompts


def _determine_needs_review(result: dict, raw_text: str) -> tuple[bool, list[str]]:
    """Heuristic-based review flagging (no fake LLM confidence)

    Returns:
        (needs_review, reasons) tuple
    """
    reasons = []

    # Heuristic 1: Very short text (ambiguous)
    if len(raw_text.strip()) < 15:
        reasons.append("Text too short")

    # Heuristic 2: LLM expressed uncertainty
    reasoning = result.get("reasoning", "").lower()
    uncertainty_keywords = ["unsure", "could be", "might be", "unclear", "ambiguous", "uncertain"]
    if any(keyword in reasoning for keyword in uncertainty_keywords):
        reasons.append("LLM expressed uncertainty")

    # Heuristic 3: Fallback classification
    if "defaulted" in reasoning or "fallback" in reasoning or "failed" in reasoning:
        reasons.append("Fallback classification used")

    # Heuristic 4: No dimensions set (weak classification)
    dimensions = result.get("dimensions", {})
    if isinstance(dimensions, dict) and not any(dimensions.values()):
        reasons.append("No clear dimensions identified")

    return len(reasons) > 0, reasons

# LLM client now imported from api.llm

@tool
def classify_note(raw_text: str) -> dict:
    """Classify a note using multi-dimensional analysis.

    NOTE: This synchronous version is kept for future agent integration.
    For production FastAPI endpoints, use classify_note_async() instead.

    Args:
        raw_text: The raw note content to classify

    Returns:
        Dictionary with title, tags, status, dimensions (boolean flags)
    """
    llm = get_llm()  # Use singleton instance
    # Use centralized prompt from llm/prompts.py
    from ..llm.prompts import Prompts
    prompt = Prompts.CLASSIFY_NOTE.format(text=raw_text)

    try:
        response = llm.invoke(prompt)
        result = json.loads(response.content)

        # Extract dimensions from LLM response
        dimensions = result.get("dimensions", {})

        # Validate dimensions structure
        default_dimensions = {
            "has_action_items": False,
            "is_social": False,
            "is_emotional": False,
            "is_knowledge": False,
            "is_exploratory": False
        }

        # Merge with defaults
        for key in default_dimensions:
            if key not in dimensions:
                dimensions[key] = default_dimensions[key]

        result["dimensions"] = dimensions

        # Validate status field - ONLY for notes with action items
        status = result.get("status")
        if status == "null":
            status = None

        if dimensions.get("has_action_items"):
            valid_statuses = ["todo", "in_progress", "done", None]
            if status not in valid_statuses:
                status = "todo"
        else:
            status = None

        result["status"] = status

        # Ensure required fields
        result.setdefault("title", raw_text.split("\n")[0][:60])
        result.setdefault("tags", [])

        return result

    except Exception as e:
        # Fallback on error
        return {
            "title": raw_text.split("\n")[0][:60],
            "dimensions": {
                "has_action_items": False,
                "is_social": False,
                "is_emotional": True,  # Safe fallback
                "is_knowledge": False,
                "is_exploratory": False
            },
            "tags": [],
            "status": None,
            "error": str(e)
        }


async def classify_note_async(raw_text: str) -> dict:
    """Async version of classify_note for FastAPI endpoints.

    Provides better performance by not blocking the event loop.

    Returns multi-dimensional classification - dimensions determine everything.

    Args:
        raw_text: The raw note content to classify

    Returns:
        Dictionary with title, tags, status, dimensions (boolean flags)
    """
    llm = get_llm()  # Use singleton instance from api.llm
    prompt = Prompts.CLASSIFY_NOTE.format(text=raw_text)

    try:
        response = await llm.ainvoke(prompt)  # Async call
        result = json.loads(response.content)

        # Extract dimensions from LLM response
        dimensions = result.get("dimensions", {})

        # Validate dimensions structure - ensure all keys present
        default_dimensions = {
            "has_action_items": False,
            "is_social": False,
            "is_emotional": False,
            "is_knowledge": False,
            "is_exploratory": False
        }

        # Merge with defaults (in case LLM missed some)
        for key in default_dimensions:
            if key not in dimensions:
                dimensions[key] = default_dimensions[key]

        result["dimensions"] = dimensions

        # Validate status field - ONLY for notes with action items
        status = result.get("status")
        if status == "null":
            status = None

        if dimensions.get("has_action_items"):
            # Validate status for actionable notes
            valid_statuses = ["todo", "in_progress", "done", None]
            if status not in valid_statuses:
                status = "todo"  # Default to todo for action items
        else:
            # Non-actionable notes should NOT have status
            status = None

        result["status"] = status

        # Ensure required fields
        result.setdefault("title", raw_text.split("\n")[0][:60])
        result.setdefault("tags", [])
        result.setdefault("reasoning", "")

        # Heuristic-based review flagging (no fake confidence)
        needs_review, review_reasons = _determine_needs_review(result, raw_text)
        result["needs_review"] = needs_review
        if review_reasons:
            result["reasoning"] = result.get("reasoning", "") + " | Review: " + "; ".join(review_reasons)

        return result

    except Exception as e:
        # Fallback on error - default to all dimensions false
        return {
            "title": raw_text.split("\n")[0][:60],
            "dimensions": {
                "has_action_items": False,
                "is_social": False,
                "is_emotional": True,  # Assume emotional/journal as safe fallback
                "is_knowledge": False,
                "is_exploratory": False
            },
            "tags": [],
            "status": None,
            "reasoning": f"Classification failed: {str(e)}",
            "needs_review": True,
            "error": str(e)
        }
