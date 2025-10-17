"""
Centralized LLM Prompts
All prompt templates in one place for easy management and versioning
"""


class Prompts:
    """Container for all LLM prompt templates"""

    # ========================================================================
    # CLASSIFICATION PROMPTS
    # ========================================================================

    CLASSIFY_NOTE = """You are a note classifier using multi-dimensional analysis. Analyze this note and return JSON.

Note: {text}

Return ONLY valid JSON:
{{
  "title": "Short descriptive title (max 10 words)",
  "dimensions": {{
    "has_action_items": true|false,
    "is_social": true|false,
    "is_emotional": true|false,
    "is_knowledge": true|false,
    "is_exploratory": true|false
  }},
  "reasoning": "Brief explanation of dimension choices",
  "tags": ["tag1", "tag2", "tag3"],
  "status": "todo|in_progress|done|null"
}}

Dimension Guide (Multi-dimensional Classification):

**has_action_items** (Executive Function)
- Contains actionable items, todos, or tasks with clear completion state
- ONLY notes with action items can have status (todo/in_progress/done)
- Examples: "Fix login bug", "Call Sarah tomorrow", "Deploy to production", "Buy groceries"
- If it has a checkbox or implies something to DO, set this true

**is_social** (Social Cognition)
- Involves conversations, meetings, discussions with other people
- Captures WHO you interacted with
- Examples: "Met with Sarah about research", "Team standup", "1-on-1 with manager", "Coffee chat"
- Can be true WITH has_action_items (e.g., "Meeting with Sarah - action: follow up on proposal")

**is_emotional** (Emotional Processing)
- Expresses personal feelings, reflections, emotional states
- Captures HOW you feel
- Examples: "Feeling overwhelmed today", "Grateful for support", "Excited about new project"
- Can be true WITH other dimensions (e.g., "Frustrated with this bug" = emotional + has_action_items)

**is_knowledge** (Procedural Memory)
- Contains learnings, how-tos, reference information, evergreen knowledge
- Information you'll want to reference later
- Examples: "How Postgres EXPLAIN works", "Python async patterns", "Notes from research paper"
- Can be true WITH other dimensions (e.g., meeting notes that teach you something)

**is_exploratory** (Creative Exploration)
- Brainstorms, hypotheses, "what if" thoughts, open-ended exploration
- Thinking mode, not execution mode
- Examples: "Could we use Redis?", "Product idea: bulk export", "Hypothesis about user behavior"
- Can be true WITH has_action_items (e.g., "Explore Redis - TODO: benchmark it")

Classification Rules:
1. Multiple dimensions can be TRUE simultaneously (notes are multi-faceted!)
2. If a note has actionable todos/checkboxes, has_action_items MUST be true
3. Status field ONLY valid when has_action_items=true
4. When uncertain, explain in reasoning
5. Be conservative - only set dimensions that are CLEARLY present

Tags should be lowercase, 3-6 relevant keywords.

JSON:"""

    # ========================================================================
    # ENRICHMENT PROMPTS
    # ========================================================================

    ENRICH_METADATA = """Extract metadata from this note for search and knowledge graph.

Note: {text}
Context: {primary_context}

Extract boolean dimensions (same as classification) and entities:

**people**: Person names with optional role/relation
- Format: {{"name": "...", "role": "...", "relation": "..."}}
- Extract ALL names, even casual mentions

**entities**: Concepts, tools, projects, topics mentioned
- Be specific: "FAISS", "memory consolidation", "Python"
- Don't categorize, just extract what's present

**emotions**: Feeling words if clearly expressed
- Examples: excited, frustrated, anxious, grateful

**time_references**: Dates, deadlines, meetings
- Format: {{"type": "meeting|deadline", "datetime": null, "description": "..."}}

Example output format:
{{{{
  "has_action_items": false,
  "is_social": true,
  "is_emotional": false,
  "is_knowledge": true,
  "is_exploratory": false,
  "people": [{{{{"name": "Sarah", "role": "researcher", "relation": "expert"}}}}],
  "entities": ["memory consolidation", "hippocampus"],
  "emotions": [],
  "time_references": [],
  "reasoning": "Brief explanation"
}}}}

Rules:
- Extract only what's CLEARLY present (empty arrays OK)
- Multiple dimensions can be true
- Return ONLY JSON with: 5 dimensions, people, entities, emotions, time_references, reasoning

JSON:"""

    # ========================================================================
    # SEARCH PROMPTS
    # ========================================================================

    PARSE_SEARCH_QUERY = """## Identity

You are a search query parser for a brain-based note-taking system. Your goal is to extract structured filters from natural language queries to enable precise multi-dimensional search.

User query: "{query}"

---

## Extraction Guidelines

Extract the following filters from the query:

### person
Proper name of a person mentioned in the query.
- Extract proper names only (e.g., "Sarah", "Alex", "John")
- Example: "notes with Sarah" → person = "Sarah"

### emotion
Feeling or mood word expressed in the query.
- Extract any emotion or feeling word the user mentions
- Common examples: excited, frustrated, curious, worried, happy, anxious, grateful, overwhelmed, proud, confused
- But not limited to these - extract whatever emotion is mentioned
- Example: "notes where I felt excited" → emotion = "excited"

### entity
Specific named thing being searched.
- Extract when user searches for a specific tool, concept, project, or topic
- Examples:
  - "notes about FAISS" → entity = "FAISS"
  - "vector search project" → entity = "vector search"
  - "notes about Python" → entity = "Python"

### context
Dimension context to search within (maps to boolean dimension flags).
- Valid values ONLY: tasks, meetings, ideas, reference, journal
- Extract only if one of these is explicitly mentioned
- Example: "meetings about AWS" → context = "meetings"

### text_query
Core searchable keywords for full-text search.
- Extract ONLY the main subject/topic being searched
- **Remove filler words**: "about", "discussions", "I remember", "there are", "some", "what", "did I"
- **Keep core concepts**: The actual nouns and key terms
- Examples:
  - "discussions about memory" → text_query = "memory"
  - "I remember some notes about vector search" → text_query = "vector search"
  - "what did I write about databases?" → text_query = "databases"

### sort
Time-based sorting preference.
- Values: "recent" or "oldest"
- Extract only if explicitly mentioned (words like "recent", "latest", "newest", "oldest", "earliest")
- Example: "recent notes with Sarah" → sort = "recent"

---

## Examples

**Example 1 - Person search:**

Input: "what's the recent project I did with Sarah"

Output:
{{{{
  "person": "Sarah",
  "entity": "project",
  "sort": "recent",
  "text_query": null,
  "emotion": null,
  "context": null
}}}}

**Example 2 - Emotion + entity search:**

Input: "notes where I felt excited about FAISS"

Output:
{{{{
  "emotion": "excited",
  "entity": "FAISS",
  "text_query": null,
  "person": null,
  "context": null,
  "sort": null
}}}}

**Example 3 - Context + entity search:**

Input: "meetings about AWS infrastructure"

Output:
{{{{
  "context": "meetings",
  "entity": "AWS",
  "text_query": null,
  "person": null,
  "emotion": null,
  "sort": null
}}}}

**Example 4 - Text query with filler words:**

Input: "I remember there are some discussions about memory"

Output:
{{{{
  "text_query": "memory",
  "person": null,
  "emotion": null,
  "entity": null,
  "context": null,
  "sort": null
}}}}

**Example 5 - Multiple keywords:**

Input: "discussions about memory consolidation"

Output:
{{{{
  "text_query": "memory consolidation",
  "person": null,
  "emotion": null,
  "entity": null,
  "context": null,
  "sort": null
}}}}

**Example 6 - Question format:**

Input: "what sport did I watch?"

Output:
{{{{
  "text_query": "sport",
  "person": null,
  "emotion": null,
  "entity": null,
  "context": null,
  "sort": null
}}}}

**Example 7 - Entity + additional text:**

Input: "notes about AWS and cloud infrastructure"

Output:
{{{{
  "entity": "AWS",
  "text_query": "cloud infrastructure",
  "person": null,
  "emotion": null,
  "context": null,
  "sort": null
}}}}

---

## Important Notes

**Core principle for text_query:**
Extract the CORE searchable terms that represent what the user wants to find. Strip away conversational filler words. Keep only the actual subject being searched.

**Entity extraction guideline:**
Only extract entity when it's a clear, specific named thing (like "FAISS", "AWS", "Docker"). Generic concepts like "memory" or "search" should go in text_query instead.

**Emotions are flexible:**
Extract any emotion word the user mentions. Don't limit yourself to a predefined list.

**Context is strict:**
Only extract context if it matches one of the five valid dimension contexts: tasks, meetings, ideas, reference, journal.

**Use null for missing fields:**
If a filter is not clearly present in the query, return null for that field. Do not invent or assume information.

**Return format:**
Return ONLY the JSON object with all six fields (person, emotion, entity, context, text_query, sort). No additional text or explanation.

JSON:"""

    # ========================================================================
    # SYNTHESIS PROMPTS
    # ========================================================================

    SYNTHESIZE_NOTES = """You are a note synthesis assistant. The user asked: "{query}"

I found {notes_count} relevant notes. Please provide a concise summary answering their question based on these notes.

{notes_context}

---

Instructions:
1. Directly answer the user's question: "{query}"
2. Synthesize information across all notes (don't just list them)
3. Highlight key findings, people, concepts, or insights
4. Keep the summary focused and concise (2-4 paragraphs max)
5. If multiple notes contradict each other, acknowledge different perspectives
6. Reference specific notes when relevant (e.g., "Note 1 mentions...")

Summary:"""

    # ========================================================================
    # CONSOLIDATION PROMPTS
    # ========================================================================

    SUGGEST_LINKS = """You are a knowledge graph linker. Analyze connections between notes.

NEW NOTE:
{new_note_text}

EXISTING NOTES:
{candidates_text}

Task: Which existing notes should link to the new note? Analyze ALL at once.

Link Types:
- **related**: Discusses same topic/concept
- **spawned**: New note is follow-up/action from old note
- **references**: New note builds on old note's idea
- **contradicts**: New note challenges old note's conclusion

Rules:
1. Only include if CLEAR connection (shared specific concept/person/project/decision)
2. Use the "Overlap" statistics as context - higher overlap suggests stronger potential connection
3. Reason must be specific (not "both mention topics")
4. Max 5 links total (prioritize strongest)
5. Must use exact note ID from brackets above
6. Trust your judgment - if overlap is high but semantic meaning differs, skip it

Return ONLY a JSON array (even if empty or single link):

Examples:
- Multiple links:
[
  {{"id": "2025-01-10T14:30:00-08:00_abc1", "link_type": "spawned", "reason": "New note is action item from this meeting"}},
  {{"id": "2025-01-09T10:15:00-08:00_def2", "link_type": "references", "reason": "Builds on the memory consolidation research discussed here"}}
]

- Single link:
[
  {{"id": "2025-01-08T09:00:00-08:00_ghi3", "link_type": "related", "reason": "Both discuss Sarah's research on hippocampus function"}}
]

- No links:
[]

JSON:"""
