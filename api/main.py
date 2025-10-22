"""
GraphRAG Note Assistant API - Clean Rewrite

Architecture:
- Phase 1: Episodic Layer (WHO/WHAT/WHEN/WHERE extraction) ✅
- Phase 2: Semantic Layer (embeddings + auto-linking) ✅
- Phase 3: Prospective Layer (metadata-only, no edges) ✅
- Phase 4: Retrieval Layer (hybrid search) - TODO
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache
from datetime import datetime
import asyncio

from .llm import initialize_llm, shutdown_llm
from .models import ClassifyRequest, CaptureNoteResponse, EpisodicMetadata, TimeReference
from .services.episodic import extract_episodic_metadata
from .services.prospective import extract_prospective_items
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
    """Capture note with GraphRAG episodic + prospective metadata extraction.

    Flow:
    1. Extract episodic metadata (Phase 1)
    2. Extract prospective items AFTER episodic (Phase 3 - needs WHEN data)
    3. Save markdown file with title and tags
    4. Store graph node with episodic + prospective metadata (JSON only, no edges)
    5. Commit transaction & return response immediately
    6. [Phase 2 only] Background: Generate embedding, create semantic/entity/tag edges

    Returns:
        CaptureNoteResponse with note_id, title, episodic metadata, and path
    """
    con = get_db_connection()

    try:
        # Phase 1: Extract episodic metadata
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M PST')
        episodic_data = await extract_episodic_metadata(req.text, current_date)

        # Phase 3: Extract prospective items (SEQUENTIAL - needs WHEN data from Phase 1)
        prospective_data = await extract_prospective_items(
            text=req.text,
            when_data=episodic_data['when']
        )

        # Store prospective data in episodic metadata
        episodic_data['prospective'] = prospective_data

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
        # Note: Phase 3 prospective is metadata-only, no edges created
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


# ==============================================================================
# Graph Visualization Endpoints (Phase 2 - for frontend)
# ==============================================================================

@app.get("/graph/nodes")
async def get_graph_nodes():
    """Get all graph nodes for visualization

    Returns list of nodes with episodic metadata for graph rendering
    """
    from .db.graph import get_all_nodes

    nodes = get_all_nodes()

    return {
        "nodes": nodes,
        "count": len(nodes)
    }


@app.get("/graph/edges")
async def get_graph_edges(relation: str = None):
    """Get all graph edges for visualization

    Args:
        relation: Optional filter by edge type (semantic, entity_link, tag_link)

    Returns list of edges with src, dst, relation, weight, metadata
    """
    con = get_db_connection()

    try:
        if relation:
            query = """
                SELECT src_node_id, dst_node_id, relation, weight, metadata
                FROM graph_edges
                WHERE relation = ?
                ORDER BY weight DESC
            """
            rows = con.execute(query, (relation,)).fetchall()
        else:
            query = """
                SELECT src_node_id, dst_node_id, relation, weight, metadata
                FROM graph_edges
                ORDER BY relation, weight DESC
            """
            rows = con.execute(query).fetchall()

        edges = []
        for src, dst, rel, weight, metadata in rows:
            import json
            edges.append({
                "source": src,  # D3.js/vis.js convention
                "target": dst,
                "relation": rel,
                "weight": weight,
                "metadata": json.loads(metadata) if metadata else None
            })

        return {
            "edges": edges,
            "count": len(edges)
        }
    finally:
        con.close()


@app.get("/graph/node/{note_id}")
async def get_node_detail(note_id: str):
    """Get detailed node information including connected edges

    Useful for node click/hover in graph visualization
    """
    from .db.graph import get_graph_node, get_node_edges

    node = get_graph_node(note_id)
    if not node:
        return {"error": "Node not found"}, 404

    edges = get_node_edges(note_id)

    return {
        "node": node,
        "edges": edges,
        "edge_count": len(edges)
    }


@app.get("/graph/stats")
async def get_graph_stats():
    """Get graph statistics for visualization summary

    Returns counts by edge type, node count, clustering info
    """
    con = get_db_connection()

    try:
        # Node count
        node_count = con.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0]

        # Nodes with embeddings
        embedded_count = con.execute(
            "SELECT COUNT(*) FROM graph_nodes WHERE embedding IS NOT NULL"
        ).fetchone()[0]

        # Edge counts by type
        edge_stats = con.execute("""
            SELECT relation, COUNT(*) as count, AVG(weight) as avg_weight
            FROM graph_edges
            GROUP BY relation
        """).fetchall()

        edges_by_type = {}
        total_edges = 0
        for relation, count, avg_weight in edge_stats:
            edges_by_type[relation] = {
                "count": count,
                "avg_weight": float(avg_weight) if avg_weight else 0
            }
            total_edges += count

        return {
            "nodes": {
                "total": node_count,
                "with_embeddings": embedded_count
            },
            "edges": {
                "total": total_edges,
                "by_type": edges_by_type
            }
        }
    finally:
        con.close()


@app.get("/notes/{note_id}/content")
async def get_note_content(note_id: str):
    """Get markdown content for a note

    Used by frontend to display full note text on click
    """
    node = get_graph_node(note_id)
    if not node:
        return {"error": "Note not found"}, 404

    try:
        with open(node['file_path'], 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            "note_id": note_id,
            "content": content,
            "file_path": node['file_path']
        }
    except FileNotFoundError:
        return {"error": "File not found"}, 404
    except Exception as e:
        return {"error": str(e)}, 500


def process_semantic_and_linking(note_id: str):
    """Process embedding generation and linking (runs after response sent)

    Phase 2 background tasks only:
    1. Generate & store embedding
    2. Create semantic edges (similarity-based)
    3. Create entity links (WHO/WHAT/WHERE)
    4. Create tag links (Jaccard similarity)

    Note: Phase 3 prospective is metadata-only (no edges created)

    Args:
        note_id: Note ID to process
    """
    from .services.semantic import generate_embedding, store_embedding, create_semantic_edges
    from .services.linking import create_entity_links, create_tag_links

    con = get_db_connection()

    try:
        print(f"[Background] Processing edges for {note_id}")

        # Phase 2: Semantic layer
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
        print(f"[Background] 🎉 Completed all edge processing for {note_id}")

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
