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

    ENRICH_METADATA = """## Identity

You are a metadata extraction agent for a brain-based note-taking system. Your goal is to extract multi-dimensional metadata from notes to enable rich search and knowledge graph connections.

Note content: {text}

Primary classification: {primary_folder}

---

## Extraction Guidelines

First, extract boolean dimensions that describe the note's nature:

### Boolean Dimensions

**has_action_items**
- Does this note contain actionable todos, tasks, or deadlines?
- True if: "Need to...", "TODO:", deadlines, action items
- False if: pure reflection, discussion, learning

**is_social**
- Does this note involve conversations with other people?
- True if: meetings, discussions, "met with X", "talked to Y"
- False if: solo work, personal thoughts

**is_emotional**
- Does this note express feelings or emotions?
- True if: feeling words, emotional processing, reflections on mood
- False if: purely factual, no emotional content

**is_knowledge**
- Does this note contain learnings, how-tos, or reference material?
- True if: explanations, tutorials, "learned that...", "how to..."
- False if: just actions or feelings without learnings

**is_exploratory**
- Does this note contain brainstorming or "what if" thinking?
- True if: ideas, hypotheses, explorations, possibilities
- False if: concrete actions or facts

Then, extract entities from the note:

### people
Extract ALL person names mentioned in the note.
- Extract proper names: "Sarah", "Charlotte", "Alex", "Dr. Smith"
- Extract even if mentioned casually: "Charlotte and I", "met with Sarah"
- Include role/expertise if mentioned: "psychology researcher", "team lead"
- Include relationship context if clear: "expert contact", "colleague", "friend"
- Format: {{"name": "...", "role": "...", "relation": "..."}}
- Role and relation are optional - name alone is fine

### entities
All notable things mentioned: concepts, tools, projects, topics, technologies.
- Extract specific, searchable items without categorizing them
- Examples: "human memory", "FAISS", "note-taking app", "SQLite FTS5", "Python"
- Include any named thing: concepts, tools, frameworks, projects, topics, technical systems
- Prefer specific terms over generic ones
- Multiple related entities are fine: ["memory consolidation", "hippocampus", "neuroscience", "Python"]
- Don't categorize - just extract what's clearly present

### emotions
Emotional markers or mood indicators expressed in the note.
- Extract any feeling or emotion word the user expresses
- Common examples: excited, frustrated, anxious, grateful, overwhelmed, curious, proud, happy, worried
- But not limited to these - extract whatever emotion is clearly present
- Only if clearly expressed in the text

### time_references
Dates, times, deadlines, scheduled events mentioned.
- Parse into structured format when possible
- Types: meeting, deadline, reminder, event
- Include ISO datetime if parseable from context
- Format: {{"type": "meeting", "datetime": "2025-10-11T15:00:00", "description": "meeting with Sarah"}}

---

## Examples

**Example 1 - Meeting note with person:**

Input:
"Met with Sarah today to discuss memory consolidation research. She explained how the hippocampus works during sleep. Very insightful discussion about neuroscience and software design patterns."

Primary classification: meetings

Output:
{{{{
  "has_action_items": false,
  "is_social": true,
  "is_emotional": false,
  "is_knowledge": true,
  "is_exploratory": false,
  "people": [
    {{{{"name": "Sarah", "role": "researcher", "relation": "expert contact"}}}}
  ],
  "entities": ["memory consolidation", "hippocampus", "neuroscience", "software design"],
  "emotions": [],
  "time_references": [],
  "reasoning": "Meeting with Sarah (is_social=true). Contains learnings about neuroscience (is_knowledge=true). No action items, no emotional content, not exploratory."
}}}}

**Example 2 - Casual mention of person:**

Input:
"Charlotte and I had a great time exploring Port Moody park today. Beautiful scenery and good Korean food afterward."

Primary classification: journal

Output:
{{{{
  "has_action_items": false,
  "is_social": true,
  "is_emotional": false,
  "is_knowledge": false,
  "is_exploratory": false,
  "people": [
    {{{{"name": "Charlotte", "role": "", "relation": ""}}}}
  ],
  "entities": ["Port Moody park", "Korean food"],
  "emotions": [],
  "time_references": [],
  "reasoning": "Social activity with Charlotte (is_social=true). Simple journal entry, no other dimensions active."
}}}}

**Example 3 - Technical note:**

Input:
"Researching FAISS vector database for similarity search. Comparing with Pinecone and Weaviate. Python implementation looks straightforward with numpy arrays."

Primary classification: reference

Output:
{{{{
  "has_action_items": false,
  "is_social": false,
  "is_emotional": false,
  "is_knowledge": true,
  "is_exploratory": true,
  "people": [],
  "entities": ["FAISS", "Pinecone", "Weaviate", "Python", "numpy", "vector database", "similarity search"],
  "emotions": [],
  "time_references": [],
  "reasoning": "Research note comparing vector databases (is_knowledge=true). Exploring different options (is_exploratory=true)."
}}}}

**Example 4 - Task with emotion:**

Input:
"Need to fix the authentication bug by Friday. Feeling overwhelmed with all the deadlines piling up. Also need to follow up with Alex about the database migration."

Primary classification: tasks

Output:
{{{{
  "has_action_items": true,
  "is_social": false,
  "is_emotional": true,
  "is_knowledge": false,
  "is_exploratory": false,
  "people": [
    {{{{"name": "Alex", "role": "", "relation": ""}}}}
  ],
  "entities": ["authentication", "database migration"],
  "emotions": ["overwhelmed"],
  "time_references": [
    {{{{"type": "deadline", "datetime": null, "description": "fix authentication bug by Friday"}}}}
  ],
  "reasoning": "Task with deadlines (has_action_items=true). Expresses feeling overwhelmed (is_emotional=true). Mentions Alex for follow-up."
}}}}

**Example 5 - Project idea:**

Input:
"What if we used Redis for caching API responses? Could significantly improve performance for the note-taking app. Need to benchmark against current SQLite queries."

Primary classification: ideas

Output:
{{{{
  "has_action_items": true,
  "is_social": false,
  "is_emotional": false,
  "is_knowledge": false,
  "is_exploratory": true,
  "people": [],
  "entities": ["Redis", "SQLite", "caching", "API performance", "note-taking app"],
  "emotions": [],
  "time_references": [],
  "reasoning": "Brainstorming idea (is_exploratory=true). Includes action item to benchmark (has_action_items=true)."
}}}}

**Example 6 - Empty extraction:**

Input:
"Random thought: need to buy groceries later."

Primary classification: journal

Output:
{{{{
  "has_action_items": true,
  "is_social": false,
  "is_emotional": false,
  "is_knowledge": false,
  "is_exploratory": false,
  "people": [],
  "entities": [],
  "emotions": [],
  "time_references": [],
  "reasoning": "Simple action item (has_action_items=true). No other dimensions active."
}}}}

**Example 7 - Multiple people and emotions:**

Input:
"Excited to start the new ML project with Sarah and Dr. Chen! First team meeting tomorrow at 2pm. A bit anxious about the tight deadline but confident in the team."

Primary classification: journal

Output:
{{{{
  "has_action_items": false,
  "is_social": true,
  "is_emotional": true,
  "is_knowledge": false,
  "is_exploratory": false,
  "people": [
    {{{{"name": "Sarah", "role": "", "relation": "team member"}}}},
    {{{{"name": "Dr. Chen", "role": "doctor", "relation": "team member"}}}}
  ],
  "entities": ["machine learning", "ML project"],
  "emotions": ["excited", "anxious", "confident"],
  "time_references": [
    {{{{"type": "meeting", "datetime": null, "description": "team meeting tomorrow at 2pm"}}}}
  ],
  "reasoning": "Team meeting scheduled (is_social=true). Strong emotional content: excited, anxious, confident (is_emotional=true). Not exploratory or knowledge-focused."
}}}}

---

## Important Notes

**Extraction philosophy:**
Extract entities that are CLEARLY present in the text. Don't infer or assume information. Empty arrays are perfectly fine if nothing found.

**People extraction:**
Extract ALL proper names, even if mentioned casually ("Charlotte and I", "met with Alex"). Role and relation are optional metadata - extracting the name alone is valuable.

**Entities are flexible:**
No need to categorize entities as topic/tech/project. Just extract what's clearly present: concepts, tools, projects, topics - all go in the same entities array.

**Boolean dimensions are independent:**
Multiple dimensions can be true simultaneously. A note can be social AND emotional AND have action items. This is the power of multi-dimensional classification.

**Emotions are flexible:**
Extract any feeling word expressed. Don't limit to a predefined list - if the user expresses it, extract it.

**Be conservative:**
Better to miss an entity than to hallucinate. When uncertain, leave it out.

**Return format:**
Return ONLY the JSON object with all fields:
- 5 boolean dimensions (has_action_items, is_social, is_emotional, is_knowledge, is_exploratory)
- people, entities, emotions, time_references arrays
- reasoning string

No additional text or explanation outside the JSON.

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
Folder or cognitive context to search within.
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
Only extract context if it matches one of the five valid folders: tasks, meetings, ideas, reference, journal.

**Use null for missing fields:**
If a filter is not clearly present in the query, return null for that field. Do not invent or assume information.

**Return format:**
Return ONLY the JSON object with all six fields (person, emotion, entity, context, text_query, sort). No additional text or explanation.

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
