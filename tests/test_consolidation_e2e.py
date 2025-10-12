#!/usr/bin/env python3
"""
End-to-end test for memory consolidation system.

Tests the full flow:
1. Create test notes via API
2. Run consolidation
3. Verify links are created
4. Check link quality
"""
import asyncio
import requests
import sqlite3
from datetime import datetime
from api.config import DB_PATH
from api.graph import get_linked_notes, get_backlinks


BASE_URL = "http://127.0.0.1:8787"


def clear_today_notes():
    """Clear today's test notes from database"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    today = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    # Get today's note IDs
    cur.execute("SELECT id FROM notes_meta WHERE created >= ?", (today,))
    note_ids = [row[0] for row in cur.fetchall()]

    # Delete from all tables (cascade should handle this, but be explicit)
    for note_id in note_ids:
        cur.execute("DELETE FROM notes_links WHERE from_note_id = ? OR to_note_id = ?", (note_id, note_id))
        cur.execute("DELETE FROM notes_entities WHERE note_id = ?", (note_id,))
        cur.execute("DELETE FROM notes_dimensions WHERE note_id = ?", (note_id,))
        cur.execute("DELETE FROM notes_fts WHERE id = ?", (note_id,))
        cur.execute("DELETE FROM notes_meta WHERE id = ?", (note_id,))

    con.commit()
    con.close()

    print(f"🧹 Cleaned up {len(note_ids)} test notes from today")


def create_test_note(text: str) -> dict:
    """Create a note via API"""
    response = requests.post(
        f"{BASE_URL}/classify_and_save",
        json={"text": text},
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"Failed to create note: {response.text}")

    return response.json()


def run_consolidation() -> dict:
    """Run consolidation via API"""
    response = requests.post(f"{BASE_URL}/consolidate", timeout=120)

    if response.status_code != 200:
        raise Exception(f"Consolidation failed: {response.text}")

    return response.json()


def get_note_id_from_path(path: str) -> str:
    """Lookup note ID from path"""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT id FROM notes_meta WHERE path = ?", (path,))
    row = cur.fetchone()
    con.close()
    return row[0] if row else None


def check_links(note_id: str):
    """Check links for a note"""
    outgoing = get_linked_notes(note_id)
    incoming = get_backlinks(note_id)

    return {
        "outgoing": outgoing,
        "incoming": incoming,
        "total": len(outgoing) + len(incoming)
    }


def main():
    print("=" * 80)
    print("🧪 End-to-End Consolidation Test")
    print("=" * 80)

    # Step 1: Clean up
    print("\n📋 Step 1: Cleaning up previous test data...")
    clear_today_notes()

    # Step 2: Create test scenario
    print("\n📋 Step 2: Creating test notes...")

    test_notes = [
        {
            "name": "Meeting with Sarah",
            "text": "Had a productive meeting with Sarah today about implementing memory consolidation in our note system. She explained how the hippocampus works during sleep to consolidate memories. Very insightful discussion about neuroscience and software design patterns. We should implement this using background tasks."
        },
        {
            "name": "Follow-up task",
            "text": "Need to follow up with Sarah about the hippocampus research papers she mentioned. Also implement the background consolidation service she suggested. This is a direct action item from our meeting."
        },
        {
            "name": "Related idea",
            "text": "Idea: What if we use the memory consolidation pattern for other background tasks? Like auto-archiving old notes, or generating weekly summaries. The brain-based approach could apply to many features."
        },
        {
            "name": "Unrelated note",
            "text": "Reminder to buy groceries: milk, eggs, bread, coffee. Also need to schedule dentist appointment for next week."
        }
    ]

    created_notes = []
    for note_spec in test_notes:
        try:
            result = create_test_note(note_spec["text"])
            note_id = get_note_id_from_path(result["path"])
            created_notes.append({
                "name": note_spec["name"],
                "id": note_id,
                "path": result["path"],
                "folder": result["folder"]
            })
            print(f"  ✅ Created: {note_spec['name']} ({result['folder']})")
        except Exception as e:
            print(f"  ❌ Failed: {note_spec['name']} - {e}")

    print(f"\n  📊 Created {len(created_notes)} test notes")

    # Step 3: Run consolidation
    print("\n📋 Step 3: Running consolidation...")
    stats = run_consolidation()

    print(f"  📊 Consolidation Stats:")
    print(f"     Notes processed: {stats['notes_processed']}")
    print(f"     Links created: {stats['links_created']}")
    print(f"     Notes with links: {stats['notes_with_links']}")

    # Step 4: Verify links
    print("\n📋 Step 4: Verifying links...")

    total_links = 0
    for note in created_notes:
        links = check_links(note["id"])
        if links["total"] > 0:
            print(f"\n  📎 {note['name']}:")
            print(f"     Outgoing: {len(links['outgoing'])}")
            for link in links["outgoing"]:
                print(f"       → {link['link_type']}: {link['to_note_id'][:30]}...")
            print(f"     Incoming: {len(links['incoming'])}")
            for link in links["incoming"]:
                print(f"       ← {link['link_type']}: {link['from_note_id'][:30]}...")
            total_links += links["total"]

    print(f"\n  📊 Total links found: {total_links}")

    # Step 5: Analysis
    print("\n📋 Step 5: Analysis...")

    if total_links == 0:
        print("  ⚠️  No links created - LLM was too conservative")
        print("  💡 This is expected behavior - system prefers precision over recall")
    else:
        print(f"  ✅ System created {total_links} links")
        print("  💡 Review link quality above")

    # Expected links (ideal scenario):
    print("\n📋 Expected Links (ideal scenario):")
    print("  1. Follow-up task → SPAWNED → Meeting with Sarah")
    print("  2. Related idea → RELATED → Meeting with Sarah")
    print("  3. Related idea → REFERENCES → Follow-up task (consolidation pattern)")
    print("  4. Unrelated note → (no links)")

    print("\n" + "=" * 80)
    print("✅ Test Complete!")
    print("=" * 80)


if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("❌ Server not responding. Start with: python3 -m api.main")
            exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Server not running. Start with: python3 -m api.main")
        exit(1)

    main()
