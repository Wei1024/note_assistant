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
