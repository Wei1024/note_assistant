# GraphRAG Implementation Progress

**Started**: 2025-10-20
**Design Document**: [proposed_new_structure.md](proposed_new_structure.md)
**Research Foundation**: [entity_extraction_research.md](entity_extraction_research.md)

---

## Architecture Overview

Implementing a local GraphRAG system with four layers:

1. **Episodic Layer** - Extract WHO/WHAT/WHEN/WHERE entities from notes
2. **Semantic Layer** - Create embeddings and auto-link via similarity
3. **Prospective Layer** - Detect future times/todos, create time-based edges
4. **Retrieval Layer** - Hybrid search (FTS5 + embeddings) with graph expansion

---

## Phase 1: Episodic Layer - Entity Extraction

**Status**: ✅ PARTIALLY COMPLETE (Core extraction working, endpoint integration pending)

### Completed

#### ✅ Research & Validation
- Entity extraction research validated hybrid approach (docs/entity_extraction_research.md)
- LLM optimal for WHO/WHAT/WHERE (0.69-0.93 F1)
- dateparser optimal for WHEN (0.944 F1 vs LLM's 0.833 F1)
- Fixed LLM hallucination bug (prompt contamination)

#### ✅ Core Services Created
- **`api/services/episodic.py`** (NEW)
  - `extract_episodic_metadata()` - Main extraction function
  - `_extract_entities_and_tags_llm()` - LLM for WHO/WHAT/WHERE/tags/title
  - `_extract_time_references()` - dateparser for WHEN
  - Integrates LLM audit logging via `track_llm_call`

#### ✅ Database Schema Updated
- **`api/db/schema.py`** - Added graph tables:
  - `graph_nodes` - Stores notes with episodic metadata (WHO/WHAT/WHERE/WHEN/tags)
  - `graph_edges` - Stores relationships (semantic, entity_link, tag_link, time_next, reminder)
  - Indexes on created, cluster_id, src/dst nodes, relation types

#### ✅ Graph Database Helpers
- **`api/db/graph.py`** (NEW)
  - `store_graph_node()` - Save note with episodic metadata
  - `get_graph_node()` - Retrieve node by ID
  - `get_all_nodes()` - Query all nodes
  - `create_edge()` - Create typed relationships
  - `get_node_edges()` - Query node relationships

#### ✅ Testing
- **`test_phase1_endpoint.py`** - Standalone test script
- Tested on 4 sample notes - All extractions successful:
  - ✅ WHO: "Sarah", "Mom" extracted correctly
  - ✅ WHAT: Concepts like "memory consolidation research" extracted
  - ✅ WHEN: Time references parsed accurately (dateparser)
  - ✅ Tags: Thematic categories generated ("meeting", "research", "programming")
  - ✅ Title: Descriptive titles generated

#### ✅ Code Organization
- Moved old services to `api/services/deprecated/`
  - `capture.py` (old dimension-based classification)
  - `enrichment.py` (old redundant extraction)
- New episodic service is cleaner, single-purpose

### Pending

#### ⏳ API Endpoint Integration
**File**: `api/main.py` (745 lines)

**Current state**:
- Old imports still reference deprecated services
- `classify_and_save()` endpoint uses old dimension-based flow
- Need to rewrite endpoint to use `extract_episodic_metadata()` + `store_graph_node()`

**Required changes**:
```python
# Current (OLD):
from .services.capture import classify_note_async
from .services.enrichment import enrich_note_metadata, store_enrichment_metadata

# Step 1: classify_note_async() → dimensions
# Step 2: enrich_note_metadata() → redundant entities
# Step 3: write_markdown() with dimensions
# Step 4: store_enrichment_metadata()

# Target (NEW):
from .services.episodic import extract_episodic_metadata
from .db.graph import store_graph_node

# Step 1: extract_episodic_metadata() → WHO/WHAT/WHEN/WHERE/tags/title
# Step 2: write_markdown() with title/tags only
# Step 3: store_graph_node() with episodic metadata
```

**Options**:
1. **Full rewrite** of `api/main.py` (risky, many endpoints)
2. **Incremental** - Only modify `classify_and_save()`, leave other endpoints
3. **Parallel endpoint** - Create `/capture_note` (new), keep `/classify_and_save` (old) for compatibility

**Recommendation**: Option 2 (Incremental) - Less risk, focused change

#### ⏳ Full Integration Test
- Import 30-note test dataset through new endpoint
- Verify graph_nodes table populated correctly
- Compare extraction quality vs old system
- Validate database transactions work correctly

### Known Issues

1. **Minor extraction bug**: "today" sometimes extracted as WHERE instead of staying in WHEN only
2. **Endpoint not updated**: Can't test end-to-end until main.py modified
3. **Missing write_markdown() simplification**: Still passes enrichment/status (deprecated params)

---

## Phase 2: Semantic Layer - Embeddings & Auto-Linking

**Status**: ⏸️ NOT STARTED (Blocked by Phase 1 completion)

### Planned Components

1. **Embedding Generation**
   - Use `sentence-transformers` (MiniLM-L6-v2, 384-dim)
   - Generate on note save, store in `graph_nodes.embedding`
   - Background task to avoid blocking API response

2. **Semantic Edge Creation**
   - k-NN search for similar notes (cosine similarity)
   - Create `semantic` edges with similarity weight
   - Threshold: 0.7+ similarity = create edge

3. **Entity-Based Linking**
   - Find notes sharing WHO entities → `entity_link` edges
   - Find notes sharing WHAT entities → `entity_link` edges
   - Find notes sharing tags → `tag_link` edges

4. **Clustering**
   - Load graph into NetworkX
   - Run Louvain community detection
   - Store `cluster_id` in graph_nodes
   - Generate cluster summaries

### Prerequisites
- ✅ Graph schema ready (graph_nodes, graph_edges)
- ⏳ Phase 1 endpoint integration complete
- ⏳ Database populated with nodes

---

## Phase 3: Prospective Layer - Time-Based Edges

**Status**: ⏸️ NOT STARTED

### Planned Components

1. **Future Time Detection**
   - Parse `graph_nodes.time_references` JSON
   - Filter for future dates (after current time)
   - Identify action-oriented language ("TODO", "need to", "call", "fix")

2. **Prospective Edge Creation**
   - Notes with future times → `time_next` edges to themselves (reminder)
   - Notes mentioning same person + future → `time_next` edges between them
   - Deadline notes → `reminder` edges

3. **Upcoming Actions API**
   - Endpoint: `/upcoming_actions`
   - Query: Follow `time_next` edges, sort by parsed time
   - Return: Sorted list of upcoming tasks/events

---

## Phase 4: Retrieval Layer - Hybrid Search

**Status**: ⏸️ NOT STARTED

### Planned Components

1. **Hybrid Search**
   - FTS5 full-text search (existing infrastructure)
   - Vector similarity search (new - cosine on embeddings)
   - Re-ranking: `score = 0.6 * cosine + 0.4 * fts_rank`

2. **Graph Expansion**
   - Take top-K search results (initial nodes)
   - Expand 1-2 hops via typed edges:
     - Priority 1: `entity_link` (shared entities)
     - Priority 2: `semantic` (similar content)
     - Priority 3: `time_next` (temporal context)
   - Return subgraph with context

3. **Context Assembly**
   - Assemble subgraph nodes as context
   - Rank by combined relevance score
   - Pass to LLM for synthesis/summarization

---

## Technical Decisions Made

### Entity vs Tag Distinction
- **Entities**: Specific, concrete (WHO/WHAT/WHERE) - "Sarah", "FAISS", "OAuth2"
- **Tags**: Broad, thematic - "meeting", "security", "ai-research"
- Different granularities enable different linking strategies

### Hybrid Extraction Approach
- **LLM**: WHO/WHAT/WHERE (requires semantic understanding)
- **dateparser**: WHEN (rule-based more accurate, 0.944 vs 0.833 F1)
- Validated by 30-note comparison test

### Database Architecture
- **SQLite**: Persistence, FTS5, ACID transactions
- **NetworkX**: In-memory graph for clustering/traversal
- Load graph on demand, don't keep in memory full-time

### Edge Types Defined
- `semantic`: Embedding cosine similarity
- `entity_link`: Shared WHO/WHAT entities
- `tag_link`: Shared thematic tags
- `time_next`: Future temporal relationships
- `reminder`: User-specified reminders

---

## Metrics & Validation

### Phase 1 Test Results (4 sample notes)
| Metric | Result | Notes |
|--------|--------|-------|
| WHO extraction | ✅ 100% | "Sarah", "Mom" found |
| WHAT extraction | ✅ 75% | Concepts found, some over-extraction |
| WHEN extraction | ✅ 100% | All time refs found, minor duplication |
| WHERE extraction | ⚠️ 50% | "today" misclassified as WHERE |
| Tags generation | ✅ 100% | Relevant themes identified |
| Title generation | ✅ 100% | Descriptive, concise |

### Expected Full Test (30 notes)
- Based on research: 0.69-0.94 F1 scores per field
- Will compare against old dimension system (43.3% accuracy)

---

## Next Steps

### Immediate (Complete Phase 1)
1. **Rewrite `classify_and_save()` endpoint** in `api/main.py`
   - Replace old service calls with `extract_episodic_metadata()`
   - Add `store_graph_node()` call
   - Remove dimension extraction logic
   - Test with single note first

2. **Simplify `write_markdown()`** in `api/notes.py`
   - Remove deprecated `enrichment` and `status` parameters
   - Only accept title, tags, body, db_connection

3. **Full integration test**
   - Import 30-note dataset through new endpoint
   - Verify graph_nodes table populated
   - Check LLM audit logging still works

4. **Fix minor extraction issues**
   - Prevent "today" from being WHERE
   - Reduce WHEN duplication ("5pm" extracted separately)

### After Phase 1 Complete
1. Start Phase 2 (Semantic Layer)
2. Choose embedding model (MiniLM-L6-v2 vs BGE-small)
3. Implement background embedding generation
4. Build entity-based linking logic
5. Test clustering quality

---

## Files Modified/Created

### Created (New System)
- `api/services/episodic.py` - Episodic layer extraction service
- `api/db/graph.py` - Graph database helpers
- `test_phase1_endpoint.py` - Phase 1 test script
- `docs/proposed_new_structure.md` - Architecture design (with Claude feedback)
- `docs/graphrag_implementation_progress.md` - This file

### Modified (Infrastructure)
- `api/db/schema.py` - Added graph_nodes and graph_edges tables
- `api/main.py` - Imports changed (not yet refactored endpoint)

### Deprecated (Old System)
- `api/services/deprecated/capture.py` - Old dimension classification
- `api/services/deprecated/enrichment.py` - Old redundant extraction

### Preserved (Still Used)
- `api/llm/audit.py` - LLM audit logging (integrated into episodic.py)
- `api/fts.py` - Full-text search (will be used in Phase 4 retrieval)
- `api/notes.py` - Markdown file writing (needs simplification)
- `api/db/schema.py` - Database schema (extended, not replaced)

---

## Lessons Learned

1. **Test extraction quality first** - Our 30-note research prevented bad architecture
2. **Incremental migration safer** - Moving old services to deprecated/ keeps them accessible
3. **Schema extension > replacement** - Added graph tables, kept existing tables for compatibility
4. **Validate with small tests** - 4-note test caught issues before full integration
5. **Document decisions** - This progress doc helps track "why" not just "what"

---

**Last Updated**: 2025-10-20
**Next Milestone**: Phase 1 completion (endpoint integration)
