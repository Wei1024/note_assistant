"""
Memory Consolidation Service
Background linking service that connects today's notes to existing knowledge.

Inspired by brain's memory consolidation during sleep - runs asynchronously
to find and create meaningful connections without blocking note capture.
"""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from .config import DB_PATH
from .capture_service import get_llm
from .graph import add_link
from .notes import get_notes_created_today


def _iso_now():
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _iso_today_start():
    """Get ISO timestamp for start of today (00:00:00)"""
    today = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    return today.isoformat()


def calculate_candidate_overlap(note: Dict, candidate_id: str, candidate_path: str,
                                note_tags: set = None, db_cursor=None) -> Dict:
    """Calculate how many dimensions two notes share.

    This provides quantitative context for LLM to assess connection strength.

    Args:
        note: Dict with entities from get_notes_created_today()
        candidate_id: Candidate note ID
        candidate_path: Candidate note path (for tag extraction)
        note_tags: Optional pre-computed tags for the note (optimization)
        db_cursor: Optional database cursor (optimization)

    Returns:
        {
            "shared_people": ["Sarah", "Alex"],
            "shared_topics": ["memory", "consolidation"],
            "shared_projects": ["note-taking app"],
            "shared_tags": ["research"],
            "people_count": 2,
            "topics_count": 2,
            "projects_count": 1,
            "tags_count": 1,
            "total": 6
        }
    """
    import yaml

    # Use provided cursor or create new connection
    own_connection = False
    if db_cursor is None:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        own_connection = True
    else:
        cur = db_cursor

    # Get note's entities
    note_people = {e[1] for e in note.get("entities", []) if e[0] == "person"}
    note_topics = {e[1] for e in note.get("entities", []) if e[0] == "topic"}
    note_projects = {e[1] for e in note.get("entities", []) if e[0] == "project"}

    # Get note's tags (use cached if provided)
    if note_tags is None:
        note_tags = set()
        try:
            with open(note.get("path", ""), 'r', encoding='utf-8') as f:
                content = f.read()
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 2:
                        frontmatter = yaml.safe_load(parts[1])
                        note_tags = set(frontmatter.get("tags", []))
        except Exception:
            pass

    # Get candidate's entities
    cur.execute("SELECT entity_type, entity_value FROM notes_entities WHERE note_id = ?", (candidate_id,))
    candidate_entities = cur.fetchall()

    candidate_people = {e[1] for e in candidate_entities if e[0] == "person"}
    candidate_topics = {e[1] for e in candidate_entities if e[0] == "topic"}
    candidate_projects = {e[1] for e in candidate_entities if e[0] == "project"}

    # Get candidate's tags
    candidate_tags = set()
    try:
        with open(candidate_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 2:
                    frontmatter = yaml.safe_load(parts[1])
                    candidate_tags = set(frontmatter.get("tags", []))
    except Exception:
        pass

    if own_connection:
        con.close()

    # Calculate overlaps
    shared_people = list(note_people & candidate_people)
    shared_topics = list(note_topics & candidate_topics)
    shared_projects = list(note_projects & candidate_projects)
    shared_tags = list(note_tags & candidate_tags)

    overlap = {
        "shared_people": shared_people,
        "shared_topics": shared_topics,
        "shared_projects": shared_projects,
        "shared_tags": shared_tags,
        "people_count": len(shared_people),
        "topics_count": len(shared_topics),
        "projects_count": len(shared_projects),
        "tags_count": len(shared_tags),
        "total": len(shared_people) + len(shared_topics) + len(shared_projects) + len(shared_tags)
    }

    return overlap


def find_link_candidates(note: Dict, max_candidates: int = 10,
                         exclude_today: bool = True) -> List[Dict]:
    """Find potential notes to link to based on shared metadata.

    Args:
        note: Dict with id, entities, dimensions
        max_candidates: Maximum number of candidates to return
        exclude_today: If True, only search notes before today (established knowledge)

    Returns:
        List of candidate dicts with: id, title, snippet, match_reason
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    candidates = {}  # Use dict to deduplicate by note_id

    # Get date filter
    if exclude_today:
        today_start = _iso_today_start()
        date_filter = f"AND m.created < '{today_start}'"
    else:
        date_filter = ""

    # Search by people
    people = [e[1] for e in note.get("entities", []) if e[0] == "person"]
    for person in people:
        cur.execute(f"""
            SELECT DISTINCT m.id, m.path
            FROM notes_entities e
            JOIN notes_meta m ON m.id = e.note_id
            WHERE e.entity_type = 'person'
              AND e.entity_value = ?
              AND e.note_id != ?
              {date_filter}
            ORDER BY m.created DESC
            LIMIT 5
        """, (person, note["id"]))

        for row in cur.fetchall():
            if row[0] not in candidates:
                candidates[row[0]] = {
                    "id": row[0],
                    "path": row[1],
                    "match_reason": f"mentions {person}"
                }

    # Search by topics
    topics = [e[1] for e in note.get("entities", []) if e[0] == "topic"]
    for topic in topics[:3]:  # Limit to top 3 topics
        cur.execute(f"""
            SELECT DISTINCT m.id, m.path
            FROM notes_entities e
            JOIN notes_meta m ON m.id = e.note_id
            WHERE e.entity_type = 'topic'
              AND e.entity_value = ?
              AND e.note_id != ?
              {date_filter}
            ORDER BY m.created DESC
            LIMIT 3
        """, (topic, note["id"]))

        for row in cur.fetchall():
            if row[0] not in candidates:
                candidates[row[0]] = {
                    "id": row[0],
                    "path": row[1],
                    "match_reason": f"discusses {topic}"
                }

    # Search by projects
    projects = [e[1] for e in note.get("entities", []) if e[0] == "project"]
    for project in projects:
        cur.execute(f"""
            SELECT DISTINCT m.id, m.path
            FROM notes_entities e
            JOIN notes_meta m ON m.id = e.note_id
            WHERE e.entity_type = 'project'
              AND e.entity_value = ?
              AND e.note_id != ?
              {date_filter}
            ORDER BY m.created DESC
            LIMIT 3
        """, (project, note["id"]))

        for row in cur.fetchall():
            if row[0] not in candidates:
                candidates[row[0]] = {
                    "id": row[0],
                    "path": row[1],
                    "match_reason": f"related to {project}"
                }

    # Search by tags (Phase 2.3b enhancement)
    # Tags are intentional metadata - high signal for relatedness
    from .fts import search_notes

    # Get tags from note metadata
    tags = []
    try:
        with open(note.get("path", ""), 'r', encoding='utf-8') as f:
            content = f.read()
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 2:
                    import yaml
                    frontmatter = yaml.safe_load(parts[1])
                    tags = frontmatter.get("tags", [])
    except Exception:
        pass

    # Search FTS5 by each tag
    for tag in tags[:3]:  # Top 3 tags
        tag_results = search_notes(tag, limit=2)
        for result in tag_results:
            result_path = result.get("path")

            # Lookup note ID from path
            try:
                cur.execute("SELECT id, created FROM notes_meta WHERE path = ?", (result_path,))
                row = cur.fetchone()
                if not row:
                    continue

                result_id, result_created = row

                # Skip self
                if result_id == note["id"]:
                    continue

                # Skip today's notes if exclude_today
                if exclude_today and result_created >= today_start:
                    continue

                # Add to candidates
                if result_id not in candidates:
                    candidates[result_id] = {
                        "id": result_id,
                        "path": result_path,
                        "match_reason": f"shares tag: {tag}"
                    }

            except Exception as e:
                # Skip on error
                continue

    # Pre-compute note's tags for overlap calculation (optimization)
    import yaml
    note_tags = set()
    try:
        with open(note.get("path", ""), 'r', encoding='utf-8') as f:
            content = f.read()
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 2:
                    frontmatter = yaml.safe_load(parts[1])
                    note_tags = set(frontmatter.get("tags", []))
    except Exception:
        pass

    # Keep DB connection open for overlap calculations (optimization)
    # Read snippets from files
    result = []
    for candidate in list(candidates.values())[:max_candidates]:
        try:
            with open(candidate["path"], 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract title and body
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1])
                        title = frontmatter.get("title", "Untitled")
                        body = parts[2].strip()
                        snippet = body[:200]  # First 200 chars
                    else:
                        title = "Untitled"
                        snippet = content[:200]
                else:
                    title = "Untitled"
                    snippet = content[:200]

                # Calculate overlap statistics for LLM context (with optimizations)
                overlap = calculate_candidate_overlap(
                    note, candidate["id"], candidate["path"],
                    note_tags=note_tags, db_cursor=cur
                )

                result.append({
                    "id": candidate["id"],
                    "title": title,
                    "snippet": snippet,
                    "match_reason": candidate["match_reason"],
                    "overlap": overlap
                })
        except Exception as e:
            print(f"Error reading candidate {candidate['path']}: {e}")
            continue

    con.close()
    return result


async def suggest_links_batch(new_note_text: str, candidates: List[Dict]) -> List[Dict]:
    """Use LLM to analyze all candidates at once and suggest links.

    Args:
        new_note_text: Full text of the new note
        candidates: List of candidate notes to compare against

    Returns:
        List of suggested links: [{"id": "...", "link_type": "...", "reason": "..."}, ...]
    """
    if not candidates:
        return []

    llm = get_llm()

    # Format all candidates in one prompt with overlap statistics
    candidates_text = "\n".join([
        f"{i+1}. [{c['id']}] {c['title']}\n"
        f"   Snippet: {c['snippet']}\n"
        f"   Match: {c['match_reason']}\n"
        f"   Overlap: {c['overlap']['total']} shared dimensions "
        f"({c['overlap']['people_count']} people, {c['overlap']['topics_count']} topics, "
        f"{c['overlap']['projects_count']} projects, {c['overlap']['tags_count']} tags)"
        for i, c in enumerate(candidates)
    ])

    prompt = f"""You are a knowledge graph linker. Analyze connections between notes.

NEW NOTE:
{new_note_text}

EXISTING NOTES:
{candidates_text}

Task: Which existing notes should link to the new note? Analyze ALL at once.

Link Types:
- **related**: Discusses same topic/concept
- **spawned**: New note is follow-up/action from old note
- **references**: New note builds on old note's idea
- **contradicts**: New note challenges old note's conclusion

Rules:
1. Only include if CLEAR connection (shared specific concept/person/project/decision)
2. Use the "Overlap" statistics as context - higher overlap suggests stronger potential connection
3. Reason must be specific (not "both mention topics")
4. Max 5 links total (prioritize strongest)
5. Must use exact note ID from brackets above
6. Trust your judgment - if overlap is high but semantic meaning differs, skip it

Return ONLY a JSON array (even if empty or single link):

Examples:
- Multiple links:
[
  {{"id": "2025-01-10T14:30:00-08:00_abc1", "link_type": "spawned", "reason": "New note is action item from this meeting"}},
  {{"id": "2025-01-09T10:15:00-08:00_def2", "link_type": "references", "reason": "Builds on the memory consolidation research discussed here"}}
]

- Single link:
[
  {{"id": "2025-01-08T09:00:00-08:00_ghi3", "link_type": "related", "reason": "Both discuss Sarah's research on hippocampus function"}}
]

- No links:
[]

JSON:"""

    try:
        response = await llm.ainvoke(prompt)
        result = json.loads(response.content)

        # Handle both array and single object responses
        if isinstance(result, dict):
            result = [result]
        elif not isinstance(result, list):
            result = []

        # Validate and filter results
        valid_links = []
        valid_ids = {c["id"] for c in candidates}

        for link in result:
            # Check required fields
            if not all(k in link for k in ["id", "link_type", "reason"]):
                continue

            # Validate ID
            if link["id"] not in valid_ids:
                continue

            # Validate link type
            if link["link_type"] not in ["related", "spawned", "references", "contradicts"]:
                continue

            # Heuristic: Skip very vague reasons (relaxed filter)
            reason_lower = link["reason"].lower()
            vague_keywords = ["might be", "possibly", "unclear"]
            if any(kw in reason_lower for kw in vague_keywords):
                continue

            valid_links.append(link)

        return valid_links[:5]  # Max 5 links

    except Exception as e:
        print(f"Error in suggest_links_batch: {e}")
        return []


async def consolidate_note(note_id: str) -> Dict:
    """Consolidate a single note - find and create links to existing knowledge.

    Core function that processes one note at a time. This allows flexible scheduling:
    - Run after each note is created (continuous)
    - Run every N minutes on recent notes (periodic)
    - Run once at end of day on all notes (batch)

    Args:
        note_id: ID of note to consolidate

    Returns:
        Dict with consolidation statistics for this note
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Get note data
    cur.execute("""
        SELECT id, path, created
        FROM notes_meta
        WHERE id = ?
    """, (note_id,))
    row = cur.fetchone()

    if not row:
        con.close()
        return {"error": "Note not found", "note_id": note_id}

    note_id, path, created = row

    # Read note body from file
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract body (after frontmatter)
            if content.startswith('---'):
                parts = content.split('---', 2)
                body = parts[2].strip() if len(parts) >= 3 else content
            else:
                body = content
    except Exception as e:
        con.close()
        return {"error": f"Could not read note file: {e}", "note_id": note_id}

    # Get entities and dimensions
    cur.execute("SELECT entity_type, entity_value FROM notes_entities WHERE note_id = ?", (note_id,))
    entities = cur.fetchall()

    cur.execute("SELECT dimension_type, dimension_value FROM notes_dimensions WHERE note_id = ?", (note_id,))
    dimensions = cur.fetchall()

    con.close()

    note = {
        "id": note_id,
        "path": path,
        "body": body,
        "created": created,
        "entities": entities,
        "dimensions": dimensions
    }

    # Find candidates
    candidates = find_link_candidates(note, max_candidates=10, exclude_today=False)

    if not candidates:
        return {
            "note_id": note_id,
            "links_created": 0,
            "candidates_found": 0
        }

    # Suggest links using LLM
    suggested_links = await suggest_links_batch(note["body"], candidates)

    # Store links in database
    links_added = 0
    for link in suggested_links:
        try:
            add_link(note["id"], link["id"], link["link_type"])
            links_added += 1
        except Exception as e:
            print(f"Error storing link from {note['id']} to {link['id']}: {e}")

    return {
        "note_id": note_id,
        "links_created": links_added,
        "candidates_found": len(candidates)
    }


async def consolidate_notes(note_ids: List[str]) -> Dict:
    """Batch consolidate a list of notes sequentially.

    Generic batch processor - processes notes one at a time in sequence.
    Each note can link to any older note (including earlier in the batch).

    Args:
        note_ids: List of note IDs to consolidate

    Returns:
        Dict with aggregated consolidation statistics
    """
    stats = {
        "notes_processed": 0,
        "links_created": 0,
        "notes_with_links": 0,
        "started_at": _iso_now()
    }

    for note_id in note_ids:
        result = await consolidate_note(note_id)

        stats["notes_processed"] += 1
        if result.get("links_created", 0) > 0:
            stats["notes_with_links"] += 1
            stats["links_created"] += result["links_created"]

    stats["completed_at"] = _iso_now()

    return stats


async def consolidate_daily_notes() -> Dict:
    """Convenience wrapper to consolidate all of today's notes.

    Returns:
        Dict with aggregated consolidation statistics
    """
    notes = get_notes_created_today()
    note_ids = [note["id"] for note in notes]
    return await consolidate_notes(note_ids)
