"""
Centralized LLM Client with Connection Pooling
Singleton instance shared across all services
"""
import httpx
from langchain_ollama import ChatOllama
from typing import Optional
from ..config import LLM_MODEL, LLM_BASE_URL, LLM_TEMPERATURE

# Global singleton instances
_http_client: Optional[httpx.AsyncClient] = None
_llm_instance: Optional[ChatOllama] = None


def get_http_client() -> httpx.AsyncClient:
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


_UNSET = object()  # Sentinel value to detect if parameter was passed

def get_llm(temperature: Optional[float] = None, format: Optional[str] = _UNSET) -> ChatOllama:
    """Get or create singleton LLM instance with connection pooling

    Args:
        temperature: Optional temperature override (default: from config)
        format: Optional format override. Use "json" for JSON, None for plain text.
                If not specified, defaults to "json" for singleton.

    Returns:
        ChatOllama instance
    """
    global _llm_instance

    # If requesting different parameters, create new instance
    if temperature is not None or format is not _UNSET:
        return ChatOllama(
            base_url=LLM_BASE_URL,
            model=LLM_MODEL,
            temperature=temperature if temperature is not None else LLM_TEMPERATURE,
            format=format if format is not _UNSET else None,
            http_client=get_http_client()
        )

    # Otherwise return singleton with JSON format default
    if _llm_instance is None:
        _llm_instance = ChatOllama(
            base_url=LLM_BASE_URL,
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            format="json",  # Default to JSON format
            http_client=get_http_client()
        )
    return _llm_instance


async def initialize_llm():
    """Initialize LLM client on application startup

    Call this in FastAPI lifespan startup
    """
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=30.0
            ),
            timeout=httpx.Timeout(30.0, connect=5.0)
        )


async def shutdown_llm():
    """Cleanup LLM client on application shutdown

    Call this in FastAPI lifespan shutdown to properly close connections
    """
    global _http_client, _llm_instance

    if _http_client:
        await _http_client.aclose()
        _http_client = None

    _llm_instance = None
