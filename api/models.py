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

# Phase 3.1: Multi-dimensional query models
class DimensionSearchRequest(BaseModel):
    dimension_type: str  # context, emotion, time_reference
    dimension_value: str
    query_text: Optional[str] = None  # Optional FTS5 combination

class EntitySearchRequest(BaseModel):
    entity_type: str  # person, topic, project, tech
    entity_value: str
    context: Optional[str] = None  # Optional folder filter

class PersonSearchRequest(BaseModel):
    name: str
    context: Optional[str] = None  # Optional folder filter

class GraphSearchRequest(BaseModel):
    start_note_id: str
    depth: int = 2
    relationship_type: Optional[str] = None  # Optional: related, spawned, references, contradicts

class GraphData(BaseModel):
    nodes: List[dict]
    edges: List[dict]
