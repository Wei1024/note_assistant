"""
Synthesis Service - LLM-powered summarization of search results
GraphRAG Phase 4+ Integration

Combines:
1. Hybrid search (FTS5 + vector similarity)
2. Graph expansion (contextual neighbors)
3. Cluster context (thematic summaries)
4. LLM synthesis (coherent answer generation)
"""
import json
from typing import AsyncGenerator, Dict, List, Any
from ..llm import get_llm
from ..llm.prompts import Prompts
from ..services.search import hybrid_search, expand_via_graph, assemble_context
from ..db.graph import get_graph_node


async def synthesize_search_results(
    query: str,
    limit: int = 10,
    expand_graph: bool = True,
    max_hops: int = 1
) -> Dict[str, Any]:
    """Synthesize search results into coherent summary using GraphRAG

    Flow:
    1. Execute hybrid search (FTS5 + vector similarity)
    2. Expand via graph (optional, get contextual neighbors)
    3. Assemble context with cluster summaries
    4. Generate LLM synthesis from enriched context
    5. Return summary + full search results

    Args:
        query: User's natural language query
        limit: Max primary results to return
        expand_graph: Whether to include graph neighbors
        max_hops: Graph traversal depth (1-2)

    Returns:
        Dict with query, summary, notes_analyzed, search_results, expanded_results, cluster_summaries
    """
    # Step 1: Hybrid search with GraphRAG Phase 4
    primary_results = await hybrid_search(
        query=query,
        top_k=limit,
        fts_weight=0.4,
        vector_weight=0.6
    )

    if not primary_results:
        return {
            "query": query,
            "summary": "No notes found matching your query. Try different keywords or check if notes have been indexed.",
            "notes_analyzed": 0,
            "search_results": [],
            "expanded_results": [],
            "cluster_summaries": []
        }

    # Step 2: Graph expansion (optional)
    expanded_results = []
    if expand_graph:
        seed_ids = [r.note_id for r in primary_results]
        expanded_results = expand_via_graph(
            seed_note_ids=seed_ids,
            max_hops=max_hops,
            max_expanded=10  # Limit expanded for synthesis context
        )

    # Step 3: Assemble rich context
    context = assemble_context(
        primary_results=primary_results,
        expanded_results=expanded_results,
        max_context_tokens=3000,  # Larger context for synthesis
        include_cluster_summaries=True
    )

    # Step 4: Read full content of top notes for synthesis
    notes_to_synthesize = min(5, len(primary_results))  # Top 5 for LLM
    note_contents = []

    for i, result in enumerate(primary_results[:notes_to_synthesize]):
        try:
            # Read markdown file
            with open(result.file_path, 'r', encoding='utf-8') as f:
                content = f.read()

                # Extract body (skip frontmatter if present)
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    body = parts[2].strip() if len(parts) >= 3 else content
                else:
                    body = content

            # Include episodic metadata for richer context
            metadata_context = _format_episodic_metadata(result.episodic)

            note_contents.append({
                "index": i + 1,
                "note_id": result.note_id,
                "title": result.title,
                "content": body[:1500],  # Limit per note to fit context
                "metadata": metadata_context,
                "score": result.score
            })
        except Exception as e:
            print(f"❌ Failed to read note {result.file_path}: {e}")
            continue

    if not note_contents:
        return {
            "query": query,
            "summary": "Found matching notes but couldn't read their content. Files may have been moved or deleted.",
            "notes_analyzed": 0,
            "search_results": [r.to_dict() for r in primary_results],
            "expanded_results": [n.to_dict() for n in expanded_results],
            "cluster_summaries": context.get('cluster_summaries', [])
        }

    # Step 5: Build enriched context for LLM
    notes_context = "\n\n".join([
        f"--- Note {note['index']}: {note['title']} (Score: {note['score']:.2f}) ---\n{note['metadata']}\n\n{note['content']}"
        for note in note_contents
    ])

    # Add cluster context if available
    if context.get('cluster_summaries'):
        cluster_context = "\n\n--- CLUSTER CONTEXT ---\n"
        for cluster in context['cluster_summaries']:
            cluster_context += f"• {cluster['title']}: {cluster['summary']}\n"
        notes_context = cluster_context + "\n" + notes_context

    # Add expanded results context if available
    if expanded_results:
        expanded_context = f"\n\n--- RELATED NOTES (via graph) ---\n"
        expanded_context += f"Found {len(expanded_results)} connected notes via {', '.join(set(n.relation for n in expanded_results[:5]))} relationships.\n"
        notes_context += expanded_context

    # Step 6: Generate synthesis using enhanced prompt
    llm = get_llm(temperature=0.3, format=None)  # Slightly creative, plain text

    synthesis_prompt = Prompts.SYNTHESIZE_NOTES.format(
        query=query,
        notes_count=len(note_contents),
        notes_context=notes_context
    )

    try:
        response = await llm.ainvoke(synthesis_prompt)
        summary = response.content.strip()
    except Exception as e:
        print(f"❌ LLM synthesis failed: {e}")
        summary = f"Found {len(primary_results)} notes but couldn't generate summary. LLM error: {str(e)[:100]}"

    # Step 7: Return comprehensive result
    return {
        "query": query,
        "summary": summary,
        "notes_analyzed": len(note_contents),
        "search_results": [r.to_dict() for r in primary_results],
        "expanded_results": [n.to_dict() for n in expanded_results],
        "cluster_summaries": context.get('cluster_summaries', [])
    }


async def synthesize_search_results_stream(
    query: str,
    limit: int = 10,
    expand_graph: bool = True,
    max_hops: int = 1
) -> AsyncGenerator[str, None]:
    """Stream synthesis results in real-time using Server-Sent Events

    Flow:
    1. Execute search + expansion (same as non-streaming)
    2. Send metadata event (notes count, cluster info)
    3. Stream LLM synthesis chunks as they're generated
    4. Send search results event
    5. Send completion event

    Args:
        query: User's natural language query
        limit: Max results
        expand_graph: Include graph neighbors
        max_hops: Graph traversal depth

    Yields:
        SSE-formatted strings with events:
        - metadata: {type, query, notes_analyzed, has_clusters, has_expanded}
        - chunk: {type, content} - Incremental synthesis text
        - results: {type, search_results, expanded_results, cluster_summaries}
        - done: {type} - Completion signal
    """
    # Step 1: Hybrid search
    primary_results = await hybrid_search(
        query=query,
        top_k=limit,
        fts_weight=0.4,
        vector_weight=0.6
    )

    if not primary_results:
        # Send empty results
        yield f"data: {json.dumps({'type': 'metadata', 'query': query, 'notes_analyzed': 0, 'has_clusters': False, 'has_expanded': False})}\n\n"
        yield f"data: {json.dumps({'type': 'chunk', 'content': 'No notes found matching your query. Try different keywords.'})}\n\n"
        yield f"data: {json.dumps({'type': 'results', 'search_results': [], 'expanded_results': [], 'cluster_summaries': []})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    # Step 2: Graph expansion
    expanded_results = []
    if expand_graph:
        seed_ids = [r.note_id for r in primary_results]
        expanded_results = expand_via_graph(
            seed_note_ids=seed_ids,
            max_hops=max_hops,
            max_expanded=10
        )

    # Step 3: Assemble context
    context = assemble_context(
        primary_results=primary_results,
        expanded_results=expanded_results,
        max_context_tokens=3000,
        include_cluster_summaries=True
    )

    # Step 4: Read note contents
    notes_to_synthesize = min(5, len(primary_results))
    note_contents = []

    for i, result in enumerate(primary_results[:notes_to_synthesize]):
        try:
            with open(result.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    body = parts[2].strip() if len(parts) >= 3 else content
                else:
                    body = content

            metadata_context = _format_episodic_metadata(result.episodic)

            note_contents.append({
                "index": i + 1,
                "note_id": result.note_id,
                "title": result.title,
                "content": body[:1500],
                "metadata": metadata_context,
                "score": result.score
            })
        except Exception as e:
            print(f"❌ Failed to read note {result.file_path}: {e}")
            continue

    if not note_contents:
        yield f"data: {json.dumps({'type': 'metadata', 'query': query, 'notes_analyzed': 0, 'has_clusters': False, 'has_expanded': False})}\n\n"
        yield f"data: {json.dumps({'type': 'chunk', 'content': 'Found matching notes but could not read their content.'})}\n\n"
        yield f"data: {json.dumps({'type': 'results', 'search_results': [r.to_dict() for r in primary_results], 'expanded_results': [], 'cluster_summaries': []})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    # Step 5: Send metadata first
    metadata = {
        'type': 'metadata',
        'query': query,
        'notes_analyzed': len(note_contents),
        'has_clusters': len(context.get('cluster_summaries', [])) > 0,
        'has_expanded': len(expanded_results) > 0
    }
    yield f"data: {json.dumps(metadata)}\n\n"

    # Step 6: Build context (same as non-streaming)
    notes_context = "\n\n".join([
        f"--- Note {note['index']}: {note['title']} (Score: {note['score']:.2f}) ---\n{note['metadata']}\n\n{note['content']}"
        for note in note_contents
    ])

    if context.get('cluster_summaries'):
        cluster_context = "\n\n--- CLUSTER CONTEXT ---\n"
        for cluster in context['cluster_summaries']:
            cluster_context += f"• {cluster['title']}: {cluster['summary']}\n"
        notes_context = cluster_context + "\n" + notes_context

    if expanded_results:
        expanded_context = f"\n\n--- RELATED NOTES (via graph) ---\n"
        expanded_context += f"Found {len(expanded_results)} connected notes.\n"
        notes_context += expanded_context

    # Step 7: Stream LLM synthesis
    llm = get_llm(temperature=0.3, format=None)

    synthesis_prompt = Prompts.SYNTHESIZE_NOTES.format(
        query=query,
        notes_count=len(note_contents),
        notes_context=notes_context
    )

    try:
        # Stream chunks as they arrive
        async for chunk in llm.astream(synthesis_prompt):
            if chunk.content:
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk.content})}\n\n"
    except Exception as e:
        print(f"❌ LLM synthesis streaming failed: {e}")
        error_msg = f"Found {len(primary_results)} notes but synthesis failed. Error: {str(e)[:100]}"
        yield f"data: {json.dumps({'type': 'chunk', 'content': error_msg})}\n\n"

    # Step 8: Send search results
    results_data = {
        'type': 'results',
        'search_results': [r.to_dict() for r in primary_results],
        'expanded_results': [n.to_dict() for n in expanded_results],
        'cluster_summaries': context.get('cluster_summaries', [])
    }
    yield f"data: {json.dumps(results_data)}\n\n"

    # Step 9: Send completion signal
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


# ==============================================================================
# Helper Functions
# ==============================================================================

def _format_episodic_metadata(episodic: Dict[str, Any]) -> str:
    """Format episodic metadata for synthesis context

    Args:
        episodic: Dict with who/what/where/when/tags

    Returns:
        Formatted string for LLM context
    """
    parts = []

    if episodic.get('who'):
        parts.append(f"People: {', '.join(episodic['who'])}")

    if episodic.get('what'):
        parts.append(f"Topics: {', '.join(episodic['what'][:5])}")  # Top 5

    if episodic.get('where'):
        parts.append(f"Location: {', '.join(episodic['where'])}")

    if episodic.get('tags'):
        parts.append(f"Tags: {', '.join(episodic['tags'][:5])}")

    return " | ".join(parts) if parts else "No metadata"
