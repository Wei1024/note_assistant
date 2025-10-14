#!/usr/bin/env python3
"""
QuickNote AI - Interactive CLI Tester v2 (Fully Optimized)
- Capture: Fast direct LLM classification (~60% faster)
- Search: Fast natural language search (~70% faster)
"""
import requests
import sys
from pathlib import Path

# Simple colored terminal output
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

BACKEND_URL = "http://127.0.0.1:8787"

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")

def print_section(emoji, title):
    print(f"\n{Colors.BOLD}{Colors.YELLOW}{emoji} {title}{Colors.END}")
    print(f"{Colors.YELLOW}{'─'*60}{Colors.END}")

def check_backend():
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"{Colors.GREEN}✓ Backend running - Model: {data.get('model')}{Colors.END}")
            return True
    except:
        print(f"{Colors.RED}✗ Backend not running! Start with: python3 -m app-backend.main{Colors.END}")
        return False

def capture_note():
    """Capture note with optimized classification (fast path)"""
    print_section("📝", "Capture Note (Fast Classification)")

    print(f"{Colors.CYAN}Enter note:{Colors.END} ", end='')
    text = input().strip()

    if not text:
        return

    print(f"\n{Colors.YELLOW}⏳ Classifying...{Colors.END}\n")

    try:
        # Use optimized fast endpoint
        response = requests.post(
            f"{BACKEND_URL}/classify_and_save",
            json={"text": text},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()

            # Show result
            print_section("✅", "Saved!")
            print(f"Title: {data.get('title')}")
            print(f"Folder: {data.get('folder')}")
            print(f"Tags: {', '.join(data.get('tags', []))}")
            print(f"Path: {data.get('path', 'N/A')}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")

def search_notes():
    """Search with smart natural language understanding"""
    print_section("🔍", "Smart Search (Natural Language)")

    print(f"{Colors.CYAN}Enter search query:{Colors.END} ", end='')
    query = input().strip()

    if not query:
        return

    print(f"\n{Colors.YELLOW}⏳ Searching...{Colors.END}\n")

    try:
        response = requests.post(
            f"{BACKEND_URL}/search_smart",
            json={"query": query, "limit": 10},
            timeout=30
        )

        if response.status_code == 200:
            results = response.json()

            if results:
                print_section("📋", f"Found {len(results)} notes")
                for i, r in enumerate(results[:5], 1):
                    path = Path(r['path'])
                    print(f"\n{Colors.BOLD}{i}. {path.name}{Colors.END}")
                    snippet = r['snippet'].replace('<b>', Colors.GREEN).replace('</b>', Colors.END)
                    print(f"   {snippet}")
                    print(f"   {Colors.CYAN}Score: {r['score']:.2f}{Colors.END}")

                if len(results) > 5:
                    print(f"\n{Colors.YELLOW}... and {len(results) - 5} more results{Colors.END}")
            else:
                print(f"\n{Colors.YELLOW}No results found{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")

def list_notes():
    """List all notes"""
    print_section("📋", "List Notes")
    
    import os
    notes_dir = Path(os.getenv("NOTES_DIR", "~/Notes")).expanduser()
    
    if not notes_dir.exists():
        print(f"{Colors.RED}Notes directory not found{Colors.END}")
        return
    
    for folder in ["inbox", "projects", "people", "research", "journal"]:
        folder_path = notes_dir / folder
        if folder_path.exists():
            notes = sorted(folder_path.glob("*.md"))
            if notes:
                print(f"\n{Colors.CYAN}{folder.upper()}{Colors.END} ({len(notes)} notes)")
                for note in notes[:5]:
                    print(f"  • {note.name}")
                if len(notes) > 5:
                    print(f"  ... and {len(notes) - 5} more")

def main_menu():
    print_header("QuickNote AI - CLI Tester v2")
    
    if not check_backend():
        sys.exit(1)
    
    while True:
        print(f"\n{Colors.BOLD}Main Menu:{Colors.END}")
        print(f"  {Colors.CYAN}1.{Colors.END} 📝 Capture Note (Fast)")
        print(f"  {Colors.CYAN}2.{Colors.END} 🔍 Search Notes (Smart - Natural Language)")
        print(f"  {Colors.CYAN}3.{Colors.END} 📋 List Notes")
        print(f"  {Colors.CYAN}4.{Colors.END} ❌ Quit")
        
        choice = input(f"\n{Colors.BOLD}Your choice:{Colors.END} ").strip()
        
        if choice == "1":
            capture_note()
        elif choice == "2":
            search_notes()
        elif choice == "3":
            list_notes()
        elif choice == "4" or choice.lower() == "q":
            print(f"\n{Colors.GREEN}Goodbye!{Colors.END}\n")
            break
        else:
            print(f"{Colors.RED}Invalid choice!{Colors.END}")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Interrupted{Colors.END}")
        sys.exit(0)
