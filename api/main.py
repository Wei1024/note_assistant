from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache
from .llm import initialize_llm, shutdown_llm
from .models import (
    ClassifyRequest, ClassifyResponse, DimensionFlags, SearchRequest, SearchHit, UpdateStatusRequest,
    DimensionSearchRequest, EntitySearchRequest, PersonSearchRequest,
    GraphSearchRequest, GraphData, SynthesisRequest, SynthesisResponse,
    ConsolidateBatchRequest, ConsolidateBatchResponse, ClusteredGraphData
)
from .services.capture import classify_note_async
from .services.search import search_notes_smart
from .services.enrichment import enrich_note_metadata, store_enrichment_metadata
from .services.consolidation import consolidate_daily_notes, consolidate_note, consolidate_notes
from .services.synthesis import synthesize_search_results, synthesize_search_results_stream
from .services.clustering import detect_clusters
from .services.cluster_summary import get_cluster_summary
from .services.query import (
    search_by_dimension, search_by_entity, search_by_person,
    search_graph, get_graph_visualization
)
from .graph import get_full_graph
from .notes import write_markdown, update_note_status
from .fts import search_notes
from .db import ensure_db
from .config import BACKEND_HOST, BACKEND_PORT, LLM_MODEL, DB_PATH
import sqlite3

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    set_llm_cache(InMemoryCache())
    await initialize_llm()  # Initialize LLM client
    ensure_db()
    print(f"\n🚀 QuickNote Backend Started")
    print(f"🤖 Using Model: {LLM_MODEL}")
    print(f"💾 LLM Cache: Enabled (InMemory)")
    print(f"🔌 Connection Pooling: Enabled (10 keepalive)\n")
    yield
    # Shutdown
    await shutdown_llm()  # Cleanup LLM client and HTTP connections
    print("\n👋 QuickNote Backend Shutting Down\n")

app = FastAPI(title="QuickNote Backend", version="0.2.0", lifespan=lifespan)

# CORS for Tauri and Vue frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "tauri://localhost",
        "http://localhost:5173",  # Vue frontend dev server
        "http://localhost:5174",  # Alternative port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok", "model": LLM_MODEL}

@app.post("/classify_and_save", response_model=ClassifyResponse)
async def classify_and_save(req: ClassifyRequest):
    """Extract metadata and save note (dimensions-based classification)"""
    # Create single database connection for entire transaction
    from .config import get_db_connection
    con = get_db_connection()

    try:
        # Step 1: Extract title/tags
        # NOTE: classify_note_async uses track_llm_call internally which will need connection
        result = await classify_note_async(req.text)

        # Step 2: Enrich with dimensions + entities
        # NOTE: enrich_note_metadata uses track_llm_call internally which will need connection
        enrichment = None
        try:
            enrichment = await enrich_note_metadata(req.text, result)
        except Exception as enrich_error:
            print(f"Enrichment failed: {enrich_error}")
            enrichment = {}

        # Step 3: Save to flat structure (using shared connection)
        note_id, filepath, title = write_markdown(
            title=result["title"],
            tags=result["tags"],
            body=req.text,
            status=result.get("status"),
            enrichment=enrichment,
            db_connection=con  # Pass shared connection
        )

        # Step 4: Store enrichment in database (using shared connection)
        if enrichment:
            try:
                store_enrichment_metadata(note_id, enrichment, con)
            except Exception as db_error:
                print(f"Failed to store enrichment: {db_error}")

        # Extract dimensions from classification result (not enrichment!)
        classification_dims = result.get("dimensions", {})
        dimensions = DimensionFlags(
            has_action_items=classification_dims.get("has_action_items", False),
            is_social=classification_dims.get("is_social", False),
            is_emotional=classification_dims.get("is_emotional", False),
            is_knowledge=classification_dims.get("is_knowledge", False),
            is_exploratory=classification_dims.get("is_exploratory", False)
        )

        # Commit all changes in one transaction
        con.commit()

        return ClassifyResponse(
            title=title,
            dimensions=dimensions,
            tags=result["tags"],
            path=filepath
        )

    except Exception as e:
        # Rollback on error
        con.rollback()

        first_line = req.text.split("\n")[0][:60]
        note_id, filepath, title = write_markdown(
            title=first_line,
            tags=[],
            body=req.text,
            db_connection=con  # Use same connection
        )

        # Commit fallback save
        con.commit()

        return ClassifyResponse(
            title=title,
            dimensions=DimensionFlags(),  # All False on error
            tags=[],
            path=filepath
        )
    finally:
        # Always close connection
        con.close()

async def enrich_note_background(note_id: str, note_path: str, note_text: str):
    """Background task to classify and enrich a note after it's been saved.

    Updates the note file and database with LLM-generated metadata.
    """
    try:
        # Step 1: Classify
        result = await classify_note_async(note_text)

        # Step 2: Enrich
        enrichment = None
        try:
            enrichment = await enrich_note_metadata(note_text, result)
        except Exception as e:
            print(f"Background enrichment failed for {note_id}: {e}")
            enrichment = {}

        # Step 3: Update note file with better title/tags
        import re
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Update frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                # Update title and tags in frontmatter
                frontmatter = parts[1]
                frontmatter = re.sub(r'title:.*', f'title: {result["title"]}', frontmatter)
                tags_str = ', '.join(result.get('tags', []))
                frontmatter = re.sub(r'tags:.*', f'tags: {tags_str}', frontmatter)

                # Add status if present
                if result.get('status'):
                    if 'status:' in frontmatter:
                        frontmatter = re.sub(r'status:.*', f'status: {result["status"]}', frontmatter)
                    else:
                        frontmatter += f'\nstatus: {result["status"]}'

                content = f'---{frontmatter}---{parts[2]}'

                with open(note_path, 'w', encoding='utf-8') as f:
                    f.write(content)

        # Step 4: Store enrichment in database
        if enrichment:
            try:
                con = sqlite3.connect(DB_PATH)
                store_enrichment_metadata(note_id, enrichment, con)
                con.close()
            except Exception as e:
                print(f"Failed to store enrichment for {note_id}: {e}")

        print(f"✓ Background enrichment complete for {note_id}")

    except Exception as e:
        print(f"Background enrichment failed for {note_id}: {e}")


@app.post("/save_fast", response_model=ClassifyResponse)
async def save_fast(req: ClassifyRequest, background_tasks: BackgroundTasks):
    """Save note immediately, classify in background.

    Returns instantly with basic metadata. Background task enriches
    the note with LLM-generated title, tags, dimensions, and entities.

    Use this for better UX - user gets immediate feedback while
    classification happens asynchronously.
    """
    # Save immediately with basic title (first line)
    first_line = req.text.split("\n")[0][:60].strip()

    note_id, filepath, title = write_markdown(
        title=first_line or "Untitled note",
        tags=[],
        body=req.text
    )

    # Enrich in background
    background_tasks.add_task(enrich_note_background, note_id, filepath, req.text)

    return ClassifyResponse(
        title=title,
        dimensions=DimensionFlags(),  # Will be updated by background task
        tags=[],
        path=filepath
    )


@app.post("/save_journal", response_model=ClassifyResponse)
async def save_journal(req: ClassifyRequest):
    """Save directly without classification (flat structure)"""
    first_line = req.text.split("\n")[0][:60]

    note_id, filepath, title = write_markdown(
        title=first_line,
        tags=[],
        body=req.text
    )

    return ClassifyResponse(
        title=title,
        dimensions=DimensionFlags(is_emotional=True),  # Assume journal is emotional
        tags=[],
        path=filepath
    )

@app.post("/search", response_model=list[SearchHit])
async def search(req: SearchRequest):
    """Search notes using FTS5 (direct keyword match)

    Supports status filtering:
    - POST /search {"query": "...", "status": "todo"}
    """
    results = search_notes(req.query, req.limit, req.status)
    return [SearchHit(**r) for r in results]

@app.post("/search_smart", response_model=list[SearchHit])
async def search_smart(req: SearchRequest):
    """Smart natural language search with multi-dimensional filtering

    Intelligently routes queries to appropriate search endpoints:
    - Understands people: "notes with Sarah" → search_by_person()
    - Understands emotions: "excited notes" → search_by_dimension()
    - Understands entities: "FAISS project" → search_by_entity()
    - Falls back to FTS5 text search for everything else

    Example queries:
    - "what's the recent project I did with Sarah"
    - "notes where I felt excited"
    - "meetings about FAISS"
    - "what sport did I watch?"

    Supports status filtering:
    - POST /search_smart {"query": "...", "status": "todo"}
    """
    results = await search_notes_smart(req.query, req.limit, req.status)
    return [SearchHit(**r) for r in results]

@app.post("/search_fast", response_model=list[SearchHit])
async def search_fast(req: SearchRequest):
    """DEPRECATED: Use /search_smart instead

    Kept for backwards compatibility. Will be removed in future version.
    """
    results = await search_notes_smart(req.query, req.limit, req.status)
    return [SearchHit(**r) for r in results]

@app.post("/synthesize", response_model=SynthesisResponse)
async def synthesize(req: SynthesisRequest):
    """Synthesize search results into a coherent summary.

    Uses smart search to find relevant notes, then generates an LLM-powered
    summary that answers the user's natural language query.

    Request body:
    {
        "query": "what did I learn about memory consolidation?",
        "limit": 10
    }

    Returns:
    {
        "query": "what did I learn about memory consolidation?",
        "summary": "Based on your notes, you learned...",
        "notes_analyzed": 3,
        "search_results": [...]
    }

    Duration: ~2-4 seconds (search + LLM synthesis)
    """
    result = await synthesize_search_results(req.query, req.limit)
    return SynthesisResponse(**result)

@app.post("/synthesize/stream")
async def synthesize_stream(req: SynthesisRequest):
    """Stream synthesis results in real-time using Server-Sent Events.

    Uses smart search to find relevant notes, then streams an LLM-powered
    summary as it's being generated for better UX.

    Request body:
    {
        "query": "what did I learn about memory consolidation?",
        "limit": 10
    }

    Returns SSE stream with event types:
    - metadata: {"type": "metadata", "query": "...", "notes_analyzed": 3}
    - chunk: {"type": "chunk", "content": "Based on your notes, "}
    - results: {"type": "results", "search_results": [...]}
    - done: {"type": "done"}

    Example stream:
    data: {"type": "metadata", "query": "...", "notes_analyzed": 2}

    data: {"type": "chunk", "content": "Memory consolidation "}

    data: {"type": "chunk", "content": "happens during sleep..."}

    data: {"type": "results", "search_results": [...]}

    data: {"type": "done"}

    Duration: Same as /synthesize (~2-4s) but progressive rendering
    """
    return StreamingResponse(
        synthesize_search_results_stream(req.query, req.limit),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

@app.patch("/notes/status")
async def update_status(req: UpdateStatusRequest):
    """Update the status of a note

    Request body:
    {
        "note_path": "/path/to/note.md",
        "status": "done"  // or "todo", "in_progress", null
    }

    Returns:
        {"success": true} or {"success": false, "error": "..."}
    """
    # Validate status
    valid_statuses = ["todo", "in_progress", "done", "null", None]
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    # Convert "null" string to None
    status_value = None if req.status == "null" or req.status is None else req.status

    # Update the note
    success = update_note_status(req.note_path, status_value)

    if success:
        return {"success": True, "message": f"Status updated to: {status_value}"}
    else:
        raise HTTPException(status_code=404, detail="Note not found or update failed")

@app.post("/consolidate", response_model=ConsolidateBatchResponse)
async def consolidate_batch(request: ConsolidateBatchRequest):
    """Generic batch consolidation for any list of note IDs.

    Processes notes sequentially - each can link to earlier notes in the batch.
    This allows flexible note selection logic (all notes, unlinked notes, by date
    range, by dimension, etc.) while keeping consolidation logic separate.

    Args:
        request: ConsolidateBatchRequest with note_ids list

    Returns:
        ConsolidateBatchResponse with:
        {
            "notes_processed": 5,
            "links_created": 12,
            "notes_with_links": 4,
            "started_at": "2025-10-11T22:00:00",
            "completed_at": "2025-10-11T22:00:15"
        }
    """
    stats = await consolidate_notes(request.note_ids)
    return stats


@app.post("/consolidate/today", response_model=ConsolidateBatchResponse)
async def consolidate_today():
    """Convenience endpoint: Consolidate all of today's notes.

    Returns:
        ConsolidateBatchResponse with consolidation statistics
    """
    stats = await consolidate_daily_notes()
    return stats


@app.post("/consolidate/{note_id}")
async def consolidate_single_note(note_id: str):
    """Consolidate a single note - find and create links to existing knowledge.

    Args:
        note_id: ID of note to consolidate

    Returns:
        {
            "note_id": "2025-10-12T15:32:09-07:00_e189",
            "links_created": 2,
            "candidates_found": 5
        }
    """
    result = await consolidate_note(note_id)
    return result


# ============================================================================
# Phase 3.1: Multi-Dimensional Query Endpoints
# ============================================================================

@app.post("/search/dimensions", response_model=list[SearchHit])
async def search_dimensions(req: DimensionSearchRequest):
    """Search notes by dimension (context, emotion, time_reference).

    Optionally combine with FTS5 text search.

    Examples:
        - {"dimension_type": "emotion", "dimension_value": "excited"}
        - {"dimension_type": "emotion", "dimension_value": "excited", "query_text": "vector search"}
        - {"dimension_type": "context", "dimension_value": "tasks"}
    """
    results = search_by_dimension(
        req.dimension_type,
        req.dimension_value,
        query_text=req.query_text
    )
    return [SearchHit(**r) for r in results]


@app.post("/search/entities", response_model=list[SearchHit])
async def search_entities(req: EntitySearchRequest):
    """Search notes by entity (person, topic, project, tech).

    Optionally filter by dimension context.

    Examples:
        - {"entity_type": "topic", "entity_value": "vector search"}
        - {"entity_type": "person", "entity_value": "Sarah", "context": "meetings"}
        - {"entity_type": "project", "entity_value": "note-taking app"}
    """
    results = search_by_entity(
        req.entity_type,
        req.entity_value,
        context=req.context
    )
    return [SearchHit(**r) for r in results]


@app.post("/search/person", response_model=list[SearchHit])
async def search_person(req: PersonSearchRequest):
    """Convenience endpoint for person search with case-insensitive matching.

    Examples:
        - {"name": "Sarah"}
        - {"name": "sarah", "context": "meetings"}
    """
    results = search_by_person(req.name, context=req.context)
    return [SearchHit(**r) for r in results]


@app.post("/search/graph", response_model=GraphData)
async def search_graph_endpoint(req: GraphSearchRequest):
    """Traverse graph from starting note and return nodes + edges.

    Examples:
        - {"start_note_id": "2025-10-12T09:00:00-07:00_a1b2", "depth": 2}
        - {"start_note_id": "...", "depth": 1, "relationship_type": "spawned"}
    """
    graph = search_graph(
        req.start_note_id,
        depth=req.depth,
        relationship_type=req.relationship_type
    )
    return GraphData(**graph)


@app.get("/notes/{note_id}/graph", response_model=GraphData)
async def get_note_graph(note_id: str, depth: int = 2):
    """Get graph visualization data for a note.

    Query params:
        - depth: Traversal depth (default: 2)

    Returns graph data formatted for D3.js, Cytoscape, Vue Flow, etc.
    """
    graph = get_graph_visualization(note_id, depth=depth)
    return GraphData(**graph)

@app.get("/notes/{note_id}/content")
async def get_note_content(note_id: str):
    """Get the full markdown content of a note by its ID.

    Args:
        note_id: Note ID (e.g., "2025-10-12T16:01:08-07:00_ae68")

    Returns:
        JSON with 'content' (markdown text) and 'path' fields

    Raises:
        404: Note ID not found in database
    """
    # Get the file path from database
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT path FROM notes_meta WHERE id = ?", (note_id,))
    row = cur.fetchone()
    con.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")

    file_path = row[0]

    # Read the markdown file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"content": content, "path": file_path}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

@app.get("/graph/full", response_model=GraphData)
async def get_full_corpus_graph(
    min_links: int = 0,
    dimension: str = None,
    limit: int = 500
):
    """Get full corpus graph (all notes + links).

    Query params:
        - min_links: Only show notes with N+ connections (default: 0)
        - dimension: Filter by dimension (e.g., "is_knowledge", "has_action_items")
        - limit: Max nodes to return (default: 500, prevents browser overload)

    Returns:
        GraphData with all nodes and edges (filtered by params)

    Examples:
        /graph/full - All notes
        /graph/full?min_links=1 - Only notes with links
        /graph/full?dimension=is_knowledge - Only knowledge notes
        /graph/full?limit=100 - First 100 notes
    """
    graph = get_full_graph(
        min_links=min_links,
        dimension_filter=dimension,
        limit=limit
    )
    return GraphData(**graph)

@app.get("/graph/clusters", response_model=ClusteredGraphData)
async def get_clustered_graph(
    min_links: int = 1,
    limit: int = 100
):
    """Get full graph with cluster detection and summaries.

    Uses Louvain algorithm to detect communities in the knowledge graph,
    then generates semantic summaries for each cluster.

    Query params:
        - min_links: Only include notes with N+ connections (default: 1)
        - limit: Max nodes to include in clustering (default: 100)

    Returns:
        ClusteredGraphData with nodes, edges, and cluster summaries

    Examples:
        /graph/clusters - Default clustering
        /graph/clusters?min_links=2&limit=50 - Only well-connected notes
    """
    # Step 1: Detect clusters
    clusters = detect_clusters(min_links=min_links, limit=limit)

    # Step 2: Get graph data for these nodes
    all_node_ids = []
    for node_ids in clusters.values():
        all_node_ids.extend(node_ids)

    # Get full graph for these nodes
    graph = get_full_graph(min_links=min_links, limit=limit)

    # Add cluster_id to each node
    node_to_cluster = {}
    for cluster_id, node_ids in clusters.items():
        for node_id in node_ids:
            node_to_cluster[node_id] = cluster_id

    for node in graph['nodes']:
        node['cluster_id'] = node_to_cluster.get(node['id'], -1)

    # Step 3: Generate summaries for each cluster
    cluster_summaries = []
    for cluster_id, node_ids in clusters.items():
        summary = await get_cluster_summary(cluster_id, node_ids)
        cluster_summaries.append(summary)

    # Sort clusters by size (largest first)
    cluster_summaries.sort(key=lambda c: c['size'], reverse=True)

    return ClusteredGraphData(
        nodes=graph['nodes'],
        edges=graph['edges'],
        clusters=cluster_summaries
    )

# EXPERIMENTAL ENDPOINTS (not in production use)
# These are commented out - see future_agent.py for LangGraph implementations
# Uncomment and import from future_agent if you want to experiment with agents

# @app.post("/classify_with_trace")
# async def classify_with_trace(req: ClassifyRequest):
#     """Classify note with full agent reasoning trace"""
#     from .future_agent import create_classification_agent
#     agent = create_classification_agent()
#     steps = []
#     final_result = None
#     try:
#         for chunk in agent.stream(
#             {"messages": [("user", f"Classify this note: {req.text}")]},
#             stream_mode="values"
#         ):
#             if "messages" in chunk:
#                 last_msg = chunk["messages"][-1]
#                 if hasattr(last_msg, "content"):
#                     steps.append({"type": "thought", "content": last_msg.content})
#                 if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
#                     for tool_call in last_msg.tool_calls:
#                         steps.append({"type": "tool_call", "name": tool_call["name"], "args": tool_call["args"]})
#                 if last_msg.type == "tool":
#                     steps.append({"type": "tool_response", "content": last_msg.content})
#         from .capture_service import classify_note
#         result = classify_note.invoke({"raw_text": req.text})
#         final_result = result
#         note_id, filepath, title, folder = write_markdown(
#             title=result["title"], folder=result["folder"], tags=result["tags"], body=req.text
#         )
#         final_result["saved"] = True
#         final_result["path"] = filepath
#     except Exception as e:
#         steps.append({"type": "error", "content": str(e)})
#         first_line = req.text.split("\n")[0][:60]
#         note_id, filepath, title, folder = write_markdown(
#             folder="inbox", title=first_line, tags=[], body=req.text
#         )
#         final_result = {
#             "title": title, "folder": "inbox", "tags": [],
#             "first_sentence": first_line, "error": str(e),
#             "saved": True, "path": filepath
#         }
#     return {"steps": steps, "final": final_result, "note_text": req.text}

# @app.post("/search_with_agent")
# async def search_with_agent(req: SearchRequest):
#     """Search notes with agent-powered natural language understanding"""
#     from .future_agent import create_search_agent
#     agent = create_search_agent()
#     steps = []
#     results = []
#     final_answer = None
#     try:
#         for chunk in agent.stream(
#             {"messages": [("user", f"Search my notes for: {req.query}")]},
#             stream_mode="values"
#         ):
#             if "messages" in chunk:
#                 last_msg = chunk["messages"][-1]
#                 if hasattr(last_msg, "content") and last_msg.content:
#                     steps.append({"type": "thought", "content": last_msg.content})
#                     if hasattr(last_msg, "type") and last_msg.type == "ai":
#                         final_answer = last_msg.content
#                 if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
#                     for tool_call in last_msg.tool_calls:
#                         steps.append({"type": "tool_call", "name": tool_call["name"], "args": tool_call["args"]})
#                 if last_msg.type == "tool":
#                     steps.append({"type": "tool_response", "content": last_msg.content})
#                     try:
#                         import json
#                         tool_results = json.loads(last_msg.content) if isinstance(last_msg.content, str) else last_msg.content
#                         if isinstance(tool_results, list) and tool_results:
#                             results = tool_results
#                     except:
#                         pass
#     except Exception as e:
#         steps.append({"type": "error", "content": str(e)})
#     return {"steps": steps, "results": results, "final_answer": final_answer, "query": req.query}

if __name__ == "__main__":
    import uvicorn
    import os

    # Enable auto-reload in development
    reload = os.getenv("ENV", "development") == "development"

    uvicorn.run(
        "api.main:app",  # Pass as import string for reload to work
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        reload=reload,  # Auto-reload on file changes
        reload_dirs=["api"] if reload else None  # Watch api directory
    )
