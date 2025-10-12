"""
Note Classification Service
Direct LLM-based classification (no agent overhead for fast performance)
"""
import json
import httpx
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from .config import LLM_MODEL, LLM_BASE_URL, LLM_TEMPERATURE, VALID_FOLDERS, WORKING_FOLDERS, CLASSIFICATION_CONFIDENCE_THRESHOLD

# HTTP client with connection pooling for Ollama
_http_client = None
_llm_instance = None


def _determine_needs_review(result: dict, raw_text: str) -> tuple[bool, list[str]]:
    """Heuristic-based review flagging (no fake LLM confidence)

    Returns:
        (needs_review, reasons) tuple
    """
    reasons = []

    # Heuristic 1: Very short text (ambiguous)
    if len(raw_text.strip()) < 15:
        reasons.append("Text too short")

    # Heuristic 2: LLM expressed uncertainty
    reasoning = result.get("reasoning", "").lower()
    uncertainty_keywords = ["unsure", "could be", "might be", "unclear", "ambiguous", "uncertain"]
    if any(keyword in reasoning for keyword in uncertainty_keywords):
        reasons.append("LLM expressed uncertainty")

    # Heuristic 3: Fallback classification
    if "defaulted" in reasoning or "fallback" in reasoning:
        reasons.append("Fallback classification used")

    # Heuristic 4: No clear folder match
    if result.get("folder") == "journal" and not any(word in raw_text.lower() for word in ["feel", "reflect", "today", "grateful", "overwhelmed"]):
        # Classified as journal but doesn't have journal keywords
        reasons.append("Weak match for journal folder")

    return len(reasons) > 0, reasons

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
        Dictionary with title, folder, tags, first_sentence, status
    """
    llm = get_llm()  # Use singleton instance

    prompt = f"""You are a note classifier using a brain-based cognitive model. Analyze this note and return JSON.

Note: {raw_text}

Return ONLY valid JSON:
{{
  "title": "Short descriptive title (max 10 words)",
  "folder": "tasks|meetings|ideas|reference|journal",
  "reasoning": "Brief explanation of classification choice",
  "tags": ["tag1", "tag2", "tag3"],
  "first_sentence": "One sentence summary",
  "status": "todo|in_progress|done|null"
}}

Folder Selection Guide (Cognitive Contexts):

**tasks** (Executive Function - Working Memory)
- Actionable items with clear completion state
- ONLY folder that can have status (todo/in_progress/done)
- Examples: "Fix login bug", "Call Sarah tomorrow", "Deploy to production"
- If NOT actionable, it's NOT a task!

**meetings** (Social Cognition - Working Memory)
- Conversations, discussions, standup notes
- Captures WHO + WHEN + WHAT was discussed
- Examples: "Met with Sarah about memory research", "Team standup notes", "1-on-1 with manager"
- NO status field (meetings happened or didn't happen, not todo/done)

**ideas** (Creative Exploration - Working Memory)
- Brainstorms, hypotheses, "what if" thoughts
- Exploration mode, not execution mode
- Examples: "Could we use Redis for caching?", "Product idea: bulk export", "Hypothesis about user behavior"
- NO status field (ideas are explored, not completed)

**reference** (Procedural Memory - Working Memory)
- How-tos, learnings, evergreen knowledge
- Timeless information you'll reference later
- Examples: "How Postgres EXPLAIN works", "Git rebase tutorial", "Python async patterns"
- NO status field (knowledge just exists)

**journal** (Emotional Processing - Limbic System)
- Personal reflections, feelings, thoughts
- Not task-oriented, just being present
- Examples: "Feeling overwhelmed today", "Grateful for team support", "Reflecting on career growth"
- NO status field (emotions aren't tasks)

Classification Rules:
1. If uncertain about classification, explain why in reasoning (e.g., "could be task or idea")
2. Focus on PRIMARY intent (what is this note mainly about?)
3. Status field ONLY valid for "tasks" folder
4. When uncertain between folders, prefer the most actionable context

Tags should be lowercase, 3-6 relevant keywords.

JSON:"""

    try:
        response = await llm.ainvoke(prompt)  # Async call
        result = json.loads(response.content)

        # Validation
        folder = result.get("folder")
        if folder not in VALID_FOLDERS:
            # Fallback to journal for uncertain classifications
            folder = "journal"
            result["folder"] = folder
            result["reasoning"] = f"Invalid folder '{result.get('folder')}', defaulted to journal"

        # Validate status field - ONLY for tasks folder
        status = result.get("status")
        if status == "null":
            status = None

        if folder == "tasks":
            # Validate status for tasks
            valid_statuses = ["todo", "in_progress", "done", None]
            if status not in valid_statuses:
                status = "todo"  # Default to todo for tasks
        else:
            # Non-task folders should NOT have status
            status = None

        result["status"] = status

        # Ensure required fields
        result.setdefault("title", raw_text.split("\n")[0][:60])
        result.setdefault("tags", [])
        result.setdefault("first_sentence", raw_text.split("\n")[0])
        result.setdefault("reasoning", "")

        # Heuristic-based review flagging (no fake confidence)
        needs_review, review_reasons = _determine_needs_review(result, raw_text)
        result["needs_review"] = needs_review
        if review_reasons:
            result["reasoning"] = result.get("reasoning", "") + " | Review: " + "; ".join(review_reasons)

        return result

    except Exception as e:
        # Fallback on error
        return {
            "title": raw_text.split("\n")[0][:60],
            "folder": "journal",  # Safe fallback
            "tags": [],
            "first_sentence": raw_text.split("\n")[0],
            "status": None,
            "reasoning": f"Classification failed: {str(e)}",
            "needs_review": True,
            "error": str(e)
        }
