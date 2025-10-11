#!/usr/bin/env python3
"""
QuickNote AI - Interactive CLI Tester
Shows full agent reasoning trace with clean text output
"""
import requests
import sys
from pathlib import Path

# Simple colored terminal output (no dependencies needed)
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

BACKEND_URL = "http://127.0.0.1:8787"

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")

def print_section(emoji, title):
    print(f"\n{Colors.BOLD}{Colors.YELLOW}{emoji} {title}{Colors.END}")
    print(f"{Colors.YELLOW}{'─'*60}{Colors.END}")

def print_box(content, color=Colors.BLUE):
    lines = content.strip().split('\n')
    max_len = max(len(line) for line in lines) + 4

    print(f"{color}┌{'─'*max_len}┐{Colors.END}")
    for line in lines:
        padding = max_len - len(line) - 2
        print(f"{color}│{Colors.END} {line}{' '*padding} {color}│{Colors.END}")
    print(f"{color}└{'─'*max_len}┘{Colors.END}")

def check_backend():
    """Check if backend is running"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"{Colors.GREEN}✓ Backend is running{Colors.END}")
            print(f"  Model: {data.get('model', 'unknown')}")
            return True
    except Exception as e:
        print(f"{Colors.RED}✗ Backend not running!{Colors.END}")
        print(f"  Error: {e}")
        print(f"\n  Start it with: python3 -m app-backend.main")
        return False

def capture_note():
    """Capture note with AI classification agent"""
    print_section("📝", "Capture Note")

    print(f"{Colors.CYAN}Enter note text:{Colors.END} ", end='')
    text = input().strip()

    if not text:
        print(f"{Colors.RED}No text entered!{Colors.END}")
        return

    print(f"\n{Colors.YELLOW}⏳ Running agent with trace...{Colors.END}\n")

    try:
        response = requests.post(
            f"{BACKEND_URL}/classify_with_trace",
            json={"text": text},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()

            # Display agent trace
            print_section("🔍", "Agent Execution Trace")

            if data.get("steps"):
                for i, step in enumerate(data["steps"], 1):
                    step_type = step.get("type", "unknown")

                    if step_type == "thought":
                        print(f"\n{Colors.CYAN}💭 Step {i} - Agent Thought:{Colors.END}")
                        print(f"   {step['content']}")

                    elif step_type == "tool_call":
                        print(f"\n{Colors.YELLOW}🔧 Step {i} - Tool Call:{Colors.END}")
                        print(f"   Tool: {Colors.BOLD}{step['name']}{Colors.END}")
                        print(f"   Args:")
                        for key, val in step['args'].items():
                            preview = str(val)[:100] + "..." if len(str(val)) > 100 else str(val)
                            print(f"     {key}: {preview}")

                    elif step_type == "tool_response":
                        print(f"\n{Colors.GREEN}📥 Step {i} - Tool Response:{Colors.END}")
                        print_box(step['content'], Colors.GREEN)

                    elif step_type == "error":
                        print(f"\n{Colors.RED}❌ Error:{Colors.END}")
                        print(f"   {step['content']}")
            else:
                print(f"{Colors.YELLOW}No trace steps captured (using simple tool call){Colors.END}")

            # Display final result
            print_section("✅", "Final Result")
            final = data.get("final", {})

            result_text = f"""Title: {final.get('title', 'N/A')}
Folder: {final.get('folder', 'N/A')}
Tags: {', '.join(final.get('tags', []))}
First Sentence: {final.get('first_sentence', 'N/A')}"""

            if final.get('saved'):
                result_text += f"\n\n✓ Saved to: {final.get('path', 'N/A')}"

            if 'error' in final:
                result_text += f"\nError: {final['error']}"

            print_box(result_text, Colors.GREEN)

        else:
            print(f"{Colors.RED}Error: {response.status_code}{Colors.END}")
            print(response.text)

    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")

def search_notes():
    """Search notes with FTS5"""
    print_section("🔍", "Search Notes")

    print(f"{Colors.CYAN}Enter search query:{Colors.END} ", end='')
    query = input().strip()

    if not query:
        print(f"{Colors.RED}No query entered!{Colors.END}")
        return

    print(f"\n{Colors.YELLOW}Searching...{Colors.END}\n")

    try:
        response = requests.post(
            f"{BACKEND_URL}/search",
            json={"query": query, "limit": 10},
            timeout=10
        )

        if response.status_code == 200:
            results = response.json()

            if results:
                print(f"{Colors.GREEN}Found {len(results)} results:{Colors.END}\n")

                for i, result in enumerate(results, 1):
                    path = Path(result['path'])
                    filename = path.name

                    print(f"{Colors.BOLD}{i}. {filename}{Colors.END}")
                    print(f"   Path: {result['path']}")
                    print(f"   Score: {result['score']:.6f}")

                    # Display snippet (HTML tags removed for clean output)
                    snippet = result['snippet'].replace('<b>', Colors.GREEN).replace('</b>', Colors.END)
                    print(f"   Preview: {snippet}")
                    print()
            else:
                print(f"{Colors.YELLOW}No results found{Colors.END}")

        else:
            print(f"{Colors.RED}Error: {response.status_code}{Colors.END}")
            print(response.text)

    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")

def list_notes():
    """List all notes (simple version - reads from Notes directory)"""
    print_section("📋", "List Notes")

    import os
    notes_dir_str = os.getenv("NOTES_DIR", "~/Notes")
    notes_dir = Path(notes_dir_str).expanduser()

    if not notes_dir.exists():
        print(f"{Colors.RED}Notes directory not found: {notes_dir}{Colors.END}")
        return

    folders = ["inbox", "projects", "people", "research", "journal"]

    for folder in folders:
        folder_path = notes_dir / folder
        if folder_path.exists():
            notes = sorted(folder_path.glob("*.md"))
            if notes:
                print(f"\n{Colors.CYAN}{folder.upper()}{Colors.END} ({len(notes)} notes)")
                for note in notes[:5]:  # Show first 5
                    print(f"  • {note.name}")
                if len(notes) > 5:
                    print(f"  ... and {len(notes) - 5} more")

def main_menu():
    """Main interactive menu"""
    print_header("QuickNote AI - CLI Tester")

    if not check_backend():
        print(f"\n{Colors.RED}Cannot continue without backend running.{Colors.END}")
        sys.exit(1)

    while True:
        print(f"\n{Colors.BOLD}Main Menu:{Colors.END}")
        print(f"  {Colors.CYAN}1.{Colors.END} 📝 Capture Note (Simple)")
        print(f"  {Colors.CYAN}2.{Colors.END} 🔍 Search Notes")
        print(f"  {Colors.CYAN}3.{Colors.END} 📋 List Notes")
        print(f"  {Colors.CYAN}4.{Colors.END} 🤖 Test Agent Trace (Show Full Reasoning)")
        print(f"  {Colors.CYAN}5.{Colors.END} ❌ Quit")

        choice = input(f"\n{Colors.BOLD}Your choice:{Colors.END} ").strip()

        if choice == "1":
            capture_simple()
        elif choice == "2":
            search_notes()
        elif choice == "3":
            list_notes()
        elif choice == "4":
            capture_with_trace()
        elif choice == "5" or choice.lower() == "q":
            print(f"\n{Colors.GREEN}Goodbye!{Colors.END}\n")
            break
        else:
            print(f"{Colors.RED}Invalid choice!{Colors.END}")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Interrupted by user{Colors.END}")
        sys.exit(0)
