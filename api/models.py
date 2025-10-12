from pydantic import BaseModel, Field
from typing import List, Optional

class ClassifyRequest(BaseModel):
    text: str
    context_hint: Optional[str] = None

class ClassifyResponse(BaseModel):
    title: str
    folder: str
    tags: List[str]
    first_sentence: str
    path: str

class SearchRequest(BaseModel):
    query: str
    limit: int = 20
    status: Optional[str] = None  # Filter by status: todo, in_progress, done

class SearchHit(BaseModel):
    path: str
    snippet: str
    score: float = 0.0

class UpdateStatusRequest(BaseModel):
    note_path: str
    status: str  # todo, in_progress, done, or null to remove
