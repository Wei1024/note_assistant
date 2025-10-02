# LangGraph Implementation Plan for QuickNote AI

## Goal
Implement LangGraph-based note classification with **local-first, offline tracing** for the QuickNote AI system.

---

## Architecture Decision

### ✅ Use LangGraph Because:
- Production-ready with built-in features
- Graph visualization for debugging
- State management out of the box
- Built-in streaming for local tracing
- Clean abstraction over custom agentic loops

### ✅ Tracing Strategy: Built-in Streaming (Local-First)
- **Production**: Built-in streaming + local file logging
- **Development**: Optional LangSmith (can be disabled)
- **No external dependencies** for production tracing
- **Full offline operation** maintained

---

## LangGraph Core Concepts Review

### 1. State
Shared data structure passed between nodes:
```python
from typing import TypedDict, Annotated
from operator import add

class NoteState(TypedDict):
    raw_text: str                              # Original note content
    title: str                                 # Extracted/generated title
    folder: str                                # projects/inbox/people/research/journal
    tags: Annotated[list[str], add]           # Tags (append with reducer)
    first_sentence: str                        # Summary sentence
    error: str | None                          # Error tracking
    retry_count: int                           # For retry logic
```

### 2. Nodes
Functions that process state:
```python
def classify_note(state: NoteState) -> dict:
    """Call LLM to classify the note"""
    # Returns updates to state
    return {"title": "...", "folder": "...", "tags": [...]}

def validate_classification(state: NoteState) -> dict:
    """Validate LLM output"""
    # Check if folder is valid, etc.
    return {"error": None} or {"error": "Invalid folder"}

def save_to_inbox(state: NoteState) -> dict:
    """Fallback: save to inbox"""
    return {"folder": "inbox", "tags": []}
```

### 3. Edges
Control flow:
- **Normal edges**: Always A → B
- **Conditional edges**: Dynamic routing based on state
  ```python
  def should_retry(state: NoteState) -> str:
      if state["error"] and state["retry_count"] < 3:
          return "retry"
      elif state["error"]:
          return "fallback"
      return "save"
  ```

---

## Implementation Plan

### Phase 1: Basic LangGraph Agent (Use Prebuilt)

Start with `create_react_agent` to validate LLM tool calling:

```python
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama
from langchain_core.tools import tool

@tool
def classify_note(raw_text: str) -> dict:
    """Classify a note into folder and tags.

    Args:
        raw_text: The raw note content

    Returns:
        Dictionary with title, folder, tags, first_sentence
    """
    # This will be called by the LLM
    # For now, return structured output
    # Later: call LLM with structured output
    return {
        "title": "...",
        "folder": "projects",
        "tags": ["aws", "architecture"],
        "first_sentence": "..."
    }

llm = ChatOllama(model="qwen3:4b-instruct", temperature=0.1)
agent = create_react_agent(llm, tools=[classify_note])

# Use with streaming
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": note_text}]},
    stream_mode="updates"
):
    print(chunk)
```

**Test this first** to validate Qwen3 can do tool calling.

---

### Phase 2: Custom LangGraph with Validation & Retry

Build custom graph for more control:

```python
from langgraph.graph import StateGraph, START, END

# Define state
class NoteState(TypedDict):
    raw_text: str
    title: str
    folder: str
    tags: Annotated[list[str], add]
    first_sentence: str
    error: str | None
    retry_count: int

# Define nodes
def llm_classify(state: NoteState) -> dict:
    """Call LLM to classify"""
    prompt = build_classification_prompt(state["raw_text"])
    response = llm.invoke(prompt)
    parsed = parse_llm_response(response)
    return {
        "title": parsed["title"],
        "folder": parsed["folder"],
        "tags": parsed["tags"],
        "first_sentence": parsed["first_sentence"]
    }

def validate(state: NoteState) -> dict:
    """Validate classification"""
    valid_folders = ["inbox", "projects", "people", "research", "journal"]
    if state["folder"] not in valid_folders:
        return {"error": f"Invalid folder: {state['folder']}"}
    return {"error": None}

def fallback_to_inbox(state: NoteState) -> dict:
    """Fallback: save to inbox"""
    first_line = state["raw_text"].split("\n")[0][:60]
    return {
        "title": first_line,
        "folder": "inbox",
        "tags": [],
        "error": None
    }

# Build graph
builder = StateGraph(NoteState)

# Add nodes
builder.add_node("classify", llm_classify)
builder.add_node("validate", validate)
builder.add_node("fallback", fallback_to_inbox)

# Add edges
builder.add_edge(START, "classify")
builder.add_edge("classify", "validate")

# Conditional routing after validation
def route_after_validation(state: NoteState) -> str:
    if state["error"] is None:
        return END
    elif state["retry_count"] < 2:
        return "classify"  # Retry
    else:
        return "fallback"  # Give up, use inbox

builder.add_conditional_edges(
    "validate",
    route_after_validation,
    {
        END: END,
        "classify": "classify",
        "fallback": "fallback"
    }
)
builder.add_edge("fallback", END)

# Compile
graph = builder.compile()
```

---

### Phase 3: Local Tracing & Logging

Implement local-first tracing:

```python
import json
from pathlib import Path
from datetime import datetime

class LocalTracer:
    """Local trace logger for QuickNote AI"""

    def __init__(self, trace_dir: Path = Path("~/.quicknote/traces")):
        self.trace_dir = trace_dir.expanduser()
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.trace_file = self.trace_dir / "classifications.jsonl"

    def log_classification(self, state: NoteState, execution_time: float):
        """Log a classification trace"""
        trace = {
            "timestamp": datetime.now().isoformat(),
            "input": state["raw_text"][:200],  # First 200 chars
            "output": {
                "title": state["title"],
                "folder": state["folder"],
                "tags": state["tags"],
            },
            "error": state.get("error"),
            "retry_count": state.get("retry_count", 0),
            "execution_time_ms": round(execution_time * 1000, 2),
            "model": "qwen3:4b-instruct"
        }

        with open(self.trace_file, "a") as f:
            f.write(json.dumps(trace) + "\n")

    def get_recent_traces(self, limit: int = 20):
        """Get recent classification traces"""
        if not self.trace_file.exists():
            return []

        traces = []
        with open(self.trace_file) as f:
            for line in f:
                traces.append(json.loads(line))

        return traces[-limit:]

# Usage with streaming
tracer = LocalTracer()

print("=== Classification Process ===")
for chunk in graph.stream(
    {
        "raw_text": note_text,
        "title": "",
        "folder": "",
        "tags": [],
        "first_sentence": "",
        "error": None,
        "retry_count": 0
    },
    stream_mode="updates"
):
    print(f"Step: {chunk}")

# Log final result
final_state = graph.invoke(input_state)
tracer.log_classification(final_state, execution_time)
```

---

## Streaming Modes for Debugging

### Development Mode: See Everything
```python
# Option 1: Stream updates (what changed)
for chunk in graph.stream(input, stream_mode="updates"):
    print(f"[UPDATE] {chunk}")

# Option 2: Stream full state (everything)
for chunk in graph.stream(input, stream_mode="values"):
    print(f"[STATE] {chunk}")

# Option 3: Debug mode (all details)
for chunk in graph.stream(input, stream_mode="debug"):
    print(f"[DEBUG] {chunk}")

# Option 4: Multiple modes
async for mode, chunk in graph.astream(
    input,
    stream_mode=["updates", "debug"]
):
    print(f"[{mode}] {chunk}")
```

### Production Mode: Minimal Logging
```python
# Just log final decisions
final_state = graph.invoke(input)
tracer.log_classification(final_state, time.time() - start)
```

---

## Optional: LangSmith for Development

**Use during development** to see nice UI, then disable for production:

```python
import os

# Development: Enable LangSmith tracing
if os.getenv("QUICKNOTE_DEBUG"):
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = "your-key"
    print("🔍 LangSmith tracing enabled (dev mode)")
else:
    os.environ["LANGSMITH_TRACING"] = "false"
    print("🏠 Local-only mode (production)")

# Run agent - traces go to LangSmith if enabled, otherwise just local
result = graph.invoke(input)
```

**To completely disable external dependencies**:
```bash
# Production .env
QUICKNOTE_DEBUG=false

# Development .env
QUICKNOTE_DEBUG=true
LANGSMITH_API_KEY=your-key-here
```

---

## Visualization During Development

```python
# View graph structure
from IPython.display import Image, display

# ASCII (terminal)
print(graph.get_graph().draw_ascii())

# Mermaid (paste into mermaid.live)
print(graph.get_graph().draw_mermaid())

# PNG (save to file)
png_data = graph.get_graph().draw_mermaid_png()
with open("note_classification_graph.png", "wb") as f:
    f.write(png_data)
```

---

## Integration with Existing Backend

Update `app-backend/llm.py` to use LangGraph:

```python
# app-backend/llm.py
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from typing import TypedDict
import asyncio

# State definition
class NoteState(TypedDict):
    raw_text: str
    title: str
    folder: str
    tags: list[str]
    first_sentence: str
    error: str | None

# Build graph (done once at startup)
llm = ChatOllama(
    base_url=LLM_BASE_URL,
    model=LLM_MODEL,
    temperature=0.2
)

graph = build_classification_graph(llm)  # Your graph builder

# FastAPI endpoint
async def classify(text: str) -> dict:
    """Classify note using LangGraph"""
    try:
        # Stream for debugging (optional in dev mode)
        if os.getenv("DEBUG"):
            async for chunk in graph.astream(
                {"raw_text": text, "title": "", "folder": "", "tags": [], "first_sentence": "", "error": None},
                stream_mode="updates"
            ):
                print(f"[CLASSIFY] {chunk}")

        # Get final result
        result = await graph.ainvoke({
            "raw_text": text,
            "title": "",
            "folder": "",
            "tags": [],
            "first_sentence": "",
            "error": None
        })

        return {
            "title": result["title"],
            "folder": result["folder"],
            "tags": result["tags"],
            "first_sentence": result["first_sentence"]
        }
    except Exception as e:
        # Fallback to inbox
        return {
            "title": text.split("\n")[0][:60],
            "folder": "inbox",
            "tags": [],
            "first_sentence": text.split("\n")[0]
        }
```

---

## Testing Strategy

### 1. Unit Test Individual Nodes
```python
def test_classify_node():
    state = {"raw_text": "Fix ALB + Cognito issue", ...}
    result = llm_classify(state)
    assert result["folder"] in VALID_FOLDERS
    assert len(result["tags"]) > 0
```

### 2. Integration Test Full Graph
```python
def test_full_classification():
    result = graph.invoke({
        "raw_text": "Review terraform modules for ECS deployment",
        "title": "", "folder": "", "tags": [], "first_sentence": "", "error": None
    })
    assert result["folder"] == "projects"
    assert "terraform" in result["tags"]
```

### 3. Test Fallback Behavior
```python
def test_fallback_on_invalid_output():
    # Mock LLM to return invalid folder
    result = graph.invoke({"raw_text": "test", ...})
    assert result["folder"] == "inbox"  # Should fall back
```

---

## File Structure

```
app-backend/
├── langgraph_agent.py        # LangGraph implementation
│   ├── NoteState (class)
│   ├── build_classification_graph()
│   └── ClassificationAgent (wrapper)
├── llm.py                     # Update to use langgraph_agent
├── tracer.py                  # LocalTracer implementation
├── models.py                  # Pydantic models (unchanged)
└── main.py                    # FastAPI routes (minimal changes)

tests/
├── test_langgraph_agent.py    # Unit tests for nodes
├── test_classification.py     # Integration tests
└── test_tracing.py           # Test local tracing
```

---

## Dependencies

Add to `requirements.txt`:
```
langchain-core>=0.3.76
langchain-ollama>=0.3.8
langgraph>=0.6.8
grandalf>=0.8              # For visualization (dev only)

# Optional: LangSmith (dev only)
langsmith>=0.4.31          # Only if QUICKNOTE_DEBUG=true
```

---

## Next Steps

1. ✅ **Phase 1**: Implement `create_react_agent` with tool calling
   - Test if Qwen3 can reliably call `classify_note` tool
   - Validate JSON parsing works

2. ✅ **Phase 2**: Build custom graph with validation & retry
   - Add nodes: classify → validate → fallback
   - Add conditional edges for retry logic
   - Test edge cases

3. ✅ **Phase 3**: Add local tracing
   - Implement `LocalTracer` class
   - Save traces to `~/.quicknote/traces/`
   - Build simple trace viewer (optional)

4. ✅ **Phase 4**: Integrate with FastAPI backend
   - Update `llm.py` to use LangGraph
   - Keep existing API interface unchanged
   - Add debug mode with streaming

5. ✅ **Phase 5**: Production testing
   - Disable LangSmith
   - Test fully offline
   - Validate performance (should be fast for 4B model)

---

## Success Criteria

- ✅ Note classification works with local Qwen3 model
- ✅ Fallback to inbox on errors
- ✅ Full offline operation (no external API calls)
- ✅ Local trace logging for debugging
- ✅ Clear visibility into classification decisions
- ✅ Fast response time (<2s for classification)
- ✅ Visualization available for development

---

## Privacy & Security

- ✅ All data stays local (notes never leave machine)
- ✅ LLM runs locally (Ollama)
- ✅ Traces stored locally (`~/.quicknote/traces/`)
- ✅ Optional LangSmith can be disabled (production default)
- ✅ No external dependencies in production

---

## Performance Targets

- Classification: <2 seconds (4B model)
- Retry logic: Max 3 attempts, <6 seconds total
- Streaming overhead: Negligible
- Local trace logging: <10ms per entry

---

## Comparison: Prebuilt vs Custom Graph

| Feature | `create_react_agent` | Custom `StateGraph` |
|---------|---------------------|---------------------|
| Setup time | 5 minutes | 30 minutes |
| Control | Limited | Full control |
| Retry logic | Basic | Custom |
| Validation | None | Custom |
| Fallback | None | Custom |
| Complexity | Low | Medium |
| **Recommendation** | **Start here** | Migrate if needed |

---

## Summary

**LangGraph gives us**:
- ✅ Production-ready agent framework
- ✅ Built-in streaming for local tracing
- ✅ Graph visualization for debugging
- ✅ State management out of the box
- ✅ Optional LangSmith (dev only)
- ✅ Full offline operation maintained
- ✅ Clear visibility into agent decisions

**No compromises on**:
- ✅ Local-first architecture
- ✅ Privacy (all data stays local)
- ✅ Offline capability
- ✅ No mandatory external services
