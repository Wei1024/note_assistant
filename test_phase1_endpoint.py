"""
Phase 1 Test Endpoint
Minimal endpoint to test episodic layer extraction
"""
import asyncio
from api.services.episodic import extract_episodic_metadata


async def test_episodic_extraction():
    """Test the new episodic extraction on sample notes"""

    test_notes = [
        "I have a dental appointment on October 25 at 5 pm",
        "Met with Sarah today to discuss memory consolidation research",
        "Call Mom tomorrow at 2pm",
        "Python async/await patterns: Use asyncio.gather() for concurrent operations",
    ]

    print("="*80)
    print("PHASE 1 - EPISODIC LAYER TEST")
    print("="*80)

    for i, note in enumerate(test_notes, 1):
        print(f"\n[{i}] Testing: {note[:60]}...")
        print("-" * 80)

        metadata = await extract_episodic_metadata(note, "2025-10-20 00:00 PST")

        print(f"  Title: {metadata['title']}")
        print(f"  WHO:   {metadata['who']}")
        print(f"  WHAT:  {metadata['what']}")
        print(f"  WHERE: {metadata['where']}")
        print(f"  WHEN:  {[t['original'] for t in metadata['when']]}")
        print(f"  Tags:  {metadata['tags']}")


if __name__ == "__main__":
    asyncio.run(test_episodic_extraction())
