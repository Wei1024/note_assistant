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
        - secondary_contexts: List of additional cognitive contexts
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

        # Validate secondary_contexts against valid folders
        valid_secondary = []
        primary_folder = primary_classification.get("folder")

        for ctx in result.get("secondary_contexts", []):
            if ctx in WORKING_FOLDERS and ctx != primary_folder:
                valid_secondary.append(ctx)

        result["secondary_contexts"] = valid_secondary

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
            "secondary_contexts": [],
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
