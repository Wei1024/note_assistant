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
    - Tags: User-created hashtags (extracted from text, no LLM)

    Args:
        text: Raw note content
        current_date: Current date for resolving relative times (ISO format)

    Returns:
        {
            "who": ["Sarah", "Tom"],
            "what": ["FAISS", "vector search"],
            "where": ["Café Awesome"],
            "when": [{"original": "tomorrow", "parsed": "2025-10-21T14:00:00", "type": "relative"}],
            "tags": ["project/alpha", "sprint/planning"],  # Extracted from #hashtags
            "title": "Generated title"
        }
    """
    if current_date is None:
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M %Z')

    # Step 1: Extract WHO/WHAT/WHERE/title with LLM (episodic extraction)
    entities = await _extract_entities_llm(text, current_date)

    # Step 2: Extract WHEN with dateparser (more accurate than LLM)
    time_references = _extract_time_references(text, current_date)

    # Step 3: Extract user hashtags from text (no LLM - user-controlled)
    tags = extract_hashtags_from_text(text)

    return {
        "who": entities.get("who", []),
        "what": entities.get("what", []),
        "where": entities.get("where", []),
        "when": time_references,
        "tags": tags,
        "title": entities.get("title", text.split("\n")[0][:60])
    }


async def _extract_entities_llm(text: str, current_date: str) -> Dict[str, Any]:
    """Extract WHO/WHAT/WHERE entities using LLM (optimized for small local models).

    Separate from tag extraction for better focus and accuracy.
    Avoids few-shot examples to prevent hallucination in small models.
    """
    prompt = f"""Extract people, topics, and locations from this note.

TODAY'S DATE: {current_date} (Pacific Time)

NOTE TEXT:
{text}

INSTRUCTIONS:
1. WHO: Extract names of people and organizations mentioned in the note
2. WHAT: Extract specific concepts, technologies, or topics mentioned
3. WHERE: Extract physical places, virtual locations, or meeting contexts
4. TITLE: Generate a short descriptive title (max 10 words)

RULES:
- Only extract entities EXPLICITLY mentioned in the text
- Use empty arrays if nothing found
- Return valid JSON only

OUTPUT FORMAT:
{{
  "who": [],
  "what": [],
  "where": [],
  "title": ""
}}

Your JSON response:"""

    llm = get_llm()

    try:
        # Track LLM call for audit
        with track_llm_call('entity_extraction', prompt) as tracker:
            response = await llm.ainvoke(prompt)
            tracker.set_response(response)

            result = json.loads(response.content)
            tracker.set_parsed_output(result)

        # Ensure all required fields exist
        result.setdefault("who", [])
        result.setdefault("what", [])
        result.setdefault("where", [])
        result.setdefault("title", text.split("\n")[0][:60])

        return result

    except Exception as e:
        # Fallback on error
        return {
            "who": [],
            "what": [],
            "where": [],
            "title": text.split("\n")[0][:60],
            "error": str(e)
        }


def extract_hashtags_from_text(text: str) -> List[str]:
    """Extract user hashtags from note text.

    Supports:
    - Flat tags: #personal, #urgent, #meeting
    - Hierarchical tags (2-3 levels): #project/alpha, #client/acme/project

    Design:
    - Pure text parsing (no LLM calls)
    - User-controlled taxonomy
    - Supports batch operations (future)

    Pattern: #[alphanumeric_-]+(/[alphanumeric_-]+)*
    - Allows: letters, numbers, underscores, hyphens
    - Hierarchy delimiter: /
    - Max practical depth: 3 (soft limit, UI encourages 2)

    Examples:
        "#project/alpha and #sprint/planning" → ["project/alpha", "sprint/planning"]
        "#personal #health/fitness" → ["personal", "health/fitness"]
        "#work-stuff #client-acme" → ["work-stuff", "client-acme"]

    Args:
        text: Note content with embedded #hashtags

    Returns:
        List of unique tag names (without # prefix)
    """
    # Regex pattern for hashtags with optional hierarchy
    # Matches: #tag or #parent/child or #grandparent/parent/child
    # Allows: a-z A-Z 0-9 _ - (no spaces)
    pattern = r'#([a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*)'

    matches = re.findall(pattern, text)

    # Deduplicate while preserving order (for consistency)
    seen = set()
    unique_tags = []
    for tag in matches:
        tag_lower = tag.lower()  # Case-insensitive deduplication
        if tag_lower not in seen:
            seen.add(tag_lower)
            unique_tags.append(tag_lower)

    return unique_tags


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
