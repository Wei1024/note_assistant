# GraphRAG Implementation Progress

**Started**: 2025-10-20
**Design Document**: [proposed_new_structure.md](proposed_new_structure.md)
**Research Foundation**: [entity_extraction_research.md](entity_extraction_research.md)

---

## 🎉 MAJOR MILESTONE: Clean Rewrite Complete (2025-10-20)

**Decision**: After initial incremental approach, we performed a **complete rewrite** to pure GraphRAG architecture.

**Rationale**:
- No external users yet (only 30 test notes)
- Mixing old dimension system with new GraphRAG created confusion
- Clean slate enables faster development of Phases 2-4
- Old codebase preserved in `api/legacy/` for reference

---

## Architecture Overview

Implementing a local GraphRAG system with four layers:

1. **Episodic Layer** - Extract WHO/WHAT/WHEN/WHERE entities from notes ✅ **COMPLETE**
2. **Semantic Layer** - Create embeddings and auto-link via similarity ⏸️ NOT STARTED
3. **Prospective Layer** - Detect future times/todos, create time-based edges ⏸️ NOT STARTED
4. **Retrieval Layer** - Hybrid search (FTS5 + embeddings) with graph expansion ⏸️ NOT STARTED

---

## Phase 1: Episodic Layer ✅ **COMPLETE**

**Status**: ✅ **FULLY COMPLETE** (Extraction working, endpoint integrated, tested)

### Production Codebase (Clean GraphRAG Only)

```
api/
├── main.py (162 lines)          # Single /capture_note endpoint
├── models.py                    # GraphRAG models: CaptureNoteResponse, EpisodicMetadata
├── config.py (42 lines)         # Minimal config (no dimensions/folders)
├── fts.py                       # Simplified FTS5 (no dimensions)
├── notes.py                     # Simplified write_markdown (no dimensions)
├── services/
│   └── episodic.py              # ONLY production service
├── db/
│   ├── schema.py                # GraphRAG schema
│   └── graph.py                 # Graph node/edge helpers
└── llm/                         # LLM infrastructure
```

### Archived Code (`api/legacy/`)

All old dimension-based code moved to `api/legacy/`:
- Old `main.py` (745 lines, 20+ endpoints)
- Old `models.py` (DimensionFlags, dimension search models)
- Old services: capture, enrichment, consolidation, search, synthesis, clustering, query
- Research code: `entity_extraction.py` (LLM vs Hybrid comparison)
- Old utilities: graph.py, fts.py, notes.py, config.py

### Database Schema (GraphRAG)

**FTS5 & Metadata**:
- `notes_fts`: Full-text search index
- `notes_meta`: Basic metadata (id, path, created, updated) - **NO dimension columns**

**Graph Structure**:
- `graph_nodes`: Episodic metadata stored as JSON
  - `entities_who`: People, organizations
  - `entities_what`: Concepts, topics
  - `entities_where`: Locations
  - `time_references`: Parsed time objects
  - `tags`: Thematic categories
  - `embedding`: Vector (Phase 2)
  - `cluster_id`: Community (Phase 2)

- `graph_edges`: Typed relationships
  - `semantic`: Embedding similarity (Phase 2)
  - `entity_link`: Shared entities (Phase 2)
  - `tag_link`: Shared tags (Phase 2)
  - `time_next`: Future temporal (Phase 3)
  - `reminder`: User-specified (Phase 3)

**Preserved**:
- `llm_operations`: LLM audit logging

### API Endpoints

**Production** (`/capture_note`):
```python
POST /capture_note
Request: {"text": "Met with Sarah..."}
Response: {
  "note_id": "2025-10-20T22:49:08-07:00_e756",
  "title": "Discuss FAISS Vector Search Implementation",
  "episodic": {
    "who": ["Sarah"],
    "what": ["FAISS", "vector search", "HNSW"],
    "where": ["Café Awesome"],
    "when": [{"original": "today at 2pm", "parsed": "2025-10-20T14:00:00", "type": "relative"}],
    "tags": ["meeting", "implementation"]
  },
  "path": "/Users/.../2025-10-20-discuss-faiss-vector-search-implementation.md"
}
```

### Core Service: `api/services/episodic.py`

**Function**: `extract_episodic_metadata(text, current_date) → Dict`

**Hybrid Approach** (validated by research):
- **LLM**: WHO/WHAT/WHERE/tags/title (semantic understanding required)
- **dateparser**: WHEN (rule-based more accurate: 0.944 F1 vs LLM's 0.833 F1)

**Returns**:
```python
{
  "who": ["Sarah", "Tom"],
  "what": ["FAISS", "vector search"],
  "where": ["Café Awesome"],
  "when": [{"original": "tomorrow", "parsed": "2025-10-21T14:00:00", "type": "relative"}],
  "tags": ["meeting", "ai-research"],
  "title": "Generated title"
}
```

### Testing & Validation

✅ **Unit Tests**: Episodic extraction tested on 4 sample notes
✅ **Integration Tests**: `/capture_note` endpoint working (multiple successful requests)
✅ **Graph Storage**: Verified graph_nodes populated correctly
✅ **No Dimension Pollution**: Clean codebase confirmed

**Test Results** (4 sample notes):
| Metric | Result | Notes |
|--------|--------|-------|
| WHO extraction | ✅ 100% | "Sarah", "Mom" found |
| WHAT extraction | ✅ 90% | Concepts accurately extracted |
| WHEN extraction | ✅ 100% | All time refs parsed (minor duplication) |
| WHERE extraction | ✅ 100% | Locations identified |
| Tags generation | ✅ 100% | Relevant themes |
| Title generation | ✅ 100% | Descriptive, concise |

**Research Foundation** (30-note comparison):
- WHO/WHAT/WHERE: 0.691-0.944 F1 scores
- WHEN (dateparser): 0.944 F1
- Fixed LLM hallucination bug (prompt contamination)
- Full results: `docs/entity_extraction_research.md`

---

## Phase 2: Semantic Layer - Embeddings & Auto-Linking

**Status**: ⏸️ **NOT STARTED** (Ready to begin)

### Planned Components

1. **Embedding Generation**
   - Model: `sentence-transformers/all-MiniLM-L6-v2` (384-dim)
   - Generate on note save, store in `graph_nodes.embedding` as BLOB
   - Background task to avoid blocking API response

2. **Semantic Edge Creation**
   - k-NN search for similar notes (cosine similarity)
   - Threshold: 0.7+ similarity → create `semantic` edge
   - Store similarity as edge weight

3. **Entity-Based Linking**
   - Notes sharing WHO entities → `entity_link` edges
   - Notes sharing WHAT entities → `entity_link` edges
   - Notes sharing tags → `tag_link` edges

4. **Clustering**
   - Load graph into NetworkX
   - Run Louvain community detection
   - Store `cluster_id` in graph_nodes
   - Generate cluster summaries via LLM

### Prerequisites
- ✅ Graph schema ready
- ✅ Phase 1 complete (notes with episodic metadata)
- ⏳ Choose embedding model
- ⏳ Implement background task system

---

## Phase 3: Prospective Layer - Time-Based Edges

**Status**: ⏸️ **NOT STARTED**

### Planned Components

1. **Future Time Detection**
   - Parse `graph_nodes.time_references` JSON
   - Filter for future dates (> current time)
   - Identify action-oriented language ("TODO", "need to", "call")

2. **Prospective Edge Creation**
   - Notes with future times → `time_next` edges (self-reminder)
   - Notes with same person + future time → `time_next` edges
   - Deadline notes → `reminder` edges with urgency weight

3. **Upcoming Actions API**
   - Endpoint: `GET /upcoming_actions`
   - Query: Follow `time_next` edges, sort by parsed time
   - Return: Sorted list of upcoming tasks/events with context

---

## Phase 4: Retrieval Layer - Hybrid Search

**Status**: ⏸️ **NOT STARTED**

### Planned Components

1. **Hybrid Search**
   - FTS5 full-text search (existing: `api/fts.py`)
   - Vector similarity search (cosine on embeddings)
   - Re-ranking: `score = 0.6 * cosine + 0.4 * fts_rank`

2. **Graph Expansion**
   - Start: Top-K search results (initial nodes)
   - Expand 1-2 hops via typed edges:
     - Priority 1: `entity_link` (shared entities)
     - Priority 2: `semantic` (similar content)
     - Priority 3: `time_next` (temporal context)
   - Return: Subgraph with contextual neighbors

3. **Context Assembly for LLM**
   - Assemble subgraph nodes as context
   - Rank by combined relevance score
   - Pass to LLM for synthesis/summarization

---

## Technical Decisions Made

### Clean Rewrite vs Incremental Migration
- **Chosen**: Clean rewrite, archive old code to `api/legacy/`
- **Why**: No production users, eliminates confusion, faster development
- **Trade-off**: Breaking change, but acceptable given no external users

### Entity vs Tag Distinction
- **Entities (WHO/WHAT/WHERE)**: Specific, concrete - "Sarah", "FAISS", "OAuth2"
- **Tags**: Broad, thematic - "meeting", "security", "ai-research"
- **Why**: Different granularities enable different linking strategies

### Hybrid Extraction Approach
- **LLM**: WHO/WHAT/WHERE (requires semantic understanding)
- **dateparser**: WHEN (rule-based more accurate: 0.944 vs 0.833 F1)
- **Validated**: 30-note comparison test (`docs/entity_extraction_research.md`)

### Database Architecture
- **SQLite**: Persistence, FTS5, ACID transactions
- **NetworkX**: In-memory graph for clustering/traversal (load on demand)
- **Why**: SQLite for durability, NetworkX for graph algorithms

### Edge Types
- `semantic`: Embedding cosine similarity (Phase 2)
- `entity_link`: Shared WHO/WHAT entities (Phase 2)
- `tag_link`: Shared thematic tags (Phase 2)
- `time_next`: Future temporal relationships (Phase 3)
- `reminder`: User-specified reminders (Phase 3)

---

## Next Steps

### Immediate (Start Phase 2)
1. **Choose embedding model**
   - Option A: `all-MiniLM-L6-v2` (384-dim, fast, good quality)
   - Option B: `bge-small-en-v1.5` (384-dim, SOTA quality)

2. **Implement background embedding generation**
   - FastAPI BackgroundTasks on `/capture_note`
   - Generate embedding after note saved
   - Update `graph_nodes.embedding`

3. **Build semantic linking**
   - k-NN search via NumPy/Faiss
   - Create `semantic` edges for similar notes
   - Threshold: 0.7+ cosine similarity

4. **Implement entity-based linking**
   - Query notes sharing WHO entities
   - Query notes sharing WHAT entities
   - Create `entity_link` edges

5. **Test clustering**
   - Load graph into NetworkX
   - Run Louvain algorithm
   - Store `cluster_id` in graph_nodes

### After Phase 2
1. Start Phase 3 (Prospective Layer)
2. Build `/upcoming_actions` endpoint
3. Create time-based edges

### After Phase 3
1. Start Phase 4 (Retrieval Layer)
2. Implement hybrid search (FTS5 + vector)
3. Build graph expansion logic
4. Test end-to-end retrieval quality

---

## Lessons Learned

1. **Research first, build second** - 30-note entity extraction test prevented bad architecture
2. **Clean rewrite > incremental migration** - For small projects with no users, clean slate is faster
3. **Archive old code, don't delete** - `api/legacy/` preserves institutional knowledge
4. **Test with real data early** - 4-note test caught extraction issues before full integration
5. **Document decisions** - Progress doc helps track "why" not just "what"
6. **Hybrid approaches work** - LLM + traditional NLP (dateparser) = best results

---

## Files Created/Modified

### Created (GraphRAG System)
- `api/main.py` (NEW - 162 lines) - Clean FastAPI with `/capture_note`
- `api/models.py` (NEW) - GraphRAG models only
- `api/services/episodic.py` (NEW) - Production entity extraction
- `api/db/graph.py` (NEW) - Graph node/edge helpers
- `docs/proposed_new_structure.md` - Architecture design
- `docs/graphrag_implementation_progress.md` - This file
- `test_phase1_endpoint.py` - Phase 1 test script
- `test_batch_import.py` - Batch import test for 30 notes

### Modified (Cleaned)
- `api/config.py` - Removed dimension configs (42 lines, was 84)
- `api/fts.py` - Removed dimension parameters, simplified
- `api/notes.py` - Removed dimension code, deleted legacy functions
- `api/db/schema.py` - Added graph_nodes and graph_edges tables

### Archived (`api/legacy/`)
- All old dimension-based code (main.py, models.py, services/, etc.)
- Research code (`entity_extraction.py`)
- Old utilities (graph.py, fts.py, notes.py, config.py)

---

**Last Updated**: 2025-10-20
**Current Phase**: Phase 1 ✅ Complete
**Next Milestone**: Phase 2 - Semantic Layer (embeddings & auto-linking)
