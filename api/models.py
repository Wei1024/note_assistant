"""
GraphRAG Note Assistant - Pydantic Models
"""
from pydantic import BaseModel
from typing import List, Optional


# Input Models
class ClassifyRequest(BaseModel):
    """Request to capture a note"""
    text: str
    context_hint: Optional[str] = None


# GraphRAG Response Models
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


# Phase 4: Search & Retrieval Models

class SearchResultModel(BaseModel):
    """Single search result with hybrid scoring"""
    note_id: str
    title: str
    snippet: str
    score: float
    fts_score: float
    vector_score: float
    episodic: EpisodicMetadata
    file_path: str
    text_preview: str


class ExpandedNodeModel(BaseModel):
    """Graph-expanded result (contextual neighbor)"""
    note_id: str
    title: str
    text_preview: str
    relation: str  # Edge type: semantic, entity_link, tag_link
    hop_distance: int
    relevance_score: float
    connected_to: List[str]  # Seed note IDs this connects to


class ClusterSummaryModel(BaseModel):
    """Cluster context for search results"""
    cluster_id: int
    title: str
    summary: str
    size: int


class SearchResponse(BaseModel):
    """Response from /search endpoint"""
    query: str
    primary_results: List[SearchResultModel]
    expanded_results: List[ExpandedNodeModel]
    cluster_summaries: List[ClusterSummaryModel]
    total_results: int
    execution_time_ms: int


class SimilarityResponse(BaseModel):
    """Response from /search/similar endpoint"""
    query_note_id: str
    similar_notes: List[SearchResultModel]
    total: int
