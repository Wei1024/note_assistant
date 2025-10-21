# Data Architecture - Clean Design (Post Phase 2)

**Last Updated:** 2025-10-16
**Status:** Phase 2 Complete - Folder classification fully eliminated, pure dimension-based system

---

## Overview

The note system uses a **hybrid architecture** combining:
1. **Flat file storage** - All notes in ~/Notes/ (no subfolders)
2. **Structured database** - Fast queries via SQLite
3. **Graph metadata** - Flexible relationships via notes_entities/notes_dimensions

---

## Storage Layers

### 1. Markdown Files (~/Notes/*.md)
**Purpose:** Human-readable note content

**Structure:**
```yaml
---
id: 2025-10-11T22:02:40-07:00_a27f
title: Meeting with Sarah on memory research
tags: [meeting, psychology]
related_ids: []
created: '2025-10-11T22:02:40-07:00'
updated: '2025-10-11T22:02:40-07:00'
dimensions:
  - type: emotion
    value: excited
entities:
  people: [Sarah]
  entities: [human memory, psychology]
---

Meeting with Sarah today at 3 pm...
```

**What it stores:**
- ✅ Human-readable content
- ✅ YAML frontmatter for visibility
- ❌ NOT the source of truth for metadata (database is)

---

## Database Tables

### Table 1: notes_meta (Core + Boolean Dimensions)
**Purpose:** Fast filtering and core metadata

**Schema:**
```sql
CREATE TABLE notes_meta (
    id TEXT PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    created TEXT NOT NULL,
    updated TEXT NOT NULL,
    status TEXT,                    -- todo/in_progress/done (tasks only)

    -- Phase 2: Boolean Dimensions (multi-dimensional classification)
    has_action_items BOOLEAN,       -- Contains tasks/todos
    is_social BOOLEAN,              -- Involves conversations
    is_emotional BOOLEAN,           -- Expresses feelings
    is_knowledge BOOLEAN,           -- Contains learnings
    is_exploratory BOOLEAN,         -- Brainstorming/ideas

    -- Review system
    needs_review BOOLEAN,
    review_reason TEXT,
    reviewed_at TEXT,
    original_classification TEXT
);
```

**Use cases:**
- Fast queries: "Show all tasks" → `WHERE has_action_items=1`
- Multiple dimensions: "Social + emotional notes" → `WHERE is_social=1 AND is_emotional=1`
- File metadata: paths, timestamps

**What it does NOT store:**
- ❌ People/entities (those are in notes_entities)
- ❌ Specific emotion names (those are in notes_dimensions)
- ❌ Folder classification (removed in Phase 2)

---

### Table 2: notes_entities (Graph - People & Entities)
**Purpose:** Flexible graph of mentioned things

**Schema:**
```sql
CREATE TABLE notes_entities (
    note_id TEXT,
    entity_type TEXT,               -- 'person' or 'entity'
    entity_value TEXT,              -- The actual value
    entity_metadata TEXT,           -- JSON for extra data
    extraction_confidence REAL,
    created TEXT
);
```

**Entity Types:**
- **person**: People mentioned ("Sarah", "Alex", "Charlotte")
- **entity**: Generic entities - topics, tools, concepts, technologies
  - Phase 1 merged: topics/technologies/projects → generic "entity"

**Example Data:**
```sql
-- People
(note_id, 'person', 'Sarah', '{"role": "psychologist"}', ...)

-- Generic entities
(note_id, 'entity', 'human memory', NULL, ...)
(note_id, 'entity', 'SQLite FTS5', NULL, ...)
(note_id, 'entity', 'FAISS', NULL, ...)
```

**Use cases:**
- "Find notes mentioning Sarah" → `WHERE entity_type='person' AND entity_value='Sarah'`
- "Find notes about FAISS" → `WHERE entity_type='entity' AND entity_value LIKE '%FAISS%'`
- Graph analysis: co-occurrence patterns

---

### Table 3: notes_dimensions (Rich Detail Metadata)
**Purpose:** Store non-boolean dimensions with specific values

**Schema:**
```sql
CREATE TABLE notes_dimensions (
    note_id TEXT,
    dimension_type TEXT,            -- 'emotion' or 'time_reference'
    dimension_value TEXT,           -- Specific value
    extraction_confidence REAL,
    created TEXT
);
```

**Dimension Types:**
- **emotion**: Actual emotion names ("excited", "frustrated", "curious")
- **time_reference**: Meeting times, deadlines ("2025-10-11T15:00:00")

**Why separate from notes_meta?**
- notes_meta has `is_emotional=1` (boolean - fast filter)
- notes_dimensions has `["excited", "curious"]` (rich detail - what emotions exactly?)

**Example Data:**
```sql
-- Emotions (what emotions, not just "is emotional")
(note_id, 'emotion', 'excited', ...)
(note_id, 'emotion', 'curious', ...)

-- Time references (meeting times, deadlines)
(note_id, 'time_reference', '2025-10-11T15:00:00', ...)
```

**Use cases:**
- "What emotions are in this note?" → Query for specific emotion values
- "Notes with excitement" → `WHERE dimension_type='emotion' AND dimension_value='excited'`
- "Meetings at 3pm" → Time reference queries

**What it does NOT store (anymore):**
- ❌ secondary_contexts (removed - redundant with boolean dimensions)

---

### Table 4: notes_fts (Full-Text Search)
**Purpose:** Fast keyword search

**Schema:**
```sql
CREATE VIRTUAL TABLE notes_fts USING fts5(
    id UNINDEXED,
    title,
    body,
    tags
);
```

**Use cases:**
- Keyword search: "authentication bug"
- Phrase search: "machine learning"
- Boolean queries: "python OR rust"

---

### Table 5: notes_links (Note Relationships)
**Purpose:** Track connections between notes

**Schema:**
```sql
CREATE TABLE notes_links (
    from_note_id TEXT,
    to_note_id TEXT,
    link_type TEXT,                 -- 'related', 'similar', 'continues'
    created TEXT,
    PRIMARY KEY(from_note_id, to_note_id, link_type)
);
```

**Use cases:**
- Consolidation suggestions
- Manual links
- Backlinks

---

### Table 6: notes_embeddings (Future - Phase 7)
**Purpose:** Semantic search via vector embeddings

**Schema:**
```sql
CREATE TABLE notes_embeddings (
    note_id TEXT PRIMARY KEY,
    embedding BLOB,
    model TEXT,
    created TEXT
);
```

**Status:** Placeholder for future semantic search feature

---

## Data Flow: Note Creation

```python
# 1. User enters text
text = "Meeting with Sarah about memory research..."

# 2. LLM classification (title/tags)
classification = classify_note_async(text)
# → {title: "Meeting with Sarah", tags: [...]}

# 3. LLM enrichment (everything else)
enrichment = enrich_note_metadata(text, classification)
# → {
#      has_action_items: False,     # Boolean dimensions
#      is_social: True,
#      is_emotional: True,
#      entities: ["memory research"], # Generic entities
#      people: [{"name": "Sarah"}],
#      emotions: ["excited"],         # Rich detail
#      time_references: [...]
#    }

# 4. Write markdown file (flat structure)
write_markdown(title, tags, body, enrichment=enrichment)
# → ~/Notes/2025-10-11-meeting-with-sarah.md
# → Frontmatter: visual metadata for humans
# → Calls index_note() for database storage

# 5. index_note() → notes_meta + notes_fts
index_note(note_id, title, body, tags, path,
           has_action_items=False, is_social=True, ...)
# → INSERT INTO notes_meta (boolean dimensions)
# → INSERT INTO notes_fts (keyword search)

# 6. store_enrichment_metadata() → graph tables
store_enrichment_metadata(note_id, enrichment, con)
# → Calls graph.py functions:
#   - add_entity(note_id, "person", "Sarah")
#   - add_entity(note_id, "entity", "memory research")
#   - add_dimension(note_id, "emotion", "excited")
# → INSERT INTO notes_entities (people + entities)
# → INSERT INTO notes_dimensions (emotions, time refs)
```

---

## Query Patterns

### Fast Boolean Filters (notes_meta)
```python
# Show all tasks
"SELECT * FROM notes_meta WHERE has_action_items=1"

# Social + emotional notes
"SELECT * FROM notes_meta WHERE is_social=1 AND is_emotional=1"

# Knowledge base
"SELECT * FROM notes_meta WHERE is_knowledge=1"
```

### Graph Queries (notes_entities)
```python
# Notes mentioning Sarah
"SELECT note_id FROM notes_entities
 WHERE entity_type='person' AND entity_value='Sarah'"

# Notes about FAISS
"SELECT note_id FROM notes_entities
 WHERE entity_type='entity' AND entity_value LIKE '%FAISS%'"
```

### Rich Detail Queries (notes_dimensions)
```python
# What emotions are in this note?
"SELECT dimension_value FROM notes_dimensions
 WHERE note_id='...' AND dimension_type='emotion'"

# Notes expressing excitement
"SELECT note_id FROM notes_dimensions
 WHERE dimension_type='emotion' AND dimension_value='excited'"
```

### Keyword Search (notes_fts)
```python
# Keyword search
"SELECT * FROM notes_fts WHERE notes_fts MATCH 'authentication bug'"
```

---

## Design Rationale

### Why Hybrid Architecture?

**Boolean dimensions in notes_meta:**
- ✅ Fast indexed queries
- ✅ Simple SQL: `WHERE is_social=1`
- ✅ Common use case: filtering by type

**Graph tables (entities/dimensions):**
- ✅ Flexible many-to-many relationships
- ✅ Rich detail: actual emotion names, not just "is emotional"
- ✅ Extensible: add new entity types without schema changes

**Flat file structure:**
- ✅ No forced categorization during storage
- ✅ Multi-dimensional notes allowed
- ✅ Natural chronological sorting by filename

---

## Migration History

**Phase 0 → Phase 1:**
- Merged entity types: topics/technologies/projects → generic "entity"
- 47 database records migrated

**Phase 1 → Phase 2:**
- Added boolean dimension columns to notes_meta
- Removed folder column from notes_meta
- Flattened file structure (all notes to ~/Notes/)
- Removed secondary_contexts (redundant with boolean dimensions)

**Legacy Removed:**
- ❌ Folder-based classification
- ❌ secondary_contexts in notes_dimensions
- ❌ Separate topic/tech/project entity types

---

## Summary: What Lives Where

| Data Type | Table | Example | Query Speed |
|-----------|-------|---------|-------------|
| **Boolean Dimensions** | notes_meta | has_action_items=1 | ⚡ Fast |
| **People** | notes_entities | entity_type='person', value='Sarah' | 🔍 Medium |
| **Generic Entities** | notes_entities | entity_type='entity', value='FAISS' | 🔍 Medium |
| **Emotions (values)** | notes_dimensions | dimension_type='emotion', value='excited' | 🔍 Medium |
| **Time References** | notes_dimensions | dimension_type='time_reference' | 🔍 Medium |
| **Note Content** | notes_fts | FTS5 index | ⚡ Fast |
| **File Metadata** | notes_meta | path, timestamps | ⚡ Fast |

---

## Best Practices

1. **Use notes_meta for filtering** - Boolean dimensions optimized for WHERE clauses
2. **Use notes_entities for graph** - People and entity relationships
3. **Use notes_dimensions for details** - What specific emotions, not just "is emotional"
4. **Use notes_fts for search** - Keyword and phrase queries
5. **Markdown is for humans** - Database is source of truth for metadata

---

**Architecture Status:** Clean and production-ready after Phase 2 cleanup.
