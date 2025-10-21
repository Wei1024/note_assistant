# QuickNote AI — Full Build Spec (Tauri Frontend + Python Backend + LangGraph)

**Goal**: A minimal, always-on-top capture window (like Spotlight) where you type a thought → a local LLM (Qwen3/Gemma3 4B) suggests `title/folder/tags` → note saved as Markdown with YAML front-matter → instantly searchable via SQLite FTS5.

**Stack**: Frontend = Tauri (Rust shell + web UI). Backend = Python (FastAPI + LangGraph). LLM = Local (via Ollama).

---

## 0) MVP Feature Checklist

- Global hotkey opens a frameless, always-on-top window.
- Multiline input; Enter = Save (LLM organize), Cmd/Ctrl+Enter = Save to Inbox (skip LLM), Esc = Close.
- Files written as Markdown + YAML under `~/Notes/<folder>/...`.
- SQLite FTS5 index for fast search; `/` toggles search mode; Enter opens note in default editor.
- If LLM unavailable or JSON invalid → fallback to Inbox.
- **NEW**: Configurable model selection (Qwen3 vs Gemma3)
- **NEW**: LangGraph for reliable tool calling and classification

---

## 1) Architecture

```
[Tauri UI]  <--tauri::invoke-->  [Python FastAPI @ http://127.0.0.1:8787]
                     |                               |
                capture/search              LangGraph Agent
                     |                               |
                  (user)          ---->        SQLite FTS5
                                         |             |
                                    Markdown Files    |
                                         |             |
                                Local LLM (Qwen3/Gemma3 4B) via Ollama
```

**Why Tauri + Python + LangGraph?**
- Tauri: Tiny, native, always-on-top window + global hotkeys
- Python FastAPI: Quick iteration, easy SQLite integration
- LangGraph: Production-ready agent framework with tool calling and validation

---

## 2) Directory Layout

```
quicknote-ai/
├─ app-frontend/                # Tauri project (Vite + React)
│  ├─ src-tauri/
│  │  ├─ src/
│  │  │  ├─ main.rs
│  │  │  └─ cmds.rs             # optional native commands
│  │  └─ tauri.conf.json
│  ├─ src/
│  │  ├─ main.tsx               # UI logic (capture/search)
│  │  └─ styles.css
│  └─ package.json
├─ app-backend/                 # Python FastAPI backend
│  ├─ __init__.py
│  ├─ main.py
│  ├─ classification_tool.py    # LangGraph tool (replaces llm.py)
│  ├─ notes.py
│  ├─ fts.py
│  ├─ models.py
│  ├─ config.py
│  └─ requirements.txt
├─ .env                         # Configuration
├─ test_model_comparison.py     # Compare Qwen3 vs Gemma3
├─ switch_model.sh              # Easy model switching
└─ README.md
```

---

## 3) Environment (.env)

```bash
# Notes Configuration
NOTES_DIR=~/Notes
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8787
OPEN_EDITOR_CMD=code            # or "open" (macOS) / "xdg-open" (Linux)

# LLM Configuration - EASY TO SWITCH!
LLM_MODEL=qwen3:4b-instruct     # or gemma3:4b
LLM_BASE_URL=http://127.0.0.1:11434
LLM_TEMPERATURE=0.2

# Optional: LangSmith for debugging (dev only)
# LANGSMITH_TRACING=false
# LANGSMITH_API_KEY=your-key-here
```

**Quick model switching**:
```bash
./switch_model.sh qwen    # Switch to Qwen3
./switch_model.sh gemma   # Switch to Gemma3
```

---

## 4) Notes File Layout & YAML Schema

```
~/Notes/
  inbox/
  projects/
  people/
  research/
  journal/
  .index/notes.sqlite
```

**Markdown template**:
```markdown
---
id: 2025-10-01T21:04:13Z_d4c2
title: Draft ALB + Cognito flow
tags: [aws, architecture, alb, cognito]
folder: projects
related_ids: []
created: 2025-10-01T21:04:13Z
updated: 2025-10-01T21:04:13Z
---
Consider ALB public, Fargate private. Check ECR VPC endpoints issue.
```

**Filename**: `YYYY-MM-DD-slugified-title.md` (fallback to timestamp if no title)

---

## 5) SQLite FTS5 Schema

```sql
-- FTS content table
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
  id UNINDEXED,
  title,
  body,
  tags,
  content=''
);

-- Metadata table
CREATE TABLE IF NOT EXISTS notes_meta (
  id TEXT PRIMARY KEY,
  path TEXT NOT NULL,
  folder TEXT NOT NULL,
  created TEXT NOT NULL,
  updated TEXT NOT NULL
);
```

**Search query**:
```sql
SELECT n.path,
       snippet(notes_fts, 1, '<b>','</b>','…', 8) AS snip,
       bm25(notes_fts) AS rank
FROM notes_fts f
JOIN notes_meta n ON n.id = f.id
WHERE f MATCH ?
ORDER BY rank
LIMIT 20;
```

---

## 6) Backend (Python / FastAPI + LangGraph)

### app-backend/requirements.txt

```
fastapi
uvicorn[standard]
pydantic
python-dotenv
pyyaml
httpx

# LangGraph for agent framework
langchain-core>=0.3.76
langchain-ollama>=0.3.8
langgraph>=0.6.8
grandalf                        # For graph visualization (dev only)
```

---

### app-backend/config.py

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Notes storage
NOTES_DIR = Path(os.getenv("NOTES_DIR", "~/Notes")).expanduser()
DB_PATH = NOTES_DIR / ".index" / "notes.sqlite"

# Backend server
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8787"))

# LLM Configuration
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:4b-instruct")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# Editor
OPEN_EDITOR_CMD = os.getenv("OPEN_EDITOR_CMD", "code")

# Display config on startup
print(f"🤖 LLM Model: {LLM_MODEL}")
print(f"📁 Notes Dir: {NOTES_DIR}")
```

---

### app-backend/models.py

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class ClassifyRequest(BaseModel):
    text: str
    context_hint: Optional[str] = None

class ClassifyResponse(BaseModel):
    title: str
    folder: str
    tags: List[str]
    first_sentence: str
    path: str

class SearchRequest(BaseModel):
    query: str
    limit: int = 20

class SearchHit(BaseModel):
    path: str
    snippet: str
    score: float = 0.0
```

---

### app-backend/classification_tool.py (NEW - LangGraph Implementation)

```python
"""
LangGraph-based note classification using local LLM
Replaces the old llm.py httpx-based implementation
"""
import json
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from .config import LLM_MODEL, LLM_BASE_URL, LLM_TEMPERATURE

@tool
def classify_note(raw_text: str) -> dict:
    """Classify a note into title, folder, and tags using local LLM.

    Args:
        raw_text: The raw note content to classify

    Returns:
        Dictionary with title, folder, tags, first_sentence
    """
    llm = ChatOllama(
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        format="json"
    )

    prompt = f"""You are a note classifier. Analyze this note and return JSON.

Note: {raw_text}

Return ONLY valid JSON:
{{
  "title": "Short descriptive title (max 10 words)",
  "folder": "inbox|projects|people|research|journal",
  "tags": ["tag1", "tag2", "tag3"],
  "first_sentence": "One sentence summary"
}}

Folder selection guide:
- projects: Work tasks, technical issues, code
- people: Meetings, conversations, relationships
- research: Learning, articles, investigations
- journal: Personal thoughts, reflections
- inbox: When unsure

Tags should be lowercase, 3-6 relevant keywords.

JSON:"""

    try:
        response = llm.invoke(prompt)
        result = json.loads(response.content)

        # Validation
        valid_folders = ["inbox", "projects", "people", "research", "journal"]
        if result.get("folder") not in valid_folders:
            result["folder"] = "inbox"

        # Ensure required fields
        result.setdefault("title", raw_text.split("\n")[0][:60])
        result.setdefault("tags", [])
        result.setdefault("first_sentence", raw_text.split("\n")[0])

        return result

    except Exception as e:
        # Fallback on error
        return {
            "title": raw_text.split("\n")[0][:60],
            "folder": "inbox",
            "tags": [],
            "first_sentence": raw_text.split("\n")[0],
            "error": str(e)
        }


# Optional: LangGraph ReAct agent wrapper (for future enhancements)
def create_classification_agent():
    """Create a LangGraph agent for classification (alternative approach)"""
    from langgraph.prebuilt import create_react_agent

    llm = ChatOllama(
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE
    )

    agent = create_react_agent(llm, tools=[classify_note])
    return agent
```

---

### app-backend/notes.py

```python
import os
import re
import yaml
from datetime import datetime
import uuid
from pathlib import Path
from .config import NOTES_DIR
from .fts import index_note

SLUG_RE = re.compile(r"[^a-z0-9\-]+")

def _iso_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = SLUG_RE.sub("-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "note"

def pick_filename(title: str, created_iso: str) -> str:
    ymd = created_iso[:10]
    slug = slugify(title)[:80]
    return f"{ymd}-{slug}.md"

def write_markdown(folder: str, title: str, tags: list, body: str, related_ids=None):
    """Write note to disk and index in SQLite"""
    related_ids = related_ids or []
    created = _iso_now()
    updated = created
    nid = f"{created}_{uuid.uuid4().hex[:4]}"

    # Create folder
    folder_path = NOTES_DIR / folder
    folder_path.mkdir(parents=True, exist_ok=True)

    # Generate filename
    fname = pick_filename(title or "note", created)
    path = folder_path / fname

    # Prepare frontmatter
    front = {
        "id": nid,
        "title": title or body.splitlines()[0][:60] if body else "Untitled",
        "tags": tags,
        "folder": folder,
        "related_ids": related_ids,
        "created": created,
        "updated": updated
    }

    # Write file
    content = "---\n"
    content += yaml.safe_dump(front, sort_keys=False, allow_unicode=True)
    content += "---\n\n"
    content += body.strip() + "\n"

    path.write_text(content, encoding='utf-8')

    # Index in SQLite
    index_note(
        note_id=nid,
        title=front["title"],
        body=body,
        tags=tags,
        folder=folder,
        path=str(path),
        created=created
    )

    return nid, str(path), front["title"], folder
```

---

### app-backend/fts.py

```python
import sqlite3
from pathlib import Path
from .config import DB_PATH

def ensure_db():
    """Initialize SQLite FTS5 database"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("PRAGMA case_sensitive_like=OFF;")

    # FTS5 table
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
        USING fts5(id UNINDEXED, title, body, tags, content='')
    """)

    # Metadata table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes_meta (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            folder TEXT NOT NULL,
            created TEXT NOT NULL,
            updated TEXT NOT NULL
        )
    """)

    con.commit()
    con.close()

def index_note(note_id: str, title: str, body: str, tags: list,
               folder: str, path: str, created: str):
    """Add note to FTS5 index"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    tags_csv = ",".join(tags)

    cur.execute(
        "INSERT INTO notes_fts (id, title, body, tags) VALUES (?, ?, ?, ?)",
        (note_id, title, body, tags_csv)
    )

    cur.execute(
        "INSERT OR REPLACE INTO notes_meta VALUES (?, ?, ?, ?, ?)",
        (note_id, path, folder, created, created)
    )

    con.commit()
    con.close()

def search_notes(query: str, limit: int = 20):
    """Search notes using FTS5"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        SELECT n.path,
               snippet(notes_fts, 1, '<b>', '</b>', '…', 8) AS snippet,
               bm25(notes_fts) AS score
        FROM notes_fts f
        JOIN notes_meta n ON n.id = f.id
        WHERE f MATCH ?
        ORDER BY score
        LIMIT ?
    """, (query, limit))

    results = [
        {"path": row[0], "snippet": row[1], "score": row[2]}
        for row in cur.fetchall()
    ]

    con.close()
    return results
```

---

### app-backend/main.py

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import ClassifyRequest, ClassifyResponse, SearchRequest, SearchHit
from .classification_tool import classify_note
from .notes import write_markdown
from .fts import ensure_db, search_notes
from .config import BACKEND_HOST, BACKEND_PORT, LLM_MODEL

app = FastAPI(title="QuickNote Backend", version="0.2.0")

# CORS for Tauri
app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://localhost", "http://127.0.0.1"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    ensure_db()
    print(f"\n🚀 QuickNote Backend Started")
    print(f"🤖 Using Model: {LLM_MODEL}\n")

@app.get("/health")
async def health():
    return {"status": "ok", "model": LLM_MODEL}

@app.post("/classify_and_save", response_model=ClassifyResponse)
async def classify_and_save(req: ClassifyRequest):
    """Classify note using LangGraph and save to disk"""
    try:
        # Use LangGraph tool for classification
        result = classify_note.invoke({"raw_text": req.text})

        # Save to disk
        note_id, filepath, title, folder = write_markdown(
            title=result["title"],
            folder=result["folder"],
            tags=result["tags"],
            body=req.text
        )

        return ClassifyResponse(
            title=title,
            folder=folder,
            tags=result["tags"],
            first_sentence=result["first_sentence"],
            path=filepath
        )

    except Exception as e:
        # Fallback to inbox on any error
        first_line = req.text.split("\n")[0][:60]
        note_id, filepath, title, folder = write_markdown(
            folder="inbox",
            title=first_line,
            tags=[],
            body=req.text
        )
        return ClassifyResponse(
            title=title,
            folder="inbox",
            tags=[],
            first_sentence=first_line,
            path=filepath
        )

@app.post("/save_inbox", response_model=ClassifyResponse)
async def save_inbox(req: ClassifyRequest):
    """Save directly to inbox without classification"""
    first_line = req.text.split("\n")[0][:60]

    note_id, filepath, title, folder = write_markdown(
        folder="inbox",
        title=first_line,
        tags=[],
        body=req.text
    )

    return ClassifyResponse(
        title=title,
        folder="inbox",
        tags=[],
        first_sentence=first_line,
        path=filepath
    )

@app.post("/search", response_model=list[SearchHit])
async def search(req: SearchRequest):
    """Search notes using FTS5"""
    results = search_notes(req.query, req.limit)
    return [SearchHit(**r) for r in results]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)
```

---

## 7) Frontend (Tauri)

*(Same as original plan.md - no changes needed)*

### app-frontend/src-tauri/tauri.conf.json

```json
{
  "tauri": {
    "windows": [
      {
        "title": "QuickNote",
        "width": 640,
        "height": 220,
        "decorations": false,
        "transparent": true,
        "alwaysOnTop": true,
        "resizable": true
      }
    ],
    "allowlist": {
      "shell": {"all": false, "open": true},
      "globalShortcut": {"all": true},
      "window": {"all": true},
      "http": {"all": true}
    }
  }
}
```

### app-frontend/src-tauri/src/main.rs

```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use tauri::{Manager, Window};
use tauri_plugin_global_shortcut::GlobalShortcutExt;

#[tauri::command]
fn show_window(window: Window) {
    window.show().unwrap();
    window.set_focus().unwrap();
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .setup(|app| {
            let handle = app.handle();
            let win = app.get_window("main").unwrap();

            #[cfg(target_os = "macos")]
            handle.global_shortcut().register("Alt+Cmd+N", move || {
                win.show().ok();
                win.set_focus().ok();
            })?;

            #[cfg(not(target_os = "macos"))]
            handle.global_shortcut().register("Ctrl+Alt+N", move || {
                win.show().ok();
                win.set_focus().ok();
            })?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![show_window])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### app-frontend/src/main.tsx

*(Same React code as original plan.md)*

---

## 8) LLM Setup

### Option A: Ollama (Recommended)

```bash
# Install Ollama
brew install ollama  # macOS
# or download from https://ollama.ai

# Pull models
ollama pull qwen3:4b-instruct
ollama pull gemma3:4b

# Start server
ollama serve
```

### Option B: llama.cpp server

```bash
# Set in .env:
LLM_BASE_URL=http://127.0.0.1:8000
LLM_MODEL=qwen-3-4b-instruct
```

---

## 9) Model Comparison & Selection

### Compare Both Models

Create `test_model_comparison.py`:

```python
import os
from app_backend.classification_tool import classify_note

TEST_NOTES = [
    "Fix AWS ALB + Cognito integration issue",
    "Meeting with Sarah about Q4 roadmap",
    "Read article about LangGraph memory patterns",
    "Feeling grateful for team support this week",
    "Review terraform modules for ECS deployment"
]

def test_model(model_name: str):
    os.environ["LLM_MODEL"] = model_name
    print(f"\n{'='*60}\nTesting: {model_name}\n{'='*60}")

    for note in TEST_NOTES:
        result = classify_note.invoke({"raw_text": note})
        print(f"\nNote: {note}")
        print(f"  → {result['folder']:<12} {result['tags'][:3]}")

# Test both
test_model("qwen3:4b-instruct")
test_model("gemma3:4b")
```

Run: `python3 test_model_comparison.py`

### Quick Model Switching

Create `switch_model.sh`:

```bash
#!/bin/bash
if [ "$1" = "qwen" ]; then
    sed -i '' 's/^LLM_MODEL=.*/LLM_MODEL=qwen3:4b-instruct/' .env
    echo "✅ Switched to Qwen3"
elif [ "$1" = "gemma" ]; then
    sed -i '' 's/^LLM_MODEL=.*/LLM_MODEL=gemma3:4b/' .env
    echo "✅ Switched to Gemma3"
fi
```

Usage:
```bash
chmod +x switch_model.sh
./switch_model.sh qwen   # Switch to Qwen3
./switch_model.sh gemma  # Switch to Gemma3
```

---

## 10) Build & Run

### Backend

```bash
cd app-backend

# Create venv
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
python -m app_backend.main
```

### Frontend

```bash
cd app-frontend

# Install dependencies
npm install  # or pnpm/yarn

# Run in dev mode
npm run tauri dev
```

### Ensure Ollama is Running

```bash
ollama serve
ollama list  # Verify models are pulled
```

---

## 11) LangGraph Features (Optional)

### Streaming for Debugging

```python
# In classification_tool.py
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(llm, tools=[classify_note])

# Stream execution
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": note_text}]},
    stream_mode="updates"
):
    print(f"[STEP] {chunk}")
```

### Local Tracing (No External Services)

```python
# Save traces locally
import json
from datetime import datetime

def log_classification(note, result):
    trace = {
        "timestamp": datetime.now().isoformat(),
        "note": note[:100],
        "result": result
    }
    with open("traces.jsonl", "a") as f:
        f.write(json.dumps(trace) + "\n")
```

---

## 12) Acceptance Criteria (MVP)

- ✅ Global hotkey opens window
- ✅ Enter = AI classify & save
- ✅ Cmd/Ctrl+Enter = Save to inbox (skip AI)
- ✅ Markdown files with YAML frontmatter created
- ✅ SQLite FTS5 search works (`/` to search)
- ✅ Works fully offline with local LLM
- ✅ Fallback to inbox on errors
- ✅ Configurable model selection (Qwen3/Gemma3)
- ✅ No external dependencies (LangSmith optional for dev)

---

## 13) Security & Privacy

- ✅ All data stays local (Markdown + SQLite in `~/Notes`)
- ✅ HTTP calls only to localhost (backend + Ollama)
- ✅ No analytics or external calls
- ✅ LangSmith tracing is OPTIONAL (disabled by default)

---

## 14) Troubleshooting

### FTS5 Missing
```bash
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"
# Should be 3.9.0+ for FTS5 support
```

### LLM Connection Issues
```bash
# Test Ollama
curl http://127.0.0.1:11434/api/tags

# Test classification
curl -X POST http://127.0.0.1:8787/classify_and_save \
  -H "Content-Type: application/json" \
  -d '{"text": "Test note"}'
```

### Model Not Found
```bash
ollama list           # Check installed models
ollama pull qwen3:4b-instruct  # Install if missing
```

---

## 15) What's New in This Version

### Changes from Original Plan

1. **LangGraph Integration**
   - Replaced raw `httpx` calls with LangGraph `@tool` decorator
   - More reliable tool calling and JSON parsing
   - Built-in error handling and retries

2. **Configurable Model Selection**
   - Easy switching between Qwen3 and Gemma3 via `.env`
   - Model comparison script included
   - Helper script for quick switching

3. **Improved Error Handling**
   - Automatic fallback to inbox on LLM errors
   - Better JSON parsing with validation
   - Graceful degradation

4. **Optional Debugging**
   - Local trace logging (no external services)
   - Streaming support for development
   - Graph visualization tools

5. **Updated Dependencies**
   - LangChain/LangGraph libraries
   - Modern FastAPI patterns
   - Pathlib instead of os.path

---

## 16) Next Steps

### Phase 1: Backend (This Week)
1. Set up `.env` configuration
2. Implement classification tool with LangGraph
3. Test with both Qwen3 and Gemma3
4. Pick the better model
5. Complete all backend endpoints

### Phase 2: Frontend (Next Week)
6. Set up Tauri project
7. Build capture UI
8. Implement search UI
9. Add global hotkey
10. Connect to backend API

### Phase 3: Polish (Week 3)
11. Test end-to-end
12. Fix bugs
13. Add local tracing
14. Documentation
15. Demo video

---

## 17) Future Enhancements (Phase 2)

- Auto-preview of title/tags while typing
- Rules engine ("if tag=aws → folder=projects")
- Related notes suggestions (using embeddings)
- Voice capture (local Whisper)
- Import existing notes vault
- Custom folder configuration
- Multi-user support (different LLM_MODEL per user)

---

**Ready to build!** Start with backend setup, test classification, then move to frontend.
