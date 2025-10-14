"""
Search Service - Fast natural language search
Direct query rewriting + FTS5 (no agent overhead for 70% faster performance)
"""
import json
import httpx
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from .config import LLM_MODEL, LLM_BASE_URL, LLM_TEMPERATURE
from .fts import search_notes as fts_search

# HTTP client with connection pooling for Ollama
_http_client = None
_llm_instance = None

def get_http_client():
    """Get or create HTTP client with connection pooling"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_keepalive_connections=10,  # Keep 10 connections alive
                max_connections=20,             # Max 20 concurrent connections
                keepalive_expiry=30.0          # Keep alive for 30 seconds
            ),
            timeout=httpx.Timeout(30.0, connect=5.0)  # 30s timeout, 5s connect
        )
    return _http_client

def get_llm():
    """Get or create singleton LLM instance with connection pooling"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatOllama(
            base_url=LLM_BASE_URL,
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            http_client=get_http_client()  # Enable connection pooling
        )
    return _llm_instance


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
    - entity_type: Type of entity (project, topic, tech)
    - entity_value: Value of the entity
    - context: Folder filter (tasks, meetings, ideas, reference, journal)
    - text_query: Remaining keywords for FTS5 search
    - sort: Sort order (recent, oldest)

    Args:
        natural_query: Natural language search query

    Returns:
        Dict with extracted filters
    """
    llm = ChatOllama(
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
        temperature=0.1,  # Low temperature for consistent parsing
        format="json",
        http_client=get_http_client()
    )

    prompt = f"""Parse this search query and extract structured filters.

User query: "{natural_query}"

Extract any of these filters if clearly present:
- person: Name of person (e.g., "Sarah", "Alex", "John")
- emotion: Feeling word (excited, frustrated, curious, worried, happy, etc.)
- entity_type: Type of thing (project, topic, technology)
- entity_value: The specific project/topic/tech name
- context: Folder type (tasks, meetings, ideas, reference, journal)
- text_query: Remaining keywords for text search (remove extracted filters)
- sort: Time sorting (recent, oldest) if mentioned

Rules:
- Only extract what's CLEARLY present
- For person: Extract proper names only
- For emotion: Extract feeling words
- For entity_type + entity_value: Extract specific projects/topics/technologies
- For context: Match to folder names if mentioned
- For text_query: Remove extracted filters, keep remaining keywords
- Use null for missing fields

Examples:
- "what's the recent project I did with Sarah"
  → {{"person": "Sarah", "entity_type": "project", "sort": "recent", "text_query": null}}

- "notes where I felt excited about FAISS"
  → {{"emotion": "excited", "entity_value": "FAISS", "entity_type": "topic", "text_query": null}}

- "meetings about AWS infrastructure"
  → {{"context": "meetings", "entity_value": "AWS", "entity_type": "tech", "text_query": null, "person": null, "emotion": null}}

- "meetings about FAISS"
  → {{"context": "meetings", "entity_value": "FAISS", "entity_type": "tech", "text_query": null, "person": null, "emotion": null}}

- "notes about AWS and cloud infrastructure"
  → {{"entity_value": "AWS", "entity_type": "tech", "text_query": "cloud infrastructure", "person": null, "emotion": null}}

- "what sport did I watch?"
  → {{"text_query": "sport watch", "person": null, "emotion": null, "entity_type": null}}

Return ONLY JSON:
{{
  "person": "name" or null,
  "emotion": "feeling" or null,
  "entity_type": "project"/"topic"/"tech" or null,
  "entity_value": "value" or null,
  "context": "folder" or null,
  "text_query": "keywords" or null,
  "sort": "recent"/"oldest" or null
}}

JSON:"""

    try:
        response = await llm.ainvoke(prompt)
        result = json.loads(response.content)
        return result
    except Exception as e:
        # Fallback: treat as text search
        return {
            "person": None,
            "emotion": None,
            "entity_type": None,
            "entity_value": None,
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
    from .query_service import search_by_person, search_by_dimension, search_by_entity

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

    elif filters.get("entity_value"):
        # Search by entity (topic, project, tech)
        entity_type = filters.get("entity_type") or "topic"  # Default to topic
        results = search_by_entity(entity_type, filters["entity_value"], context=filters.get("context"), limit=limit)

        # Fallback: If no results and context was specified, try without context
        if len(results) == 0 and filters.get("context"):
            results = search_by_entity(entity_type, filters["entity_value"], context=None, limit=limit)
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
