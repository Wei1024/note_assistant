#!/usr/bin/env python3
"""
QuickNote AI Backend - OpenAI Agents SDK Implementation
Uses local Qwen model via Ollama for note organization
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from agents import Agent, Runner, function_tool
from openai import AsyncOpenAI
import yaml
import sqlite3
import re

# Configuration
NOTES_DIR = Path.home() / "Notes"
DB_PATH = NOTES_DIR / ".index" / "notes.sqlite"
OLLAMA_BASE_URL = "http://localhost:11434/v1"

# Pydantic models for structured outputs
class NoteOrganization(BaseModel):
    """Structured output for note organization"""
    title: str = Field(description="Concise title (max 10 words)")
    folder: str = Field(description="One of: inbox, projects, people, research, journal")
    tags: List[str] = Field(description="3-6 relevant tags, lowercase with underscores")
    first_sentence: str = Field(description="Key point or summary")

class SaveResult(BaseModel):
    """Result of saving a note"""
    id: str
    title: str
    folder: str
    path: str
    success: bool

class SearchResult(BaseModel):
    """Search result entry"""
    path: str
    snippet: str
    score: float

# Initialize database
def init_database():
    """Initialize SQLite FTS5 database"""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create FTS5 table for search
    cur.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
        id UNINDEXED,
        title,
        body,
        tags,
        content=''
    );
    """)

    # Create metadata table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes_meta (
        id TEXT PRIMARY KEY,
        path TEXT NOT NULL,
        folder TEXT NOT NULL,
        created TEXT NOT NULL,
        updated TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()

# Tool definitions using @function_tool decorator
@function_tool
def organize_note(content: str) -> Dict:
    """
    Analyze a note and suggest organization metadata.
    Returns title, folder, tags, and first sentence.
    """
    # This would normally call the LLM, but for the tool definition
    # we'll return a structured response that the agent will refine
    lines = content.strip().split('\n')
    first_line = lines[0] if lines else "Untitled"

    # Basic heuristics (agent will improve on these)
    folder = "inbox"
    if any(word in content.lower() for word in ["meeting", "discussed", "team"]):
        folder = "people"
    elif any(word in content.lower() for word in ["research", "discovered", "learned"]):
        folder = "research"
    elif any(word in content.lower() for word in ["project", "build", "implement"]):
        folder = "projects"
    elif any(word in content.lower() for word in ["feeling", "today", "personal"]):
        folder = "journal"

    return {
        "title": first_line[:50],
        "folder": folder,
        "tags": [],
        "first_sentence": first_line
    }

@function_tool
def save_note(title: str, folder: str, tags: List[str], content: str) -> Dict:
    """
    Save a note to the filesystem with YAML frontmatter.
    Returns the note ID and file path.
    """
    # Create folder if needed
    folder_path = NOTES_DIR / folder
    folder_path.mkdir(parents=True, exist_ok=True)

    # Generate ID and filename
    now = datetime.utcnow()
    note_id = f"{now.isoformat()}_{os.urandom(2).hex()}"

    # Slugify title for filename
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[-\s]+', '-', slug)[:80]
    filename = f"{now.strftime('%Y-%m-%d')}-{slug}.md"
    filepath = folder_path / filename

    # Create frontmatter
    frontmatter = {
        "id": note_id,
        "title": title,
        "tags": tags,
        "folder": folder,
        "created": now.isoformat() + "Z",
        "updated": now.isoformat() + "Z"
    }

    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("---\n")
        f.write(yaml.dump(frontmatter, sort_keys=False))
        f.write("---\n\n")
        f.write(content.strip())
        f.write("\n")

    # Update search index
    update_search_index(note_id, title, content, tags, folder, str(filepath),
                       frontmatter['created'], frontmatter['updated'])

    return {
        "id": note_id,
        "title": title,
        "folder": folder,
        "path": str(filepath),
        "success": True
    }

@function_tool
def search_notes(query: str, limit: int = 20) -> List[Dict]:
    """
    Search notes using SQLite FTS5.
    Returns matching notes with snippets.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    SELECT n.path,
           snippet(notes_fts, 1, '<b>', '</b>', '...', 10) AS snip,
           bm25(notes_fts) AS score
    FROM notes_fts f
    JOIN notes_meta n ON n.id = f.id
    WHERE f MATCH ?
    ORDER BY score
    LIMIT ?;
    """, (query, limit))

    results = []
    for row in cur.fetchall():
        results.append({
            "path": row[0],
            "snippet": row[1],
            "score": row[2]
        })

    conn.close()
    return results

def update_search_index(note_id: str, title: str, body: str, tags: List[str],
                        folder: str, path: str, created: str, updated: str):
    """Update the FTS5 search index"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Insert into FTS table
    tags_str = ",".join(tags)
    cur.execute("""
    INSERT OR REPLACE INTO notes_fts (id, title, body, tags)
    VALUES (?, ?, ?, ?)
    """, (note_id, title, body, tags_str))

    # Insert into metadata table
    cur.execute("""
    INSERT OR REPLACE INTO notes_meta (id, path, folder, created, updated)
    VALUES (?, ?, ?, ?, ?)
    """, (note_id, path, folder, created, updated))

    conn.commit()
    conn.close()

# Create the Note Organization Agent
def create_note_agent():
    """Create the main note organization agent"""

    # Configure Ollama client for local Qwen model
    ollama_client = AsyncOpenAI(
        base_url=OLLAMA_BASE_URL,
        api_key="ollama"  # Required but unused
    )

    agent = Agent(
        name="Note Organizer",
        instructions="""You are a intelligent note organization assistant.

        Your responsibilities:
        1. Analyze incoming notes and extract key information
        2. Generate concise, descriptive titles (max 10 words)
        3. Categorize notes into appropriate folders:
           - inbox: general tasks, todos, uncategorized items
           - projects: technical work, development, building things
           - people: meetings, conversations, team interactions
           - research: learning, discoveries, technical exploration
           - journal: personal reflections, daily logs, feelings
        4. Generate 3-6 relevant tags using lowercase with underscores
        5. Extract the most important sentence or key point

        When using tools:
        - First use organize_note to analyze the content
        - Then use save_note to persist it with improved metadata
        - Use search_notes when the user asks to find existing notes

        Be thoughtful about categorization - consider the primary focus of the note.
        """,
        tools=[organize_note, save_note, search_notes],
        model="qwen3:4b-instruct",  # Using local model via Ollama
        # output_type=NoteOrganization  # For structured responses
    )

    return agent

# Main API functions
async def process_and_save_note(content: str) -> SaveResult:
    """
    Process a note through the agent pipeline and save it.
    """
    agent = create_note_agent()

    # Configure Ollama client
    ollama_client = AsyncOpenAI(
        base_url=OLLAMA_BASE_URL,
        api_key="ollama"
    )

    try:
        # Run the agent with the note content
        result = await Runner.run(
            starting_agent=agent,
            input=f"Please organize and save this note: {content}",
            model_client=ollama_client,
            model="qwen3:4b-instruct"
        )

        # Extract the save result from the agent's response
        # The agent should have called save_note and returned the result
        if hasattr(result, 'tool_calls') and result.tool_calls:
            for call in result.tool_calls:
                if call.function.name == 'save_note':
                    return SaveResult(**json.loads(call.function.arguments))

        # Fallback if no tool was called
        return await save_to_inbox(content)

    except Exception as e:
        print(f"Error processing note: {e}")
        # Fallback to inbox on any error
        return await save_to_inbox(content)

async def save_to_inbox(content: str) -> SaveResult:
    """Fallback function to save directly to inbox"""
    lines = content.strip().split('\n')
    title = lines[0][:50] if lines else "Untitled"

    result = save_note(
        title=title,
        folder="inbox",
        tags=["unprocessed"],
        content=content
    )

    return SaveResult(**result)

async def search(query: str, limit: int = 20) -> List[SearchResult]:
    """
    Search for notes using the agent.
    """
    agent = create_note_agent()

    # Configure Ollama client
    ollama_client = AsyncOpenAI(
        base_url=OLLAMA_BASE_URL,
        api_key="ollama"
    )

    result = await Runner.run(
        starting_agent=agent,
        input=f"Search for notes matching: {query}",
        model_client=ollama_client,
        model="qwen3:4b-instruct"
    )

    # Extract search results
    if hasattr(result, 'tool_calls') and result.tool_calls:
        for call in result.tool_calls:
            if call.function.name == 'search_notes':
                results = json.loads(call.function.arguments)
                return [SearchResult(**r) for r in results]

    return []

# FastAPI integration (optional)
def create_fastapi_app():
    """Create FastAPI app with agent endpoints"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="QuickNote AI Backend")

    # CORS for Tauri frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["tauri://localhost", "http://localhost"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup():
        init_database()

    @app.post("/organize_and_save", response_model=SaveResult)
    async def organize_and_save(content: str):
        """Process and save a note with AI organization"""
        return await process_and_save_note(content)

    @app.post("/save_inbox", response_model=SaveResult)
    async def save_inbox(content: str):
        """Save directly to inbox without AI processing"""
        return await save_to_inbox(content)

    @app.post("/search", response_model=List[SearchResult])
    async def search_endpoint(query: str, limit: int = 20):
        """Search notes"""
        return await search(query, limit)

    return app

# Example usage
async def main():
    """Example usage of the agent"""
    init_database()

    # Test note
    test_note = """
    Met with Sarah from the design team about the new dashboard.
    She suggested using a card-based layout with real-time updates.
    Need to follow up next week with mockups.
    """

    print("Processing note...")
    result = await process_and_save_note(test_note)
    print(f"Saved: {result.title} in {result.folder}")
    print(f"Path: {result.path}")

    # Search test
    print("\nSearching for 'dashboard'...")
    search_results = await search("dashboard")
    for sr in search_results:
        print(f"Found: {sr.path}")
        print(f"  Snippet: {sr.snippet}")

if __name__ == "__main__":
    # Run example
    asyncio.run(main())

    # Or run as API server
    # import uvicorn
    # app = create_fastapi_app()
    # uvicorn.run(app, host="127.0.0.1", port=8787)