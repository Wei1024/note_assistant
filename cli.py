#!/usr/bin/env python3
"""
QuickNote AI - Multi-Dimensional CLI v3 (Hybrid Mode)
- Interactive menu for exploration
- Command-line args for power users
- Full Phase 3.1 feature integration
"""
import requests
import sys
import argparse
import os
from pathlib import Path
from datetime import datetime

# Simple colored terminal output
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'

BACKEND_URL = "http://127.0.0.1:8787"

# ============================================================================
# Display Helpers
# ============================================================================

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")

def print_section(emoji, title):
    print(f"\n{Colors.BOLD}{Colors.YELLOW}{emoji} {title}{Colors.END}")
    print(f"{Colors.YELLOW}{'─'*70}{Colors.END}")

def print_box(title, content, metadata=None):
    """Print a nice box for search results"""
    print(f"\n  ╭{'─'*66}╮")
    print(f"  │ {Colors.BOLD}{title[:64]}{Colors.END}{' '*(64-len(title))}│")
    if metadata:
        print(f"  │ {Colors.DIM}{metadata[:64]}{Colors.END}{' '*(64-len(metadata))}│")
    print(f"  ├{'─'*66}┤")

    # Content lines (wrap at 64 chars)
    content_lines = content.split('\n')
    for line in content_lines[:3]:  # Max 3 lines
        if len(line) > 64:
            line = line[:61] + "..."
        print(f"  │ {line}{' '*(64-len(line))}│")

    print(f"  ╰{'─'*66}╯")

def format_metadata_line(note_data):
    """Format metadata line with entities/dimensions"""
    parts = []

    metadata = note_data.get('metadata', {})

    # People
    if 'has_entities' in metadata and 'person' in metadata['has_entities']:
        people = metadata['has_entities']['person']
        if people:
            parts.append(f"👤 {', '.join(people[:2])}")

    # Topics
    if 'has_entities' in metadata and 'topic' in metadata['has_entities']:
        topics = metadata['has_entities']['topic']
        if topics:
            parts.append(f"🏷️  {', '.join(topics[:2])}")

    # Match type (for smart search)
    if metadata.get('match_type') == 'related':
        parts.append(f"{Colors.YELLOW}(relaxed match){Colors.END}")

    # Links
    link_count = metadata.get('link_count', 0)
    if link_count > 0:
        parts.append(f"🔗 {link_count} links")

    return "  │ " + " • ".join(parts) if parts else ""

def check_backend():
    """Check if backend is running"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"{Colors.GREEN}✓ Backend running - Model: {data.get('model')}{Colors.END}")
            return True
    except:
        print(f"{Colors.RED}✗ Backend not running! Start with: python3 -m api.main{Colors.END}")
        return False

# ============================================================================
# Core Commands
# ============================================================================

def capture_note(text=None):
    """Capture note with optimized classification"""
    print_section("📝", "Capture Note")

    if not text:
        print(f"{Colors.CYAN}Enter note (or Ctrl+C to cancel):{Colors.END}")
        text = input().strip()

    if not text:
        print(f"{Colors.YELLOW}No text provided{Colors.END}")
        return

    print(f"\n{Colors.YELLOW}⏳ Classifying and enriching...{Colors.END}\n")

    try:
        response = requests.post(
            f"{BACKEND_URL}/classify_and_save",
            json={"text": text},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            print_section("✅", "Saved!")
            print(f"  Title:  {data.get('title')}")
            print(f"  Folder: {Colors.CYAN}{data.get('folder')}{Colors.END}")
            print(f"  Tags:   {', '.join(data.get('tags', []))}")
            print(f"  Path:   {Colors.DIM}{data.get('path', 'N/A')}{Colors.END}")
        else:
            print(f"{Colors.RED}Error: {response.text}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")

def display_search_results(results, query_info=None):
    """Display search results with enhanced formatting"""
    if not results:
        print(f"\n{Colors.YELLOW}No results found{Colors.END}")
        return

    print_section("📋", f"Found {len(results)} notes")

    if query_info:
        print(f"{Colors.DIM}Query: {query_info}{Colors.END}\n")

    for i, r in enumerate(results[:10], 1):
        path = Path(r['path'])
        title = path.stem.replace('-', ' ').title()

        # Metadata line
        metadata = r.get('metadata') or {}
        folder = metadata.get('folder', 'unknown')
        created = metadata.get('created', '')
        if created:
            try:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                created = dt.strftime('%Y-%m-%d %H:%M')
            except:
                created = created[:16]

        meta_line = f"{folder} • {created}" if created else folder

        # Snippet
        snippet = r['snippet'][:200]
        snippet = snippet.replace('<b>', Colors.GREEN).replace('</b>', Colors.END)

        # Display
        print(f"\n  {Colors.BOLD}{i}. {title[:60]}{Colors.END}")
        print(f"  {Colors.DIM}{meta_line}{Colors.END}")
        print(f"  {snippet}")

        # Entity metadata
        meta_info = format_metadata_line(r)
        if meta_info:
            print(meta_info)

        print(f"  {Colors.DIM}Score: {r['score']:.2f} • {path.name}{Colors.END}")

    if len(results) > 10:
        print(f"\n{Colors.YELLOW}... and {len(results) - 10} more results{Colors.END}")

def search_smart(query, limit=10):
    """Smart search with natural language understanding"""
    print_section("🔍", "Smart Search")

    print(f"\n{Colors.YELLOW}⏳ Searching...{Colors.END}\n")

    try:
        response = requests.post(
            f"{BACKEND_URL}/search_smart",
            json={"query": query, "limit": limit},
            timeout=30
        )

        if response.status_code == 200:
            results = response.json()
            display_search_results(results, query_info=query)
        else:
            print(f"{Colors.RED}Error: {response.text}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")

def search_by_person_cmd(name, context=None, limit=10):
    """Search by person"""
    print_section("👤", f"Notes mentioning: {name}")

    try:
        payload = {"name": name}
        if context:
            payload["context"] = context

        response = requests.post(
            f"{BACKEND_URL}/search/person",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            results = response.json()
            query_info = f"Person: {name}" + (f" in {context}" if context else "")
            display_search_results(results[:limit], query_info=query_info)
        else:
            print(f"{Colors.RED}Error: {response.text}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")

def search_by_emotion_cmd(emotion, limit=10):
    """Search by emotion"""
    print_section("😊", f"Notes with emotion: {emotion}")

    try:
        response = requests.post(
            f"{BACKEND_URL}/search/dimensions",
            json={"dimension_type": "emotion", "dimension_value": emotion},
            timeout=30
        )

        if response.status_code == 200:
            results = response.json()
            display_search_results(results[:limit], query_info=f"Emotion: {emotion}")
        else:
            print(f"{Colors.RED}Error: {response.text}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")

def search_by_entity_cmd(entity_type, entity_value, context=None, limit=10):
    """Search by entity (person/topic/project/tech)"""
    print_section("🏷️", f"Notes about: {entity_value} ({entity_type})")

    try:
        payload = {"entity_type": entity_type, "entity_value": entity_value}
        if context:
            payload["context"] = context

        response = requests.post(
            f"{BACKEND_URL}/search/entities",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            results = response.json()
            query_info = f"{entity_type}: {entity_value}" + (f" in {context}" if context else "")
            display_search_results(results[:limit], query_info=query_info)
        else:
            print(f"{Colors.RED}Error: {response.text}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")

def search_by_context_cmd(context, limit=10):
    """Search by context/folder"""
    print_section("📁", f"Notes in: {context}")

    try:
        response = requests.post(
            f"{BACKEND_URL}/search/dimensions",
            json={"dimension_type": "context", "dimension_value": context},
            timeout=30
        )

        if response.status_code == 200:
            results = response.json()
            display_search_results(results[:limit], query_info=f"Context: {context}")
        else:
            print(f"{Colors.RED}Error: {response.text}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")

def explore_graph(note_id=None, depth=1):
    """Interactive graph explorer"""
    print_section("🔗", "Graph Explorer")

    if not note_id:
        print(f"{Colors.CYAN}Enter note ID:{Colors.END} ", end='')
        note_id = input().strip()

    if not note_id:
        print(f"{Colors.YELLOW}No note ID provided{Colors.END}")
        return

    try:
        response = requests.post(
            f"{BACKEND_URL}/search/graph",
            json={"start_note_id": note_id, "depth": depth},
            timeout=30
        )

        if response.status_code == 200:
            graph = response.json()
            display_graph(graph, note_id)
        else:
            print(f"{Colors.RED}Error: {response.text}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")

def display_graph(graph, root_id):
    """Display graph as ASCII tree"""
    nodes = {n['id']: n for n in graph['nodes']}
    edges = graph['edges']

    if root_id not in nodes:
        print(f"{Colors.RED}Note not found in graph{Colors.END}")
        return

    root = nodes[root_id]
    print(f"\n{Colors.BOLD}📄 {root['title']}{Colors.END} ({root.get('folder', 'unknown')})")
    print(f"{Colors.DIM}   {root.get('created', '')}{Colors.END}")

    # Show entities
    if 'has_entities' in root.get('metadata', {}):
        entities = root['metadata']['has_entities']
        if entities:
            print(f"\n{Colors.CYAN}   Entities:{Colors.END}")
            for etype, values in entities.items():
                if values:
                    print(f"   • {etype}: {', '.join(values[:3])}")

    # Show connections
    outgoing = [e for e in edges if e['from'] == root_id]
    incoming = [e for e in edges if e['to'] == root_id]

    if outgoing or incoming:
        print(f"\n{Colors.CYAN}   🔗 Connections:{Colors.END}")

        for edge in outgoing:
            target = nodes.get(edge['to'])
            if target:
                link_type = edge.get('type', 'related')
                print(f"   ├─[{link_type}]→ {target['title'][:50]}")

        for edge in incoming:
            source = nodes.get(edge['from'])
            if source:
                link_type = edge.get('type', 'related')
                print(f"   ├─[{link_type}]← {source['title'][:50]}")
    else:
        print(f"\n{Colors.YELLOW}   No connections found{Colors.END}")

    print(f"\n{Colors.DIM}Total nodes: {len(nodes)}, Total edges: {len(edges)}{Colors.END}")

def consolidate_notes():
    """Trigger memory consolidation"""
    print_section("🔄", "Memory Consolidation")

    print(f"\n{Colors.CYAN}This will analyze today's notes and create links based on:{Colors.END}")
    print(f"  • Shared people, topics, projects")
    print(f"  • Shared tags")
    print(f"  • Semantic relationships")

    confirm = input(f"\n{Colors.BOLD}Continue? (y/n):{Colors.END} ").strip().lower()

    if confirm != 'y':
        print(f"{Colors.YELLOW}Cancelled{Colors.END}")
        return

    print(f"\n{Colors.YELLOW}⏳ Running consolidation...{Colors.END}\n")

    try:
        response = requests.post(f"{BACKEND_URL}/consolidate", timeout=120)

        if response.status_code == 200:
            stats = response.json()

            print_section("✅", "Consolidation Complete!")
            print(f"  Notes Processed:  {stats['notes_processed']}")
            print(f"  Links Created:    {stats['links_created']}")
            print(f"  Notes with Links: {stats['notes_with_links']}")

            if stats['links_created'] == 0:
                print(f"\n{Colors.YELLOW}  💡 No links created - system prefers precision over recall{Colors.END}")
            else:
                print(f"\n{Colors.GREEN}  🎉 Successfully created {stats['links_created']} connections!{Colors.END}")
        else:
            print(f"{Colors.RED}Error: {response.text}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")

def show_stats():
    """Show system statistics"""
    print_section("📊", "System Statistics")

    print(f"\n{Colors.YELLOW}⏳ Gathering stats...{Colors.END}\n")

    try:
        # We'll compute stats locally from the database
        import sqlite3
        from api.config import DB_PATH

        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()

        # Total notes
        cur.execute("SELECT COUNT(*) FROM notes_meta")
        total_notes = cur.fetchone()[0]

        print(f"{Colors.BOLD}Knowledge Base:{Colors.END}")
        print(f"  Total Notes: {total_notes}")

        # By dimensions (replaced folder classification)
        dimensions = [
            ('has_action_items', 'tasks', '📋'),
            ('is_social', 'meetings', '🤝'),
            ('is_exploratory', 'ideas', '💡'),
            ('is_knowledge', 'reference', '📚'),
            ('is_emotional', 'journal', '📓')
        ]

        print(f"\n{Colors.BOLD}By Dimension:{Colors.END}")
        max_count = 0
        dimension_counts = []

        for dim_col, label, emoji in dimensions:
            cur.execute(f"SELECT COUNT(*) FROM notes_meta WHERE {dim_col} = 1")
            count = cur.fetchone()[0]
            dimension_counts.append((label, count, emoji))
            max_count = max(max_count, count)

        for label, count, emoji in dimension_counts:
            if count > 0:
                pct = (count / total_notes * 100) if total_notes > 0 else 0
                bar_length = int(count / max_count * 20) if max_count > 0 else 0
                bar = '█' * bar_length + '░' * (20 - bar_length)
                print(f"  {emoji} {label:12s} {count:3d} notes ({pct:5.1f}%)  [{bar}]")

        # Top people
        cur.execute("""
            SELECT entity_value, COUNT(DISTINCT note_id) as cnt
            FROM notes_entities
            WHERE entity_type='person'
            GROUP BY entity_value
            ORDER BY cnt DESC
            LIMIT 5
        """)
        people = cur.fetchall()

        if people:
            print(f"\n{Colors.BOLD}Top People:{Colors.END}")
            for name, count in people:
                print(f"  👤 {name:20s} {count} notes")

        # Top entities
        cur.execute("""
            SELECT entity_value, COUNT(DISTINCT note_id) as cnt
            FROM notes_entities
            WHERE entity_type='entity'
            GROUP BY entity_value
            ORDER BY cnt DESC
            LIMIT 5
        """)
        entities = cur.fetchall()

        if entities:
            print(f"\n{Colors.BOLD}Top Entities:{Colors.END}")
            for entity, count in entities:
                print(f"  🏷️  {entity:20s} {count} notes")

        # Emotions
        cur.execute("""
            SELECT dimension_value, COUNT(DISTINCT note_id) as cnt
            FROM notes_dimensions
            WHERE dimension_type='emotion'
            GROUP BY dimension_value
            ORDER BY cnt DESC
            LIMIT 5
        """)
        emotions = cur.fetchall()

        if emotions:
            print(f"\n{Colors.BOLD}Emotions:{Colors.END}")
            emoji_map = {'excited': '😊', 'curious': '🤔', 'frustrated': '😤', 'happy': '😄', 'worried': '😟'}
            for emotion, count in emotions:
                emoji = emoji_map.get(emotion, '💭')
                print(f"  {emoji} {emotion:12s} {count} notes")

        # Graph stats
        cur.execute("SELECT COUNT(*) FROM notes_links")
        total_links = cur.fetchone()[0]

        print(f"\n{Colors.BOLD}Graph:{Colors.END}")
        print(f"  🔗 Total Links: {total_links}")
        if total_notes > 0:
            avg_links = total_links / total_notes
            print(f"  📊 Avg Links per Note: {avg_links:.2f}")

        con.close()

    except Exception as e:
        print(f"{Colors.RED}Error computing stats: {e}{Colors.END}")

def list_notes():
    """List notes by context"""
    print_section("📋", "List Notes by Context")

    notes_dir = Path(os.getenv("NOTES_DIR", "~/Notes")).expanduser()

    if not notes_dir.exists():
        print(f"{Colors.RED}Notes directory not found: {notes_dir}{Colors.END}")
        return

    # Use correct folder names (Phase 1 cognitive model)
    folders = ["tasks", "meetings", "ideas", "reference", "journal", "inbox"]

    total = 0
    for folder in folders:
        folder_path = notes_dir / folder
        if folder_path.exists():
            notes = sorted(folder_path.glob("*.md"), reverse=True)  # Most recent first
            if notes:
                emoji = {'tasks': '📋', 'meetings': '🤝', 'ideas': '💡', 'reference': '📚', 'journal': '📓', 'inbox': '📥'}.get(folder, '📁')
                print(f"\n{Colors.CYAN}{emoji} {folder.upper()}{Colors.END} ({len(notes)} notes)")
                for note in notes[:10]:
                    print(f"  • {note.name}")
                if len(notes) > 10:
                    print(f"  {Colors.DIM}... and {len(notes) - 10} more{Colors.END}")
                total += len(notes)

    print(f"\n{Colors.BOLD}Total: {total} notes{Colors.END}")

# ============================================================================
# Interactive Menu System
# ============================================================================

def search_menu():
    """Search submenu"""
    while True:
        print(f"\n{Colors.BOLD}🔍 Search Menu:{Colors.END}")
        print(f"  {Colors.CYAN}1.{Colors.END} 💬 Smart Search (Natural Language)")
        print(f"  {Colors.CYAN}2.{Colors.END} 👤 By Person")
        print(f"  {Colors.CYAN}3.{Colors.END} 😊 By Emotion")
        print(f"  {Colors.CYAN}4.{Colors.END} 🏷️  By Entity (topic/project/tech)")
        print(f"  {Colors.CYAN}5.{Colors.END} 📁 By Context (folder)")
        print(f"  {Colors.CYAN}6.{Colors.END} ← Back to Main Menu")

        choice = input(f"\n{Colors.BOLD}Your choice:{Colors.END} ").strip()

        if choice == "1":
            query = input(f"{Colors.CYAN}Enter query:{Colors.END} ").strip()
            if query:
                search_smart(query)
        elif choice == "2":
            name = input(f"{Colors.CYAN}Person name:{Colors.END} ").strip()
            if name:
                context = input(f"{Colors.CYAN}Filter by context (optional):{Colors.END} ").strip() or None
                search_by_person_cmd(name, context)
        elif choice == "3":
            emotion = input(f"{Colors.CYAN}Emotion (excited/curious/frustrated):{Colors.END} ").strip()
            if emotion:
                search_by_emotion_cmd(emotion)
        elif choice == "4":
            etype = input(f"{Colors.CYAN}Entity type (topic/project/tech/person):{Colors.END} ").strip()
            value = input(f"{Colors.CYAN}Entity value:{Colors.END} ").strip()
            if etype and value:
                context = input(f"{Colors.CYAN}Filter by context (optional):{Colors.END} ").strip() or None
                search_by_entity_cmd(etype, value, context)
        elif choice == "5":
            context = input(f"{Colors.CYAN}Context (tasks/meetings/ideas/reference/journal):{Colors.END} ").strip()
            if context:
                search_by_context_cmd(context)
        elif choice == "6":
            break
        else:
            print(f"{Colors.RED}Invalid choice!{Colors.END}")

def main_menu():
    """Main interactive menu"""
    print_header("QuickNote AI - Multi-Dimensional CLI")

    if not check_backend():
        sys.exit(1)

    while True:
        print(f"\n{Colors.BOLD}Main Menu:{Colors.END}")
        print(f"  {Colors.CYAN}1.{Colors.END} 📝  Capture Note")
        print(f"  {Colors.CYAN}2.{Colors.END} 🔍  Search Notes")
        print(f"  {Colors.CYAN}3.{Colors.END} 🔗  Graph Explorer")
        print(f"  {Colors.CYAN}4.{Colors.END} 📊  System Stats")
        print(f"  {Colors.CYAN}5.{Colors.END} 🔄  Consolidate Notes")
        print(f"  {Colors.CYAN}6.{Colors.END} 📋  List Notes by Context")
        print(f"  {Colors.CYAN}7.{Colors.END} ❌  Quit")

        choice = input(f"\n{Colors.BOLD}Your choice:{Colors.END} ").strip()

        if choice == "1":
            capture_note()
        elif choice == "2":
            search_menu()
        elif choice == "3":
            explore_graph()
        elif choice == "4":
            show_stats()
        elif choice == "5":
            consolidate_notes()
        elif choice == "6":
            list_notes()
        elif choice == "7" or choice.lower() == "q":
            print(f"\n{Colors.GREEN}Goodbye!{Colors.END}\n")
            break
        else:
            print(f"{Colors.RED}Invalid choice!{Colors.END}")

# ============================================================================
# Command-Line Interface (Direct Mode)
# ============================================================================

def main():
    """Main entry point with hybrid mode support"""
    parser = argparse.ArgumentParser(
        description='QuickNote AI - Multi-Dimensional CLI',
        epilog='Run without arguments for interactive menu'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Capture
    capture_parser = subparsers.add_parser('capture', help='Capture a note')
    capture_parser.add_argument('text', nargs='?', help='Note text')

    # Search
    search_parser = subparsers.add_parser('search', help='Search notes')
    search_parser.add_argument('query', nargs='?', help='Search query')
    search_parser.add_argument('--person', help='Search by person')
    search_parser.add_argument('--emotion', help='Search by emotion')
    search_parser.add_argument('--entity', help='Search by entity (format: type:value)')
    search_parser.add_argument('--context', help='Search by context/folder')
    search_parser.add_argument('--limit', type=int, default=10, help='Max results')

    # Graph
    graph_parser = subparsers.add_parser('graph', help='Explore graph')
    graph_parser.add_argument('note_id', nargs='?', help='Note ID to explore')
    graph_parser.add_argument('--depth', type=int, default=1, help='Traversal depth')

    # Stats
    subparsers.add_parser('stats', help='Show system statistics')

    # Consolidate
    subparsers.add_parser('consolidate', help='Run memory consolidation')

    # List
    subparsers.add_parser('list', help='List notes by context')

    args = parser.parse_args()

    # Check backend for all commands
    if args.command:
        if not check_backend():
            sys.exit(1)

    # Route to appropriate function
    if args.command == 'capture':
        capture_note(args.text)
    elif args.command == 'search':
        if args.person:
            search_by_person_cmd(args.person, args.context, args.limit)
        elif args.emotion:
            search_by_emotion_cmd(args.emotion, args.limit)
        elif args.entity:
            if ':' in args.entity:
                etype, value = args.entity.split(':', 1)
                search_by_entity_cmd(etype, value, args.context, args.limit)
            else:
                print(f"{Colors.RED}Entity must be in format type:value (e.g., topic:FAISS){Colors.END}")
        elif args.context:
            search_by_context_cmd(args.context, args.limit)
        elif args.query:
            search_smart(args.query, args.limit)
        else:
            print(f"{Colors.RED}Please provide a query or filter{Colors.END}")
    elif args.command == 'graph':
        explore_graph(args.note_id, args.depth)
    elif args.command == 'stats':
        show_stats()
    elif args.command == 'consolidate':
        consolidate_notes()
    elif args.command == 'list':
        list_notes()
    else:
        # No command provided - launch interactive menu
        main_menu()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Interrupted{Colors.END}")
        sys.exit(0)
