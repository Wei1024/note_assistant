"""
Note Enrichment Service
Extracts multi-dimensional metadata from classified notes
"""
import json
from datetime import datetime
from .capture_service import get_llm
from .config import WORKING_FOLDERS


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
        - dimensions: List of secondary contexts
        - entities: Dict of people, topics, projects, technologies
        - suggested_links: List of note IDs that might be related
        - emotional_markers: Detected emotions/moods
    """
    llm = get_llm()

    primary_folder = primary_classification.get("folder", "journal")

    prompt = f"""You are a metadata extraction agent. Analyze this note and extract multi-dimensional metadata.

Note content: {text}

Primary classification: {primary_folder}

Extract ONLY valid JSON:
{{
  "secondary_contexts": ["tasks", "ideas", "reference"],
  "people": [
    {{"name": "Sarah", "role": "psychology researcher", "relation": "expert contact"}}
  ],
  "topics": ["human memory", "psychology", "note-taking"],
  "projects": ["note-taking app"],
  "technologies": ["LLM", "SQLite"],
  "emotions": ["excited", "curious"],
  "time_references": [
    {{"type": "meeting", "datetime": "2025-10-11T15:00:00", "description": "meeting with Sarah"}}
  ],
  "reasoning": "Brief explanation of why these entities were extracted"
}}

**Extraction Guidelines**:

1. **secondary_contexts**: What OTHER cognitive contexts does this note touch?
   - Primary folder: {primary_folder}
   - Look for ADDITIONAL contexts beyond primary
   - Example: A meeting note (primary: meetings) might also be an idea or reference
   - Only include if truly relevant

2. **people**: Extract person names mentioned
   - Include role/expertise if mentioned
   - Include relationship context if clear
   - Format: {{"name": "...", "role": "...", "relation": "..."}}

3. **topics**: Key concepts, subjects, domains discussed
   - Specific enough to be useful for search
   - Examples: "machine learning", "productivity", "SQLite FTS5"

4. **projects**: Named projects or ongoing initiatives
   - Must be explicitly named or clearly identifiable
   - Examples: "note-taking app", "website redesign", "Q4 planning"

5. **technologies**: Tools, frameworks, languages, platforms
   - Only if explicitly mentioned
   - Examples: "Python", "FastAPI", "Postgres", "Docker"

6. **emotions**: Emotional markers or mood indicators
   - Look for feeling words: excited, frustrated, anxious, grateful
   - Only if clearly expressed

7. **time_references**: Dates, times, deadlines, scheduled events
   - Parse into structured format when possible
   - Types: meeting, deadline, reminder, event
   - Include ISO datetime if parseable

**Important**:
- Only extract entities that are CLEARLY present in the text
- Don't infer or assume information
- Empty arrays are fine if nothing found
- Be conservative - better to miss than hallucinate

JSON:"""

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
        result.setdefault("topics", [])
        result.setdefault("projects", [])
        result.setdefault("technologies", [])
        result.setdefault("emotions", [])
        result.setdefault("time_references", [])
        result.setdefault("reasoning", "")

        return result

    except Exception as e:
        # Return empty enrichment on error
        return {
            "secondary_contexts": [],
            "people": [],
            "topics": [],
            "projects": [],
            "technologies": [],
            "emotions": [],
            "time_references": [],
            "reasoning": f"Enrichment failed: {str(e)}",
            "error": str(e)
        }


def store_enrichment_metadata(note_id: str, enrichment: dict, db_connection):
    """Store enrichment metadata in database tables using graph.py helpers.

    Args:
        note_id: Note ID to associate metadata with
        enrichment: Result from enrich_note_metadata()
        db_connection: SQLite connection object
    """
    from .graph import index_note_with_enrichment

    # Use graph.py helper to batch store all enrichment metadata
    index_note_with_enrichment(note_id, enrichment, db_connection)
