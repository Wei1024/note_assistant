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


async def search_notes_smart(natural_query: str, limit: int = 10) -> list:
    """Fast search with natural language understanding (no agent overhead).

    This is the optimized version that skips the ReAct agent wrapper for
    70% faster performance while maintaining NL query understanding.

    Flow:
    1. Rewrite natural query to keywords using LLM (~2s)
    2. Execute FTS5 search (~50ms)
    3. Return results directly

    Args:
        natural_query: Natural language search query
        limit: Maximum number of results

    Returns:
        List of search results with path, snippet, score
    """
    # Step 1: Rewrite query using LLM (async for non-blocking)
    llm = ChatOllama(
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
        temperature=0.1,  # Low temperature for consistent rewrites
        format="json",
        http_client=get_http_client()  # Use connection pooling
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
        response = await llm.ainvoke(prompt)  # Async call
        result = json.loads(response.content)
        search_query = result.get("keywords", natural_query)
    except:
        # Fallback: use original query
        search_query = natural_query

    # Step 2: Execute FTS5 search
    results = fts_search(search_query, limit=limit)

    return results
