"""
GraphRAG Note Assistant API - Clean Rewrite

Architecture:
- Phase 1: Episodic Layer (WHO/WHAT/WHEN/WHERE extraction) ✅
- Phase 2: Semantic Layer (embeddings + auto-linking) 🔄 IN PROGRESS
- Phase 3: Prospective Layer (time-based edges) - TODO
- Phase 4: Retrieval Layer (hybrid search) - TODO
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache
from datetime import datetime

from .llm import initialize_llm, shutdown_llm
from .models import ClassifyRequest, CaptureNoteResponse, EpisodicMetadata, TimeReference
from .services.episodic import extract_episodic_metadata
from .db.graph import store_graph_node, get_graph_node
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
async def capture_note(req: ClassifyRequest, background_tasks: BackgroundTasks):
    """Capture note with GraphRAG episodic metadata extraction.

    Flow:
    1. Extract episodic metadata (WHO/WHAT/WHEN/WHERE/tags/title) via LLM + dateparser
    2. Save markdown file with title and tags
    3. Store graph node with episodic metadata
    4. Commit transaction & return response immediately
    5. [Phase 2] Background: Generate embedding, create semantic/entity/tag edges
    6. [Phase 3 TODO] Create prospective edges for time references

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

        # Phase 2: Background tasks (don't block response)
        background_tasks.add_task(process_semantic_and_linking, note_id)

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


def process_semantic_and_linking(note_id: str):
    """Process embedding generation and linking (runs after response sent)

    Phase 2 background tasks:
    1. Generate & store embedding
    2. Create semantic edges (similarity-based)
    3. Create entity links (WHO/WHAT/WHERE)
    4. Create tag links (Jaccard similarity)

    Args:
        note_id: Note ID to process
    """
    from .services.semantic import generate_embedding, store_embedding, create_semantic_edges
    from .services.linking import create_entity_links, create_tag_links

    con = get_db_connection()

    try:
        print(f"[Background] Processing semantic links for {note_id}")

        # 1. Generate & store embedding
        node = get_graph_node(note_id)
        if node:
            embedding = generate_embedding(node['text'])
            store_embedding(note_id, embedding, con)
            print(f"[Background] ✅ Embedding generated for {note_id}")
        else:
            print(f"[Background] ⚠️  Node not found: {note_id}")
            return

        # 2. Create semantic edges
        create_semantic_edges(note_id, con)
        print(f"[Background] ✅ Semantic edges created for {note_id}")

        # 3. Create entity links (WHO/WHAT/WHERE)
        create_entity_links(note_id, con)
        print(f"[Background] ✅ Entity links created for {note_id}")

        # 4. Create tag links
        create_tag_links(note_id, con)
        print(f"[Background] ✅ Tag links created for {note_id}")

        con.commit()
        print(f"[Background] 🎉 Completed processing for {note_id}")

    except Exception as e:
        con.rollback()
        print(f"[Background] ❌ Error processing {note_id}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        con.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)
