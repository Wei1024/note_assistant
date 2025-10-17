# Note Assistant API Documentation

**Base URL:** `http://localhost:8734`
**Version:** 1.0
**Last Updated:** 2025-10-16

A FastAPI-based backend for a multi-dimensional note-taking system with LLM-powered classification, enrichment, and knowledge graph linking.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [Endpoints](#endpoints)
   - [Health Check](#health-check)
   - [Note Capture](#note-capture)
   - [Search](#search)
   - [Consolidation (Linking)](#consolidation-linking)
   - [Graph Traversal](#graph-traversal)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)
6. [Performance](#performance)

---

## Quick Start

### Start the API Server

```bash
cd /path/to/note_assistant
source .venv/bin/activate
python -m uvicorn api.main:app --host 0.0.0.0 --port 8734
```

### Health Check

```bash
curl http://localhost:8734/health
# Response: {"status": "ok", "model": "qwen3:4b-instruct"}
```

### Capture Your First Note

```bash
curl -X POST http://localhost:8734/classify_and_save \
  -H "Content-Type: application/json" \
  -d '{"text": "Meeting with Sarah tomorrow about the authentication refactor"}'
```

---

## Core Concepts

### Multi-Dimensional Classification

Notes are classified using **5 independent boolean dimensions** (not folders):

| Dimension | Description | Example |
|-----------|-------------|---------|
| `has_action_items` | Contains tasks/todos | "Fix the login bug" |
| `is_social` | Involves conversations | "Meeting with Sarah" |
| `is_emotional` | Expresses feelings | "Feeling frustrated about..." |
| `is_knowledge` | Contains learnings | "Python async event loop works by..." |
| `is_exploratory` | Brainstorming/ideas | "What if we used graph DB instead?" |

**Notes can have multiple dimensions simultaneously** (e.g., a meeting note can be both `is_social=true` AND `has_action_items=true`).

### Enrichment Metadata

The LLM automatically extracts:
- **People**: Names mentioned in the note
- **Entities**: Topics, tools, technologies, concepts
- **Emotions**: Specific emotion words (excited, frustrated, curious, etc.)
- **Time References**: Meeting times, deadlines, dates

### Knowledge Graph

Notes are automatically linked via consolidation:
- **Link types**: `related`, `spawned`, `references`, `contradicts`
- **Bidirectional**: Links work both ways
- **LLM-suggested**: AI analyzes content and shared metadata to propose connections

---

## Endpoints

### Health Check

**GET** `/health`

Check if the API server is running and which LLM model is configured.

**Response:**
```json
{
  "status": "ok",
  "model": "qwen3:4b-instruct"
}
```

---

### Note Capture

#### 1. Classify and Save Note

**POST** `/classify_and_save`

Captures a note with full LLM classification and enrichment. This is the **primary endpoint** for creating notes.

**Request Body:**
```json
{
  "text": "Meeting with Sarah tomorrow at 3pm to discuss the new authentication system. She suggested using OAuth2 with JWT tokens."
}
```

**Response:**
```json
{
  "title": "Meeting with Sarah on authentication",
  "dimensions": {
    "has_action_items": false,
    "is_social": true,
    "is_emotional": false,
    "is_knowledge": true,
    "is_exploratory": false
  },
  "tags": ["meeting", "authentication", "oauth2", "jwt"],
  "path": "/Users/you/Notes/2025-10-16-meeting-with-sarah-on-authentication.md"
}
```

**Processing Flow:**
1. LLM classifies note (dimensions, title, tags, status)
2. LLM enriches metadata (people, entities, emotions, time refs)
3. Markdown file created in flat structure
4. Database indexed (FTS5 + metadata tables)
5. Returns classification result

**Duration:** ~3-5 seconds (LLM-dependent)

---

#### 2. Save Journal Entry

**POST** `/save_journal`

Quick capture without full enrichment. Useful for simple journal entries.

**Request Body:**
```json
{
  "text": "Feeling really productive today!"
}
```

**Response:** Same as `/classify_and_save`

**Difference:** Skips enrichment step, faster but less metadata.

---

### Search

#### 1. Smart Search (Natural Language)

**POST** `/search_smart`

Natural language search that parses intent and searches across multiple dimensions.

**Request Body:**
```json
{
  "query": "meetings about Sarah where I felt excited",
  "limit": 10
}
```

**What it understands:**
- **People**: "notes about Sarah" → searches person entities
- **Emotions**: "where I felt excited" → filters by emotion dimension
- **Context**: "meetings" → filters `is_social=true`
- **Entities**: "about FAISS" → searches entity mentions
- **Keywords**: Falls back to FTS5 for remaining terms

**Response:**
```json
[
  {
    "path": "/Users/you/Notes/2025-10-16-meeting-with-sarah.md",
    "snippet": "Meeting with <b>Sarah</b> today was amazing...",
    "score": 0.95,
    "metadata": {
      "created": "2025-10-16T15:30:00-07:00",
      "dimensions": {
        "has_action_items": false,
        "is_social": true,
        "is_emotional": true,
        "is_knowledge": false,
        "is_exploratory": false
      }
    }
  }
]
```

---

#### 2. Synthesis (Summarize Findings)

**POST** `/synthesize`

Synthesizes search results into a coherent summary that answers your natural language question. Combines smart search with LLM-powered summarization.

**Request Body:**
```json
{
  "query": "what did I learn about memory consolidation?",
  "limit": 10
}
```

**Response:**
```json
{
  "query": "what did I learn about memory consolidation?",
  "summary": "Based on your notes, you learned that memory consolidation happens primarily during sleep, when the hippocampus replays memories and transfers them to long-term storage. Note 1 mentions a conversation with Sarah about how this process mirrors software caching patterns. Note 2 explores the idea of applying these neuroscience principles to note-taking systems...",
  "notes_analyzed": 3,
  "search_results": [
    {
      "path": "/Users/you/Notes/2025-10-16-memory-consolidation.md",
      "snippet": "Memory <b>consolidation</b> during sleep...",
      "score": 0.95,
      "metadata": {...}
    }
  ]
}
```

**How it works:**
1. Executes smart search with your natural language query
2. Reads full content of top 5 matching notes
3. LLM analyzes and synthesizes findings into a coherent answer
4. Returns summary + original search results for reference

**Use cases:**
- "What did I learn about vector databases?"
- "What are my key insights from meetings with Sarah?"
- "Summarize my thoughts on the authentication refactor"

**Duration:** ~2-4 seconds (smart search + LLM synthesis)

---

#### 2b. Synthesis with Streaming (Real-time)

**POST** `/synthesize/stream`

Same as `/synthesize` but streams the summary in real-time using Server-Sent Events (SSE). Provides better UX by showing progressive results as the LLM generates them.

**Request Body:**
```json
{
  "query": "what did I learn about memory consolidation?",
  "limit": 10
}
```

**Response (SSE Stream):**
```
data: {"type": "metadata", "query": "what did I learn...", "notes_analyzed": 2}

data: {"type": "chunk", "content": "Memory consolidation "}

data: {"type": "chunk", "content": "refers to the process "}

data: {"type": "chunk", "content": "by which the brain stabilizes..."}

data: {"type": "results", "search_results": [...]}

data: {"type": "done"}
```

**Event Types:**
- `metadata`: Initial information (query, notes count)
- `chunk`: Incremental summary content
- `results`: Full search results array
- `done`: Stream completion signal

**Frontend Integration:**
```typescript
const eventSource = new EventSource('/synthesize/stream', {
  method: 'POST',
  body: JSON.stringify({ query: "...", limit: 10 })
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'metadata') {
    console.log(`Analyzing ${data.notes_analyzed} notes...`);
  } else if (data.type === 'chunk') {
    // Append to summary display
    summaryElement.textContent += data.content;
  } else if (data.type === 'results') {
    // Show search results
    displayResults(data.search_results);
  } else if (data.type === 'done') {
    eventSource.close();
  }
};
```

**Benefits:**
- Progressive rendering - user sees output immediately
- Better perceived performance
- Interactive "typing" effect
- Can cancel mid-stream if needed

**Duration:** Same total time (~2-4s) but starts showing results after ~1s

---

#### 3. Keyword Search (Fast)

**POST** `/search` or `/search_fast`

Direct FTS5 keyword search without LLM parsing.

**Request Body:**
```json
{
  "query": "authentication OAuth2",
  "limit": 20
}
```

**Supports:**
- Boolean operators: `"python OR rust"`
- Phrase search: `"machine learning"`
- Simple keywords: `authentication`

**Response:** Same as smart search

**Duration:** <0.1 seconds (no LLM)

---

#### 4. Search by Dimensions

**POST** `/search/dimensions`

Filter notes by specific dimension values.

**Request Body:**
```json
{
  "dimension_type": "context",
  "dimension_value": "tasks",
  "query_text": "authentication",
  "limit": 10
}
```

**Dimension Types:**
- `context`: Maps to boolean flags
  - Values: `tasks`, `meetings`, `ideas`, `reference`, `journal`
- `emotion`: Specific emotions
  - Values: `excited`, `frustrated`, `curious`, etc.
- `time_reference`: Meeting times/deadlines

**Response:** Same as smart search

---

#### 5. Search by Entity

**POST** `/search/entities`

Find notes mentioning specific people, topics, or technologies.

**Request Body:**
```json
{
  "entity_type": "person",
  "entity_value": "Sarah",
  "context": "meetings",
  "limit": 10
}
```

**Entity Types:**
- `person`: People names
- `topic`, `project`, `tech`: All stored as generic `entity`

**Optional Context Filter:** `tasks`, `meetings`, `ideas`, `reference`, `journal`

**Response:** Same as smart search

---

#### 6. Search by Person (Convenience)

**POST** `/search/person`

Shortcut for searching notes mentioning a person.

**Request Body:**
```json
{
  "name": "Sarah",
  "context": "meetings",
  "limit": 10
}
```

**Response:** Same as smart search

---

### Consolidation (Linking)

#### 1. Consolidate Single Note

**POST** `/consolidate/{note_id}`

Analyze one note and create links to related existing notes.

**Path Parameter:**
- `note_id`: Note ID (e.g., `2025-10-16T15:30:00-07:00_a27f`)

**Response:**
```json
{
  "note_id": "2025-10-16T15:30:00-07:00_a27f",
  "links_created": 2,
  "candidates_found": 5,
  "timings": {
    "db_query": 0.002,
    "find_candidates": 0.003,
    "llm_suggest": 4.613,
    "store_links": 0.002,
    "total": 4.620
  }
}
```

**How it works:**
1. Finds candidate notes with shared people, entities, or tags
2. LLM analyzes candidates and suggests meaningful links
3. Stores links in database with types (related/spawned/references/contradicts)

**Duration:** ~4-5 seconds per note (LLM-dependent)

**Performance:** LLM calls account for 99.85% of time

---

#### 2. Batch Consolidation

**POST** `/consolidate`

Consolidate all of today's notes in sequence.

**Request Body:** None (processes today's notes automatically)

**Response:**
```json
{
  "notes_processed": 10,
  "links_created": 12,
  "notes_with_links": 8,
  "started_at": "2025-10-16T20:00:00-07:00",
  "completed_at": "2025-10-16T20:01:30-07:00"
}
```

**Use Case:** Run at end of day to build knowledge graph connections

**Duration:** ~5 seconds per note × number of notes

---

### Graph Traversal

#### 1. Search Graph (by Start Note)

**POST** `/search/graph`

Traverse the knowledge graph from a starting note.

**Request Body:**
```json
{
  "start_note_id": "2025-10-16T15:30:00-07:00_a27f",
  "depth": 2,
  "relationship_type": "related"
}
```

**Parameters:**
- `depth`: How many hops to traverse (1-3 recommended)
- `relationship_type` (optional): Filter by link type
  - Values: `related`, `spawned`, `references`, `contradicts`

**Response:**
```json
{
  "nodes": [
    {
      "id": "2025-10-16T15:30:00-07:00_a27f",
      "path": "/Users/you/Notes/2025-10-16-meeting-with-sarah.md",
      "created": "2025-10-16T15:30:00-07:00",
      "dimensions": {
        "has_action_items": false,
        "is_social": true,
        "is_emotional": false,
        "is_knowledge": true,
        "is_exploratory": false
      }
    }
  ],
  "edges": [
    {
      "from": "2025-10-16T15:30:00-07:00_a27f",
      "to": "2025-10-15T14:20:00-07:00_b3f2",
      "type": "related"
    }
  ]
}
```

**Use Case:** Visualize note relationships, explore knowledge connections

---

#### 2. Get Note Graph (Convenience)

**GET** `/notes/{note_id}/graph`

Same as `/search/graph` but via GET request.

**Query Parameters:**
- `depth`: Default 2
- `relationship_type`: Optional filter

---

## Data Models

### ClassifyResponse

```typescript
{
  title: string;              // "Meeting with Sarah"
  dimensions: {
    has_action_items: boolean;
    is_social: boolean;
    is_emotional: boolean;
    is_knowledge: boolean;
    is_exploratory: boolean;
  };
  tags: string[];             // ["meeting", "authentication"]
  path: string;               // Full file path
}
```

### SearchHit

```typescript
{
  path: string;               // Note file path
  snippet: string;            // Search result snippet with <b> highlights
  score: number;              // Relevance score (0-1)
  metadata: {
    created: string;          // ISO timestamp
    dimensions: {
      has_action_items: boolean;
      is_social: boolean;
      is_emotional: boolean;
      is_knowledge: boolean;
      is_exploratory: boolean;
    }
  }
}
```

### GraphData

```typescript
{
  nodes: Array<{
    id: string;
    path: string;
    created: string;
    dimensions: { ... }
  }>;
  edges: Array<{
    from: string;             // Note ID
    to: string;               // Note ID
    type: string;             // "related" | "spawned" | "references" | "contradicts"
  }>;
}
```

### SynthesisResponse

```typescript
{
  query: string;              // Original user query
  summary: string;            // LLM-generated synthesis
  notes_analyzed: number;     // Number of notes used for synthesis
  search_results: SearchHit[]; // Full search results for reference
}
```

---

## Error Handling

### HTTP Status Codes

- `200`: Success
- `400`: Bad Request (invalid input)
- `404`: Not Found (note doesn't exist)
- `500`: Internal Server Error (LLM failure, database error)

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

**LLM Classification Failure:**
```json
{
  "detail": "Classification failed: Connection refused (Ollama not running)"
}
```

**Solution:** Ensure Ollama is running (`ollama serve`)

**Invalid Note ID:**
```json
{
  "detail": "Note not found"
}
```

**Solution:** Verify note ID exists in database

---

## Performance

### Response Times

| Endpoint | Typical Duration | Bottleneck | Notes |
|----------|-----------------|------------|-------|
| `/health` | <10ms | None | - |
| `/search_fast` | <100ms | FTS5 query | - |
| `/search_smart` | 1-2s | LLM parsing | - |
| `/synthesize` | 2-4s | LLM synthesis + search | Full response at end |
| `/synthesize/stream` | 2-4s | LLM synthesis + search | Progressive chunks (SSE) |
| `/classify_and_save` | 3-5s | LLM classification + enrichment | - |
| `/consolidate/{note_id}` | 4-5s | LLM link suggestion (99.85%) | - |
| `/search/graph` | <100ms | Database query | - |

### Optimization Notes

1. **Database operations are fast** (<10ms)
2. **LLM is the bottleneck** (3-5s per call)
3. **Consolidation scales linearly** with number of notes
4. **Search is instant** for keyword/dimension queries

### Caching

- No caching implemented (stateless API)
- LLM responses are not cached (ensures fresh analysis)
- Consider client-side caching for search results

---

## Example Frontend Integration

### React Hook Example

```typescript
// hooks/useNoteCapture.ts
export function useNoteCapture() {
  const capture = async (text: string) => {
    const response = await fetch('http://localhost:8734/classify_and_save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });

    if (!response.ok) {
      throw new Error('Failed to capture note');
    }

    return await response.json();
  };

  return { capture };
}
```

### Search Component Example

```typescript
// components/SearchBar.tsx
const search = async (query: string) => {
  const response = await fetch('http://localhost:8734/search_smart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, limit: 20 })
  });

  const results = await response.json();
  setSearchResults(results);
};
```

### Graph Visualization Example

```typescript
// components/KnowledgeGraph.tsx
const loadGraph = async (noteId: string) => {
  const response = await fetch('http://localhost:8734/search/graph', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      start_note_id: noteId,
      depth: 2
    })
  });

  const { nodes, edges } = await response.json();
  // Use D3.js, Cytoscape.js, or React Flow to visualize
};
```

---

## Development

### Running Tests

```bash
source .venv/bin/activate
python -m pytest tests/test_refactor_regression.py -v
```

**Current Status:** 14/15 tests passing (1 skipped)

### API Documentation

FastAPI provides auto-generated interactive docs:
- **Swagger UI**: http://localhost:8734/docs
- **ReDoc**: http://localhost:8734/redoc

### Environment Variables

```bash
# .env (optional)
NOTES_DIR=/Users/you/Notes
LLM_MODEL=qwen3:4b-instruct
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8734
```

---

## Architecture

- **Framework**: FastAPI (Python 3.13)
- **LLM**: Local Ollama (qwen3:4b-instruct)
- **Database**: SQLite with FTS5
- **Storage**: Flat markdown files + structured DB

See [DATA_ARCHITECTURE.md](../DATA_ARCHITECTURE.md) for detailed schema documentation.

---

## Support & Issues

For bugs or feature requests, check the project repository or contact the maintainer.

**API Version:** 1.0
**Last Updated:** 2025-10-16
