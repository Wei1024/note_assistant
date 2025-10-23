# User Tag System - Implementation Plan

**Last Updated:** 2025-10-22
**Status:** Phase 1-2 Complete ✅ | Phase 3 In Progress 🚧

## Progress Summary

✅ **Completed:**
- Phase 1: Backend infrastructure (schema, repository, hashtag extraction)
- Phase 2: API endpoints (tag search, autocomplete)
- Migration script and documentation
- Test data with 11 manually tagged notes
- 3 meaningful tag edges created (vs 183 noisy LLM edges before)

🚧 **Current:**
- Phase 3: Frontend autocomplete component

⏳ **Next:**
- Tag input UI in note editor
- Tag management dashboard (optional)

---

## Overview

Transition from LLM-generated tags to user-controlled hashtag system with hierarchical support.

**Decision Summary:**
- ✅ User hashtags extracted from markdown (`#tag`, `#parent/child`)
- ✅ Auto-entities remain (WHO/WHAT/WHERE from LLM)
- ✅ Fresh start (clear old LLM tags)
- ✅ 2-level hierarchy max (soft limit, UI encourages this)
- ✅ No batch tagging initially (Phase 3+)
- ✅ Batch-compatible design (UUID-based, normalized storage)

---

## Phase 1: Backend Infrastructure ✅

### 1.1 Database Schema ✅

**File:** `api/db/schema_tags.sql`

**Tables:**
```sql
tags (
  id TEXT PRIMARY KEY,              -- UUID for stable references
  name TEXT UNIQUE,                 -- "project/alpha" or "personal"
  parent_id TEXT,                   -- NULL for root, UUID for children
  level INTEGER,                    -- 0=root, 1=child, 2=grandchild
  use_count INTEGER,                -- Cached count (auto-updated by triggers)
  created_at TEXT,
  last_used_at TEXT
)

note_tags (
  note_id TEXT,
  tag_id TEXT,
  created_at TEXT,
  source TEXT,                      -- 'user' | 'detected' | 'suggested'
  PRIMARY KEY (note_id, tag_id)
)
```

**Triggers:**
- `increment_tag_usage` - Auto-update use_count and last_used_at on insert
- `decrement_tag_usage` - Auto-update use_count on delete

**Views:**
- `tags_with_hierarchy` - Tags with parent info and child count
- `tag_usage_stats` - Analytics (active/stale/dormant status)

**Batch Compatibility:**
- UUID-based references → renaming safe
- Triggers auto-maintain counts → no manual cache invalidation
- Normalized storage → bulk operations are simple INSERT/DELETE

### 1.2 Hashtag Extraction ✅

**File:** `api/services/episodic.py`

**Function:** `extract_hashtags_from_text(text: str) -> List[str]`

**Pattern:** `#([a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*)`

**Features:**
- Extracts `#tag` and `#parent/child` syntax
- Case-insensitive deduplication
- Preserves order
- No LLM calls (instant)

**Examples:**
```python
extract_hashtags_from_text("#project/alpha and #sprint/planning")
# → ["project/alpha", "sprint/planning"]

extract_hashtags_from_text("#Personal #health/fitness #HEALTH/FITNESS")
# → ["personal", "health/fitness"]  # Deduped
```

**Changes to `extract_episodic_metadata()`:**
- ❌ Removed: `await _extract_tags_llm(text)`
- ✅ Added: `extract_hashtags_from_text(text)`
- Tags now come from user input, not LLM

### 1.3 Tag Repository ✅

**File:** `api/repositories/tag_repository.py`

**Key Methods:**

| Method | Purpose | Batch-Compatible |
|--------|---------|------------------|
| `get_or_create_tag(name)` | Create tag + parent hierarchy | ✅ Idempotent |
| `add_tag_to_note(note_id, tag_name)` | Single tag → note | ✅ Loop-friendly |
| `add_tags_to_note_bulk(note_id, tags)` | Multiple tags → note | ✅ Single transaction |
| `remove_tag_from_note(note_id, tag_id)` | Remove tag | ✅ Loop-friendly |
| `get_note_tags(note_id)` | Get all tags for note | - |
| `search_tags(query, limit)` | Autocomplete search | - |
| `get_tag_children(tag_name)` | Get hierarchy children | - |
| `rename_tag(tag_id, new_name)` | Rename (UUID-safe) | ✅ Bulk rename |
| `merge_tags(source_ids, target_name)` | Merge duplicates | ✅ Cleanup |
| `get_notes_by_tag(tag_id, include_children)` | Tag → notes | ✅ Batch selection |

**Design Highlights:**

1. **Hierarchy Parsing:**
   ```python
   "project/alpha" → (name="project/alpha", parent="project", level=1)
   ```
   - Auto-creates parent if doesn't exist
   - Parent-child relationship via `parent_id` FK

2. **Fuzzy Search (Autocomplete):**
   ```sql
   WHERE LOWER(name) LIKE 'proj%' OR LOWER(name) LIKE '%proj%'
   ORDER BY
     CASE WHEN exact THEN 1 WHEN prefix THEN 2 ELSE 3 END,
     use_count DESC
   ```
   - Prioritizes: exact → prefix → contains
   - Secondary sort: most used first

3. **Batch Operations:**
   ```python
   # Future: Batch tagging
   note_ids = get_notes_by_tag("project")
   for note_id in note_ids:
       add_tag_to_note(note_id, "archived")
   ```
   - Each operation is independent
   - Transaction-safe
   - UUID references prevent breakage

---

## Phase 2: API Endpoints ✅

### 2.1 Tag Management Routes ✅

**File:** `api/routes/tags.py`

**Status:** Core search endpoints implemented and tested

```python
# List all tags (tree structure)
GET /tags
Response: {
  "tags": [
    {
      "id": "uuid",
      "name": "project",
      "level": 0,
      "use_count": 23,
      "children": [
        {"id": "uuid", "name": "project/alpha", "use_count": 12},
        {"id": "uuid", "name": "project/beta", "use_count": 8}
      ]
    }
  ]
}

# Search tags (autocomplete)
GET /tags/search?q=proj&limit=10
Response: {
  "tags": [
    {"id": "uuid", "name": "project", "use_count": 23},
    {"id": "uuid", "name": "project/alpha", "use_count": 12},
    {"id": "uuid", "name": "side-project", "use_count": 3}
  ]
}

# Get tag children (for hierarchical autocomplete)
GET /tags/{tag_id}/children
Response: {
  "parent": {"id": "uuid", "name": "project"},
  "children": [
    {"id": "uuid", "name": "project/alpha", "use_count": 12},
    {"id": "uuid", "name": "project/beta", "use_count": 8}
  ]
}

# Get notes with tag (for filtering)
GET /tags/{tag_id}/notes?include_children=true
Response: {
  "tag": {"id": "uuid", "name": "project"},
  "note_ids": ["uuid1", "uuid2", ...],
  "count": 23
}

# Create tag (manual creation, optional)
POST /tags
Body: {"name": "client/acme"}
Response: {"id": "uuid", "name": "client/acme", "level": 1}

# Rename tag
PUT /tags/{tag_id}
Body: {"name": "new-name"}
Response: {"id": "uuid", "name": "new-name"}

# Merge tags (cleanup duplicates)
POST /tags/merge
Body: {
  "source_ids": ["uuid1", "uuid2"],
  "target_name": "canonical"
}
Response: {"target_id": "uuid", "merged_count": 2}

# Delete tag
DELETE /tags/{tag_id}
Response: {"deleted": true}

# Get tag analytics
GET /tags/stats
Response: {
  "stats": [
    {
      "name": "project",
      "use_count": 23,
      "last_used_at": "2025-10-22T...",
      "status": "active"  // active | recent | stale | dormant
    }
  ]
}
```

### 2.2 Note Tag Operations

**File:** `api/routes/notes.py` (extend existing)

```python
# Get tags for a note
GET /notes/{note_id}/tags
Response: {
  "tags": [
    {"id": "uuid", "name": "project/alpha", "source": "detected"},
    {"id": "uuid", "name": "urgent", "source": "user"}
  ]
}

# Add tag to note
POST /notes/{note_id}/tags
Body: {"tag_name": "project/alpha"}  # Auto-creates if doesn't exist
Response: {"tag": {"id": "uuid", "name": "project/alpha"}}

# Remove tag from note
DELETE /notes/{note_id}/tags/{tag_id}
Response: {"deleted": true}

# Get semantic tag suggestions (from similar notes)
GET /notes/{note_id}/tag-suggestions
Response: {
  "suggestions": [
    {
      "tag_name": "project/alpha",
      "reason": "Used in 4 similar notes",
      "frequency": 4
    }
  ]
}
```

---

## Phase 3: Frontend 🚧

**Current Editor:** `frontend/src/views/CaptureView.vue` (simple `<textarea>`)

### 3.1 Tag Autocomplete Component (IN PROGRESS)

**Next Steps:**
1. Create `TagAutocomplete.vue` component
2. Detect `#` keystroke in textarea
3. Extract query after `#` (e.g., `#pro` → query="pro")
4. Call `GET /tags/search?q=pro`
5. Show dropdown below cursor
6. Insert selected tag on click/enter

### 3.2 Tag Input Component (PLANNED)

**File:** `frontend/src/components/TagInput.vue` (new)

**Features:**
1. **Inline hashtag detection** in markdown editor
   - Detect `#` keystroke
   - Trigger autocomplete dropdown
   - Show hierarchy visually

2. **Autocomplete Dropdown:**
   ```
   ┌─────────────────────────────┐
   │ #project                (23)│  ← parent tag
   │   ├─ alpha             (12)│  ← child
   │   └─ beta               (8)│  ← child
   │ #side-project            (3)│  ← flat tag
   │ ────────────────────────────│
   │ Create "project/gamma"      │  ← if no match
   └─────────────────────────────┘
   ```

3. **Tag Input Field** (below editor)
   - Tag badges (removable)
   - Add new tag button
   - Shows detected vs user-added tags differently

4. **Real-time Feedback:**
   - "4 other notes with #project/alpha" tooltip
   - Visual hint when tag is recognized vs new

**Fuzzy Matching:**
```typescript
// User types: #proj
searchTags("proj") → API call
// Returns: ["project", "project/alpha", "side-project"]
// Display with highlighting: **proj**ect, **proj**ect/alpha
```

**Hierarchical Input:**
```typescript
// User types: #project/
searchTags("project/") → get_tag_children("project")
// Returns: ["project/alpha", "project/beta"]
// Show only children in dropdown
```

### 3.2 Tag Management Dashboard

**File:** `frontend/src/views/TagManagement.vue` (new)

**Sections:**

1. **Tag Tree View**
   ```
   Tags (42 total)
   ├─ project (23)
   │  ├─ alpha (12)
   │  └─ beta (8)
   ├─ client (15)
   │  ├─ acme (7)
   │  └─ initech (8)
   └─ personal (4)
   ```

2. **Tag List View** (flat)
   - Sortable by: name, use_count, last_used_at
   - Filter by: active, stale, dormant, never_used

3. **Actions:**
   - Rename tag (modal with input)
   - Merge duplicates (select multiple → merge)
   - Delete unused tags (confirmation)

4. **Analytics:**
   - Most used tags (bar chart)
   - Tag activity timeline (last 30 days)
   - Dormant tags (unused >90 days)

### 3.3 Graph View Integration

**File:** `frontend/src/views/GraphView.vue` (extend)

**Changes:**

1. **Tag editing in detail panel:**
   - When node selected → show tags
   - Add/remove tags without opening editor
   - Click tag → filter graph to that tag

2. **Tag-based filtering:**
   - "Show notes with #project/alpha" button
   - Highlight nodes with specific tag
   - Dim unrelated nodes

3. **Tag edges visualization:**
   - Now uses user tags (not LLM tags)
   - Jaccard threshold can be lower (0.2-0.3)
   - Edges should be meaningful, not hairballs

---

## Phase 4: Migration (TODO)

### 4.1 Migration Script

**File:** `migrate_to_user_tags.py`

```python
"""
Migration: LLM Tags → User Hashtag System

Steps:
1. Create new tables (tags, note_tags)
2. Clear old LLM-generated tags from graph_nodes
3. Parse any existing #hashtags from note content
4. Test with 10-15 manually tagged notes
"""

import sqlite3
from api.config import get_db_connection
from api.repositories.tag_repository import TagRepository
from api.services.episodic import extract_hashtags_from_text

def migrate():
    # Step 1: Create tables
    print("Creating tag tables...")
    conn = get_db_connection()
    with open('api/db/schema_tags.sql', 'r') as f:
        schema = f.read()
        conn.executescript(schema)
    conn.close()

    # Step 2: Clear old tags
    print("Clearing old LLM-generated tags...")
    conn = get_db_connection()
    conn.execute("UPDATE graph_nodes SET tags = '[]'")
    conn.commit()
    conn.close()

    # Step 3: Parse hashtags from existing notes
    print("Parsing hashtags from note content...")
    conn = get_db_connection()
    cursor = conn.execute("SELECT id, file_path FROM graph_nodes")
    notes = cursor.fetchall()

    for note_id, file_path in notes:
        # Read note content
        with open(file_path, 'r') as f:
            content = f.read()

        # Extract hashtags
        tags = extract_hashtags_from_text(content)

        # Add to database
        if tags:
            TagRepository.add_tags_to_note_bulk(note_id, tags, source='detected')
            print(f"  {note_id}: {tags}")

    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
```

### 4.2 Test Data Preparation

**Manual tagging strategy:**

1. **Select 10-15 notes** from realistic_test_notes.csv
2. **Add hashtags** to note content:
   ```markdown
   # GraphRAG Architecture Discussion

   Discussed vector database options with Sarah. #project/graphrag #research/rag
   Need to evaluate FAISS vs Weaviate. #tech/vector-db

   Action items:
   - Benchmark both systems #task
   - Present findings next week #meeting/team
   ```

3. **Tag categories to create:**
   - `#project/graphrag` (5 notes)
   - `#client/acme` (3 notes)
   - `#research/neuroscience` (4 notes)
   - `#health/fitness` (3 notes)
   - `#personal`, `#urgent`, `#task` (scattered)

4. **Expected outcomes:**
   - Autocomplete populated with ~10-15 tags
   - Hierarchy visible (project/*, client/*, research/*, health/*)
   - Tag edges connect thematically related notes
   - No hairballs (tags are specific, not generic)

---

## Testing Plan

### Unit Tests

**File:** `tests/test_tag_system.py`

```python
def test_hashtag_extraction():
    text = "#project/alpha and #sprint/planning"
    tags = extract_hashtags_from_text(text)
    assert tags == ["project/alpha", "sprint/planning"]

def test_hierarchy_parsing():
    name, parent, level = TagRepository._parse_tag_hierarchy("project/alpha")
    assert name == "project/alpha"
    assert parent == "project"
    assert level == 1

def test_get_or_create_tag():
    tag_id = TagRepository.get_or_create_tag("project/alpha")
    # Should auto-create "project" parent
    parent = get_tag_by_name("project")
    assert parent is not None

def test_fuzzy_search():
    create_tags(["project", "project/alpha", "side-project"])
    results = TagRepository.search_tags("proj")
    assert len(results) == 3
    assert results[0]['name'] == "project"  # Prefix match first

def test_merge_tags():
    # Create duplicates
    id1 = TagRepository.get_or_create_tag("work")
    id2 = TagRepository.get_or_create_tag("Work")
    id3 = TagRepository.get_or_create_tag("WORK")

    # Merge to canonical
    target_id = TagRepository.merge_tags([id1, id2, id3], "work")

    # Check only one remains
    all_tags = TagRepository.get_all_tags()
    work_tags = [t for t in all_tags if 'work' in t['name'].lower()]
    assert len(work_tags) == 1
```

### Integration Tests

**Manual testing workflow:**

1. **Create note with hashtags:**
   ```bash
   curl -X POST http://localhost:8000/notes \
     -d '{"content": "Meeting notes #project/alpha #urgent"}'
   ```

2. **Verify tags extracted:**
   ```bash
   curl http://localhost:8000/notes/{id}/tags
   # Should return: ["project/alpha", "urgent"]
   ```

3. **Test autocomplete:**
   ```bash
   curl http://localhost:8000/tags/search?q=proj
   # Should return: ["project", "project/alpha"]
   ```

4. **Test hierarchy:**
   ```bash
   curl http://localhost:8000/tags/{project_id}/children
   # Should return: ["project/alpha", "project/beta"]
   ```

5. **Test merge:**
   ```bash
   curl -X POST http://localhost:8000/tags/merge \
     -d '{"source_ids": ["uuid1", "uuid2"], "target_name": "work"}'
   ```

### Graph Visualization Test

1. Import 50 test notes with manual tags
2. View graph with different filters:
   - All (semantic + entity, no tags)
   - Tags only
   - Specific tag filter
3. Verify:
   - No hairballs
   - Tag edges connect thematically related notes
   - Hierarchy rolls up correctly

---

## Success Criteria

### Phase 1 (Backend) ✅
- [x] Database schema created with triggers and views
- [x] Hashtag extraction function working
- [x] Tag repository with all CRUD operations
- [x] Batch-compatible design (UUID-based)

### Phase 2 (API) ⏳
- [ ] All tag management endpoints implemented
- [ ] Note-tag relationship endpoints working
- [ ] Autocomplete endpoint returns fuzzy matches
- [ ] Tag suggestions from similar notes

### Phase 3 (Frontend) ⏳
- [ ] Inline hashtag detection in markdown editor
- [ ] Autocomplete dropdown with hierarchy
- [ ] Tag management dashboard (view, merge, rename)
- [ ] Graph view tag filtering

### Phase 4 (Migration) ⏳
- [ ] Migration script clears old tags
- [ ] 10-15 notes manually tagged for testing
- [ ] Tag edges visible in graph
- [ ] No performance issues with new schema

### User Experience Goals
- [ ] Tagging feels "frictionless" (<2 seconds to add tag)
- [ ] Autocomplete prevents duplicates
- [ ] Hierarchy emerges naturally (users don't pre-plan)
- [ ] Immediate value visible ("4 other notes with this tag")
- [ ] Tag cleanup tools work smoothly (merge/rename)

---

## Future Enhancements (Phase 3+)

### Batch Tagging
```python
# Select multiple notes in graph view
selected_notes = ["uuid1", "uuid2", "uuid3"]

# Apply tag to all
for note_id in selected_notes:
    TagRepository.add_tag_to_note(note_id, "sprint/planning")

# Or optimize with bulk API:
POST /notes/batch/tags
Body: {
  "note_ids": ["uuid1", "uuid2", "uuid3"],
  "tag_name": "sprint/planning"
}
```

### Tag Analytics Dashboard
- Tag co-occurrence heatmap
- Tag usage over time (line chart)
- Trending tags (most growth this month)
- Tag network graph (which tags appear together)

### Smart Suggestions
- Semantic suggestions: "Similar notes use #project/alpha"
- Context-based: "You often tag client meetings with #client/name"
- Completion: "You started typing #proj, did you mean #project/alpha?"

### Tag Templates
- Quick-add common tag sets
- Example: "Meeting template" → auto-adds #meeting, #task, #follow-up
- User-customizable

---

## Design Philosophy

1. **User agency over automation**
   - Tags are explicit user decisions
   - Entities remain automated (WHO/WHAT/WHERE)
   - Clear separation of concerns

2. **Emergent structure**
   - Hierarchy emerges from usage, not pre-planning
   - No forced taxonomies
   - Users create tags as needed

3. **Frictionless interaction**
   - Inline `#hashtag` syntax (familiar)
   - Autocomplete in <2 seconds
   - Keyboard-driven workflow

4. **Show immediate value**
   - "4 other notes" feedback
   - Related notes visible on hover
   - Graph filters by tag

5. **Batch-compatible design**
   - UUID-based references
   - Normalized storage
   - Transaction-safe operations
   - Future-proof for power users

---

## Quick Start Guide

### Testing Current System

**1. Add hashtags to notes:**
```bash
# Edit any note file in ~/Notes/
# Add tags like: #project/alpha #meeting #urgent
```

**2. Re-run migration to detect new tags:**
```bash
python migrate_to_user_tags.py
```

**3. Rebuild edges:**
```bash
python rebuild_all_edges.py
```

**4. Test API:**
```bash
# Start backend
cd api && uvicorn main:app --reload

# Test search
curl "http://localhost:8000/tags/search?q=proj"

# Get all tags
curl "http://localhost:8000/tags"
```

**5. View in graph:**
```bash
# Start frontend
cd frontend && npm run dev

# Open http://localhost:5173
# Click graph view, toggle filters
```

### Current Test Data

- **11 notes** manually tagged
- **27 unique tags** (14 root + 13 children)
- **3 tag edges** connecting related notes
- **Clusters:** #project/graphrag (4), #meeting (3), #personal (3), #health/fitness (2)

---

## References

- **Research doc**: User's tag research compilation
- **Database schema**: `api/db/schema_tags.sql`
- **Tag repository**: `api/repositories/tag_repository.py`
- **Tag API routes**: `api/routes/tags.py`
- **Hashtag extraction**: `api/services/episodic.py`
- **Migration summary**: `docs/tag_system_migration_complete.md`
