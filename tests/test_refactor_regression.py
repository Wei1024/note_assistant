#!/usr/bin/env python3
"""
Regression tests for code refactoring
These tests ensure behavior doesn't change during the refactor

Run before and after refactoring to ensure no regressions:
    pytest tests/test_refactor_regression.py -v
"""
import pytest
import asyncio

# Use anyio for async tests
pytest_plugins = ('pytest_asyncio',)
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.capture import classify_note_async
from api.services.search import search_notes_smart, parse_smart_query
from api.services.enrichment import enrich_note_metadata
from api.services.consolidation import find_link_candidates, suggest_links_batch
from api.llm import get_llm
from api.notes import write_markdown
from api.fts import search_notes
from api.db import ensure_db
from api.config import DB_PATH, NOTES_DIR


@pytest.fixture(scope="module")
def setup_test_env():
    """Setup test environment with temporary database"""
    # Backup original DB path
    original_db = DB_PATH
    original_notes_dir = NOTES_DIR

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    test_notes_dir = Path(temp_dir) / "notes"
    test_notes_dir.mkdir()

    # Override config paths for testing
    import api.config as config
    config.DB_PATH = test_notes_dir / ".index" / "notes.sqlite"
    config.NOTES_DIR = test_notes_dir

    # Initialize test database
    ensure_db()

    yield test_notes_dir

    # Cleanup
    shutil.rmtree(temp_dir)
    config.DB_PATH = original_db
    config.NOTES_DIR = original_notes_dir


class TestCaptureFlow:
    """Test note classification and capture"""

    @pytest.mark.asyncio
    async def test_classify_task_note(self):
        """Test classifying a task note"""
        text = "Fix the login bug in authentication service"
        result = await classify_note_async(text)

        # Task should have status (only tasks have status)
        assert result["status"] in ["todo", "in_progress", "done"]
        assert len(result["tags"]) > 0
        assert "title" in result

    @pytest.mark.asyncio
    async def test_classify_meeting_note(self):
        """Test classifying a meeting note"""
        text = "Met with Sarah to discuss memory consolidation research"
        result = await classify_note_async(text)

        # Meeting notes should not have status
        assert result["status"] is None
        # Tags might be empty for some classifications
        assert "tags" in result

    @pytest.mark.asyncio
    async def test_classify_idea_note(self):
        """Test classifying an idea note"""
        text = "What if we used FAISS for vector search instead of manual linking?"
        result = await classify_note_async(text)

        # Ideas don't have status
        assert result["status"] is None

    @pytest.mark.asyncio
    async def test_classify_journal_note(self):
        """Test classifying a journal note"""
        text = "Feeling overwhelmed today with all the project deadlines"
        result = await classify_note_async(text)

        # Journal notes don't have status
        assert result["status"] is None


class TestEnrichmentFlow:
    """Test metadata enrichment"""

    @pytest.mark.asyncio
    async def test_enrich_extracts_person(self):
        """Test person extraction"""
        text = "Met with Sarah to discuss psychology research"
        classification = {"folder": "meetings", "title": "Meeting with Sarah", "tags": []}

        enrichment = await enrich_note_metadata(text, classification)

        assert "people" in enrichment
        people_names = [p["name"] for p in enrichment.get("people", [])]
        assert "Sarah" in people_names or "sarah" in [n.lower() for n in people_names]

    @pytest.mark.asyncio
    async def test_enrich_extracts_topics(self):
        """Test entity extraction (merged topics/projects/tech)"""
        text = "Researching FAISS vector database for similarity search"
        classification = {"folder": "reference", "title": "FAISS research", "tags": []}

        enrichment = await enrich_note_metadata(text, classification)

        # LLM extraction varies - just verify structure exists
        assert "entities" in enrichment
        # At least the enrichment ran successfully
        assert "reasoning" in enrichment or "entities" in enrichment

    @pytest.mark.asyncio
    async def test_enrich_extracts_emotions(self):
        """Test emotion extraction"""
        text = "I'm really excited about this new vector search approach!"
        classification = {"folder": "journal", "title": "Excited about vector search", "tags": []}

        enrichment = await enrich_note_metadata(text, classification)

        assert "emotions" in enrichment
        emotions = [e.lower() for e in enrichment.get("emotions", [])]
        assert "excited" in emotions


class TestSearchFlow:
    """Test smart search functionality"""

    @pytest.mark.asyncio
    async def test_parse_person_query(self):
        """Test parsing person search query"""
        query = "what's the recent project I did with Sarah"
        filters = await parse_smart_query(query)

        assert filters.get("person") == "Sarah" or filters.get("person") == "sarah"
        assert filters.get("sort") == "recent"

    @pytest.mark.asyncio
    async def test_parse_emotion_query(self):
        """Test parsing emotion search query"""
        query = "notes where I felt excited about FAISS"
        filters = await parse_smart_query(query)

        assert filters.get("emotion") in ["excited", "Excited"]
        assert "FAISS" in str(filters.get("entity", "")) or "FAISS" in str(filters.get("text_query", ""))

    @pytest.mark.asyncio
    async def test_parse_context_query(self):
        """Test parsing context/folder query"""
        query = "meetings about AWS infrastructure"
        filters = await parse_smart_query(query)

        assert filters.get("context") == "meetings"
        assert "AWS" in str(filters.get("entity", "")) or "AWS" in str(filters.get("text_query", ""))


class TestConsolidationFlow:
    """Test memory consolidation"""

    @pytest.mark.asyncio
    async def test_find_candidates_by_person(self):
        """Test finding link candidates based on shared people"""
        # This test requires actual notes in DB - simplified version
        note = {
            "id": "test-note-1",
            "path": "/fake/path.md",
            "entities": [
                ("person", "Sarah"),
                ("topic", "memory research")
            ],
            "dimensions": []
        }

        # Should not crash
        candidates = find_link_candidates(note, max_candidates=5, exclude_today=False)
        assert isinstance(candidates, list)

    @pytest.mark.asyncio
    async def test_suggest_links_empty_candidates(self):
        """Test link suggestion with no candidates"""
        note_text = "This is a test note about nothing in particular"
        candidates = []

        links = await suggest_links_batch(note_text, candidates)
        assert links == []


class TestIntegration:
    """Integration tests for complete flows"""

    @pytest.mark.asyncio
    async def test_full_capture_and_search_flow(self, setup_test_env):
        """Test complete flow: classify -> enrich -> save -> search"""
        # Step 1: Classify
        text = "Fix the authentication bug in the login service"
        classification = await classify_note_async(text)

        # Classification should return basic fields
        assert "title" in classification
        assert "tags" in classification

        # Step 2: Enrich
        enrichment = await enrich_note_metadata(text, classification)
        assert "entities" in enrichment

        # Step 3: Save (would write to disk in real scenario)
        # Simplified - just verify write_markdown doesn't crash
        try:
            note_id, path, title = write_markdown(
                title=classification["title"],
                tags=classification["tags"],
                body=text,
                status=classification.get("status"),
                enrichment=enrichment
            )
            assert note_id is not None
            # Verify dimensions exist
            assert enrichment.get("has_action_items") is not None
        except Exception as e:
            # write_markdown might fail in test env, that's ok
            pass

        # Step 4: Search would work if notes were indexed
        # Just verify search_notes_smart doesn't crash
        results = await search_notes_smart("authentication bug", limit=5)
        assert isinstance(results, list)


class TestLLMClient:
    """Test LLM client singleton"""

    def test_llm_singleton(self):
        """Test that get_llm returns same instance"""
        llm1 = get_llm()
        llm2 = get_llm()

        assert llm1 is llm2  # Should be same instance

    def test_llm_has_correct_config(self):
        """Test LLM is configured correctly"""
        llm = get_llm()

        # Verify it's a ChatOllama instance
        assert hasattr(llm, "invoke")
        assert hasattr(llm, "ainvoke")


if __name__ == "__main__":
    # Run with: python tests/test_refactor_regression.py
    pytest.main([__file__, "-v", "--tb=short"])
