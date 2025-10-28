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

Implementing a local GraphRAG system with five layers:

1. **Episodic Layer** - Extract WHO/WHAT/WHEN/WHERE entities from notes ✅ **COMPLETE**
2. **Semantic Layer** - Create embeddings and auto-link via similarity ✅ **COMPLETE**
3. **Prospective Layer** - Extract future intentions as metadata (no edges) ✅ **COMPLETE**
4. **Clustering Layer** - Community detection with LLM summaries ✅ **COMPLETE** (Phase 2.5)
5. **Retrieval Layer** - Hybrid search (FTS5 + embeddings) with graph expansion ⏸️ NOT STARTED

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
- `graph_nodes`: Episodic + prospective metadata stored as JSON
  - `entities_who`: People, organizations
  - `entities_what`: Concepts, topics
  - `entities_where`: Locations
  - `time_references`: Parsed time objects
  - `tags`: Thematic categories
  - `prospective`: Prospective items (Phase 3 - metadata only)
    - `contains_prospective`: bool
    - `prospective_items`: [{content, timedata}]
  - `embedding`: Vector (Phase 2)
  - `cluster_id`: Community (Phase 2.5 - future)

- `graph_edges`: Typed relationships (Phase 2 only)
  - `semantic`: Embedding similarity
  - `entity_link`: Shared entities
  - `tag_link`: Shared tags

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

## Phase 3: Prospective Layer - Metadata-Only Approach ✅ **COMPLETE**

**Status**: ✅ **FULLY COMPLETE** (2025-10-21, Simplified 2025-10-21)

**Implementation**: Sequential LLM extraction of prospective items (actions, questions, plans) with WHEN timepoint linking - **metadata only, no graph edges**

### Design Evolution: From Edge-Based to Metadata-Only

**Original Approach** (Abandoned 2025-10-21):
- Edge-based prospective memory with three edge types:
  - `time_next`: Chronological linking (created 900 edges for 60 notes)
  - `reminder`: Shared deadline linking (created 125 edges)
  - `intention_trigger`: Event-based linking (created 20 edges)
- **Total**: 1,191 edges (900 + 125 + 20 + 146 Phase 2 edges)
- **User Feedback**: "tangled mess" - graph visualization was unreadable

**Timestamp Spread Experiment**:
- Spread 60 notes across 45 days (realistic distribution)
- Regenerated edges: 900 → 186 time_next edges (79% reduction)
- **Total**: 477 edges (186 + 125 + 20 + 146 Phase 2 edges)
- **User Feedback**: "slightly more loose hairball" - still not readable

**Root Cause**: O(n²) edge explosion
- `time_next` creates edges for all notes within 6hr-3day windows
- Week 1 (15 notes) → 63 edges alone
- Temporal proximity ≠ semantic relatedness
- Even with realistic timestamps, creates too many edges

**Final Decision**: **Metadata-only approach**
- Store prospective items as JSON in `graph_nodes`
- NO graph edges for prospective memory
- Enables todo-list view with timeline (future frontend)
- Keeps knowledge graph clean (146 Phase 2 edges only)

### Implemented Components

**1. Sequential LLM Extraction** ✅
- **Phase 3 runs AFTER Phase 1** (needs WHEN data from episodic layer)
- Phase 1 extracts episodic metadata → Phase 3 extracts prospective items
- Slight latency increase (~600ms vs 300ms parallel) acceptable for correctness
- Zero cost (local LLM)

**Prospective items extracted**:
```python
{
  "contains_prospective": bool,  # Does note contain future-oriented items?
  "prospective_items": [
    {
      "content": str,      # Action/question/plan description
      "timedata": str | null  # ISO timestamp from WHEN data, or null
    }
  ]
}
```

**Example**:
```python
# Input note:
"Met with Steve today. He suggested reconsidering Numpy for retrieval.
Need to evaluate this idea. Let me set up a meeting with Josh this Friday
to discuss."

# WHEN data from Phase 1 (episodic):
[{"original": "this Friday", "parsed": "2025-10-25T00:00:00", "type": "relative"}]

# Phase 3 output:
{
  "contains_prospective": true,
  "prospective_items": [
    {
      "content": "evaluate idea to replace Numpy",
      "timedata": null
    },
    {
      "content": "set up meeting with Josh",
      "timedata": "2025-10-25T00:00:00"
    }
  ]
}
```

**2. Metadata Storage Only** ✅
- Prospective data stored in `graph_nodes` episodic metadata JSON
- NO edge creation (abandoned `time_next`, `reminder`, `intention_trigger`)
- Clean knowledge graph (only Phase 2 semantic/entity/tag edges)

### Core Services

**`api/services/prospective.py` (simplified)**:
- `extract_prospective_items(text, when_data)` - LLM extraction with WHEN linking
- **Deleted functions** (from old edge-based approach):
  - `create_time_next_edges()` - Chronological linking
  - `create_reminder_edges()` - Shared deadline linking
  - `create_intention_trigger_edges()` - Event-based linking

**`api/main.py` (modified)**:
- Sequential execution: Phase 1 → Phase 3
- Prospective data merged into episodic metadata JSON
- Background task ONLY handles Phase 2 edges (semantic, entity_link, tag_link)

### Testing & Validation

**Benchmark Dataset**: 30 test cases with simplified ground truth

**Test Coverage**:
- Actions with deadlines (8 cases): "TODO: Call Sarah by Friday"
- Actions without deadlines (7 cases): "Need to research FAISS"
- Questions to answer (5 cases): "Should I migrate to PostgreSQL?"
- Future plans (4 cases): "Planning to implement OAuth2 next week"
- Pure observations (6 cases): No prospective items

**Ground Truth Format**:
```csv
note_id,note_text,expected_contains_prospective,expected_items
1,"Met with Sarah. Need to research vector search by Friday.",true,"[{""content"":""research vector search"",""timedata"":""2025-10-25T00:00:00""}]"
```

### Benchmark Test Results

**Status**: Tests created, pending execution

**Test Script**: `test_phase3_prospective.py` (305 lines, rewritten)

**Metrics to measure**:
- `contains_accuracy`: True/false detection of prospective items
- `item_count_accuracy`: Correct number of items extracted
- `timedata_linking_accuracy`: Correct matching to WHEN timepoints

**Previous benchmark** (old edge-based approach):
- is_action F1: 0.818
- is_question F1: 0.923
- is_plan F1: 0.714

### Architecture Decisions

**1. Metadata-Only (No Edges)**:
- **Decision**: Store prospective items as JSON, not graph edges
- **Why**: Prospective memory (task management) pollutes knowledge graph
- **Trade-off**: No graph traversal for prospective items, but cleaner graph visualization
- **Future**: Todo-list view in frontend using metadata

**2. Sequential Processing (Phase 1 → Phase 3)**:
- **Decision**: Run Phase 3 AFTER Phase 1 completes
- **Why**: Phase 3 needs WHEN timepoints from Phase 1
- **Trade-off**: ~600ms total (vs ~300ms parallel), acceptable for correctness

**3. LLM Timepoint Matching**:
- **Decision**: LLM directly matches prospective items to WHEN data
- **Why**: Semantic understanding needed ("meeting this Friday" → links to "Friday" timepoint)
- **Alternative considered**: Rule-based matching (too brittle)

**4. Generic Prompt Examples**:
- **Decision**: Use placeholder examples, not specific ones
- **Why**: Small LLM (qwen3:4b) may overfit to specific examples
- **Example**: `{"content": "<action description>", "timedata": "<ISO timestamp or null>"}`

**5. Scope Expansion**:
- **Decision**: Include "questions to answer" in prospective items
- **Why**: Questions represent future knowledge gaps needing resolution
- **Examples**: "Should I migrate DB?" "How to optimize this query?"

### Database Cleanup

**Edge Deletion** (2025-10-21):
```sql
-- Before cleanup:
SELECT relation, COUNT(*) FROM graph_edges GROUP BY relation;
-- entity_link: 34, intention_trigger: 20, reminder: 125,
-- semantic: 34, tag_link: 78, time_next: 186
-- TOTAL: 477 edges

-- Cleanup:
DELETE FROM graph_edges WHERE relation IN ('time_next', 'reminder', 'intention_trigger');

-- After cleanup:
-- entity_link: 34, semantic: 34, tag_link: 78
-- TOTAL: 146 edges (69% reduction)
```

**Graph Visualization**:
- Before: "tangled mess" (1,191 edges) → "slightly more loose hairball" (477 edges)
- After: Clean, readable graph (146 edges only)

### Files Created/Modified

**New Files**:
- ✅ `test_data/phase3_prospective_benchmark.csv` - 30 simplified test cases
- ✅ `test_phase3_prospective.py` (305 lines, rewritten) - Metadata-only testing

**Modified Files**:
- ✅ `api/services/prospective.py` - Rewritten for metadata-only approach
- ✅ `api/main.py` - Changed to sequential extraction, removed edge creation

**Deleted Files** (abandoned edge-based approach):
- ❌ `test_phase3_edges.py` - Edge validation script
- ❌ `scripts/regenerate_time_next_edges.py` - Edge regeneration utility
- ❌ `test_data/phase3_test_notes_labeled.csv` - Old benchmark with is_action/is_question/is_plan
- ❌ `test_data/phase3_edge_*` - All edge test reports

### Key Insights

**1. Prospective memory ≠ Knowledge graph**:
- Tasks are ephemeral, knowledge is permanent
- Mixing task management with knowledge building pollutes the graph
- Separate concerns: Metadata for prospective, edges for semantic relationships

**2. Temporal proximity ≠ Semantic relatedness**:
- Notes written close in time aren't necessarily related in meaning
- `time_next` edges created O(n²) connections with little value
- Better use: Temporal signal as weight modifier in retrieval (Phase 4)

**3. Graph visualization is critical**:
- "Tangled mess" and "slightly more loose hairball" forced design rethink
- User can't use a graph they can't visualize
- 146 edges (Phase 2 only) creates clean, readable graph

**4. Small LLMs prefer generic prompts**:
- Specific examples → overfitting risk for 4B parameter models
- Generic placeholders → better generalization
- Validated by qwen3:4b-instruct performance

### Next Steps

**Immediate**:
- ✅ Simplified extraction implemented
- ✅ Tests created (benchmark pending execution)
- ✅ Database cleaned up (prospective edges deleted)
- ⏳ Run benchmark test to validate accuracy

**Future Frontend Work**:
- Todo-list view: Display prospective items from metadata
- Timeline view: Show items with timedata chronologically
- Integration with graph view: Link to source notes

**Future Phases**:
- **Phase 4**: Retrieval layer (hybrid search + graph expansion)
  - Use temporal proximity as weight modifier (not standalone edges)
  - Phase 3 metadata enables "show me upcoming actions" queries

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
- ~~`time_next`: Future temporal relationships (Phase 3)~~ **DELETED** (metadata-only approach)
- ~~`reminder`: User-specified reminders (Phase 3)~~ **DELETED** (metadata-only approach)
- ~~`intention_trigger`: Event-based triggers (Phase 3)~~ **DELETED** (metadata-only approach)

---

## Phase 2.5: Clustering Layer ✅ **COMPLETE**

**Status**: ✅ **FULLY COMPLETE** (2025-10-27)
**Duration**: ~4 hours

### Implementation Summary

Added community detection to identify thematic clusters in the note graph using NetworkX Louvain algorithm.

### What Was Built

**1. Clustering Service** (`api/services/clustering.py` - 364 lines)
- `build_networkx_graph()` - Converts DB edges to NetworkX graph
- `detect_communities()` - Louvain algorithm with configurable resolution
- `assign_cluster_ids()` - Updates `graph_nodes.cluster_id`
- `generate_cluster_summary()` - LLM generates title + summary for each cluster
- `store_cluster_summary()` - Persists cluster metadata
- `run_clustering()` - Full pipeline orchestration

**2. Database Schema Updates**
- Added `graph_clusters` table:
  - `id` (INTEGER PRIMARY KEY)
  - `title` (TEXT) - Short 3-5 word title for UI display
  - `summary` (TEXT) - LLM-generated 1-2 sentence summary
  - `size` (INTEGER) - Number of notes in cluster
  - `created`, `updated` (TEXT)
- `cluster_id` column already existed in `graph_nodes` (Phase 2 prep)

**3. API Endpoints** (added to `api/main.py`)
- `POST /graph/cluster?resolution=1.0` - Run clustering on entire graph
- `GET /graph/clusters` - List all clusters with metadata
- `GET /graph/clusters/{cluster_id}` - Get detailed cluster info with all nodes

**4. LLM Integration**
- JSON format for structured output (title + summary)
- Fixed `get_llm()` sentinel pattern to properly handle `format=None` vs not passing format
- Prompt engineered for concise titles (3-5 words) and summaries (1-2 sentences)

### Test Results (59-note test dataset)

```
Nodes: 59
Edges: 30 (semantic: 12, entity_link: 19, tag_link: 3)
Clusters: 35

Cluster Distribution:
- 3 large clusters (5 notes each)
- 5 medium clusters (3-4 notes each)
- 3 small clusters (2 notes each)
- 24 singleton clusters (1 note each)
```

**Example Clusters Generated:**

| Cluster ID | Title | Summary | Size |
|------------|-------|---------|------|
| 10 | "Predictive AI for Notes" | Explores AI proactive retrieval before searches using GraphRAG and sentence transformers | 5 notes |
| 2 | "Momo: Design and Creation" | Character design and note-taking tool implementation | 4 notes |
| 34 | "Memory Consolidation Process" | Neural mechanisms of memory consolidation during sleep | 4 notes |

**Why Many Singletons?**
- Test dataset has diverse, unrelated synthetic notes
- Real personal notes will cluster better (work projects, hobbies, family themes)
- Sparse connectivity (30 edges / 59 nodes = 0.51 edges/node avg)

### Key Design Decisions

**1. JSON Format for Cluster Summaries**
- Initially tried plain text, but UI needs both title and summary
- Reverted to JSON with structured `{title, summary}` format
- Allows clean separation: title for sidebar, summary for details

**2. Sentinel Pattern Fix in `get_llm()`**
- Problem: `get_llm(format=None)` wasn't creating new instance (returned singleton with JSON)
- Solution: Used `_UNSET = object()` sentinel to detect if parameter was explicitly passed
- Now `get_llm(format=None)` correctly creates plain text instance

**3. Louvain Algorithm Choice**
- **Why**: Best modularity-based community detection
- **Resolution parameter**: Higher = more clusters, lower = fewer larger clusters
- **Default**: 1.0 (good balance for most graphs)

**4. Storage Strategy**
- Cluster metadata in separate `graph_clusters` table (not JSON in nodes)
- Enables efficient queries for cluster lists and sizes
- LLM summaries regenerated on each clustering run (cheap with local LLM)

### Files Created/Modified

**Created:**
- `api/services/clustering.py` (364 lines) - Complete clustering implementation
- `scripts/test_clustering.py` - Test script for clustering pipeline

**Modified:**
- `api/db/schema.py` - Added `graph_clusters` table with title field
- `api/main.py` - Added 3 clustering endpoints
- `api/llm/client.py` - Fixed sentinel pattern for format parameter

### API Usage Examples

```bash
# Run clustering
curl -X POST http://localhost:8732/graph/cluster?resolution=1.0

# List all clusters
curl http://localhost:8732/graph/clusters

# Get cluster details
curl http://localhost:8732/graph/clusters/10
```

### Performance

- **Graph building**: <50ms (59 nodes, 30 edges)
- **Louvain detection**: <100ms
- **LLM summaries**: ~500ms per cluster × 35 clusters = ~17s total
- **Total clustering time**: ~20s for 59 notes

---

## Next Steps

### Phase 4 - Retrieval Layer (NOT STARTED)

**Hybrid Search Implementation:**
1. Combine FTS5 full-text + vector similarity
2. Re-ranking algorithm
3. Graph expansion (1-2 hops from top results)
4. Cluster-aware retrieval (search within clusters)

**Context Assembly for LLM:**
1. Assemble subgraph as context
2. Include cluster summaries for context
3. Pass to LLM for synthesis/Q&A

---

## Lessons Learned

### Phase 1, 2, 3 & 2.5 Insights

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
11. **Visualize early, iterate fast** - Graph visualization ("tangled mess") revealed edge explosion problem
12. **Separate concerns matter** - Prospective memory (tasks) ≠ knowledge graph (semantic relationships)
13. **Metadata vs edges trade-off** - Not everything needs to be a graph edge; metadata works for retrieval
14. **User feedback is gold** - "Slightly more loose hairball" forced fundamental rethink
15. **Sentinel pattern for optional params** - Use `_UNSET = object()` to distinguish `None` from not passed
16. **JSON vs plain text LLM output** - Singleton pattern with default `format="json"` needs careful handling
17. **UI needs drive data structure** - Added cluster titles when realized sidebar needs short labels
18. **Test data ≠ production data** - Synthetic notes create more singletons than real personal notes

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

**Last Updated**: 2025-10-27
**Current Phase**: Phase 2.5 ✅ Complete (Clustering)
**Next Milestone**: Phase 4 (Retrieval Layer)

---

## Phase Summary

✅ **Phase 1: Episodic** - WHO/WHAT/WHERE/WHEN extraction (Hybrid LLM + dateparser)
✅ **Phase 2: Semantic** - Embeddings + 3 edge types (semantic, entity_link, tag_link)
✅ **Phase 3: Prospective** - Metadata-only extraction (actions, questions, plans with WHEN linking)
✅ **Phase 2.5: Clustering** - Community detection with LLM-generated titles + summaries
⏸️ **Phase 4: Retrieval** - Hybrid search + graph expansion (NOT STARTED)

**Total Edge Types**: 3 (semantic, entity_link, tag_link) - Phase 3 is metadata-only
**LLM Architecture**: Sequential Phase 1 → Phase 3 extraction (~600ms total)
**Background Processing**: Phase 2 edge creation only (~2-3s async)
**Clustering**: On-demand via API endpoint (~20s for 59 notes)
