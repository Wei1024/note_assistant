-- ============================================================================
-- USER TAG SYSTEM SCHEMA
-- ============================================================================
-- This schema supports user-created hierarchical tags with batch operations
-- Design: UUID-based references, normalized storage, many-to-many relationships
-- Future-compatible: Batch tagging, tag analytics, tag evolution tracking
-- ============================================================================

-- ============================================================================
-- TAGS TABLE
-- ============================================================================
-- Stores all unique tags in the system
-- Supports 2-level hierarchy: parent/child (e.g., "project/alpha")
-- Uses UUIDs for stable references (renaming won't break relationships)
-- ============================================================================

CREATE TABLE IF NOT EXISTS tags (
  id TEXT PRIMARY KEY,                    -- UUID v4
  name TEXT NOT NULL UNIQUE,              -- Full tag name: "project/alpha" or "personal"
  parent_id TEXT,                         -- NULL for root tags, parent UUID for children
  level INTEGER NOT NULL DEFAULT 0,       -- 0 = root, 1 = child, 2 = grandchild (soft limit at 2)
  use_count INTEGER NOT NULL DEFAULT 0,   -- Cached count of notes using this tag
  created_at TEXT NOT NULL,               -- ISO8601 timestamp
  last_used_at TEXT,                      -- ISO8601 timestamp of last usage

  FOREIGN KEY (parent_id) REFERENCES tags(id) ON DELETE CASCADE,
  CHECK (level >= 0 AND level <= 3)       -- Allow up to 3 levels, but UI encourages 2
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
CREATE INDEX IF NOT EXISTS idx_tags_parent ON tags(parent_id);
CREATE INDEX IF NOT EXISTS idx_tags_level ON tags(level);
CREATE INDEX IF NOT EXISTS idx_tags_use_count ON tags(use_count DESC);
CREATE INDEX IF NOT EXISTS idx_tags_last_used ON tags(last_used_at DESC);

-- ============================================================================
-- NOTE_TAGS JUNCTION TABLE
-- ============================================================================
-- Many-to-many relationship between notes and tags
-- Supports batch operations (insert/delete multiple rows at once)
-- Tracks creation timestamp for tag history/analytics
-- ============================================================================

CREATE TABLE IF NOT EXISTS note_tags (
  note_id TEXT NOT NULL,                  -- Foreign key to graph_nodes.id
  tag_id TEXT NOT NULL,                   -- Foreign key to tags.id
  created_at TEXT NOT NULL,               -- ISO8601 timestamp when tag was added
  source TEXT DEFAULT 'user',             -- 'user' | 'detected' | 'suggested' (for future auto-tag)

  PRIMARY KEY (note_id, tag_id),
  FOREIGN KEY (note_id) REFERENCES graph_nodes(id) ON DELETE CASCADE,
  FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_note_tags_note ON note_tags(note_id);
CREATE INDEX IF NOT EXISTS idx_note_tags_tag ON note_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_note_tags_created ON note_tags(created_at DESC);

-- ============================================================================
-- TRIGGERS
-- ============================================================================
-- Auto-update use_count and last_used_at when tags are added/removed
-- ============================================================================

-- Increment use_count when tag is added to a note
CREATE TRIGGER IF NOT EXISTS increment_tag_usage
AFTER INSERT ON note_tags
BEGIN
  UPDATE tags
  SET
    use_count = use_count + 1,
    last_used_at = NEW.created_at
  WHERE id = NEW.tag_id;
END;

-- Decrement use_count when tag is removed from a note
CREATE TRIGGER IF NOT EXISTS decrement_tag_usage
AFTER DELETE ON note_tags
BEGIN
  UPDATE tags
  SET use_count = use_count - 1
  WHERE id = OLD.tag_id;
END;

-- ============================================================================
-- VIEWS
-- ============================================================================
-- Convenient views for common queries
-- ============================================================================

-- View: All tags with their parent information and usage stats
CREATE VIEW IF NOT EXISTS tags_with_hierarchy AS
SELECT
  t.id,
  t.name,
  t.parent_id,
  p.name as parent_name,
  t.level,
  t.use_count,
  t.created_at,
  t.last_used_at,
  (SELECT COUNT(*) FROM tags WHERE parent_id = t.id) as child_count
FROM tags t
LEFT JOIN tags p ON t.parent_id = p.id;

-- View: Tag usage analytics
CREATE VIEW IF NOT EXISTS tag_usage_stats AS
SELECT
  t.id,
  t.name,
  t.use_count,
  t.last_used_at,
  julianday('now') - julianday(t.last_used_at) as days_since_last_use,
  CASE
    WHEN t.last_used_at IS NULL THEN 'never_used'
    WHEN julianday('now') - julianday(t.last_used_at) <= 7 THEN 'active'
    WHEN julianday('now') - julianday(t.last_used_at) <= 30 THEN 'recent'
    WHEN julianday('now') - julianday(t.last_used_at) <= 90 THEN 'stale'
    ELSE 'dormant'
  END as status
FROM tags t;

-- ============================================================================
-- MIGRATION NOTES
-- ============================================================================
-- 1. This schema REPLACES the 'tags' JSON column in graph_nodes
-- 2. Old tags column can be kept for backward compatibility or dropped
-- 3. Migration script should:
--    - Create these tables
--    - Parse existing tags from graph_nodes.tags JSON
--    - Populate tags and note_tags tables
--    - Clear graph_nodes.tags (or drop column)
-- ============================================================================
