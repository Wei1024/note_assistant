"""
GraphRAG Note Assistant API - Clean Rewrite

Architecture:
- Phase 1: Episodic Layer (WHO/WHAT/WHEN/WHERE extraction)
- Phase 2: Semantic Layer (embeddings + auto-linking) - TODO
- Phase 3: Prospective Layer (time-based edges) - TODO
- Phase 4: Retrieval Layer (hybrid search) - TODO
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache
from datetime import datetime

from .llm import initialize_llm, shutdown_llm
from .models import ClassifyRequest, CaptureNoteResponse, EpisodicMetadata, TimeReference
from .services.episodic import extract_episodic_metadata
from .db.graph import store_graph_node
from .notes import write_markdown
from .db import ensure_db
from .config import BACKEND_HOST, BACKEND_PORT, LLM_MODEL, get_db_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager"""
    # Startup
    set_llm_cache(InMemoryCache())
    await initialize_llm()
    ensure_db()
    print(f"\n🚀 GraphRAG Note Assistant Started")
    print(f"🤖 Using Model: {LLM_MODEL}")
    print(f"💾 LLM Cache: Enabled (InMemory)\n")

    yield

    # Shutdown
    await shutdown_llm()
    print("\n👋 GraphRAG Note Assistant Shutdown\n")


app = FastAPI(lifespan=lifespan, title="GraphRAG Note Assistant")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "model": LLM_MODEL, "system": "GraphRAG"}


@app.post("/capture_note", response_model=CaptureNoteResponse)
async def capture_note(req: ClassifyRequest):
    """Capture note with GraphRAG episodic metadata extraction.

    Flow:
    1. Extract episodic metadata (WHO/WHAT/WHEN/WHERE/tags/title) via LLM + dateparser
    2. Save markdown file with title and tags
    3. Store graph node with episodic metadata
    4. [Phase 2 TODO] Background: Semantic linking via embeddings
    5. [Phase 3 TODO] Create prospective edges for time references

    Returns:
        CaptureNoteResponse with note_id, title, episodic metadata, and path
    """
    con = get_db_connection()

    try:
        # Phase 1: Extract episodic metadata (WHO/WHAT/WHEN/WHERE/tags/title)
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M PST')
        episodic_data = await extract_episodic_metadata(req.text, current_date)

        # Save markdown file (title + tags + body)
        note_id, filepath, title = write_markdown(
            title=episodic_data["title"],
            tags=episodic_data["tags"],
            body=req.text,
            db_connection=con
        )

        # Store graph node with episodic metadata
        store_graph_node(
            note_id=note_id,
            text=req.text,
            file_path=filepath,
            episodic_metadata=episodic_data,
            db_connection=con
        )

        # Commit transaction
        con.commit()

        # Build response with proper types
        episodic_response = EpisodicMetadata(
            who=episodic_data["who"],
            what=episodic_data["what"],
            where=episodic_data["where"],
            when=[TimeReference(**t) for t in episodic_data["when"]],
            tags=episodic_data["tags"]
        )

        return CaptureNoteResponse(
            note_id=note_id,
            title=title,
            episodic=episodic_response,
            path=filepath
        )

    except Exception as e:
        # Rollback on error
        con.rollback()
        print(f"❌ Episodic extraction failed: {e}")
        import traceback
        traceback.print_exc()

        # Fallback: Save with minimal metadata
        first_line = req.text.split("\n")[0][:60]
        note_id, filepath, title = write_markdown(
            title=first_line,
            tags=[],
            body=req.text,
            db_connection=con
        )

        # Store minimal graph node (empty episodic metadata)
        store_graph_node(
            note_id=note_id,
            text=req.text,
            file_path=filepath,
            episodic_metadata={"who": [], "what": [], "where": [], "when": [], "tags": [], "title": first_line},
            db_connection=con
        )

        # Commit fallback
        con.commit()

        return CaptureNoteResponse(
            note_id=note_id,
            title=title,
            episodic=EpisodicMetadata(who=[], what=[], where=[], when=[], tags=[]),
            path=filepath
        )
    finally:
        # Always close connection
        con.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)
