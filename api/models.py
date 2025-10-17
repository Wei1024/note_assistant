from pydantic import BaseModel, Field
from typing import List, Optional

class ClassifyRequest(BaseModel):
    text: str
    context_hint: Optional[str] = None

class DimensionFlags(BaseModel):
    """Multi-dimensional boolean flags representing note characteristics"""
    has_action_items: bool = False
    is_social: bool = False
    is_emotional: bool = False
    is_knowledge: bool = False
    is_exploratory: bool = False

class ClassifyResponse(BaseModel):
    title: str
    dimensions: DimensionFlags
    tags: List[str]
    path: str

class SearchRequest(BaseModel):
    query: str
    limit: int = 20
    status: Optional[str] = None  # Filter by status: todo, in_progress, done

class SearchHit(BaseModel):
    path: str
    snippet: str
    score: float = 0.0
    metadata: Optional[dict] = None  # Optional metadata (match_type, search_note, dimensions, created, title)

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
    context: Optional[str] = None  # Optional dimension context filter (tasks, meetings, ideas, etc.)

class PersonSearchRequest(BaseModel):
    name: str
    context: Optional[str] = None  # Optional dimension context filter (tasks, meetings, ideas, etc.)

class GraphSearchRequest(BaseModel):
    start_note_id: str
    depth: int = 2
    relationship_type: Optional[str] = None  # Optional: related, spawned, references, contradicts

class GraphData(BaseModel):
    nodes: List[dict]
    edges: List[dict]

class SynthesisRequest(BaseModel):
    query: str
    limit: int = 10

class SynthesisResponse(BaseModel):
    query: str
    summary: str
    notes_analyzed: int
    search_results: List[SearchHit]
