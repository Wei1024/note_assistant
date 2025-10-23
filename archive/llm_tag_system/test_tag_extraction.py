"""
Test script for new tag extraction with three-axis taxonomy
"""
import asyncio
from api.services.episodic import _extract_tags_llm, _extract_entities_llm

# Sample notes to test
SAMPLE_NOTES = [
    "Met with Sarah and Tom today to discuss the Q4 roadmap for our GraphRAG project",
    "TODO: Research vector databases for the new search feature",
    "Grocery shopping list: milk, eggs, bread, apples",
    "Sprint retrospective - team discussed what went well and what to improve",
    "Had a great insight during my morning walk about improving work-life balance",
    "Booked dentist appointment for next Tuesday at 2pm",
]

async def test_extraction():
    print("=" * 60)
    print("Testing New Tag Extraction (Three-Axis Taxonomy)")
    print("=" * 60)
    print()

    for i, note in enumerate(SAMPLE_NOTES, 1):
        print(f"Test {i}:")
        print(f"Note: {note}")
        print()

        # Extract tags
        try:
            tags = await _extract_tags_llm(note)
            print(f"✓ Tags: {tags}")
        except Exception as e:
            print(f"✗ Tag extraction failed: {e}")

        # Extract entities
        try:
            entities = await _extract_entities_llm(note, "2025-10-22 00:00 PST")
            print(f"✓ Entities:")
            print(f"  WHO: {entities.get('who', [])}")
            print(f"  WHAT: {entities.get('what', [])}")
            print(f"  WHERE: {entities.get('where', [])}")
            print(f"  TITLE: {entities.get('title', '')}")
        except Exception as e:
            print(f"✗ Entity extraction failed: {e}")

        print()
        print("-" * 60)
        print()

if __name__ == "__main__":
    asyncio.run(test_extraction())
