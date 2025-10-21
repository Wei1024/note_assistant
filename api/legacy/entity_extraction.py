"""
Entity Extraction Service
Provides two approaches: Pure LLM vs Hybrid NLP+LLM
"""
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import dateparser


async def extract_entities_llm(text: str, current_date: str = None) -> Dict[str, Any]:
    """Extract WHO/WHAT/WHEN/WHERE using pure LLM approach.

    Args:
        text: Note content
        current_date: Current date for resolving relative dates (ISO format)

    Returns:
        {
            "who": ["Sarah", "Tom"],
            "what": ["FAISS", "vector search"],
            "when": [{"original": "tomorrow", "parsed": "2025-10-21T14:00:00", "type": "relative"}],
            "where": ["Café Awesome"],
            "execution_time_ms": 1200
        }
    """
    from ..llm import get_llm

    if current_date is None:
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M %Z')

    prompt = f"""Extract entities from this note for knowledge graph clustering.

TODAY'S DATE (for resolving relative times): {current_date} (Pacific Time)

NOTE TEXT TO ANALYZE:
{text}

EXTRACT THESE ENTITIES FROM THE NOTE TEXT ABOVE:

1. **WHO** (people/organizations):
   - Extract proper names of people and organizations
   - Normalize capitalization (e.g., "sarah" → "Sarah")
   - Output: List of strings

2. **WHAT** (topics/concepts/projects/objects):
   - Extract key concepts, technologies, projects, topics
   - Be granular: separate compound concepts into individual entities
   - Keep multi-word if they're compound nouns
   - Include specific tools, technologies, projects mentioned
   - Output: List of strings

3. **WHEN** (time/date references):
   - Extract ALL time references (dates, times, deadlines, durations, recurring events)
   - For each time reference provide:
     - "original": Exact text as written
     - "parsed": ISO 8601 format (YYYY-MM-DDTHH:MM:SS) if parseable, null otherwise
     - "type": "absolute" (specific date/time), "relative" (future/past reference), "duration" (time span), "recurring" (repeating)
   - Resolve relative dates based on current date context
   - Output: List of objects

4. **WHERE** (locations - physical/virtual/contextual):
   - Extract locations mentioned (physical places, virtual places, meeting contexts)
   - Keep verbatim as written
   - Output: List of strings

**Output format** (JSON only, no explanation):

```json
{{
  "who": ["<person_name_1>", "<person_name_2>"],
  "what": ["<concept_1>", "<concept_2>", "<technology_1>"],
  "when": [
    {{"original": "<time_reference_as_written>", "parsed": "<ISO_format_or_null>", "type": "<absolute|relative|duration|recurring>"}}
  ],
  "where": ["<location_1>"]
}}
```

**CRITICAL RULES**:
- Extract ONLY entities that are EXPLICITLY MENTIONED in the note text above
- Do NOT copy these placeholder examples - they are just format templates
- Empty arrays are REQUIRED if nothing is found in the note
- Examples of correct empty responses:
  - If no people mentioned: {{"who": []}}
  - If no time references: {{"when": []}}
  - If nothing found at all: {{"who": [], "what": [], "when": [], "where": []}}

Return ONLY the JSON object with real entities from the note text:"""

    start_time = datetime.now()

    try:
        llm = get_llm()
        response = await llm.ainvoke(prompt)
        result = json.loads(response.content)

        # Ensure all keys exist
        result.setdefault("who", [])
        result.setdefault("what", [])
        result.setdefault("when", [])
        result.setdefault("where", [])

        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        result["execution_time_ms"] = execution_time

        return result

    except Exception as e:
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return {
            "who": [],
            "what": [],
            "when": [],
            "where": [],
            "execution_time_ms": execution_time,
            "error": str(e)
        }


def extract_entities_hybrid(text: str, current_date: str = None) -> Dict[str, Any]:
    """Extract WHO/WHAT/WHEN/WHERE using hybrid NLP approach.

    Uses traditional NLP libraries:
    - spaCy for named entity recognition (WHO/WHERE)
    - dateparser for time extraction (WHEN)
    - Regex for action verbs and patterns
    - Simple keyword extraction for WHAT (no LLM)

    Args:
        text: Note content
        current_date: Current date for resolving relative dates

    Returns:
        Same format as extract_entities_llm
    """
    start_time = datetime.now()

    if current_date is None:
        current_date_obj = datetime.now()
    else:
        current_date_obj = datetime.fromisoformat(current_date.split()[0])

    result = {
        "who": [],
        "what": [],
        "when": [],
        "where": []
    }

    try:
        # WHO: Extract people names using spaCy
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(text)

            # Extract PERSON entities
            people = []
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    # Normalize: capitalize properly
                    name = ent.text.strip()
                    if name and name not in people:
                        people.append(name)

            result["who"] = people

            # WHERE: Extract locations (GPE, LOC, FAC)
            locations = []
            for ent in doc.ents:
                if ent.label_ in ["GPE", "LOC", "FAC"]:
                    loc = ent.text.strip()
                    if loc and loc not in locations:
                        locations.append(loc)

            result["where"] = locations

        except Exception as spacy_error:
            # spaCy not available or failed
            result["who"] = []
            result["where"] = []

        # WHEN: Extract time references using dateparser
        time_patterns = [
            r'\b(?:tomorrow|today|yesterday|tonight)\b(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)?\b',
            r'\b(?:next|last)\s+(?:week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?\b(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)?',
            r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)\b',
            r'\b(?:end of|start of)\s+(?:month|week|year|day)\b',
            r'\bFriday\b',
            r'\bTuesday\b',
            r'\b\d+\s+hours?\b',
            r'\bweekly\b',
        ]

        time_refs = []
        for pattern in time_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                time_text = match.group(0)

                # Try to parse with dateparser
                parsed_date = dateparser.parse(
                    time_text,
                    settings={
                        'RELATIVE_BASE': current_date_obj,
                        'TIMEZONE': 'America/Los_Angeles',
                        'RETURN_AS_TIMEZONE_AWARE': False
                    }
                )

                # Determine type
                time_type = "absolute"
                if any(word in time_text.lower() for word in ["tomorrow", "next", "today", "yesterday", "last"]):
                    time_type = "relative"
                elif "hours" in time_text.lower() or "minutes" in time_text.lower():
                    time_type = "duration"
                elif "weekly" in time_text.lower() or "daily" in time_text.lower():
                    time_type = "recurring"

                time_ref = {
                    "original": time_text,
                    "parsed": parsed_date.isoformat() if parsed_date else None,
                    "type": time_type
                }

                # Avoid duplicates
                if time_ref not in time_refs:
                    time_refs.append(time_ref)

        result["when"] = time_refs

        # WHAT: Simple keyword extraction using noun chunks from spaCy
        try:
            # Extract noun phrases and named entities (excluding PERSON)
            concepts = []

            # Get all non-person named entities
            for ent in doc.ents:
                if ent.label_ not in ["PERSON", "GPE", "LOC", "FAC", "DATE", "TIME"]:
                    concept = ent.text.strip()
                    if concept and len(concept) > 2 and concept not in concepts:
                        concepts.append(concept)

            # Get key noun chunks (simplified - take multi-word nouns)
            for chunk in doc.noun_chunks:
                # Skip pronouns and very short chunks
                if chunk.root.pos_ == "NOUN" and len(chunk.text) > 3:
                    concept = chunk.text.strip()
                    # Clean up
                    concept = re.sub(r'^(the|a|an|my|your|this|that)\s+', '', concept, flags=re.IGNORECASE)
                    if concept and len(concept) > 2 and concept not in concepts:
                        # Limit to reasonable length
                        if len(concept.split()) <= 4:
                            concepts.append(concept)

            result["what"] = concepts[:15]  # Limit to top 15 to avoid noise

        except Exception as concept_error:
            result["what"] = []

    except Exception as e:
        result["error"] = str(e)

    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
    result["execution_time_ms"] = execution_time

    return result
