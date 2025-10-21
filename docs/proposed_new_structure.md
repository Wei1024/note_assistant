Here’s your **final, updated backend-only concept summary** — now including the **FTS5 integration** and hybrid retrieval clarification throughout.

---

# Local GraphRAG Notes System — Concept Summary (Backend-Only)

## 🎯 Objectives

* Fully **local** knowledge system.
* Capture short notes → extract structured metadata (**episodic**) → link via embeddings (**semantic**) → detect upcoming items (**prospective**).
* Persist to disk while enabling fast, graph-style reasoning in memory.

---

## 🧱 Architecture (Layers)

```
User Notes
   ↓
[1] Episodic Layer
   • Extract structured metadata from each note.
   • Entities = concrete details (who, what, when, where) — specific people, places, times, or objects mentioned.
   • Tags = broader thematic or user-defined categories (e.g., “meeting”, “security”, “app-dev”).
   • Store both in metadata; they become linkable attributes for graph edges
     (entity_link for shared entities, tag_link for shared tags).

   ↓
[2] Semantic Layer
   • Create text embeddings.
   • Auto-link notes by cosine similarity and shared entities/tags.
   • Optionally cluster related notes and generate cluster summaries.

   ↓
[3] Prospective Layer
   • Parse future timestamps or “todo/next” intents.
   • Create time-linked edges (reminders/upcoming).

   ↓
[4] Retrieval Layer (Backend)
   • Query → hybrid search (FTS5 + embeddings) → expand subgraph (1–2 hops).
   • Provide subgraph + ranked context for reasoning or summarization.
```

---

## 🗃️ Storage & Runtime

* **SQLite (on disk)** = long-term store

  * Tables: `nodes`, `edges`, `embeddings` (or embed inside `nodes`)
  * **FTS5 virtual table**: `idx_nodes_text(id, text)` for keyword and phrase search

    * Keep synchronized on note insert/update/delete.
  * Optional: sqlite-vss/pgvector/Qdrant (local) for ANN vector search

* **NetworkX (in memory)** = working/“reasoning” graph

  * Load from SQLite on startup; run clustering, traversals, neighborhoods
  * Write back cluster IDs / derived edges

SQLite persists; NetworkX thinks.

---

## 📑 Minimal Data Model

### `nodes`

| id | text | ts | entities | tags | embedding | cluster_id |
| -- | ---- | -- | -------- | ---- | --------- | ---------- |

### `edges`

| src                                                                                | dst | relation | weight |
| ---------------------------------------------------------------------------------- | --- | -------- | ------ |
| Typical relations: `semantic`, `entity_link`, `tag_link`, `time_next`, `reminder`. |     |          |        |

### `idx_nodes_text` (FTS5 virtual)

| id                                                       | text |
| -------------------------------------------------------- | ---- |
| For keyword and phrase search; used in hybrid retrieval. |      |

---

## 🔁 Core Backend Flows

### 1️⃣ Ingest (Episodic)

* Save raw note + timestamp + extracted entities/tags.
* Entities capture **specific details** (who/what/when/where).
* Tags describe **broader themes** (e.g., meeting, idea, project).
* Both are stored in metadata and used for graph linking.

### 2️⃣ Embed & Link (Semantic)

* Generate embedding (local sentence-transformer).
* k-NN search vs existing embeddings → create `semantic` edges.
* Add `entity_link` or `tag_link` edges for shared metadata.
* Cluster & summarize periodically.

### 3️⃣ Prospective Detection

* Scan for future times or “todo” language → create `time_next` edges.
* List upcoming events or reminders.

### 4️⃣ Retrieval

* **Hybrid retrieval**: combine

  * **FTS5** full-text matches (keyword/phrase search) and
  * **vector** similarity matches (semantic retrieval).
* Merge and re-rank by a weighted score (e.g., 0.6 cosine + 0.4 FTS rank).
* Expand 1–2 hops (semantic + entity + time edges).
* Return subgraph + ranked nodes + (optional) generated summary.

---

## 🔍 Retrieval Strategies

Hybrid keyword + vector search → assemble context by:

1. Union of FTS5 results and ANN vector results.
2. Re-rank by combined similarity + recency.
3. Expand graph by neighbor relations (`entity_link` > `semantic` > `time_next`).
4. Deduplicate; return a subgraph ready for visualization or summarization.

---

## 🧠 Memory Analogy

| Human       | System                                       |
| ----------- | -------------------------------------------- |
| Episodic    | SQLite records with entities/tags/timestamps |
| Semantic    | Embeddings, semantic edges, clusters         |
| Prospective | Time-linked edges & reminder scans           |
| Working     | On-demand NetworkX subgraphs for reasoning   |

---

## 🔐 Local-Only Practices

* Bind API to `127.0.0.1`.
* Use local LLMs and embedding models (Ollama / sentence-transformers).
* No external calls or telemetry.
* Optional database encryption.

---

## 🧩 Extensibility

* Swap embeddings (MiniLM → BGE).
* Upgrade ANN backend (NumPy → sqlite-vss → Qdrant).
* Retain FTS5 for hybrid recall and precision.
* Migrate NetworkX → Neo4j if scale increases.
* Add new edge types (`supports`, `contradicts`).

---

## ✅ Typical Backend Behavior

* **Add note** → extract entities/tags → embed → index text in FTS5 → auto-link → persist.
* **Ask “what’s next with Collin?”** → hybrid search → find Collin cluster → follow `time_next` edges → return upcoming actions.
* **Ask “summarize my app-security work”** → retrieve hybrid results → expand graph → generate summary.

---

> **Entities = specific details (who/what/when/where).**
> **Tags = broader categories or themes.**
> **FTS5** adds keyword and phrase recall, complementing embeddings for hybrid retrieval.
> Together, these layers make the system structured, searchable, and intelligent — all running locally.

---

## 🤖 Claude's Feedback

### Validation Against Research Findings

**Alignment with entity extraction study (docs/entity_extraction_research.md):**
- ✅ Entity-first design matches our 0.691-0.944 F1 research results
- ✅ Hybrid LLM (WHO/WHAT/WHERE) + dateparser (WHEN) = optimal approach
- ✅ Tags vs entities distinction solves concept granularity problem we encountered
- ✅ Episodic layer directly uses our validated extraction methods

### Key Strengths

1. **Cognitively Grounded**: Human memory model (episodic/semantic/prospective) is not naive—it's neuroscience-backed and maps perfectly to graph operations.

2. **Solves Old System Problems**:
   - Dimension-based classification (43.3% accuracy) → Entity-based linking (69-94% accuracy)
   - Manual LLM link suggestions (expensive) → Automatic semantic edges (fast)
   - FTS5-only search → Hybrid retrieval (precision + recall)

3. **Novel Innovations**:
   - **Tags vs Entities**: Different granularities for different linking needs (theme vs specific)
   - **Prospective Memory**: Time-based edges for future actions (research didn't cover this)
   - **SQLite + NetworkX Split**: Persistence + reasoning (pragmatic architecture)

4. **State-of-the-Art RAG**: Hybrid retrieval with re-ranking (0.6 cosine + 0.4 FTS) is modern best practice.

### Implementation Considerations

**Phase 1 (Episodic Layer):**
- Use validated extraction: LLM for WHO/WHAT/WHERE, dateparser for WHEN
- Simplified schema: `nodes` table (text, entities, tags, timestamp)
- Keep existing `notes_entities` table for storage, migrate to graph schema later

**Potential Challenges:**
1. **Entity Quality**: 0.691 F1 on WHAT means 30% error rate → Allow manual entity editing
2. **Graph Scale**: Load-all works for <100k notes; consider lazy-loading later
3. **Clustering Stability**: Make on-demand initially (don't auto-cluster on every note)
4. **k-NN Performance**: NumPy works for 1k notes; add FAISS/sqlite-vss at scale

**Tech Stack Validation:**
- ✅ SQLite: Proven for local persistence, FTS5 excellent
- ✅ NetworkX: Perfect for <10k nodes, fast algorithms
- ✅ sentence-transformers: MiniLM good starting point (384-dim, fast)
- ✅ Local-first: Ollama + dateparser = no external dependencies

### Recommended Approach

**Don't create new api folder** - Rewrite existing:
- Old system uses `api/services/capture.py` + `api/services/enrichment.py`
- New system simplifies to `api/services/episodic.py` (extraction only)
- Semantic/prospective layers come later as separate services
- Keep `api/db/`, `api/llm/` infrastructure (already working)

**Migration Path:**
1. Backup old services to `api/services/deprecated/`
2. Create `api/services/episodic.py` with entity extraction
3. Modify endpoint to use new service
4. Test with same 30-note dataset
5. Compare quality vs old system
