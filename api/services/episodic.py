"""
Episodic Layer - Entity Extraction Service
Extracts WHO/WHAT/WHEN/WHERE from notes using validated hybrid approach.

Based on entity extraction research (docs/entity_extraction_research.md):
- LLM for WHO/WHAT/WHERE (0.691-0.933 F1 scores)
- dateparser for WHEN (0.944 F1 score)
"""
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import dateparser
import parsedatetime as pdt
from ..llm import get_llm
from ..llm.audit import track_llm_call

# Parsedatetime calendar instance (module-level for reuse)
_pdt_calendar = None

def _get_parsedatetime_calendar():
    """Get or create parsedatetime calendar instance."""
    global _pdt_calendar
    if _pdt_calendar is None:
        _pdt_calendar = pdt.Calendar()
    return _pdt_calendar


async def extract_episodic_metadata(text: str, current_date: str = None) -> Dict[str, Any]:
    """Extract episodic metadata from note text.

    Extracts:
    - WHO: People, organizations (LLM)
    - WHAT: Concepts, topics, entities (LLM)
    - WHERE: Locations - physical/virtual/contextual (LLM)
    - WHEN: Time references (dateparser)
    - Tags: Broader thematic categories (LLM)

    Args:
        text: Raw note content
        current_date: Current date for resolving relative times (ISO format)

    Returns:
        {
            "who": ["Sarah", "Tom"],
            "what": ["FAISS", "vector search"],
            "where": ["Café Awesome"],
            "when": [{"original": "tomorrow", "parsed": "2025-10-21T14:00:00", "type": "relative"}],
            "tags": ["meeting", "ai-research"],
            "title": "Generated title"
        }
    """
    if current_date is None:
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M %Z')

    # Step 1: Extract WHO/WHAT/WHERE/tags with LLM
    entities_and_tags = await _extract_entities_and_tags_llm(text, current_date)

    # Step 2: Extract WHEN with dateparser (more accurate than LLM)
    time_references = _extract_time_references(text, current_date)

    return {
        "who": entities_and_tags.get("who", []),
        "what": entities_and_tags.get("what", []),
        "where": entities_and_tags.get("where", []),
        "when": time_references,
        "tags": entities_and_tags.get("tags", []),
        "title": entities_and_tags.get("title", text.split("\n")[0][:60])
    }


async def _extract_entities_and_tags_llm(text: str, current_date: str) -> Dict[str, Any]:
    """Use LLM to extract WHO/WHAT/WHERE and tags.

    This is the optimal approach from our research:
    - LLM excels at semantic understanding (WHO/WHAT/WHERE)
    - Single call reduces latency
    - Generates title and tags simultaneously
    """
    prompt = f"""Extract entities and metadata from this note.

TODAY'S DATE (for context): {current_date} (Pacific Time)

NOTE TEXT TO ANALYZE:
{text}

EXTRACT THE FOLLOWING FROM THE NOTE TEXT:

1. **WHO** (people/organizations):
   - Extract proper names of people and organizations
   - Include relationship terms like "Mom", "client", "PM"
   - Normalize capitalization
   - Output: List of strings

2. **WHAT** (entities - specific concepts/topics/projects/tools):
   - Extract concrete concepts, technologies, projects, topics
   - Be specific: "Redis", "OAuth2", "vector search"
   - Limit to 5-8 most important entities
   - Output: List of strings

3. **WHERE** (locations - physical/virtual/contextual):
   - Physical places, virtual locations, meeting contexts
   - Examples: "Café Awesome", "Zoom", "team meeting"
   - Output: List of strings

4. **TAGS** (broader thematic categories):
   - High-level themes or categories
   - Examples: "meeting", "security", "ai-research", "planning"
   - 2-4 tags maximum
   - Output: List of strings

5. **TITLE**:
   - Generate a concise, descriptive title (max 10 words)
   - Capture the essence of the note
   - Output: String

**OUTPUT FORMAT** (JSON only, no explanation):

```json
{{
  "who": ["<person_name>"],
  "what": ["<concept_1>", "<concept_2>"],
  "where": ["<location>"],
  "tags": ["<theme_1>", "<theme_2>"],
  "title": "<descriptive_title>"
}}
```

**CRITICAL RULES**:
- Extract ONLY entities EXPLICITLY MENTIONED in the note text
- Do NOT copy these placeholder examples - use real entities from the note
- Empty arrays are REQUIRED if nothing found
- Distinguish entities (specific) from tags (thematic)
- Examples of correct empty responses:
  - If no people: {{"who": []}}
  - If no locations: {{"where": []}}

Return ONLY the JSON object with real entities from the note:"""

    llm = get_llm()

    try:
        # Track LLM call for audit
        with track_llm_call('episodic_extraction', prompt) as tracker:
            response = await llm.ainvoke(prompt)
            tracker.set_response(response)

            result = json.loads(response.content)
            tracker.set_parsed_output(result)

        # Ensure all required fields exist
        result.setdefault("who", [])
        result.setdefault("what", [])
        result.setdefault("where", [])
        result.setdefault("tags", [])
        result.setdefault("title", text.split("\n")[0][:60])

        return result

    except Exception as e:
        # Fallback on error
        return {
            "who": [],
            "what": [],
            "where": [],
            "tags": [],
            "title": text.split("\n")[0][:60],
            "error": str(e)
        }


def _extract_time_references(text: str, current_date: str = None) -> List[Dict[str, Any]]:
    """Extract time references using dateparser (more accurate than LLM).

    From our research: dateparser achieved 0.944 F1 vs LLM's 0.833 F1.
    """
    if current_date is None:
        current_date_obj = datetime.now()
    else:
        current_date_obj = datetime.fromisoformat(current_date.split()[0])

    # Regex patterns for common time expressions
    # ORDER MATTERS: More specific patterns first to avoid overlapping matches
    time_patterns = [
        # Next/this/last + weekday + at + time (combined pattern - must come first!)
        r'\b(?:next|this|last)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)\b',
        # Relative dates with optional times
        r'\b(?:tomorrow|today|yesterday|tonight)\b(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)?\b',
        # Next/last + day/week/month/year (without time)
        r'\b(?:next|this|last)\s+(?:week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        # Month + day with optional time
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?\b(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)?',
        # Standalone times
        r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)\b',
        # End/start of period
        r'\b(?:end of|start of)\s+(?:month|week|year|day)\b',
        # Specific weekdays
        r'\bFriday\b',
        r'\bTuesday\b',
        r'\bMonday\b',
        r'\bWednesday\b',
        r'\bThursday\b',
        r'\bSaturday\b',
        r'\bSunday\b',
        # Duration
        r'\b\d+\s+(?:hours?|minutes?|days?|weeks?|months?)\b',
        # Recurring
        r'\b(?:weekly|daily|monthly|annually)\b',
    ]

    time_refs = []
    seen = set()  # Avoid duplicates (text)
    seen_positions = []  # Avoid overlapping matches (character positions)

    for pattern in time_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            time_text = match.group(0)
            match_start = match.start()
            match_end = match.end()

            # Skip if we've seen this exact text
            if time_text.lower() in seen:
                continue

            # Skip if this match overlaps with a previously matched region
            overlaps = False
            for (prev_start, prev_end) in seen_positions:
                # Check if ranges overlap
                if not (match_end <= prev_start or match_start >= prev_end):
                    overlaps = True
                    break

            if overlaps:
                continue

            seen.add(time_text.lower())
            seen_positions.append((match_start, match_end))

            # Try to parse with dateparser (primary)
            parsed_date = dateparser.parse(
                time_text,
                settings={
                    'RELATIVE_BASE': current_date_obj,
                    'TIMEZONE': 'America/Los_Angeles',
                    'RETURN_AS_TIMEZONE_AWARE': False,
                    'PREFER_DATES_FROM': 'future'  # Prefer future dates for ambiguous weekdays
                }
            )

            # If dateparser failed, try parsedatetime (fallback for "next Tuesday", "this Friday")
            if parsed_date is None:
                cal = _get_parsedatetime_calendar()
                dt, status = cal.parseDT(time_text, sourceTime=current_date_obj)
                if status > 0:  # status > 0 means successful parsing
                    # Fix parsedatetime's 9am default for date-only parses
                    # status == 1 means date only (no time component)
                    if status == 1:
                        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                    parsed_date = dt

            # Determine type
            time_type = "absolute"
            time_lower = time_text.lower()
            if any(word in time_lower for word in ["tomorrow", "next", "today", "yesterday", "last"]):
                time_type = "relative"
            elif any(word in time_lower for word in ["hours", "minutes", "days", "weeks", "months"]):
                time_type = "duration"
            elif any(word in time_lower for word in ["weekly", "daily", "monthly", "annually"]):
                time_type = "recurring"

            # Special handling: Check context for duration patterns
            # If duration appears in past context, set parsed to None
            is_past_duration = False
            if time_type == "duration":
                # Get surrounding context (50 chars before and after)
                context_start = max(0, match_start - 50)
                context_end = min(len(text), match_end + 50)
                context = text[context_start:context_end].lower()

                # Check for past-context indicators
                past_indicators = ["for", "after", "took", "spent", "waited", "lasted"]
                # Check if duration is preceded by past context words
                before_text = text[context_start:match_start].lower()
                if any(indicator in before_text for indicator in past_indicators):
                    is_past_duration = True

            time_ref = {
                "original": time_text,
                "parsed": None if is_past_duration else (parsed_date.isoformat() if parsed_date else None),
                "type": time_type
            }

            time_refs.append(time_ref)

    return time_refs


async def generate_title_from_entities(text: str, metadata: Dict[str, Any]) -> str:
    """Generate a title using entity context (optional enhancement).

    This is called if the LLM-generated title is poor quality.
    Uses the extracted entities to create a better title.
    """
    entities = metadata.get("what", [])
    people = metadata.get("who", [])
    tags = metadata.get("tags", [])

    # Simple heuristic title generation
    if people and entities:
        return f"{', '.join(people[:2])}: {', '.join(entities[:2])}"
    elif entities:
        return ', '.join(entities[:3])
    elif tags:
        return f"{', '.join(tags[:2])}"
    else:
        # Fallback to first line
        return text.split("\n")[0][:60]
