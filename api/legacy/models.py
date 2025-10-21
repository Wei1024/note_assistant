from pydantic import BaseModel, Field
from typing import List, Optional

class ClassifyRequest(BaseModel):
    text: str
    context_hint: Optional[str] = None

# GraphRAG Models
class TimeReference(BaseModel):
    """Extracted time reference with parsed datetime"""
    original: str  # Original text (e.g., "tomorrow at 2pm")
    parsed: Optional[str] = None  # ISO datetime if parseable
    type: str  # relative, absolute, or unparsed

class EpisodicMetadata(BaseModel):
    """Episodic layer metadata (WHO/WHAT/WHEN/WHERE)"""
    who: List[str] = []  # People, organizations
    what: List[str] = []  # Concepts, topics, entities
    where: List[str] = []  # Locations (physical/virtual/contextual)
    when: List[TimeReference] = []  # Time references
    tags: List[str] = []  # Thematic categories

class CaptureNoteResponse(BaseModel):
    """Response from /capture_note endpoint (GraphRAG)"""
    note_id: str
    title: str
    episodic: EpisodicMetadata
    path: str

# Legacy Models (deprecated - for backward compatibility with old endpoints)
class DimensionFlags(BaseModel):
    """DEPRECATED: Multi-dimensional boolean flags (old system)"""
    has_action_items: bool = False
    is_social: bool = False
    is_emotional: bool = False
    is_knowledge: bool = False
    is_exploratory: bool = False

class ClassifyResponse(BaseModel):
    """DEPRECATED: Old classification response (for /classify_and_save legacy endpoint)"""
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

class ConsolidateBatchRequest(BaseModel):
    note_ids: List[str]

class ConsolidateBatchResponse(BaseModel):
    notes_processed: int
    links_created: int
    notes_with_links: int
    started_at: str
    completed_at: str

class PersonEntity(BaseModel):
    name: str
    role: Optional[str] = None
    relation: Optional[str] = None

class ConceptEntity(BaseModel):
    concept: str
    frequency: int

class TimeReference(BaseModel):
    type: Optional[str] = None
    datetime: Optional[str] = None
    description: Optional[str] = None

class ClusterSummary(BaseModel):
    cluster_id: int
    size: int
    theme: str
    people: List[PersonEntity]
    key_concepts: List[ConceptEntity]
    emotions: List[str]
    time_references: List[TimeReference]
    dimensions: DimensionFlags
    action_count: int

class ClusteredGraphData(BaseModel):
    nodes: List[dict]
    edges: List[dict]
    clusters: List[ClusterSummary]
