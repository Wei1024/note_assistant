"""
Note Enrichment Service
Extracts multi-dimensional metadata from classified notes
"""
import json
from datetime import datetime
from ..llm import get_llm
from ..llm.prompts import Prompts
from ..config import WORKING_FOLDERS


def _iso_now():
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


async def enrich_note_metadata(text: str, primary_classification: dict) -> dict:
    """Extract multi-dimensional metadata from a note.

    Args:
        text: Raw note content
        primary_classification: Result from classify_note_async()
            Must contain: folder, title, tags

    Returns:
        Dictionary with:
        - has_action_items: Boolean - contains actionable todos/tasks
        - is_social: Boolean - involves conversations with people
        - is_emotional: Boolean - expresses feelings/emotions
        - is_knowledge: Boolean - contains learnings/reference material
        - is_exploratory: Boolean - brainstorming/"what if" thinking
        - people: List of person names/objects mentioned
        - entities: List of concepts, tools, projects, topics (merged)
        - emotions: List of emotional markers
        - time_references: List of dates, deadlines, events
        - reasoning: Brief explanation of extraction
    """
    llm = get_llm()
    primary_folder = primary_classification.get("folder", "journal")
    prompt = Prompts.ENRICH_METADATA.format(text=text, primary_folder=primary_folder)

    try:
        response = await llm.ainvoke(prompt)
        result = json.loads(response.content)

        # Ensure all boolean dimensions exist
        result.setdefault("has_action_items", False)
        result.setdefault("is_social", False)
        result.setdefault("is_emotional", False)
        result.setdefault("is_knowledge", False)
        result.setdefault("is_exploratory", False)

        # Ensure all arrays exist
        result.setdefault("people", [])
        result.setdefault("entities", [])
        result.setdefault("emotions", [])
        result.setdefault("time_references", [])
        result.setdefault("reasoning", "")

        return result

    except Exception as e:
        # Return empty enrichment on error
        return {
            "has_action_items": False,
            "is_social": False,
            "is_emotional": False,
            "is_knowledge": False,
            "is_exploratory": False,
            "people": [],
            "entities": [],
            "emotions": [],
            "time_references": [],
            "reasoning": f"Enrichment failed: {str(e)}",
            "error": str(e)
        }


def store_enrichment_metadata(note_id: str, enrichment: dict, db_connection):
    """Store enrichment metadata in database tables using repository.

    Args:
        note_id: Note ID to associate metadata with
        enrichment: Result from enrich_note_metadata()
        db_connection: SQLite connection object
    """
    from ..repositories import graph_repo

    # Use repository to batch store all enrichment metadata
    graph_repo.store_enrichment(note_id, enrichment, db_connection)
