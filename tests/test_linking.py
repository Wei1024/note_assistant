#!/usr/bin/env python3
"""
Test linking system with detailed LLM decision output
"""
import asyncio
import json
from api.consolidation_service import (
    get_notes_created_today,
    find_link_candidates,
    suggest_links_batch
)
from api.capture_service import get_llm


async def test_linking_with_debug():
    """Test linking and show LLM's reasoning"""

    notes = get_notes_created_today()

    if not notes:
        print("❌ No notes created today. Create some test notes first.")
        return

    print(f"📝 Found {len(notes)} notes created today\n")
    print("=" * 80)

    for i, note in enumerate(notes, 1):
        print(f"\n🔍 Testing Note {i}/{len(notes)}")
        print(f"ID: {note['id']}")
        print(f"Path: {note['path']}")
        print(f"Body: {note['body'][:200]}...")
        print()

        # Find candidates with tag-based search
        candidates = find_link_candidates(note, max_candidates=15, exclude_today=True)

        print(f"🎯 Found {len(candidates)} candidates:")
        for j, c in enumerate(candidates, 1):
            note_id = c.get('id', 'unknown')
            title = c.get('title', 'Untitled')
            match_reason = c.get('match_reason', 'unknown')
            snippet = c.get('snippet', '')

            print(f"  {j}. [{note_id[:25]}...] {title[:60]}")
            print(f"     Match reason: {match_reason}")
            print(f"     Snippet: {snippet[:100]}...")
            print()

        if not candidates:
            print("  ⚠️  No candidates found - skipping LLM analysis\n")
            continue

        # Show LLM prompt
        print("📤 LLM Prompt Preview:")
        print("-" * 80)
        candidates_text = "\n".join([
            f"{i+1}. [{c['id']}] {c['title']}\n   Snippet: {c['snippet']}\n   Match: {c['match_reason']}"
            for i, c in enumerate(candidates[:3])
        ])
        print(f"NEW NOTE:\n{note['body'][:150]}...\n")
        print(f"EXISTING NOTES (showing first 3):\n{candidates_text}\n")
        print("-" * 80)

        # Call LLM and show response
        print("\n🤖 Calling LLM for link analysis...")
        llm = get_llm()

        # Build full prompt (same as suggest_links_batch)
        candidates_full = "\n".join([
            f"{i+1}. [{c['id']}] {c['title']}\n   Snippet: {c['snippet']}\n   Match: {c['match_reason']}"
            for i, c in enumerate(candidates)
        ])

        prompt = f"""You are a knowledge graph linker. Analyze connections between notes.

NEW NOTE:
{note['body']}

EXISTING NOTES:
{candidates_full}

Task: Which existing notes should link to the new note? Analyze ALL at once.

Return ONLY valid JSON array:
[
  {{"id": "note-id-from-above", "link_type": "related|spawned|references|contradicts", "reason": "specific shared concept"}},
  ...
]

Link Types:
- **related**: Discusses same topic/concept
- **spawned**: New note is follow-up/action from old note
- **references**: New note builds on old note's idea
- **contradicts**: New note challenges old note's conclusion

Rules:
1. Only include if STRONG connection (shared specific concept/person/project/decision)
2. Reason must be specific (not "both mention topics")
3. Max 5 links total (prioritize strongest)
4. Skip if connection is weak or vague
5. Must use exact note ID from brackets above

JSON:"""

        response = await llm.ainvoke(prompt)

        print("\n📥 LLM Raw Response:")
        print("-" * 80)
        print(response.content)
        print("-" * 80)

        # Parse and validate
        try:
            result = json.loads(response.content)
            print(f"\n✅ LLM suggested {len(result)} links:")

            if not result:
                print("  ⚠️  No links suggested (all connections too weak)")

            for link in result:
                print(f"\n  📎 Link: {link.get('link_type', 'unknown').upper()}")
                print(f"     To: [{link.get('id', 'unknown')[:25]}...]")
                print(f"     Reason: {link.get('reason', 'no reason provided')}")

                # Validate
                valid_ids = {c["id"] for c in candidates}
                if link.get("id") not in valid_ids:
                    print(f"     ❌ Invalid ID (not in candidates)")

                # Check heuristic filtering
                reason_lower = link.get("reason", "").lower()
                vague_keywords = ["might be", "could be", "possibly", "both mention", "similar"]
                if any(kw in reason_lower for kw in vague_keywords):
                    print(f"     ⚠️  Would be filtered (vague reason)")
                else:
                    print(f"     ✅ Passes heuristic filter")

        except json.JSONDecodeError as e:
            print(f"\n❌ Failed to parse LLM response as JSON: {e}")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_linking_with_debug())
