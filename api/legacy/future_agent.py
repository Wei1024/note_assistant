"""
Future LangGraph Agent Integration
===================================

This file contains LangGraph ReAct agent code for future use.
Currently, the app uses direct LLM calls for better performance (60-70% faster).

When to use agents:
- Multi-step reasoning needed
- Complex tool orchestration
- Need for planning and reflection

Current fast path:
- capture_service.py: classify_note_async() - direct LLM classification
- search_service.py: search_notes_smart() - direct query rewriting + FTS5

Agent alternatives (slower but more powerful):
- create_classification_agent() - For complex note analysis
- create_search_agent() - For multi-step search reasoning
"""

from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from .config import LLM_MODEL, LLM_BASE_URL, LLM_TEMPERATURE
from .fts import search_notes as fts_search
from .capture_service import get_llm, classify_note
from .search_service import search_notes_tool, rewrite_natural_query


# ============================================================================
# CLASSIFICATION AGENT (Alternative to direct LLM in capture_service.py)
# ============================================================================

def create_classification_agent():
    """Create a LangGraph ReAct agent for note classification.

    This is an alternative to the fast path classify_note_async().
    Use this when you need:
    - Multi-step analysis of note content
    - Tool-based reasoning about classification
    - Planning and reflection capabilities

    Currently NOT used in production (too slow for simple classification).

    Returns:
        LangGraph ReAct agent with classification tools
    """
    llm = get_llm()
    agent = create_react_agent(llm, tools=[classify_note])
    return agent


# ============================================================================
# SEARCH AGENT (Alternative to direct rewrite in search_service.py)
# ============================================================================

def create_search_agent():
    """Create a LangGraph ReAct agent for intelligent search.

    This is an alternative to the fast path search_notes_smart().
    Use this when you need:
    - Multi-step search refinement
    - Complex query understanding
    - Iterative search with reasoning

    Currently NOT used in production (70% slower than direct rewrite).
    The agent adds ~4-5s overhead for ReAct reasoning.

    Fast path: search_notes_smart() does query rewrite (~2s) + FTS5 (~50ms)
    Agent path: ReAct wrapper adds planning/reflection overhead

    Returns:
        LangGraph ReAct agent with search tools
    """
    llm = get_llm()

    agent = create_react_agent(
        llm,
        tools=[rewrite_natural_query, search_notes_tool]
    )

    return agent


# ============================================================================
# FUTURE: MULTI-AGENT WORKFLOWS
# ============================================================================

def create_multi_agent_workflow():
    """Placeholder for future multi-agent orchestration.

    Ideas for future agent workflows:
    1. Note enrichment pipeline:
       - Capture agent classifies
       - Enrichment agent adds context/links
       - Validation agent checks quality

    2. Smart search pipeline:
       - Query understanding agent
       - Search execution agent
       - Result ranking agent

    3. Note maintenance:
       - Cleanup agent (merge duplicates)
       - Tagging agent (re-classify old notes)
       - Link detection agent
    """
    raise NotImplementedError("Multi-agent workflows coming soon!")


# ============================================================================
# USAGE EXAMPLES (for future reference)
# ============================================================================

"""
Example 1: Using classification agent instead of direct LLM
------------------------------------------------------------
from .future_agent import create_classification_agent

agent = create_classification_agent()
result = agent.invoke({"messages": [("user", f"Classify this note: {text}")]})

Example 2: Using search agent for complex queries
--------------------------------------------------

agent = create_search_agent()
result = agent.invoke({
    "messages": [("user", "Find notes about AWS Lambda performance issues")]
})

Example 3: Comparing performance
---------------------------------
# Fast path (current production)
result = await search_notes_smart("what sport did I watch?")  # ~2s

# Agent path (future use)
agent = create_search_agent()
result = agent.invoke({"messages": [...]})  # ~6-7s (includes reasoning)
"""
