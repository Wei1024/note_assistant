"""
Note Classification Service
Direct LLM-based classification (no agent overhead for fast performance)
"""
import json
import httpx
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from .config import LLM_MODEL, LLM_BASE_URL, LLM_TEMPERATURE

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
            format="json",
            http_client=get_http_client()  # Enable connection pooling
        )
    return _llm_instance

@tool
def classify_note(raw_text: str) -> dict:
    """Classify a note into title, folder, and tags using local LLM.

    NOTE: This synchronous version is kept for future agent integration.
    For production FastAPI endpoints, use classify_note_async() instead.

    Args:
        raw_text: The raw note content to classify

    Returns:
        Dictionary with title, folder, tags, first_sentence
    """
    llm = get_llm()  # Use singleton instance

    prompt = f"""You are a note classifier. Analyze this note and return JSON.

Note: {raw_text}

Return ONLY valid JSON:
{{
  "title": "Short descriptive title (max 10 words)",
  "folder": "inbox|projects|people|research|journal",
  "tags": ["tag1", "tag2", "tag3"],
  "first_sentence": "One sentence summary"
}}

Folder selection guide:
- projects: Work tasks, technical issues, code
- people: Meetings, conversations, relationships
- research: Learning, articles, investigations
- journal: Personal thoughts, reflections
- inbox: When unsure

Tags should be lowercase, 3-6 relevant keywords.

JSON:"""

    try:
        response = llm.invoke(prompt)
        result = json.loads(response.content)

        # Validation
        valid_folders = ["inbox", "projects", "people", "research", "journal"]
        if result.get("folder") not in valid_folders:
            result["folder"] = "inbox"

        # Ensure required fields
        result.setdefault("title", raw_text.split("\n")[0][:60])
        result.setdefault("tags", [])
        result.setdefault("first_sentence", raw_text.split("\n")[0])

        return result

    except Exception as e:
        # Fallback on error
        return {
            "title": raw_text.split("\n")[0][:60],
            "folder": "inbox",
            "tags": [],
            "first_sentence": raw_text.split("\n")[0],
            "error": str(e)
        }


async def classify_note_async(raw_text: str) -> dict:
    """Async version of classify_note for FastAPI endpoints.

    Provides better performance by not blocking the event loop.

    Args:
        raw_text: The raw note content to classify

    Returns:
        Dictionary with title, folder, tags, first_sentence
    """
    llm = get_llm()  # Use singleton instance

    prompt = f"""You are a note classifier. Analyze this note and return JSON.

Note: {raw_text}

Return ONLY valid JSON:
{{
  "title": "Short descriptive title (max 10 words)",
  "folder": "inbox|projects|people|research|journal",
  "tags": ["tag1", "tag2", "tag3"],
  "first_sentence": "One sentence summary"
}}

Folder selection guide:
- projects: Work tasks, technical issues, code
- people: Meetings, conversations, relationships
- research: Learning, articles, investigations
- journal: Personal thoughts, reflections
- inbox: When unsure

Tags should be lowercase, 3-6 relevant keywords.

JSON:"""

    try:
        response = await llm.ainvoke(prompt)  # Async call
        result = json.loads(response.content)

        # Validation
        valid_folders = ["inbox", "projects", "people", "research", "journal"]
        if result.get("folder") not in valid_folders:
            result["folder"] = "inbox"

        # Ensure required fields
        result.setdefault("title", raw_text.split("\n")[0][:60])
        result.setdefault("tags", [])
        result.setdefault("first_sentence", raw_text.split("\n")[0])

        return result

    except Exception as e:
        # Fallback on error
        return {
            "title": raw_text.split("\n")[0][:60],
            "folder": "inbox",
            "tags": [],
            "first_sentence": raw_text.split("\n")[0],
            "error": str(e)
        }
