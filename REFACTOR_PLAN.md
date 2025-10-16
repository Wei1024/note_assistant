# Refactor Plan: Flat Metadata & Entity Simplification

**Date:** 2025-10-14
**Status:** Phase 1 & 2 Complete ✅
**Based on:** Test results from `tests/test_flat_metadata_comparison.py`

---

## Progress Update (2025-10-14)

✅ **Phase 1 Complete** (Commit da70a77)
- Merged entity types (topics/tech/projects → entities)
- Updated prompts (ENRICH_METADATA, PARSE_SEARCH_QUERY)
- Updated services (search, enrichment, consolidation)
- Migrated 47 database records to generic entity type
- Fixed cli.py stats command (entity_type='entity')
- 14/15 regression tests passing

✅ **Phase 2 FULLY Complete** (Commit 4f0d01b)
- Removed folder column from database schema (fts.py + db/schema.py)
- Flattened file structure: all notes moved to ~/Notes/ root
- Updated database paths to remove folder subdirectories
- Removed folder parameter from write_markdown(), index_note()
- Updated repository layer (notes_repo.py, search_repo.py)
- Fixed query.py to use dimension-based filtering instead of folder
- API derives display folder from dimensions
- Production gatekeeper review completed - all critical issues fixed
- 14/15 regression tests passing

---

## Executive Summary

Move from **forced single-folder classification + rigid entity categories** to **flat metadata extraction + flexible entity list**. This aligns better with how human memory works and is more robust across different LLM models.

### Test Results Supporting This Change:

| Model | Folder Classification | Flat Metadata |
|-------|----------------------|---------------|
| **Qwen3:4b** | 57.1% accuracy | **71.4% accuracy** ✓ |
| **Gemma3:4b** | **0% accuracy** 💥 | **71.4% accuracy** ✓ |

**Key Finding:** Flat metadata is model-agnostic and consistently outperforms forced categorization.

---

## Core Philosophy Changes

### From: Categorization During Encoding
**Current:**
- Classify into ONE folder immediately (tasks|meetings|ideas|reference|journal)
- Extract entities into THREE rigid types (topics|technologies|projects)
- LLM forced to make arbitrary decisions under uncertainty

### To: Extraction During Encoding, Categorization During Consolidation
**New:**
- Extract **multi-dimensional metadata** (boolean dimensions + entities)
- Merge topics/technologies/projects → single `entities` array
- Let categories **emerge from usage patterns** during consolidation

**This mirrors how the brain works:**
- Encoding: Capture rich, unstructured experience
- Consolidation: Find patterns and create categories

---

## Phase 1: Simplify Entity Extraction

### 1.1 Update ENRICH_METADATA Prompt

**Current schema:**
```json
{
  "secondary_contexts": ["tasks", "ideas"],
  "people": [{"name": "Sarah", "role": "researcher"}],
  "topics": ["memory consolidation", "psychology"],
  "projects": ["note-taking app"],
  "technologies": ["FAISS", "SQLite"],
  "emotions": ["excited", "curious"],
  "time_references": [...]
}
```

**New schema (Phase 1 only - entities merged):**
```json
{
  "people": [{"name": "Sarah", "role": "researcher"}],
  "entities": [
    "memory consolidation",
    "psychology",
    "note-taking app",
    "FAISS",
    "SQLite"
  ],
  "emotions": ["excited", "curious"],
  "time_references": [...]
}
```

**After Phase 2 (dimensions added):**
```json
{
  "has_action_items": true,
  "is_social": true,
  "is_emotional": false,
  "is_knowledge": true,
  "is_exploratory": true,

  "people": [{"name": "Sarah", "role": "researcher"}],
  "entities": ["memory consolidation", "psychology", "FAISS", "SQLite"],
  "emotions": ["excited", "curious"]
}
```

**Why:**
- No more arbitrary topic vs tech vs project distinction
- No more secondary_contexts (replaced by boolean dimensions)
- Simpler for SLM to extract
- Still fully searchable
- Can infer categories later via consolidation

**Files to modify:**
- [x] `api/llm/prompts.py` - ENRICH_METADATA (already updated with clean structure)
- [ ] Update to merge topic/tech/project → entities

### 1.2 Update Database Schema

**Current:**
```sql
CREATE TABLE notes_entities (
    note_id TEXT,
    entity_type TEXT,  -- 'topic', 'tech', 'project'
    entity_value TEXT,
    ...
);
```

**New:**
```sql
-- Keep same table structure, but use generic type
CREATE TABLE notes_entities (
    note_id TEXT,
    entity_type TEXT,  -- Always 'entity' now
    entity_value TEXT,
    ...
);

-- Optional: Add derived categories table (computed during consolidation)
CREATE TABLE entity_categories (
    entity_value TEXT PRIMARY KEY,
    inferred_category TEXT,  -- 'topic', 'tech', 'project', or null
    confidence REAL,
    mention_count INTEGER,
    last_updated TEXT,
    dimension_distribution TEXT  -- JSON: {"has_action_items": 5, "is_knowledge": 3}
);
```

**Migration script:**
```sql
-- Merge existing entities into generic type
UPDATE notes_entities
SET entity_type = 'entity'
WHERE entity_type IN ('topic', 'tech', 'project');
```

**Files to modify:**
- [ ] `api/db/schema.py` - Update schema definition (documentation only)
- [ ] `api/graph.py` - Update `add_entity()` and queries to use generic 'entity' type
- [ ] `api/repositories/graph_repo.py` - Update `add_entity()` method signature if needed

**Note:** No migration script needed - only 21 notes, will run SQL directly.

### 1.3 Update Search Query Parser

**Current:**
```json
{
  "entity_type": "tech",
  "entity_value": "FAISS",
  ...
}
```

**New:**
```json
{
  "entity": "FAISS",  // Just the value, no type needed
  ...
}
```

**Files to modify:**
- [ ] `api/llm/prompts.py` - Update `Prompts.PARSE_SEARCH_QUERY` (remove entity_type field)
- [ ] `api/services/search.py` - Update `parse_smart_query()` and `search_notes_smart()` to remove entity_type logic
- [ ] `api/graph.py` - Update `find_notes_by_entity()` to use generic 'entity' type
- [ ] `api/repositories/graph_repo.py` - Update `find_by_entity()` method

---

## Phase 2: Add Metadata Dimensions (Optional but Recommended)

### 2.1 Add Boolean Dimensions to Database

**New schema (folder removed!):**
```sql
CREATE TABLE notes_meta (
    id TEXT PRIMARY KEY,
    path TEXT,            -- Flat: ~/Notes/2025-10-14_abc.md
    title TEXT,
    created TEXT,
    updated TEXT,

    -- Boolean dimensions (replace folder!)
    has_action_items BOOLEAN DEFAULT 0,
    is_social BOOLEAN DEFAULT 0,
    is_emotional BOOLEAN DEFAULT 0,
    is_knowledge BOOLEAN DEFAULT 0,
    is_exploratory BOOLEAN DEFAULT 0,

    ...
);
```

**Why remove folder:**
- ✅ Dimensions capture everything folder did, more accurately
- ✅ No forced single-choice categorization
- ✅ Notes can be multi-dimensional (social + emotional + exploratory)
- ✅ Cleaner schema

**Migration:**
```sql
-- Drop folder column (dimensions replace it)
ALTER TABLE notes_meta DROP COLUMN folder;
```

**Test Results:**
- "Brainstorming with Alex" → T,M,J,I (tasks + meetings + journal + ideas)
- This IS accurate - the note spans multiple dimensions!

### 2.2 Update ENRICH_METADATA to Extract Dimensions

**Add to enrichment output:**
```json
{
  "has_action_items": true,
  "is_social": true,
  "is_emotional": true,
  "is_knowledge": false,
  "is_exploratory": true,

  "people": [...],
  "entities": [...],
  "emotions": [...]
}
```

**Files to modify:**
- [ ] `api/llm/prompts.py` - Update `Prompts.ENRICH_METADATA` to add 5 boolean dimensions
- [ ] `api/services/enrichment.py` - Update `enrich_note_metadata()` to return dimensions
- [ ] `api/services/enrichment.py` - Update `store_enrichment_metadata()` to store dimension booleans in notes_meta
- [ ] `api/repositories/notes_repo.py` - Add method to update dimension fields in notes_meta table

### 2.3 Create Dynamic Views

**CLI updates:**
```python
# Instead of folder-based views, use dimension-based filters
tasks_view = "SELECT * FROM notes_meta WHERE has_action_items = 1"
meetings_view = "SELECT * FROM notes_meta WHERE is_social = 1"
journal_view = "SELECT * FROM notes_meta WHERE is_emotional = 1"
reference_view = "SELECT * FROM notes_meta WHERE is_knowledge = 1"
ideas_view = "SELECT * FROM notes_meta WHERE is_exploratory = 1"

# Multi-dimensional queries
emotional_meetings = "WHERE is_social = 1 AND is_emotional = 1"
```

**Files to modify:**
- [ ] `cli.py` - Update `search_by_context_cmd()` to query dimensions instead of folder
- [ ] `cli.py` - Update stats display (lines 420-422) to show dimension distribution instead of folder
- [ ] `api/services/search.py` - Update `search_notes_smart()` to support dimension filters

---

## Phase 3: Consolidation-Based Categorization (FUTURE - OPTIONAL)

**Note:** This phase is optional and should only be implemented when you have 100+ notes. With only 21 notes, this is unnecessary. the User is doubtful about not using SLM to do the clustering so discuss with the users first

### 3.1 Entity Clustering Service

**New consolidation function:**
```python
async def discover_entity_categories() -> Dict:
    """
    Run weekly/monthly to analyze entity usage patterns
    and infer categories (topic vs tech vs project).

    Uses heuristics based on:
    - Dimension co-occurrence (appears with has_action_items → tech)
    - Entity co-occurrence patterns (appears with code terms → tech)
    - Mention frequency and spread

    Returns:
        {
            "FAISS": {"category": "tech", "confidence": 0.85},
            "memory consolidation": {"category": "topic", "confidence": 0.92},
            "note-taking app": {"category": "project", "confidence": 0.88}
        }
    """
```

**Heuristic categorization (no LLM needed):**
```python
def infer_category(entity: str, dimension_dist: Dict, co_occur: Dict) -> Dict:
    """
    Infer entity category from usage patterns.

    Args:
        entity: Entity value
        dimension_dist: {"has_action_items": 5, "is_knowledge": 3, ...}
        co_occur: {"Python": 4, "API": 2, ...}
    """
    total = sum(dimension_dist.values())
    if total == 0:
        return {"category": "entity", "confidence": 0.5}

    action_ratio = dimension_dist.get("has_action_items", 0) / total
    knowledge_ratio = dimension_dist.get("is_knowledge", 0) / total

    # High in action items + co-occurs with tech terms → technology
    if action_ratio > 0.4:
        tech_indicators = {"Python", "API", "database", "Docker", "SQLite"}
        if len(tech_indicators & set(co_occur.keys())) > 0:
            return {"category": "tech", "confidence": 0.8}

    # High in knowledge, low in action → topic
    if knowledge_ratio > 0.6 and action_ratio < 0.2:
        return {"category": "topic", "confidence": 0.7}

    # Spans multiple dimensions + high mentions → project
    if len(dimension_dist) >= 3 and total >= 5:
        return {"category": "project", "confidence": 0.75}

    return {"category": "entity", "confidence": 0.5}
```

**Files to create:**
- [ ] `api/services/entity_clustering.py` - New service
- [ ] `api/repositories/entity_categories.py` - New repository

### 3.2 CLI Command for Consolidation

```bash
python cli.py consolidate --analyze-entities
```

**Output:**
```
Analyzing entity usage patterns...

Discovered categories:
  Technologies (12): FAISS, Python, SQLite, Docker, ...
  Topics (23): memory consolidation, psychology, vector search, ...
  Projects (3): note-taking app, website redesign, Q4 planning

Updated entity_categories table.
```

---

## Data Architecture: Markdown Files vs Database

### **Core Principle: Separation of Content and Metadata**

**Markdown files = Pure content only**
```markdown
~/Notes/2025-10-11T22-22-36-07-00_0d7e.md

Had a great brainstorming session with Alex about implementing
vector embeddings in our search system. We discussed using FAISS
and ChromaDB. Feeling excited about the possibilities! Need to
research more about dimensionality reduction.
```

**NO YAML frontmatter!** Files are human-readable, no metadata clutter.

**Database = All metadata**
```sql
-- notes_meta: Core note info + boolean dimensions
id: "2025-10-11T22-22-36-07-00_0d7e"
path: "/Users/you/Notes/2025-10-11T22-22-36-07-00_0d7e.md"
title: "Brainstorming vector embeddings"
created: "2025-10-11T22:22:36-07:00"
has_action_items: 1
is_social: 1
is_emotional: 1
is_knowledge: 0
is_exploratory: 1

-- notes_entities: Generic entities (via graph.py)
(note_id, entity_type="entity", entity_value="vector embeddings")
(note_id, entity_type="entity", entity_value="FAISS")

-- notes_people: People mentioned (via graph.py)
(note_id, person_name="Alex", person_role="")

-- notes_dimensions: Emotions, secondary contexts (via graph.py)
(note_id, dimension_type="emotion", dimension_value="excited")

-- notes_links: Note-to-note connections (via graph.py)
(from_note_id, to_note_id, link_type="related")
```

### **Why This Split?**

✅ **Clean separation:** Content vs metadata
✅ **No frontmatter pollution:** Prevents LLM hallucination (issue we found in testing!)
✅ **Fast metadata queries:** SQL is optimized for this
✅ **Mutable metadata:** Can update dimensions without touching file
✅ **Human-readable files:** Just markdown, no YAML clutter
✅ **Version control friendly:** Git diffs show actual content changes

---

## Role of graph.py in New Design

### **What is graph.py?**

`graph.py` is the **knowledge graph layer** - manages connections between notes via metadata.

### **graph.py Functions:**

#### **Write Operations:**
```python
# Store metadata extracted by LLM
add_entity(note_id, "entity", "FAISS")           # Generic entities
add_person(note_id, "Alex", role="")             # People
add_dimension(note_id, "emotion", "excited")     # Emotions
add_dimension(note_id, "context", "tasks")       # Secondary contexts
add_link(note1_id, note2_id, "related")         # Note connections
```

#### **Read Operations:**
```python
# Query the knowledge graph
find_notes_by_entity("entity", "FAISS")          # Fuzzy match
find_notes_by_person("Alex")                     # People search
find_notes_by_dimension("emotion", "excited")    # Emotion search
get_linked_notes(note_id)                        # Forward links
get_backlinks(note_id)                           # Reverse links
```

### **Changes in New Design:**

- ✅ **Keep:** Link operations, dimension operations, people operations (unchanged)
- 🔄 **Simplify:** `add_entity()` always uses `entity_type = "entity"` (no topic/tech/project)
- 📝 **Note:** Boolean dimensions (has_action_items, etc.) stored in `notes_meta`, not via graph.py

### **Example Flow:**

```python
# 1. Create note (pure content)
content = "Had a great brainstorming session with Alex..."
note_id = create_note(content)  # → ~/Notes/2025-10-11_abc.md

# 2. LLM enrichment (strips frontmatter first!)
enrichment = enrich_note(content)

# 3. Store boolean dimensions → notes_meta table
update_note_dimensions(note_id, {
    "has_action_items": True,
    "is_social": True,
    ...
})

# 4. Store graph metadata → via graph.py
for entity in enrichment["entities"]:
    add_entity(note_id, "entity", entity)  # Generic type!

for person in enrichment["people"]:
    add_person(note_id, person["name"])
```

---

## File Storage: Truly Flat Structure

**DECISION: Truly flat (no date folders)**

### **New Structure:**
```
~/Notes/
  2025-10-02T03-07-45Z_20be.md
  2025-10-09T03-37-37Z_bb23.md
  2025-10-11T22-22-36-07-00_0d7e.md
  2025-10-13T21-13-18-07-00_af54.md
  inbox/  # Only keep inbox for staging new notes
```

**All notes in one directory!** No date folders.

### **Why Flat?**

✅ **No forced categorization:** Let metadata do the work
✅ **Simpler file operations:** No directory management
✅ **Natural chronological sorting:** Filenames include timestamps
✅ **Database handles all queries:** File location irrelevant
✅ **Easier backup/sync:** One directory to manage

---

## Implementation Timeline

### **SIMPLIFIED PLAN: All-at-Once Migration**

**Decision:** Since you have minimal data (~21 notes), we'll do the full migration now instead of phased approach.

### **Step 1: File Structure Migration (30 min)**
- [ ] Create new flat structure: `~/Notes/` (one directory)
- [ ] Move all existing notes from folders (tasks/, meetings/, etc.) to root `~/Notes/`
- [ ] Update file paths in database (notes_meta.path column)
- [ ] Verify all files moved correctly (should have ~21 files)

**New structure:**
```
~/Notes/
  2025-10-02T03-07-45Z_20be.md
  2025-10-09T03-37-37Z_bb23.md
  2025-10-11T22-22-36-07-00_0d7e.md
  2025-10-13T21-13-18-07-00_af54.md
  ...
  inbox/  # Keep inbox subfolder for staging new notes
```

**Migration commands:**
```bash
# Move all notes from subfolders to root
mv ~/Notes/tasks/*.md ~/Notes/
mv ~/Notes/meetings/*.md ~/Notes/
mv ~/Notes/ideas/*.md ~/Notes/
mv ~/Notes/reference/*.md ~/Notes/
mv ~/Notes/journal/*.md ~/Notes/

# Remove empty folders
rmdir ~/Notes/tasks ~/Notes/meetings ~/Notes/ideas ~/Notes/reference ~/Notes/journal

# Update database paths
sqlite3 ~/Notes/.index/notes.sqlite <<EOF
UPDATE notes_meta SET path = REPLACE(path, '/tasks/', '/');
UPDATE notes_meta SET path = REPLACE(path, '/meetings/', '/');
UPDATE notes_meta SET path = REPLACE(path, '/ideas/', '/');
UPDATE notes_meta SET path = REPLACE(path, '/reference/', '/');
UPDATE notes_meta SET path = REPLACE(path, '/journal/', '/');
EOF
```

### **Step 2: Database Schema Update (10 min)**

**No migration script needed - only 21 notes, run SQL directly.**

- [ ] **Backup database:**
  ```bash
  cp ~/Notes/.index/notes.sqlite ~/Notes/.index/notes.sqlite.backup
  ```

- [ ] **Run SQL directly:**
  ```bash
  sqlite3 ~/Notes/.index/notes.sqlite <<EOF
  -- Add dimension columns
  ALTER TABLE notes_meta ADD COLUMN has_action_items BOOLEAN DEFAULT 0;
  ALTER TABLE notes_meta ADD COLUMN is_social BOOLEAN DEFAULT 0;
  ALTER TABLE notes_meta ADD COLUMN is_emotional BOOLEAN DEFAULT 0;
  ALTER TABLE notes_meta ADD COLUMN is_knowledge BOOLEAN DEFAULT 0;
  ALTER TABLE notes_meta ADD COLUMN is_exploratory BOOLEAN DEFAULT 0;

  -- Remove folder column (dimensions replace it)
  ALTER TABLE notes_meta DROP COLUMN folder;

  -- Merge entity types to generic
  UPDATE notes_entities SET entity_type = 'entity'
  WHERE entity_type IN ('topic', 'tech', 'project');
  EOF
  ```

- [ ] **Verify schema:**
  ```bash
  sqlite3 ~/Notes/.index/notes.sqlite ".schema notes_meta"
  # Should show 5 new dimension columns, no folder column
  ```

### **Step 3: Enrichment Updates (1 hour)**
- [ ] Update ENRICH_METADATA prompt (`api/llm/prompts.py`):
  - Merge topics/technologies/projects → single entities array
  - Add boolean dimension extraction (5 dimensions)
  - Use clean structure from test (Identity → Guidelines → Examples → Notes)
  - **CRITICAL:** Remove all examples that mention topics/tech/project types
- [ ] Update enrichment service (`api/services/enrichment.py`):
  - **Add `strip_frontmatter()` function** (critical - prevents hallucinations!)
  - **Update `enrich_note_metadata()` to call `strip_frontmatter()` before LLM call**
  - Update to return merged entities (not separate topics/tech/projects)
  - Update to return 5 boolean dimensions
- [ ] Update `store_enrichment_metadata()` in `api/services/enrichment.py`:
  - Call `notes_repo.update_dimensions()` to store boolean dimensions in notes_meta
  - Ensure graph_repo stores entities with `entity_type='entity'`
- [ ] Update graph operations (`api/graph.py`):
  - Update `add_entity()` calls to always use `entity_type = 'entity'`
  - Update `find_notes_by_entity()` to use generic type
- [ ] Update `api/repositories/graph_repo.py`:
  - Update `add_entity()` method documentation
  - Update `find_by_entity()` method to use generic type
- [ ] Re-process all 21 notes with new enrichment
- [ ] Verify no hallucinations (compare to test results):
  - Check Charlotte is extracted from Port Moody note
  - Check no Sarah hallucinations in notes without her

**Example frontmatter stripping:**
```python
def strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter before LLM enrichment."""
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            return parts[2].strip()  # Content after second ---
    return content
```

### **Step 4: Search & Query Updates (1 hour)**
- [ ] Update PARSE_SEARCH_QUERY prompt (`api/llm/prompts.py`):
  - Remove entity_type + entity_value paired fields
  - Add single entity field (just value)
  - Update all 7 examples to reflect new schema
- [ ] Update search service (`api/services/search.py`):
  - Update `parse_smart_query()` to handle new entity field (no type)
  - Update `search_notes_smart()` to use generic entity search
  - Add dimension-based filtering support (if dimensions are in query)
- [ ] Update graph queries (`api/graph.py`):
  - Update `find_notes_by_entity()` to always use `entity_type = 'entity'`
  - Keep fuzzy matching (LIKE operator)

### **Step 5: CLI & Note Creation Updates (1 hour)**
- [ ] Update note creation (`api/notes.py`):
  - **Update `write_markdown()` function (line 27)**:
    - Change `folder_path = NOTES_DIR / folder` (line 59) to `folder_path = NOTES_DIR` (flat structure)
    - Remove folder subdirectory creation (line 60)
    - Handle inbox specially if needed
  - **Update frontmatter (line 67-75)**:
    - Remove `"folder": folder` from frontmatter dict
    - Will be removed entirely later when frontmatter is eliminated
- [ ] Update CLI (`cli.py`):
  - Update `search_by_context_cmd()` function to query dimensions instead of folder
  - Update display functions (lines 128, 153, 162, 327) to show dimensions instead of folder
  - Update stats function (lines 420-422) to query dimension distribution instead of folder counts:
    ```python
    # Old: SELECT folder, COUNT(*) FROM notes_meta GROUP BY folder
    # New:
    SELECT 'has_action_items', SUM(has_action_items) FROM notes_meta
    UNION SELECT 'is_social', SUM(is_social) FROM notes_meta
    # ... etc for all 5 dimensions
    ```
- [ ] Add dimension-based view commands:
  - Map `/tasks` → `WHERE has_action_items = 1`
  - Map `/meetings` → `WHERE is_social = 1`
  - Map `/journal` → `WHERE is_emotional = 1`
  - Map `/reference` → `WHERE is_knowledge = 1`
  - Map `/ideas` → `WHERE is_exploratory = 1`

### **Step 6: Testing & Validation (30 min)**
- [ ] Re-run all 15 regression tests
- [ ] Verify all 21 notes are findable
- [ ] Test dimension-based filtering
- [ ] Test entity search (without type)
- [ ] Performance check (should be fast with only 21 notes)

**Total estimated time: 3.5-4 hours** (saved 30 min by skipping migration script)

### **Optional Addon: Explicit Task Management (30 min)**

Add structured task tracking without complicating core note system:

```sql
-- New table (optional addon)
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    note_id TEXT,          -- Links back to source note
    title TEXT,
    status TEXT,           -- 'todo', 'in_progress', 'done'
    due_date TEXT,         -- ISO datetime
    priority TEXT,         -- 'low', 'medium', 'high'
    created TEXT,
    completed TEXT,

    FOREIGN KEY (note_id) REFERENCES notes_meta(id)
);
```

**How it works:**
- Notes with `has_action_items = 1` automatically create tasks
- Tasks are **derived views** of notes (notes are source of truth)
- Can check off tasks, set priorities, query deadlines
- Doesn't change core enrichment or note creation flow

**CLI additions:**
```bash
/tasks                  # Show all todos
/tasks complete abc123  # Mark task done
/tasks --overdue        # Filter overdue tasks
/tasks --due-this-week  # Upcoming deadlines
```

**Why optional:**
- Core system works fine with `has_action_items` boolean
- Only add if you need explicit task completion tracking
- ~50 lines of code, clean separation

### **Future (Optional):**
- Consolidation-based entity clustering (when you have 100+ notes)
- Explicit task management (if you need GTD-style workflow)

---

## Migration Strategy

### **All-at-Once Migration (Clean Break)**

Since you have minimal data (21 notes), we'll do a simple direct migration - no migration script needed.

**Step-by-step:**
1. **Backup:** Copy ~/Notes and database to safe location
2. **Migrate files:** Move notes to flat structure (bash commands)
3. **Update database:** Run SQL directly (no migration script)
4. **Re-enrich:** Process all notes with new extraction
5. **Verify:** Test search and retrieval
6. **Clean up:** Remove old folder subdirectories (if any remain)

**Why no migration script?**
- Only 21 notes (trivial dataset)
- One-time operation (not production deploy)
- Direct SQL is faster and easier to debug
- Less code to maintain

**Rollback plan:**
```bash
# If something goes wrong, restore from backup
cp -r ~/Notes.backup/* ~/Notes/
cp ~/Notes/.index/notes.sqlite.backup ~/Notes/.index/notes.sqlite
```

### **Testing Plan:**

1. **Pre-migration:** Run regression tests, record results
2. **Post-migration:** Re-run same tests, compare
3. **Manual validation:** Search for known notes by different dimensions
4. **Performance:** Ensure no degradation
5. **Search pattern tracking:** Monitor structured vs text_query fallback usage

### **Search Query Fallback Tracking:**

Add analytics to monitor how often smart search uses:
- **Structured search only** (person, entity, emotion filters)
- **Text fallback only** (generic keyword search)
- **Both** (belt-and-suspenders approach)

```python
# Add to search service
class SearchMetrics:
    def __init__(self):
        self.structured_only = 0
        self.text_fallback_only = 0
        self.both = 0

    def record_query(self, filters):
        has_structured = any([
            filters.get('person'),
            filters.get('entity'),
            filters.get('emotion'),
            filters.get('context')
        ])
        has_text = bool(filters.get('text_query'))

        if has_structured and not has_text:
            self.structured_only += 1
        elif not has_structured and has_text:
            self.text_fallback_only += 1
        elif has_structured and has_text:
            self.both += 1

    def report(self):
        total = self.structured_only + self.text_fallback_only + self.both
        if total == 0:
            return "No queries tracked"

        return f"""
Search Strategy Distribution:
  Structured only:        {self.structured_only}/{total} ({self.structured_only/total:.1%})
  Text fallback only:     {self.text_fallback_only}/{total} ({self.text_fallback_only/total:.1%})
  Both (belt+suspenders): {self.both}/{total} ({self.both/total:.1%})

Text_query fallback usage: {(self.text_fallback_only + self.both)/total:.1%}
        """

# CLI command to view metrics
/search-stats
```

**Why track this?**
- If text_fallback is high (>50%), entity extraction might be too conservative
- If structured_only is high (>70%), text_query might be unnecessary overhead
- Helps tune the balance between precision (structured) and recall (text fallback)

---

## Expected Benefits

### **Immediate (Phase 1 & 2):**

✅ **Higher accuracy:** 71% vs 57% (test results)
✅ **Model robustness:** Works across qwen3 and gemma3
✅ **Simpler prompts:** Less cognitive load on LLM
✅ **Captures reality:** Multi-dimensional notes recognized
✅ **No hallucinations:** With proper frontmatter stripping

### **Future (Phase 3 & 4):**

✅ **Self-correcting categories:** Adapt to usage patterns
✅ **No forced decisions:** Notes can be multi-dimensional
✅ **Brain-aligned:** Matches human memory encoding/consolidation
✅ **Scalable:** Add new dimensions without re-processing

---

## Risks & Mitigation

### **Risk 1: Loss of entity type precision**
- **Concern:** Can't filter "show me all technologies"
- **Mitigation:** Phase 3 consolidation infers categories
- **Alternative:** Keep entity_type as optional hint, not requirement

### **Risk 2: Dimension extraction accuracy**
- **Concern:** Boolean dimensions might be inaccurate
- **Mitigation:** Test results show 71% accuracy (acceptable)
- **Fallback:** Can manually review and update dimensions for important notes

### **Risk 3: Migration complexity**
- **Concern:** Breaking existing notes/searches
- **Mitigation:** Backward-compatible dual-schema support
- **Testing:** Comprehensive regression test suite

### **Risk 4: User confusion**
- **Concern:** Multi-dimensional notes less intuitive?
- **Mitigation:** CLI still shows familiar views (tasks, meetings, etc.)
- **Education:** Document how dimensions map to old folders

---

## Success Metrics

### **Migration Success Criteria:**
- [ ] All 21 notes moved to new structure (0 lost)
- [ ] All 15 regression tests pass
- [ ] Database integrity check passes
- [ ] No performance degradation

### **Enrichment Quality:**
- [ ] Dimension extraction accuracy ≥ 70% (based on test results)
- [ ] Entity extraction accuracy ≥ 70%
- [ ] No hallucinations (verified via manual spot checks)
- [ ] Charlotte extracted from Port Moody note ✓

### **Search & Retrieval:**
- [ ] Can find notes by entities (without type)
- [ ] Can filter by dimensions (tasks/meetings/journal/etc.)
- [ ] Multi-dimensional queries work ("emotional meetings")
- [ ] Fuzzy search works (search "memory" finds "human memory")

### **CLI/UX:**
- [ ] Dimension-based views work correctly
- [ ] Stats dashboard shows dimension distribution
- [ ] User can navigate notes as easily as before
- [ ] New note creation uses flat structure

---

## Open Questions

1. **Should we keep folder field in database?**
   - ~~Option A: Keep as `primary_intent` field~~
   - **Option B: Remove entirely, use dimensions only** ✓ DECIDED
   - Rationale: Dimensions capture everything folder did, more accurately

2. **What about inbox folder?**
   - **Keep ~/Notes/inbox/** as special staging area
   - New notes go here until enriched
   - After enrichment, move to main ~/Notes/ directory (flat structure)

3. **Should entity categories be inferred later?**
   - Not needed immediately (only 21 notes)
   - Add Phase 3 (consolidation clustering) when you have 100+ notes
   - **Decision:** Skip for now, add later if needed

4. **Re-process existing notes or start fresh?**
   - **Option A:** Re-enrich all 21 notes with new extraction
   - **Option B:** Start fresh with new notes only
   - **Recommendation:** Re-enrich (only 21 notes, worth getting clean data)

---

## Next Steps

1. ✅ **Review this plan** - User approved (going with flat storage, no migration script)
2. [ ] **Create feature branch** - `refactor/flat-metadata`
3. [ ] **Backup everything** - Notes folder + database
4. [ ] **Execute Steps 1-6** - Direct bash/SQL commands (no migration script)
5. [ ] **Validate** - Test searches, check no data lost
6. [ ] **Commit changes** - Use git-commit-helper agent

**Ready to start when you give the word!**

---

## References

- Test results: `tests/test_flat_metadata_comparison.py`
- Test output (qwen3): `/tmp/flat_metadata_test_clean.txt`
- Test output (gemma3): `/tmp/flat_metadata_test_gemma3.txt`
- Prompt redesign: `api/llm/prompts.py` (ENRICH_METADATA, PARSE_SEARCH_QUERY)
- Brain science discussion: Session conversation
