"""
Synthesis Service - Summarize search results using LLM
Takes natural language query results and provides a coherent summary
"""
import json
from typing import AsyncGenerator
from ..llm import get_llm
from ..llm.prompts import Prompts
from .search import search_notes_smart


async def synthesize_search_results(query: str, limit: int = 10) -> dict:
    """Synthesize search results into a coherent summary.

    Flow:
    1. Execute smart search with the user's query
    2. Read full content of top matching notes
    3. Use LLM to synthesize findings into summary
    4. Return summary with original search results

    Args:
        query: Natural language query from user
        limit: Maximum number of notes to analyze

    Returns:
        Dict with query, summary, notes_analyzed, and search_results
    """
    # Step 1: Execute smart search
    search_results = await search_notes_smart(query, limit=limit)

    if not search_results:
        return {
            "query": query,
            "summary": "No notes found matching your query.",
            "notes_analyzed": 0,
            "search_results": []
        }

    # Step 2: Read full content of top notes (limit to top 5 for synthesis)
    notes_to_synthesize = min(5, len(search_results))
    note_contents = []

    for i, result in enumerate(search_results[:notes_to_synthesize]):
        try:
            # Read note file
            with open(result["path"], 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract body (after frontmatter)
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    body = parts[2].strip() if len(parts) >= 3 else content
                else:
                    body = content

            note_contents.append({
                "index": i + 1,
                "path": result["path"],
                "content": body,
                "snippet": result.get("snippet", ""),
                "metadata": result.get("metadata", {})
            })
        except Exception as e:
            print(f"Failed to read note {result['path']}: {e}")
            continue

    if not note_contents:
        return {
            "query": query,
            "summary": "Found matching notes but couldn't read their content.",
            "notes_analyzed": 0,
            "search_results": search_results
        }

    # Step 3: Generate synthesis using LLM
    llm = get_llm(temperature=0.3)  # Slightly creative for summary generation

    # Build context for LLM
    notes_context = "\n\n".join([
        f"--- Note {note['index']} ---\n{note['content'][:1000]}"  # Limit to first 1000 chars per note
        for note in note_contents
    ])

    synthesis_prompt = Prompts.SYNTHESIZE_NOTES.format(
        query=query,
        notes_count=len(note_contents),
        notes_context=notes_context
    )

    try:
        response = await llm.ainvoke(synthesis_prompt)
        summary = response.content.strip()
    except Exception as e:
        print(f"LLM synthesis failed: {e}")
        summary = f"Found {len(search_results)} notes but couldn't generate summary. Please review the search results below."

    # Step 4: Return synthesis result
    return {
        "query": query,
        "summary": summary,
        "notes_analyzed": len(note_contents),
        "search_results": search_results
    }


async def synthesize_search_results_stream(query: str, limit: int = 10) -> AsyncGenerator[str, None]:
    """Stream synthesis results in real-time using Server-Sent Events format.

    Flow:
    1. Execute smart search and yield metadata
    2. Read full content of top matching notes
    3. Stream LLM synthesis chunks as they're generated
    4. Yield search results at the end

    Args:
        query: Natural language query from user
        limit: Maximum number of notes to analyze

    Yields:
        SSE-formatted chunks with different event types:
        - metadata: Query info and notes count
        - chunk: Incremental summary content
        - results: Search results
        - done: Completion signal
    """
    # Step 1: Execute smart search
    search_results = await search_notes_smart(query, limit=limit)

    if not search_results:
        # Send metadata indicating no results
        yield f"data: {json.dumps({'type': 'metadata', 'query': query, 'notes_analyzed': 0})}\n\n"
        yield f"data: {json.dumps({'type': 'chunk', 'content': 'No notes found matching your query.'})}\n\n"
        yield f"data: {json.dumps({'type': 'results', 'search_results': []})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    # Step 2: Read full content of top notes (limit to top 5 for synthesis)
    notes_to_synthesize = min(5, len(search_results))
    note_contents = []

    for i, result in enumerate(search_results[:notes_to_synthesize]):
        try:
            # Read note file
            with open(result["path"], 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract body (after frontmatter)
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    body = parts[2].strip() if len(parts) >= 3 else content
                else:
                    body = content

            note_contents.append({
                "index": i + 1,
                "path": result["path"],
                "content": body,
                "snippet": result.get("snippet", ""),
                "metadata": result.get("metadata", {})
            })
        except Exception as e:
            print(f"Failed to read note {result['path']}: {e}")
            continue

    if not note_contents:
        yield f"data: {json.dumps({'type': 'metadata', 'query': query, 'notes_analyzed': 0})}\n\n"
        yield f"data: {json.dumps({'type': 'chunk', 'content': 'Found matching notes but could not read their content.'})}\n\n"
        yield f"data: {json.dumps({'type': 'results', 'search_results': search_results})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    # Send metadata first
    yield f"data: {json.dumps({'type': 'metadata', 'query': query, 'notes_analyzed': len(note_contents)})}\n\n"

    # Step 3: Stream LLM synthesis
    llm = get_llm(temperature=0.3)  # Slightly creative for summary generation

    # Build context for LLM
    notes_context = "\n\n".join([
        f"--- Note {note['index']} ---\n{note['content'][:1000]}"  # Limit to first 1000 chars per note
        for note in note_contents
    ])

    synthesis_prompt = Prompts.SYNTHESIZE_NOTES.format(
        query=query,
        notes_count=len(note_contents),
        notes_context=notes_context
    )

    try:
        # Stream LLM response chunks
        async for chunk in llm.astream(synthesis_prompt):
            if chunk.content:
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk.content})}\n\n"
    except Exception as e:
        print(f"LLM synthesis failed: {e}")
        error_msg = f"Found {len(search_results)} notes but couldn't generate summary. Please review the search results below."
        yield f"data: {json.dumps({'type': 'chunk', 'content': error_msg})}\n\n"

    # Step 4: Send search results
    yield f"data: {json.dumps({'type': 'results', 'search_results': search_results})}\n\n"

    # Step 5: Send completion signal
    yield f"data: {json.dumps({'type': 'done'})}\n\n"
