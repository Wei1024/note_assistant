# Multi-Dimensional Brain-Based Note System - Implementation Progress

**Last Updated:** 2025-10-13
**Master Plan:** [refactorplan.md](refactorplan.md)
**Current Phase:** Phase 3.1 Complete ✅ | Smart Search Enhanced ✅ → Phase 3.2/4 Next

---

## 🎯 Project Vision

Transform the note-taking system from simple folder classification to a **brain-inspired, multi-dimensional knowledge management system** with:
- **Cognitive model**: Working memory (tasks/meetings/ideas/reference/journal) + Archive
- **Multi-dimensional metadata**: Notes have primary folder + secondary contexts + entities + graph relationships
- **LLM-powered enrichment**: Automatic extraction of people, topics, emotions, projects
- **Memory consolidation**: Background linking mimicking brain's sleep consolidation process
- **Graph relationships**: Notes form a knowledge graph with typed connections

---

## ✅ Completed Phases

### Phase 1: Foundation Refactor (Week 1) - COMPLETE

#### Phase 1.1: Update Folder Structure ✅
**Files Modified:** `api/config.py`, `api/capture_service.py`

**What Changed:**
- Replaced generic folders (projects/people/research) with cognitive contexts
- New structure: `tasks/`, `meetings/`, `ideas/`, `reference/`, `journal/`
- Each folder maps to a cognitive process:
  - **tasks**: Executive function (ONLY folder with status field)
  - **meetings**: Social cognition
  - **ideas**: Creative exploration
  - **reference**: Procedural memory
  - **journal**: Emotional processing (fallback when uncertain)
- Updated LLM classification prompt with brain-based reasoning

**Key Files:**
- [api/config.py](api/config.py) - WORKING_FOLDERS dictionary with cognitive metadata
- [api/capture_service.py](api/capture_service.py:27-93) - Brain-based classification prompt

---

#### Phase 1.2: Enhanced Database Schema ✅
**Files Created:** `api/fts.py` (updated)
**Tables Added:** `notes_dimensions`, `notes_entities`, `notes_links`, `notes_embeddings`

**What Changed:**
```sql
-- Multi-dimensional metadata storage
CREATE TABLE notes_dimensions (
    note_id TEXT,
    dimension_type TEXT,  -- context, emotion, time_reference
    dimension_value TEXT,
    ...
);

CREATE TABLE notes_entities (
    note_id TEXT,
    entity_type TEXT,  -- person, topic, project, tech
    entity_value TEXT,
    entity_metadata TEXT,  -- JSON for structured data
    ...
);

CREATE TABLE notes_links (
    from_note_id TEXT,
    to_note_id TEXT,
    link_type TEXT,  -- related, spawned, references, contradicts
    ...
);

CREATE TABLE notes_embeddings (
    note_id TEXT PRIMARY KEY,
    embedding BLOB,  -- For Phase 7 (vector search)
    ...
);
```

**Design Decision:**
- ❌ Rejected complex migration system (overkill for small dataset)
- ✅ Single `ensure_db()` function with complete schema
- ✅ Can rebuild database anytime from markdown files

**Key Files:**
- [api/fts.py](api/fts.py:16-118) - Complete database schema in ensure_db()

---

#### Phase 1.3: Update Markdown Frontmatter Schema ✅
**Files Modified:** `api/notes.py`

**What Changed:**
- `write_markdown()` now accepts `enrichment` parameter
- Frontmatter includes multi-dimensional metadata:

```yaml
---
id: 2025-10-11T22:22:36-07:00_0d7e
title: Brainstorming vector embeddings
folder: ideas  # Primary context
tags: [vector embeddings, faiss, chromadb]

# Multi-dimensional metadata (Phase 1.3)
dimensions:
  - {type: context, value: tasks}        # Secondary context
  - {type: emotion, value: excited}      # Emotional marker
  - {type: emotion, value: curious}

entities:
  people: [Alex]
  topics: [vector embeddings, search system, FAISS]
  technologies: [FAISS, ChromaDB]

time_references:
  - {type: meeting, datetime: "2025-10-11T15:00:00", description: "meeting with Alex"}
---
```

**Key Files:**
- [api/notes.py](api/notes.py:27-158) - write_markdown() with enrichment support

---

### Phase 2: LLM Enrichment Layer (Week 1-2) - COMPLETE

#### Phase 2.1: Multi-Dimensional Classification ✅
**Files Created:** `api/enrichment_service.py`

**What Changed:**
- LLM automatically extracts multi-dimensional metadata from note text
- Single async function: `enrich_note_metadata(text, primary_classification)`
- Extracts:
  - **Secondary contexts**: What OTHER cognitive contexts does this touch?
  - **People**: Names with roles/relationships
  - **Topics**: Key concepts and subjects
  - **Projects**: Named initiatives
  - **Technologies**: Tools, frameworks, platforms
  - **Emotions**: Feeling words (excited, frustrated, curious)
  - **Time references**: Meetings, deadlines, events (with ISO datetime)

**LLM Prompt Design:**
- Conservative extraction guidelines ("only extract what's CLEARLY present")
- No hallucination - empty arrays preferred over guessing
- Validates secondary_contexts against WORKING_FOLDERS
- Returns structured JSON

**Key Files:**
- [api/enrichment_service.py](api/enrichment_service.py:14-135) - enrich_note_metadata()

---

#### Phase 2.2: Integrate Enrichment with Storage ✅
**Files Created:** `api/graph.py`
**Files Modified:** `api/enrichment_service.py`, `api/main.py`

**What Changed:**

**1. Created graph.py (550 lines)**
Complete graph helper functions for multi-dimensional metadata:

**Write Operations:**
```python
add_dimension(note_id, type, value)        # Add secondary context/emotion/time
add_entity(note_id, type, value, metadata) # Add person/topic/project/tech
add_link(from_id, to_id, link_type)       # Create relationship between notes
index_note_with_enrichment(note_id, enrichment)  # Batch storage
```

**Read Operations:**
```python
get_dimensions(note_id)           # All dimensions for a note
get_entities(note_id)             # All entities for a note
get_linked_notes(note_id)         # Outgoing links
get_backlinks(note_id)            # Incoming links
get_all_links_for_note(note_id)   # Both directions
```

**Query Operations:**
```python
find_notes_by_dimension(type, value)  # Search by emotion/context
find_notes_by_entity(type, value)     # Search by person/topic/project
find_notes_by_person(name)            # Case-insensitive person search
get_graph_neighborhood(note_id, depth) # Graph traversal for visualization
```

**2. Updated capture flow in main.py:**
```python
# Step 1: Primary classification
result = await classify_note_async(req.text)

# Step 2: Enrich with multi-dimensional metadata
enrichment = await enrich_note_metadata(req.text, result)

# Step 3: Save to disk with enrichment in frontmatter (Phase 1.3)
note_id, filepath, title, folder = write_markdown(..., enrichment=enrichment)

# Step 4: Store enrichment metadata in database (Phase 2.2)
store_enrichment_metadata(note_id, enrichment, db_connection)
```

**Architecture:**
- ✅ Clean separation: enrichment_service extracts, graph.py stores/queries
- ✅ Reusable helpers for all graph operations
- ✅ Enrichment in both frontmatter (human-readable) and database (queryable)
- ✅ Ready for Phase 3 queries

**Key Files:**
- [api/graph.py](api/graph.py) - Complete graph helper library
- [api/enrichment_service.py](api/enrichment_service.py:138-149) - Uses graph.py helpers
- [api/main.py](api/main.py:42-86) - Integrated capture flow

---

#### Phase 2.3: Auto-Linking System ✅
**Files Created:** `api/consolidation_service.py`
**Files Modified:** `api/main.py`

**What Changed:**

**Design Decision: Async Consolidation (not sync)**
Following the brain-based cognitive model, linking is decoupled from capture:
- **Capture = awake** (fast, no linking, 0ms overhead)
- **Consolidation = sleep** (batch analysis, better connections)

This mirrors how the brain processes: immediate capture during the day, then consolidates memories during sleep by finding patterns and creating connections.

**Core Functions:**
```python
get_notes_created_today()         # Find notes to consolidate
find_link_candidates()            # Multi-strategy candidate search
suggest_links_batch()             # Single LLM call analyzes all candidates
consolidate_daily_notes()         # Main entry point
```

**Candidate Finding (4 strategies):**
1. **Entity-based (SQL)**:
   - Search by people (exact match on entity_value)
   - Search by topics (exact match on entity_value, top 3)
   - Search by projects (exact match on entity_value)

2. **Tag-based (FTS5)** ← Phase 2.3b enhancement:
   - Search by shared tags (top 3 tags)
   - Fast (<10ms), high signal (tags are intentional)
   - Catches connections entities missed

3. **Future - Content-based (Phase 7)**:
   - Embedding similarity search
   - Best coverage + speed at scale

4. **Future - Smart search (Phase 3.2)**:
   - LLM query rewriting for semantic matching
   - Only for user queries (too slow for batch)

**LLM Batch Linking:**
- Single prompt with ALL candidates (not N sequential calls)
- LLM compares across candidates for better decisions
- Link types: `related`, `spawned`, `references`, `contradicts`
- Heuristic filtering: Skip vague reasons ("might be", "both mention")
- Max 5 links per note (quality over quantity)

**Conservative by Design:**
- Better to miss connections than create false ones
- Requires strong, specific shared concepts
- Filters out weak/uncertain suggestions

**New Endpoint:**
```bash
POST /consolidate
```

Returns statistics:
```json
{
  "notes_processed": 2,
  "links_created": 0,
  "notes_with_links": 0,
  "started_at": "2025-10-12T13:24:39-07:00",
  "completed_at": "2025-10-12T13:24:47-07:00"
}
```

**Future Enhancement (Phase 2.3c):**
- Cron job at 2am: automatic nightly consolidation
- Or use APScheduler for background worker

**Key Files:**
- [api/consolidation_service.py](api/consolidation_service.py) - Complete consolidation service
- [api/main.py](api/main.py:185-208) - /consolidate endpoint

---

## ✅ Phase 3: Multi-Dimensional Querying (Complete)

### Overview
Now that we have rich metadata (dimensions, entities, links) stored, we need **query interfaces** to leverage it.

---

### Phase 3.1: Enhanced Search Endpoints ✅

**Status:** COMPLETE (2025-10-12)

**Goal:** Create API endpoints to query by dimensions, entities, and relationships.

**Files Created:**
- [api/query_service.py](api/query_service.py) - Query orchestration layer (368 lines)

**Files Modified:**
- [api/main.py](api/main.py) - Added 5 new endpoints (+83 lines)
- [api/models.py](api/models.py) - Added request/response models (+24 lines)

**Endpoints Implemented:**

**1. POST /search/dimensions**
Search by dimension (context, emotion, time_reference), optionally combined with FTS5 text search.

```bash
# Find all notes where emotion=excited
curl -X POST http://localhost:8787/search/dimensions \
  -d '{"dimension_type": "emotion", "dimension_value": "excited"}'

# Combined: excited + text contains "FAISS"
curl -X POST http://localhost:8787/search/dimensions \
  -d '{"dimension_type": "emotion", "dimension_value": "excited", "query_text": "FAISS"}'
```

**2. POST /search/entities**
Search by entity (person, topic, project, tech), optionally filtered by folder.

```bash
# Find all notes about topic=FAISS
curl -X POST http://localhost:8787/search/entities \
  -d '{"entity_type": "topic", "entity_value": "FAISS"}'

# Filter by folder: person=Sarah in meetings
curl -X POST http://localhost:8787/search/entities \
  -d '{"entity_type": "person", "entity_value": "Sarah", "context": "meetings"}'
```

**3. POST /search/person**
Convenience endpoint for person search with case-insensitive matching.

```bash
# Find all notes mentioning Sarah (case-insensitive)
curl -X POST http://localhost:8787/search/person \
  -d '{"name": "Sarah"}'

# Filter by folder context
curl -X POST http://localhost:8787/search/person \
  -d '{"name": "Sarah", "context": "meetings"}'
```

**4. POST /search/graph**
Traverse graph from starting note, return nodes + edges for visualization.

```bash
# Get all notes within 2 hops
curl -X POST http://localhost:8787/search/graph \
  -d '{"start_note_id": "2025-10-12T16:01:41-07:00_744d", "depth": 2}'

# Filter by relationship type
curl -X POST http://localhost:8787/search/graph \
  -d '{"start_note_id": "...", "depth": 1, "relationship_type": "spawned"}'
```

**5. GET /notes/{note_id}/graph**
Graph visualization data endpoint (REST-friendly GET).

```bash
# Get graph data for visualization
curl http://localhost:8787/notes/2025-10-12T16:01:41-07:00_744d/graph?depth=2
```

**Implementation Details:**

**query_service.py functions:**
- `search_by_dimension()` - Query dimensions table, optional FTS5 combo
- `search_by_entity()` - Query entities table with folder filter
- `search_by_person()` - Convenience wrapper with case-insensitive search
- `search_graph()` - Traverse graph using get_graph_neighborhood()
- `get_graph_visualization()` - Wrapper for GET endpoint

**Architecture:**
- ✅ Reuses existing graph.py helpers (no duplication)
- ✅ Thin orchestration layer (query_service.py)
- ✅ Helper functions for formatting and filtering
- ✅ D3.js/Cytoscape/Vue Flow compatible graph format
- ✅ No over-engineering (no caching/pagination yet)

**Response Format:**
All search endpoints return:
```json
[
  {
    "path": "/path/to/note.md",
    "snippet": "First 200 chars of note body...",
    "score": 1.0,
    "metadata": {
      "folder": "meetings",
      "created": "2025-10-12T09:00:00-07:00",
      "title": "Meeting with Sarah"
    }
  }
]
```

Graph endpoints return:
```json
{
  "nodes": [
    {
      "id": "...",
      "title": "...",
      "path": "...",
      "folder": "meetings",
      "created": "...",
      "metadata": {
        "entity_count": 5,
        "dimension_count": 3,
        "has_entities": {"person": ["Sarah"], "topic": ["FAISS"]}
      }
    }
  ],
  "edges": [
    {
      "from": "note_id_1",
      "to": "note_id_2",
      "source": "note_id_1",  // D3.js alias
      "target": "note_id_2",  // D3.js alias
      "type": "spawned"
    }
  ]
}
```

**Key Files:**
- [api/query_service.py](api/query_service.py) - Query orchestration layer
- [api/main.py](api/main.py:230-310) - New endpoints
- [api/models.py](api/models.py:29-51) - Request/response models

---

### Phase 3.1b: Smart Search Enhancement ✅

**Status:** COMPLETE (2025-10-13)

**Goal:** Integrate Phase 3.1 endpoints with natural language search for single search bar experience.

**What Was Built:**

**New Endpoint: POST /search_smart** (renamed from /search_fast)
- Parses natural language queries to extract filters (1 LLM call)
- Intelligently routes to appropriate Phase 3.1 endpoint
- Relaxed fallback: if no exact match, searches all folders

**Query Understanding:**
```
"meetings about FAISS"
  → Parses: context=meetings, entity_value=FAISS
  → Routes: search_by_entity("FAISS", context="meetings")
  → Fallback: If 0 results, retry without context filter
  → Returns: Results with match_type="related" indicator

"what did I do with Sarah"
  → Parses: person=Sarah
  → Routes: search_by_person("Sarah")

"notes where I felt excited"
  → Parses: emotion=excited
  → Routes: search_by_dimension("emotion", "excited")
```

**Routing Priority:**
1. Person filter → `search_by_person()`
2. Emotion filter → `search_by_dimension()`
3. Entity filter → `search_by_entity()`
4. Text only → FTS5 fallback

**Relaxed Search Behavior:**
- Tries strict search first (e.g., "meetings about FAISS" → search meetings folder)
- If 0 results, automatically relaxes (searches all folders)
- Marks relaxed results with `metadata.match_type = "related"`
- Adds helpful note: "Found in different folder (searched all folders)"

**Benefits:**
- ✅ Single search bar for frontend (no need for multiple inputs)
- ✅ Human-like flexibility (finds related results instead of nothing)
- ✅ Still only 1 LLM call (query parsing + routing combined)
- ✅ Clear indicators (exact vs related matches)

**Files Modified:**
- [api/search_service.py](api/search_service.py) - Added parse_smart_query(), enhanced routing
- [api/main.py](api/main.py) - Added /search_smart endpoint
- [api/models.py](api/models.py) - Added metadata field to SearchHit
- [cli.py](cli.py) - Updated to use /search_smart

**Key Files:**
- [api/search_service.py](api/search_service.py:121-306) - Smart query parser and router

---

### Phase 3.2: Natural Language Query Interface (Optional/Future)

**Status:** NOT IMPLEMENTED (deferred - Phase 3.1 endpoints sufficient for now)

**Goal:** User asks questions in plain English, LLM converts to structured queries.

**Decision:** Hold off on this phase because:
- Current FTS5 search already has natural language query rewriting (search_notes_smart)
- Phase 3.1 endpoints provide structured access to all metadata
- Can add later if users need conversational querying
- Would add complexity without clear user demand

**Files to Modify:**
- `api/query_service.py` - Add natural_language_query()
- `api/main.py` - Add /query/natural endpoint

**Implementation:**

```python
async def natural_language_query(user_query: str) -> Dict:
    """
    Convert natural language to structured query and execute.

    Examples:
    - "What did I discuss with Sarah?"
      → search_by_person("Sarah", context="meetings")

    - "Ideas from last week"
      → search_by_dimension("context", "idea") + date_filter

    - "What makes me excited?"
      → search_by_dimension("emotion", "excited")

    - "Notes related to vector search project"
      → search_by_entity("project", "vector search")
    """
    llm = get_llm()

    # LLM converts query to structured parameters
    prompt = f"""Convert this natural language query to structured search parameters.

User query: "{user_query}"

Available search types:
1. dimension_search: {{"type": "context|emotion", "value": "..."}}
2. entity_search: {{"type": "person|topic|project|tech", "value": "..."}}
3. graph_search: {{"start_note_id": "...", "depth": 2}}
4. text_search: {{"query": "..."}}

Return ONLY JSON:
{{
  "search_type": "dimension_search|entity_search|graph_search|text_search",
  "parameters": {{...}},
  "reasoning": "Why this search strategy"
}}
"""

    response = await llm.ainvoke(prompt)
    search_plan = json.loads(response.content)

    # Execute the planned search
    if search_plan["search_type"] == "dimension_search":
        results = search_by_dimension(**search_plan["parameters"])
    elif search_plan["search_type"] == "entity_search":
        results = search_by_entity(**search_plan["parameters"])
    # ... etc

    # Synthesize answer
    synthesis_prompt = f"""Based on these search results, answer the user's question.

User question: "{user_query}"

Search results:
{json.dumps(results[:5], indent=2)}

Provide a concise, helpful answer."""

    answer = await llm.ainvoke(synthesis_prompt)

    return {
        "query": user_query,
        "search_plan": search_plan,
        "results": results,
        "answer": answer.content
    }
```

**Endpoint:**
```python
@app.post("/query/natural")
async def natural_query(req: NaturalQueryRequest):
    """Ask questions in plain English"""
    result = await natural_language_query(req.query)
    return result
```

**When to Use LangGraph:**
This is where LangGraph shines - multi-step reasoning required:
- Agent plans search strategy
- Executes searches
- Synthesizes answer
- Can refine if results insufficient

**Consider:** Implement with LangGraph ReAct agent if query complexity requires multi-step planning.

---

### Phase 3.3: Graph Visualization Data ✅

**Status:** COMPLETE (included in Phase 3.1)

**Goal:** Provide data for future graph UI.

**What Was Built:**
Graph visualization was included in Phase 3.1 implementation:
- ✅ POST /search/graph - Returns nodes + edges with full metadata
- ✅ GET /notes/{note_id}/graph - REST-friendly GET endpoint
- ✅ D3.js/Cytoscape/Vue Flow compatible format
- ✅ Entity/dimension counts for visual styling
- ✅ source/target aliases for D3.js compatibility

This functionality is production-ready and available now.

---

## 🔮 Future Phases (Overview)

### Phase 4: Archive & Memory Consolidation (Week 3)
- Archive folder structure design (based on 2-3 months usage patterns)
- Review workflows (daily/weekly/monthly)
- Auto-archive rules
- Pattern analysis

### Phase 5: CLI & Testing (Week 3-4)
- Update CLI with new features
- Integration tests
- Migration tool for existing notes

### Phase 6: Documentation & Polish (Week 4)
- Architecture documentation
- API documentation
- Performance optimization

### Phase 7: Vector Search (Future)
- Embeddings for semantic similarity
- Hybrid search (vector + FTS5)
- Upgrade consolidation to embedding-based candidate finding

---

## 📊 Current System Capabilities

### What Works Today ✅

**1. Note Capture:**
- POST /classify_and_save - Fast capture with classification + enrichment
- Brain-based folder classification (tasks/meetings/ideas/reference/journal)
- Automatic metadata extraction (people, topics, emotions, projects, technologies)
- Enrichment stored in both frontmatter and database

**2. Search:**
- POST /search - Direct FTS5 keyword search
- POST /search_smart - Smart natural language search with multi-dimensional routing ✨ NEW
  - Intelligently routes to person/emotion/entity endpoints
  - Relaxed fallback: searches all folders if no exact context match
  - Returns metadata including match_type (exact/related)
- POST /search_fast - Deprecated (use /search_smart)
- Status filtering (find tasks by todo/in_progress/done)

**3. Status Management:**
- PATCH /notes/status - Update task status

**4. Memory Consolidation:**
- POST /consolidate - Manual trigger for daily note linking
- Multi-strategy candidate finding (entities + tags)
- Batch LLM link analysis
- Conservative linking (quality > quantity)

**5. Multi-Dimensional Queries (Phase 3.1):**
- POST /search/dimensions - Search by emotion/context/time_reference
- POST /search/entities - Search by person/topic/project/tech
- POST /search/person - Case-insensitive person search
- POST /search/graph - Graph traversal with depth control
- GET /notes/{note_id}/graph - Graph visualization data

**6. Graph Operations (via Python):**
```python
from api.graph import *

# Query functions
get_dimensions(note_id)
get_entities(note_id)
get_linked_notes(note_id)
get_backlinks(note_id)
find_notes_by_person("Sarah")
find_notes_by_entity("topic", "vector search")
get_graph_neighborhood(note_id, depth=2)
```

### What's Missing (Next Steps) 🚧

**Optional (Phase 3.2):**
- ⏸️ Natural language query interface (deferred - current endpoints sufficient)

**Later:**
- ❌ Archive system (Phase 4)
- ❌ Review workflows (Phase 4)
- ❌ Vector search with embeddings (Phase 7)
- ❌ Cron-based auto-consolidation (Phase 2.3c)

---

## 🛠️ Technical Architecture

### File Structure
```
api/
├── capture_service.py        # Primary classification (LLM)
├── enrichment_service.py     # Multi-dimensional metadata extraction (LLM)
├── consolidation_service.py  # Memory consolidation & linking (LLM + SQL)
├── graph.py                  # Graph operations (CRUD + query helpers)
├── query_service.py          # Multi-dimensional query interface (Phase 3.1) ✅
├── search_service.py         # Natural language search (LLM + FTS5)
├── notes.py                  # Markdown file operations
├── fts.py                    # SQLite FTS5 + schema management
├── config.py                 # Configuration & cognitive model
├── main.py                   # FastAPI endpoints
└── models.py                 # Pydantic models
```

### Data Flow

**Capture Flow:**
```
User input
  → classify_note_async() [LLM]
  → enrich_note_metadata() [LLM]
  → write_markdown() [File + DB]
  → store_enrichment_metadata() [DB via graph.py]
```

**Consolidation Flow:**
```
Trigger /consolidate
  → get_notes_created_today() [DB]
  → find_link_candidates() [SQL + FTS5]
  → suggest_links_batch() [LLM]
  → add_link() [DB via graph.py]
```

**Search Flow (Text Search):**
```
User query
  → search_notes_smart() [LLM query rewrite]
  → search_notes() [FTS5]
  → Results
```

**Query Flow (Phase 3.1 - Multi-Dimensional):**
```
Dimension query
  → search_by_dimension() [query_service.py]
  → find_notes_by_dimension() [graph.py → SQL]
  → Optional: combine with FTS5 text search
  → Results

Entity query
  → search_by_entity() [query_service.py]
  → find_notes_by_entity() [graph.py → SQL]
  → Optional: filter by context (folder)
  → Results

Graph query
  → search_graph() [query_service.py]
  → get_graph_neighborhood() [graph.py → SQL]
  → Enrich with metadata (entities/dimensions)
  → Nodes + Edges (D3.js/Vue compatible)
```

---

## 💡 Key Design Decisions

### 1. **Async Consolidation** (Phase 2.3)
**Decision:** Link notes asynchronously (manual trigger or cron), not during capture.

**Reasoning:**
- Brain analogy: Capture = awake (fast), consolidation = sleep (thoughtful)
- 0ms capture latency preserved
- Better link quality (more time for analysis)
- Batch processing enables cross-note pattern detection

### 2. **Conservative Linking** (Phase 2.3)
**Decision:** Better to miss connections than create false ones.

**Reasoning:**
- Heuristic filtering removes vague LLM suggestions
- Max 5 links per note prevents link spam
- Requires specific shared concepts, not just topic overlap

### 3. **Batch LLM Linking** (Phase 2.3)
**Decision:** Single LLM call analyzes all candidates, not sequential calls.

**Reasoning:**
- 10x faster (1 call vs 10 calls)
- Better quality (LLM compares across candidates)
- Simpler than LangGraph agent (linking is well-defined task)

**Future:** Upgrade to embedding-based filtering + batch LLM (Phase 7).

### 4. **Hybrid Storage** (Phase 1.3 + 2.2)
**Decision:** Store enrichment in both frontmatter and database.

**Reasoning:**
- **Frontmatter**: Human-readable, version-controllable
- **Database**: Fast queries, graph traversal
- Markdown files are source of truth, database is index

### 5. **No Fake Confidence** (Phase 1.2)
**Decision:** Use heuristic-based review flags, not LLM confidence scores.

**Reasoning:**
- LLMs cannot calibrate confidence scores reliably
- Honest heuristics (text length, uncertainty keywords) are more trustworthy
- Better user experience than fake precision

### 6. **Tag-Based Search** (Phase 2.3b)
**Decision:** Add FTS5 tag search to candidate finding.

**Reasoning:**
- Tags are intentional metadata (high signal)
- Fast (<10ms per tag)
- Complements entity-based search
- Catches connections entity extraction missed

---

## 🔧 Development Commands

### Start Backend
```bash
python3 -m api.main
# Server runs on http://127.0.0.1:8787
```

### Test Endpoints
```bash
# Health check
curl http://127.0.0.1:8787/health

# Capture note
curl -X POST http://127.0.0.1:8787/classify_and_save \
  -H "Content-Type: application/json" \
  -d '{"text": "Meeting with Sarah about memory research"}'

# Search
curl -X POST http://127.0.0.1:8787/search_fast \
  -H "Content-Type: application/json" \
  -d '{"query": "vector search"}'

# Consolidate
curl -X POST http://127.0.0.1:8787/consolidate
```

### Test Graph Functions
```python
python3 -c "
from api.graph import find_notes_by_person, get_linked_notes

# Find all notes about Sarah
sarah_notes = find_notes_by_person('Sarah')
print(f'Notes about Sarah: {len(sarah_notes)}')

# Get links from a note
links = get_linked_notes('2025-10-11T22:02:40-07:00_a27f')
print(f'Outgoing links: {len(links)}')
"
```

### Database Queries
```bash
# Check enrichment metadata
sqlite3 ~/Notes/.index/notes.sqlite "
SELECT note_id, entity_type, entity_value
FROM notes_entities
WHERE entity_type='person'
LIMIT 10;
"

# Check dimensions
sqlite3 ~/Notes/.index/notes.sqlite "
SELECT note_id, dimension_type, dimension_value
FROM notes_dimensions
WHERE dimension_type='emotion'
LIMIT 10;
"

# Check links
sqlite3 ~/Notes/.index/notes.sqlite "
SELECT from_note_id, to_note_id, link_type
FROM notes_links
ORDER BY created DESC
LIMIT 10;
"
```

---

## 📚 Resources

### Key Documentation Files
- [refactorplan.md](refactorplan.md) - Original 6-week implementation plan
- [plan.md](plan.md) - Original MVP architecture spec
- [PROGRESS.md](PROGRESS.md) - This file (current status + next steps)

### Important Code Locations
- Primary classification: [api/capture_service.py:27-93](api/capture_service.py:27-93)
- Enrichment: [api/enrichment_service.py:14-135](api/enrichment_service.py:14-135)
- Graph operations: [api/graph.py](api/graph.py)
- Consolidation: [api/consolidation_service.py](api/consolidation_service.py)
- Database schema: [api/fts.py:16-118](api/fts.py:16-118)

---

## 🚀 Getting Started for Next Agent

### Context Summary
You're working on a **brain-based note-taking system** with multi-dimensional metadata and graph relationships. We've completed Phase 2 (enrichment + consolidation). Next is Phase 3 (advanced querying).

### Your First Tasks (Phase 3.1)

1. **Create api/query_service.py**
   - Implement `search_by_dimension()`
   - Implement `search_by_entity()`
   - Implement `search_by_person()`
   - Implement `search_graph()`

2. **Add endpoints to api/main.py**
   - POST /search/dimensions
   - POST /search/entities
   - POST /search/person
   - POST /search/graph

3. **Update api/models.py**
   - Add request/response models for new endpoints

4. **Test thoroughly**
   - Create test notes with various dimensions and entities
   - Verify queries return correct results
   - Test combined filters

### Questions to Consider

1. **Should search_by_dimension() combine with FTS5?**
   - e.g., Find notes where emotion=excited AND text contains "vector"
   - Or keep them separate?

2. **How should pagination work?**
   - Graph queries could return 100+ notes
   - Default limit? Cursor-based pagination?

3. **Should we add bulk operations?**
   - e.g., /search/bulk for multiple queries at once
   - Useful for dashboard views

4. **Caching strategy?**
   - Graph queries are expensive
   - Redis? In-memory LRU cache?

### Testing Strategy

1. Create diverse test notes:
   - Notes with multiple emotions
   - Notes mentioning same person in different contexts
   - Notes with project relationships
   - Notes with contradictory information

2. Test edge cases:
   - Query for non-existent person
   - Graph traversal with circular links
   - Very deep graph queries (depth=5)

3. Performance testing:
   - Query with 1000+ notes
   - Graph traversal benchmarks
   - Combined filter queries

Good luck! 🎉
