from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import ClassifyRequest, ClassifyResponse, SearchRequest, SearchHit
from .classification_tool import classify_note
from .notes import write_markdown
from .fts import ensure_db, search_notes
from .config import BACKEND_HOST, BACKEND_PORT, LLM_MODEL

app = FastAPI(title="QuickNote Backend", version="0.2.0")

# CORS for Tauri
app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://localhost", "http://127.0.0.1"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    ensure_db()
    print(f"\n🚀 QuickNote Backend Started")
    print(f"🤖 Using Model: {LLM_MODEL}\n")

@app.get("/health")
async def health():
    return {"status": "ok", "model": LLM_MODEL}

@app.post("/classify_and_save", response_model=ClassifyResponse)
async def classify_and_save(req: ClassifyRequest):
    """Classify note using LangGraph and save to disk"""
    try:
        # Use LangGraph tool for classification
        result = classify_note.invoke({"raw_text": req.text})

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
    """Search notes using FTS5"""
    results = search_notes(req.query, req.limit)
    return [SearchHit(**r) for r in results]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)
