"""Repository Layer - Data Access Objects
Clean interfaces for database operations
"""
from .notes_repo import NotesRepository
from .graph_repo import GraphRepository
from .search_repo import SearchRepository

# Singleton instances
notes_repo = NotesRepository()
graph_repo = GraphRepository()
search_repo = SearchRepository()

__all__ = ["notes_repo", "graph_repo", "search_repo", "NotesRepository", "GraphRepository", "SearchRepository"]
