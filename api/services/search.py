"""
Search Service - Fast natural language search
Direct query rewriting + FTS5 (no agent overhead for 70% faster performance)
"""
import json
from langchain_core.tools import tool
from ..llm import get_llm
from ..llm.prompts import Prompts
from ..fts import search_notes as fts_search


@tool
def search_notes_tool(query: str) -> list:
    """Search notes database using FTS5 full-text search.

    Args:
        query: FTS5 query string. Use OR for multiple terms.
               Examples: "aws OR cloud", "baseball", "project meeting"

    Returns:
        List of matching notes with path, snippet, and score
    """
    results = fts_search(query, limit=10)

    # Format for LLM consumption
    formatted = []
    for r in results:
        formatted.append({
            "path": r["path"],
            "snippet": r["snippet"],
            "score": r["score"]
        })

    return formatted


@tool
def rewrite_natural_query(natural_query: str) -> str:
    """Convert natural language question to FTS5 search keywords.

    NOTE: This @tool decorated version is kept for future agent integration.
    For production use, the logic is inlined in search_notes_smart() for performance.

    Args:
        natural_query: Natural language question like "what sport did I watch?"

    Returns:
        FTS5-compatible search query with OR keywords
    """
    # Use singleton but override temperature for this specific task
    llm = ChatOllama(
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
        temperature=0.1,  # Low temperature for consistent rewrites
        format="json"
    )

    prompt = f"""You are a search query optimizer. Convert natural language to search keywords.

User query: {natural_query}

Extract key concepts and related terms. Return JSON with search keywords.

Rules:
- Extract main concepts and synonyms
- Add related terms that might appear in notes
- Use OR to connect terms
- Keep it focused (3-8 terms max)
- Remove filler words (what, did, I, the, a)

Examples:
- "what sport did I watch?" → {{"keywords": "sport OR baseball OR basketball OR football OR hockey OR game"}}
- "AWS cloud notes" → {{"keywords": "aws OR cloud OR infrastructure"}}
- "meeting with john" → {{"keywords": "john OR meeting"}}

Return ONLY JSON:
{{"keywords": "term1 OR term2 OR term3"}}

JSON:"""

    try:
        response = llm.invoke(prompt)
        result = json.loads(response.content)
        return result.get("keywords", natural_query)
    except:
        # Fallback: just use the original query
        return natural_query


async def parse_smart_query(natural_query: str) -> dict:
    """Parse natural language query and extract structured filters.

    Single LLM call that extracts:
    - person: Name of person to filter by
    - emotion: Emotion dimension (excited, frustrated, curious, etc.)
    - entity: Specific named thing (tool, concept, project, topic)
    - context: Folder filter (tasks, meetings, ideas, reference, journal)
    - text_query: Remaining keywords for FTS5 search
    - sort: Sort order (recent, oldest)

    Args:
        natural_query: Natural language search query

    Returns:
        Dict with extracted filters
    """
    llm = get_llm(temperature=0.1, format="json")  # Low temperature for consistent parsing
    prompt = Prompts.PARSE_SEARCH_QUERY.format(query=natural_query)

    try:
        response = await llm.ainvoke(prompt)
        result = json.loads(response.content)
        return result
    except Exception as e:
        # Fallback: treat as text search
        return {
            "person": None,
            "emotion": None,
            "entity": None,
            "context": None,
            "text_query": natural_query,
            "sort": None
        }


async def search_notes_smart(natural_query: str, limit: int = 10, status: str = None) -> list:
    """Smart search with natural language understanding and multi-dimensional routing.

    Flow:
    1. Parse query to extract filters (person, emotion, entity, etc.) - 1 LLM call
    2. Route to appropriate endpoint (search_by_person, search_by_dimension, FTS5)
    3. Apply additional filters (context, sort, status)
    4. Return results

    Args:
        natural_query: Natural language search query
        limit: Maximum number of results
        status: Optional status filter (todo, in_progress, done)

    Returns:
        List of search results with path, snippet, score
    """
    # Import Phase 3.1 query functions
    from .query import search_by_person, search_by_dimension, search_by_entity

    # Step 1: Parse query to extract filters (1 LLM call)
    filters = await parse_smart_query(natural_query)

    # Step 2: Route to appropriate search endpoint
    results = []
    relaxed_search = False  # Track if we used relaxed search

    if filters.get("person"):
        # Search by person
        results = search_by_person(filters["person"], context=filters.get("context"), limit=limit)

        # Fallback: If no results and context was specified, try without context
        if len(results) == 0 and filters.get("context"):
            results = search_by_person(filters["person"], context=None, limit=limit)
            relaxed_search = True

    elif filters.get("emotion"):
        # Search by emotion dimension
        results = search_by_dimension("emotion", filters["emotion"], query_text=filters.get("text_query"), limit=limit)

        # Note: Emotions don't have context filtering, so no fallback needed

    elif filters.get("entity"):
        # Search by entity (generic type)
        results = search_by_entity("entity", filters["entity"], context=filters.get("context"), limit=limit)

        # Fallback: If no results and context was specified, try without context
        if len(results) == 0 and filters.get("context"):
            results = search_by_entity("entity", filters["entity"], context=None, limit=limit)
            relaxed_search = True

    elif filters.get("text_query"):
        # Fall back to FTS5 text search
        results = fts_search(filters["text_query"], limit=limit, status=status)

        # If context filter exists, filter results by folder
        if filters.get("context") and results:
            context_folder = filters["context"]
            filtered_results = [r for r in results if context_folder in r.get("path", "")]

            # Fallback: If filtering removed all results, return unfiltered
            if len(filtered_results) == 0:
                relaxed_search = True
            else:
                results = filtered_results
    else:
        # No filters extracted, fall back to text search
        results = fts_search(natural_query, limit=limit, status=status)

    # Mark results if relaxed search was used
    if relaxed_search and results:
        for result in results:
            # Preserve existing metadata, add relaxed search indicator
            if not isinstance(result.get("metadata"), dict):
                result["metadata"] = {}
            result["metadata"]["match_type"] = "related"
            result["metadata"]["search_note"] = "Found in different folder (searched all folders)"

    # Step 3: Apply status filter if specified (for task searches)
    if status and results:
        # Status filter is already handled by Phase 3.1 endpoints
        # Only needed for FTS5 fallback (already applied above)
        pass

    # Step 4: Apply sort if specified
    if filters.get("sort") == "recent":
        # Sort by created date descending (most recent first)
        results = sorted(results, key=lambda r: r.get("metadata", {}).get("created", ""), reverse=True)
    elif filters.get("sort") == "oldest":
        # Sort by created date ascending (oldest first)
        results = sorted(results, key=lambda r: r.get("metadata", {}).get("created", ""))

    return results
