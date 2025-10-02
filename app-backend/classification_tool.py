"""
LangGraph-based note classification using local LLM
Replaces the old llm.py httpx-based implementation
"""
import json
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from .config import LLM_MODEL, LLM_BASE_URL, LLM_TEMPERATURE

@tool
def classify_note(raw_text: str) -> dict:
    """Classify a note into title, folder, and tags using local LLM.

    Args:
        raw_text: The raw note content to classify

    Returns:
        Dictionary with title, folder, tags, first_sentence
    """
    llm = ChatOllama(
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        format="json"
    )

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


# Optional: LangGraph ReAct agent wrapper (for future enhancements)
def create_classification_agent():
    """Create a LangGraph agent for classification (alternative approach)"""
    from langgraph.prebuilt import create_react_agent

    llm = ChatOllama(
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE
    )

    agent = create_react_agent(llm, tools=[classify_note])
    return agent
