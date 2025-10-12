from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache
from .models import ClassifyRequest, ClassifyResponse, SearchRequest, SearchHit
from .capture_service import classify_note_async
from .search_service import search_notes_smart
from .notes import write_markdown
from .fts import ensure_db, search_notes
from .config import BACKEND_HOST, BACKEND_PORT, LLM_MODEL

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    set_llm_cache(InMemoryCache())
    ensure_db()
    print(f"\n🚀 QuickNote Backend Started")
    print(f"🤖 Using Model: {LLM_MODEL}")
    print(f"💾 LLM Cache: Enabled (InMemory)")
    print(f"🔌 Connection Pooling: Enabled (10 keepalive)\n")
    yield
    # Shutdown
    print("\n👋 QuickNote Backend Shutting Down\n")

app = FastAPI(title="QuickNote Backend", version="0.2.0", lifespan=lifespan)

# CORS for Tauri
app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://localhost", "http://127.0.0.1"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok", "model": LLM_MODEL}

@app.post("/classify_and_save", response_model=ClassifyResponse)
async def classify_and_save(req: ClassifyRequest):
    """Classify note using direct LLM (fast path) and save to disk"""
    try:
        # Async LLM classification for better concurrency
        result = await classify_note_async(req.text)

        # Save to disk
        note_id, filepath, title, folder = write_markdown(
            title=result["title"],
            folder=result["folder"],
            tags=result["tags"],
            body=req.text
        )

        return ClassifyResponse(
            title=title,
            folder=folder,
            tags=result["tags"],
            first_sentence=result["first_sentence"],
            path=filepath
        )

    except Exception as e:
        # Fallback to inbox on any error
        first_line = req.text.split("\n")[0][:60]
        note_id, filepath, title, folder = write_markdown(
            folder="inbox",
            title=first_line,
            tags=[],
            body=req.text
        )
        return ClassifyResponse(
            title=title,
            folder="inbox",
            tags=[],
            first_sentence=first_line,
            path=filepath
        )

@app.post("/save_inbox", response_model=ClassifyResponse)
async def save_inbox(req: ClassifyRequest):
    """Save directly to inbox without classification"""
    first_line = req.text.split("\n")[0][:60]

    note_id, filepath, title, folder = write_markdown(
        folder="inbox",
        title=first_line,
        tags=[],
        body=req.text
    )

    return ClassifyResponse(
        title=title,
        folder="inbox",
        tags=[],
        first_sentence=first_line,
        path=filepath
    )

@app.post("/search", response_model=list[SearchHit])
async def search(req: SearchRequest):
    """Search notes using FTS5 (direct keyword match)"""
    results = search_notes(req.query, req.limit)
    return [SearchHit(**r) for r in results]

@app.post("/search_fast", response_model=list[SearchHit])
async def search_fast(req: SearchRequest):
    """Fast natural language search - 70% faster than agent-based

    Uses direct query rewriting + FTS5, no ReAct agent overhead.
    Optimized for production with async processing and connection pooling.

    Example queries:
    - "what sport did I watch?"
    - "notes about AWS"
    - "meeting with Sarah"
    """
    results = await search_notes_smart(req.query, req.limit)
    return [SearchHit(**r) for r in results]

# EXPERIMENTAL ENDPOINTS (not in production use)
# These are commented out - see future_agent.py for LangGraph implementations
# Uncomment and import from future_agent if you want to experiment with agents

# @app.post("/classify_with_trace")
# async def classify_with_trace(req: ClassifyRequest):
#     """Classify note with full agent reasoning trace"""
#     from .future_agent import create_classification_agent
#     agent = create_classification_agent()
#     steps = []
#     final_result = None
#     try:
#         for chunk in agent.stream(
#             {"messages": [("user", f"Classify this note: {req.text}")]},
#             stream_mode="values"
#         ):
#             if "messages" in chunk:
#                 last_msg = chunk["messages"][-1]
#                 if hasattr(last_msg, "content"):
#                     steps.append({"type": "thought", "content": last_msg.content})
#                 if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
#                     for tool_call in last_msg.tool_calls:
#                         steps.append({"type": "tool_call", "name": tool_call["name"], "args": tool_call["args"]})
#                 if last_msg.type == "tool":
#                     steps.append({"type": "tool_response", "content": last_msg.content})
#         from .capture_service import classify_note
#         result = classify_note.invoke({"raw_text": req.text})
#         final_result = result
#         note_id, filepath, title, folder = write_markdown(
#             title=result["title"], folder=result["folder"], tags=result["tags"], body=req.text
#         )
#         final_result["saved"] = True
#         final_result["path"] = filepath
#     except Exception as e:
#         steps.append({"type": "error", "content": str(e)})
#         first_line = req.text.split("\n")[0][:60]
#         note_id, filepath, title, folder = write_markdown(
#             folder="inbox", title=first_line, tags=[], body=req.text
#         )
#         final_result = {
#             "title": title, "folder": "inbox", "tags": [],
#             "first_sentence": first_line, "error": str(e),
#             "saved": True, "path": filepath
#         }
#     return {"steps": steps, "final": final_result, "note_text": req.text}

# @app.post("/search_with_agent")
# async def search_with_agent(req: SearchRequest):
#     """Search notes with agent-powered natural language understanding"""
#     from .future_agent import create_search_agent
#     agent = create_search_agent()
#     steps = []
#     results = []
#     final_answer = None
#     try:
#         for chunk in agent.stream(
#             {"messages": [("user", f"Search my notes for: {req.query}")]},
#             stream_mode="values"
#         ):
#             if "messages" in chunk:
#                 last_msg = chunk["messages"][-1]
#                 if hasattr(last_msg, "content") and last_msg.content:
#                     steps.append({"type": "thought", "content": last_msg.content})
#                     if hasattr(last_msg, "type") and last_msg.type == "ai":
#                         final_answer = last_msg.content
#                 if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
#                     for tool_call in last_msg.tool_calls:
#                         steps.append({"type": "tool_call", "name": tool_call["name"], "args": tool_call["args"]})
#                 if last_msg.type == "tool":
#                     steps.append({"type": "tool_response", "content": last_msg.content})
#                     try:
#                         import json
#                         tool_results = json.loads(last_msg.content) if isinstance(last_msg.content, str) else last_msg.content
#                         if isinstance(tool_results, list) and tool_results:
#                             results = tool_results
#                     except:
#                         pass
#     except Exception as e:
#         steps.append({"type": "error", "content": str(e)})
#     return {"steps": steps, "results": results, "final_answer": final_answer, "query": req.query}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)
