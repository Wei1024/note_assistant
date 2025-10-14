"""
Centralized LLM Prompts
All prompt templates in one place for easy management and versioning
"""


class Prompts:
    """Container for all LLM prompt templates"""

    # ========================================================================
    # CLASSIFICATION PROMPTS
    # ========================================================================

    CLASSIFY_NOTE = """You are a note classifier using a brain-based cognitive model. Analyze this note and return JSON.

Note: {text}

Return ONLY valid JSON:
{{
  "title": "Short descriptive title (max 10 words)",
  "folder": "tasks|meetings|ideas|reference|journal",
  "reasoning": "Brief explanation of classification choice",
  "tags": ["tag1", "tag2", "tag3"],
  "first_sentence": "One sentence summary",
  "status": "todo|in_progress|done|null"
}}

Folder Selection Guide (Cognitive Contexts):

**tasks** (Executive Function - Working Memory)
- Actionable items with clear completion state
- ONLY folder that can have status (todo/in_progress/done)
- Examples: "Fix login bug", "Call Sarah tomorrow", "Deploy to production"
- If NOT actionable, it's NOT a task!

**meetings** (Social Cognition - Working Memory)
- Conversations, discussions, standup notes
- Captures WHO + WHEN + WHAT was discussed
- Examples: "Met with Sarah about memory research", "Team standup notes", "1-on-1 with manager"
- NO status field (meetings happened or didn't happen, not todo/done)

**ideas** (Creative Exploration - Working Memory)
- Brainstorms, hypotheses, "what if" thoughts
- Exploration mode, not execution mode
- Examples: "Could we use Redis for caching?", "Product idea: bulk export", "Hypothesis about user behavior"
- NO status field (ideas are explored, not completed)

**reference** (Procedural Memory - Working Memory)
- How-tos, learnings, evergreen knowledge
- Timeless information you'll reference later
- Examples: "How Postgres EXPLAIN works", "Git rebase tutorial", "Python async patterns"
- NO status field (knowledge just exists)

**journal** (Emotional Processing - Limbic System)
- Personal reflections, feelings, thoughts
- Not task-oriented, just being present
- Examples: "Feeling overwhelmed today", "Grateful for team support", "Reflecting on career growth"
- NO status field (emotions aren't tasks)

Classification Rules:
1. If uncertain about classification, explain why in reasoning (e.g., "could be task or idea")
2. Focus on PRIMARY intent (what is this note mainly about?)
3. Status field ONLY valid for "tasks" folder
4. When uncertain between folders, prefer the most actionable context

Tags should be lowercase, 3-6 relevant keywords.

JSON:"""

    # ========================================================================
    # ENRICHMENT PROMPTS
    # ========================================================================

    ENRICH_METADATA = """You are a metadata extraction agent. Analyze this note and extract multi-dimensional metadata.

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

    # ========================================================================
    # SEARCH PROMPTS
    # ========================================================================

    PARSE_SEARCH_QUERY = """Parse this search query and extract structured filters.

User query: "{query}"

Extract any of these filters if clearly present:
- person: Name of person (e.g., "Sarah", "Alex", "John")
- emotion: Feeling word (excited, frustrated, curious, worried, happy, etc.)
- entity_type: Type of thing (project, topic, technology)
- entity_value: The specific project/topic/tech name
- context: Folder type (tasks, meetings, ideas, reference, journal)
- text_query: Remaining keywords for text search (remove extracted filters)
- sort: Time sorting (recent, oldest) if mentioned

Rules:
- Only extract what's CLEARLY present
- For person: Extract proper names only
- For emotion: Extract feeling words
- For entity_type + entity_value: Extract specific projects/topics/technologies
- For context: Match to folder names if mentioned
- For text_query: Remove extracted filters, keep remaining keywords
- Use null for missing fields

Examples:
- "what's the recent project I did with Sarah"
  → {{"person": "Sarah", "entity_type": "project", "sort": "recent", "text_query": null}}

- "notes where I felt excited about FAISS"
  → {{"emotion": "excited", "entity_value": "FAISS", "entity_type": "topic", "text_query": null}}

- "meetings about AWS infrastructure"
  → {{"context": "meetings", "entity_value": "AWS", "entity_type": "tech", "text_query": null, "person": null, "emotion": null}}

- "meetings about FAISS"
  → {{"context": "meetings", "entity_value": "FAISS", "entity_type": "tech", "text_query": null, "person": null, "emotion": null}}

- "notes about AWS and cloud infrastructure"
  → {{"entity_value": "AWS", "entity_type": "tech", "text_query": "cloud infrastructure", "person": null, "emotion": null}}

- "what sport did I watch?"
  → {{"text_query": "sport watch", "person": null, "emotion": null, "entity_type": null}}

Return ONLY JSON:
{{
  "person": "name" or null,
  "emotion": "feeling" or null,
  "entity_type": "project"/"topic"/"tech" or null,
  "entity_value": "value" or null,
  "context": "folder" or null,
  "text_query": "keywords" or null,
  "sort": "recent"/"oldest" or null
}}

JSON:"""

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
