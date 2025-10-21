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
2. **Semantic Layer** - Create embeddings and auto-link via similarity ✅ **COMPLETE**
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

## Phase 2: Semantic Layer - Embeddings & Auto-Linking ✅ **COMPLETE**

**Status**: ✅ **FULLY COMPLETE** (2025-10-21)

**Implementation**: Embedding generation, vector similarity search, entity linking, tag linking fully operational.

### Implemented Components

1. **Embedding Generation** ✅
   - Model: `sentence-transformers/all-MiniLM-L6-v2` (384-dim, ~200MB)
   - Generates normalized embeddings on note save
   - Stored in `graph_nodes.embedding` as BLOB
   - FastAPI BackgroundTasks (non-blocking, runs after response sent)

2. **Semantic Edge Creation** ✅
   - NumPy brute-force cosine similarity search
   - Threshold: **0.5+** similarity → create `semantic` edge (adjusted from initial 0.7)
   - Edge weight = cosine similarity score
   - Migration path to FAISS ready for 5K+ notes

3. **Entity-Based Linking** ✅
   - Notes sharing **WHO** entities → `entity_link` edges
   - Notes sharing **WHAT** entities → `entity_link` edges
   - Notes sharing **WHERE** entities → `entity_link` edges (added during implementation)
   - Edge weight = number of shared entities (1 = weak, 5 = strong)
   - Case-insensitive normalization ("Sarah" = "sarah")

4. **Tag-Based Linking** ✅
   - Notes sharing tags → `tag_link` edges
   - Jaccard similarity threshold: **>= 0.3**
   - Edge weight = Jaccard coefficient (0.3 to 1.0)
   - Normalization handles "ai-research" = "AI Research" = "ai_research"

5. **Clustering** ⏸️ **DEFERRED TO PHASE 2.5**
   - NetworkX dependency added
   - Will implement: Louvain community detection
   - Will store: `cluster_id` in graph_nodes
   - Will generate: LLM cluster summaries

### Core Services

**`api/services/semantic.py` (177 lines)**:
- `get_embedding_model()` - Singleton model loader
- `generate_embedding(text)` - 384-dim vector generation
- `store_embedding(note_id, embedding, con)` - BLOB storage
- `find_similar_notes(note_id, threshold, limit)` - NumPy cosine similarity
- `create_semantic_edges(note_id, con)` - Auto-link similar notes

**`api/services/linking.py` (231 lines)**:
- `normalize_entity(entity)` - Case-insensitive normalization
- `normalize_tag(tag)` - Handle delimiters ("ai-research" = "AI Research")
- `find_shared_entities(entities_a, entities_b)` - Overlap detection
- `calculate_tag_similarity(tags_a, tags_b)` - Jaccard coefficient
- `create_entity_links(note_id, con)` - Link on WHO/WHAT/WHERE
- `create_tag_links(note_id, con)` - Link on shared tags

**`api/main.py` (modified)**:
- Added `BackgroundTasks` to `/capture_note` endpoint
- `process_semantic_and_linking(note_id)` - Background processor
- Non-blocking: API returns immediately (~500ms), edges created async (~2-3s)

### Testing & Validation

✅ **Test Dataset**: 30 diverse notes (health, tech, personal, work, research)
✅ **Embedding Generation**: 100% success rate (all 30 notes have embeddings)
✅ **Edge Creation**: 15 total edges created

**Edge Breakdown (30 notes)**:
| Edge Type | Count | Weight Range | Examples |
|-----------|-------|--------------|----------|
| `semantic` | 2 | 0.594-0.602 | Dental ↔ Doctor appointment, Memory research notes |
| `entity_link` | 3 | 1.0-2.0 | Shared ["memory consolidation", "hippocampus"], Shared ["Sarah"] |
| `tag_link` | 10 | 0.333-1.0 | Shared ["health", "appointment", "planning"] |

**Validation Results**:
- ✅ All links manually verified against note content
- ✅ Normalization working correctly (case-insensitive, delimiter-agnostic)
- ✅ No false positives (dissimilar notes correctly NOT linked)
- ✅ Weight system accurate (reflects link strength)
- ✅ Metadata rich (shared entities/tags stored for debugging)

**Performance** (30 notes):
- Embedding generation: ~1-2s per note
- Similarity search: <100ms (NumPy brute-force)
- Entity linking: ~50-100ms
- Total background task: ~2-3s per note

### Test Scripts Created

1. **`test_phase2_semantic.py`** (95 lines)
   - Tests embedding generation
   - Verifies similarity computation
   - Checks embeddings in database

2. **`test_phase2_linking.py`** (313 lines)
   - Imports 30 test notes via API
   - Waits for background processing
   - Analyzes edge creation
   - Generates reports: CSV, TXT, JSON

3. **`reprocess_semantic_edges.py`** (utility)
   - Reprocesses semantic edges with new threshold
   - Used when adjusting similarity threshold

**Test Reports Generated**:
- `test_data/phase2_edges_<timestamp>.csv`
- `test_data/phase2_linking_report_<timestamp>.txt`
- `test_data/phase2_linking_results_<timestamp>.json`

### Architecture Decisions Made

**1. Vector Search: NumPy (Now) → FAISS (Future)**
- **Decision**: Start with NumPy brute-force
- **Rationale**: Fast enough for <1K notes, simple implementation
- **Migration Path**: Swap to FAISS when scaling to 5K+ notes (~2-3 hour effort)

**2. Semantic Similarity Threshold: 0.5 (adjusted from 0.7)**
- **Initial**: 0.7 threshold (too strict for real-world notes)
- **Observed**: Highest similarity ~0.6 for related notes
- **Adjusted**: 0.5 threshold captures meaningful relationships
- **Validation**: 2 semantic edges created, both manually validated as correct

**3. Entity Linking on WHO/WHAT/WHERE (not WHEN)**
- **Decision**: Link on WHO/WHAT/WHERE, defer WHEN to Phase 3
- **Rationale**: WHEN creates temporal/directional relationships (different semantics)
- **Phase 3**: Will handle time-based edges (`time_next`) separately

**4. Edge Storage: Unidirectional**
- **Decision**: Store once (A→B where A.id < B.id lexicographically)
- **Rationale**: Avoid duplication, easier consistency
- **Query**: Bidirectional (`WHERE src_node_id = X OR dst_node_id = X`)

**5. "A Link is a Link" Philosophy**
- **Decision**: Create edges for ANY shared entity/tag (even just 1)
- **Weight System**: Reflects link strength (1 shared = weak, 5 shared = strong)
- **Rationale**: Mirrors human memory (associative connections of varying strength)

### Key Insights

**Why semantic edges are rare?**
- Real notes have **moderate similarity** (0.3-0.6 range), not high (0.7+)
- Even topically related notes differ in phrasing, focus, detail
- This is **normal** for sentence-transformers
- Threshold 0.5 is appropriate (catches related notes, avoids false positives)

**Why tag links dominate?**
- LLM generates **broad thematic tags** that naturally overlap
- Tags like "planning", "meeting", "technology" appear across multiple notes
- Creates more connections than specific entity matching

**Why few entity links in test?**
- Test notes are **intentionally diverse** (different people/topics/locations)
- Real usage with recurring people/topics will increase entity links
- 3 entity links for 30 diverse notes is expected

### Files Created/Modified

**New Files**:
- ✅ `api/services/semantic.py` (177 lines)
- ✅ `api/services/linking.py` (231 lines)
- ✅ `test_phase2_semantic.py` (95 lines)
- ✅ `test_phase2_linking.py` (313 lines)
- ✅ `reprocess_semantic_edges.py` (utility script)
- ✅ `PHASE2_IMPLEMENTATION.md` (documentation)

**Modified Files**:
- ✅ `requirements.txt` - Added sentence-transformers, scikit-learn, networkx
- ✅ `api/main.py` - Added BackgroundTasks, process_semantic_and_linking()

**Dependencies Added**:
- `sentence-transformers` (~200MB with model)
- `scikit-learn` (cosine similarity)
- `networkx` (for future clustering)

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

### Immediate Options

**Option A: Phase 2.5 - Clustering**
1. **Implement NetworkX clustering**
   - Load graph from database
   - Run Louvain community detection
   - Store `cluster_id` in graph_nodes
   - Generate LLM cluster summaries

2. **Add clustering endpoints**
   - `POST /graph/cluster_all` - Trigger clustering
   - `GET /graph/cluster/{cluster_id}` - Get cluster notes
   - `GET /graph/cluster_summary/{cluster_id}` - Get LLM summary

**Option B: Phase 3 - Prospective Layer**
1. **Implement time-based edge detection**
   - Parse future dates from `graph_nodes.time_references`
   - Create `time_next` edges for upcoming actions
   - Create `reminder` edges for deadlines

2. **Build upcoming actions endpoint**
   - `GET /upcoming_actions` - List future tasks/events
   - Sort by parsed time
   - Include contextual note info

**Option C: Phase 4 - Retrieval Layer**
1. **Hybrid search implementation**
   - Combine FTS5 + vector similarity
   - Re-ranking algorithm
   - Graph expansion (1-2 hops)

2. **Context assembly for LLM**
   - Assemble subgraph as context
   - Pass to LLM for synthesis/Q&A

---

## Lessons Learned

### Phase 1 & 2 Insights

1. **Research first, build second** - 30-note entity extraction test prevented bad architecture
2. **Clean rewrite > incremental migration** - For small projects with no users, clean slate is faster
3. **Archive old code, don't delete** - `api/legacy/` preserves institutional knowledge
4. **Test with real data early** - 4-note test caught extraction issues before full integration
5. **Document decisions** - Progress doc helps track "why" not just "what"
6. **Hybrid approaches work** - LLM + traditional NLP (dateparser) = best results
7. **Don't over-optimize prematurely** - NumPy works fine for <1K notes, FAISS can wait
8. **Real-world thresholds differ from theory** - 0.7 similarity too strict, 0.5 is appropriate
9. **Validate with actual content** - Manual review of edges caught threshold issues early
10. **"A link is a link" philosophy** - Weight system captures varying connection strengths naturally

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

**Last Updated**: 2025-10-21
**Current Phase**: Phase 2 ✅ Complete (Semantic Layer)
**Next Milestone**: Phase 2.5 (Clustering), Phase 3 (Prospective), or Phase 4 (Retrieval)
