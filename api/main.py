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
from .routes import tags


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

# Include routers
app.include_router(tags.router)


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


# ==============================================================================
# Search & Retrieval Endpoints (Phase 4)
# ==============================================================================

@app.post("/search")
async def search_notes_endpoint(
    query: str,
    top_k: int = 10,
    expand_graph: bool = True,
    max_hops: int = 1,
    fts_weight: float = 0.4,
    vector_weight: float = 0.6
):
    """Hybrid search with optional graph expansion

    Combines FTS5 full-text search with vector similarity search,
    then optionally expands via graph edges to include contextual neighbors.

    Args:
        query: Search query string
        top_k: Number of primary results to return
        expand_graph: Whether to expand via graph edges
        max_hops: Maximum graph traversal depth (1-2 recommended)
        fts_weight: Weight for FTS5 score (default 0.4)
        vector_weight: Weight for vector similarity (default 0.6)

    Returns:
        SearchResponse with primary results, expanded results, and cluster context
    """
    from .services.search import hybrid_search, expand_via_graph, assemble_context
    from .models import (
        SearchResponse, SearchResultModel, ExpandedNodeModel,
        ClusterSummaryModel, EpisodicMetadata
    )
    import time

    start_time = time.time()

    # Step 1: Hybrid search
    primary_results = await hybrid_search(
        query=query,
        top_k=top_k,
        fts_weight=fts_weight,
        vector_weight=vector_weight
    )

    # Step 2: Graph expansion (optional)
    expanded_results = []
    if expand_graph and primary_results:
        seed_ids = [r.note_id for r in primary_results]
        expanded_results = expand_via_graph(
            seed_note_ids=seed_ids,
            max_hops=max_hops,
            max_expanded=20
        )

    # Step 3: Assemble context (includes cluster summaries)
    context = assemble_context(
        primary_results=primary_results,
        expanded_results=expanded_results,
        max_context_tokens=2000,
        include_cluster_summaries=True
    )

    # Convert to response models
    primary_models = []
    for result in primary_results:
        primary_models.append(SearchResultModel(
            note_id=result.note_id,
            title=result.title,
            snippet=result.snippet,
            score=result.score,
            fts_score=result.fts_score,
            vector_score=result.vector_score,
            episodic=EpisodicMetadata(**result.episodic),
            file_path=result.file_path,
            text_preview=result.text_preview
        ))

    expanded_models = []
    for node in expanded_results:
        expanded_models.append(ExpandedNodeModel(
            note_id=node.note_id,
            title=node.title,
            text_preview=node.text_preview,
            relation=node.relation,
            hop_distance=node.hop_distance,
            relevance_score=node.relevance_score,
            connected_to=node.connected_to
        ))

    cluster_models = []
    for cluster in context.get('cluster_summaries', []):
        cluster_models.append(ClusterSummaryModel(**cluster))

    execution_time_ms = int((time.time() - start_time) * 1000)

    return SearchResponse(
        query=query,
        primary_results=primary_models,
        expanded_results=expanded_models,
        cluster_summaries=cluster_models,
        total_results=len(primary_results) + len(expanded_results),
        execution_time_ms=execution_time_ms
    )


@app.post("/search/cluster/{cluster_id}")
async def search_within_cluster(
    cluster_id: int,
    query: str,
    top_k: int = 10
):
    """Search within a specific cluster

    Restricts hybrid search to notes in the specified cluster.
    Useful for "search within this topic" feature in UI.

    Args:
        cluster_id: Cluster ID to search within
        query: Search query string
        top_k: Number of results to return

    Returns:
        SearchResponse with results limited to cluster
    """
    from .services.search import hybrid_search
    from .models import SearchResponse, SearchResultModel, EpisodicMetadata
    import time

    start_time = time.time()

    # Hybrid search with cluster filter
    primary_results = await hybrid_search(
        query=query,
        top_k=top_k,
        cluster_id=cluster_id
    )

    # Convert to response models
    primary_models = []
    for result in primary_results:
        primary_models.append(SearchResultModel(
            note_id=result.note_id,
            title=result.title,
            snippet=result.snippet,
            score=result.score,
            fts_score=result.fts_score,
            vector_score=result.vector_score,
            episodic=EpisodicMetadata(**result.episodic),
            file_path=result.file_path,
            text_preview=result.text_preview
        ))

    execution_time_ms = int((time.time() - start_time) * 1000)

    return SearchResponse(
        query=query,
        primary_results=primary_models,
        expanded_results=[],
        cluster_summaries=[],
        total_results=len(primary_results),
        execution_time_ms=execution_time_ms
    )


@app.get("/search/similar/{note_id}")
async def find_similar_notes_endpoint(
    note_id: str,
    top_k: int = 10,
    threshold: float = 0.5
):
    """Find notes similar to a given note using vector similarity

    Pure vector similarity search. Useful for "Find Related" feature.

    Args:
        note_id: Note ID to find similar notes for
        top_k: Number of similar notes to return
        threshold: Minimum cosine similarity (0.0-1.0)

    Returns:
        SimilarityResponse with similar notes
    """
    from .services.semantic import find_similar_notes
    from .models import SimilarityResponse, SearchResultModel, EpisodicMetadata
    from .db.graph import get_graph_node

    # Use existing find_similar_notes from semantic.py
    similar_notes = find_similar_notes(
        note_id=note_id,
        threshold=threshold,
        limit=top_k
    )

    # Convert to SearchResultModel format
    result_models = []
    for note in similar_notes:
        # Get full node data
        node = get_graph_node(note['note_id'])
        if not node:
            continue

        # Extract title
        title = node.get('tags', [''])[0] if node.get('tags') else node['text'][:60]

        result_models.append(SearchResultModel(
            note_id=note['note_id'],
            title=title,
            snippet=note['text'][:200] + '...',
            score=note['similarity'],
            fts_score=0.0,  # Not applicable for vector-only search
            vector_score=note['similarity'],
            episodic=EpisodicMetadata(
                who=note.get('who', []),
                what=note.get('what', []),
                where=[],
                when=[],
                tags=note.get('tags', [])
            ),
            file_path=node.get('file_path', ''),
            text_preview=note['text'][:300] + '...'
        ))

    return SimilarityResponse(
        query_note_id=note_id,
        similar_notes=result_models,
        total=len(result_models)
    )


# ==============================================================================
# Synthesis Endpoints (Phase 4+: LLM-powered search summarization)
# ==============================================================================

@app.post("/synthesize")
async def synthesize_endpoint(
    query: str,
    limit: int = 10,
    expand_graph: bool = True,
    max_hops: int = 1
):
    """Synthesize search results into coherent summary using LLM

    Executes hybrid search + graph expansion, then uses LLM to generate
    a coherent answer to the user's query based on found notes.

    Args:
        query: Natural language query
        limit: Maximum number of notes to analyze
        expand_graph: Whether to include graph neighbors in context
        max_hops: Graph traversal depth (1-2)

    Returns:
        SynthesisResponse with summary, search results, and metadata
    """
    from .services.synthesis import synthesize_search_results

    result = await synthesize_search_results(
        query=query,
        limit=limit,
        expand_graph=expand_graph,
        max_hops=max_hops
    )

    return result


@app.get("/synthesize/stream")
async def synthesize_stream_endpoint(
    query: str,
    limit: int = 10,
    expand_graph: bool = True,
    max_hops: int = 1
):
    """Stream synthesis results in real-time using Server-Sent Events

    Same as /synthesize but streams LLM response chunks as they're generated.
    Better UX for long synthesis responses.

    Args:
        query: Natural language query
        limit: Maximum number of notes
        expand_graph: Include graph neighbors
        max_hops: Graph traversal depth

    Returns:
        SSE stream with events:
        - metadata: {type, query, notes_analyzed, has_clusters, has_expanded}
        - chunk: {type, content} - Incremental synthesis text
        - results: {type, search_results, expanded_results, cluster_summaries}
        - done: {type} - Completion signal
    """
    from fastapi.responses import StreamingResponse
    from .services.synthesis import synthesize_search_results_stream

    return StreamingResponse(
        synthesize_search_results_stream(
            query=query,
            limit=limit,
            expand_graph=expand_graph,
            max_hops=max_hops
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# ==============================================================================
# Clustering Endpoints (Phase 2.5)
# ==============================================================================

@app.post("/graph/cluster")
async def run_clustering_endpoint(resolution: float = 1.0):
    """Run clustering on the entire graph

    Args:
        resolution: Clustering resolution (higher = more clusters, default 1.0)

    Returns:
        Clustering statistics and cluster summaries
    """
    from .services.clustering import run_clustering

    stats = await run_clustering(resolution=resolution)
    return stats


@app.get("/graph/clusters")
async def get_clusters():
    """Get all clusters with metadata

    Returns:
        List of clusters with id, summary, size
    """
    from .services.clustering import get_all_clusters

    clusters = get_all_clusters()
    return {
        "clusters": clusters,
        "total": len(clusters)
    }


@app.get("/graph/clusters/{cluster_id}")
async def get_cluster_detail(cluster_id: int):
    """Get detailed information for a specific cluster

    Args:
        cluster_id: Cluster ID

    Returns:
        Cluster metadata with list of all nodes in the cluster
    """
    from .services.clustering import get_cluster_details

    cluster = get_cluster_details(cluster_id)
    if not cluster:
        return {"error": "Cluster not found"}, 404

    return cluster


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
