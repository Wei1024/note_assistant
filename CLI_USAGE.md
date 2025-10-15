# QuickNote AI - CLI Usage Guide

## Overview

The CLI now supports **hybrid mode**: interactive menu for exploration + command-line arguments for power users.

---

## Quick Start

### Interactive Mode (Default)
```bash
./cli.py
```

Launches the interactive menu with all features accessible through numbered choices.

### Direct Mode (Power Users)
```bash
# Capture note
./cli.py capture "Meeting with Sarah about memory consolidation"

# Search
./cli.py search "vector embeddings"
./cli.py search --person Sarah
./cli.py search --emotion excited
./cli.py search --entity topic:FAISS
./cli.py search --context meetings

# Graph explorer
./cli.py graph 2025-10-11T22:22:36-07:00_0d7e

# System stats
./cli.py stats

# Consolidate notes
./cli.py consolidate

# List notes
./cli.py list
```

---

## Interactive Menu Features

### Main Menu
1. **📝 Capture Note** - Create a new note with automatic classification and enrichment
2. **🔍 Search Notes** - Opens search submenu
3. **🔗 Graph Explorer** - Visualize note connections
4. **📊 System Stats** - View knowledge base statistics
5. **🔄 Consolidate Notes** - Trigger memory consolidation (link related notes)
6. **📋 List Notes by Context** - Browse notes by folder
7. **❌ Quit**

### Search Submenu
1. **💬 Smart Search** - Natural language queries ("what did I discuss with Sarah?")
2. **👤 By Person** - Find all notes mentioning a person
3. **😊 By Emotion** - Find notes by emotional markers (excited, curious, frustrated)
4. **🏷️ By Entity** - Search by topics, projects, or technologies
5. **📁 By Context** - Filter by folder (tasks/meetings/ideas/reference/journal)
6. **← Back**

---

## Command-Line Arguments

### Capture
```bash
# Interactive (prompts for text)
./cli.py capture

# Direct
./cli.py capture "Note text here"
```

### Search

**Smart Search (Natural Language):**
```bash
./cli.py search "meetings about FAISS"
./cli.py search "what did I discuss with Sarah"
```

**By Person:**
```bash
./cli.py search --person Sarah
./cli.py search --person Sarah --context meetings
```

**By Emotion:**
```bash
./cli.py search --emotion excited
./cli.py search --emotion curious
```

**By Entity:**
```bash
./cli.py search --entity topic:FAISS
./cli.py search --entity project:"memory consolidation"
./cli.py search --entity tech:ChromaDB --context ideas
```

**By Context:**
```bash
./cli.py search --context tasks
./cli.py search --context meetings
```

**Limit Results:**
```bash
./cli.py search "vector" --limit 20
```

### Graph Explorer

**Interactive:**
```bash
./cli.py graph
# Prompts for note ID
```

**Direct:**
```bash
./cli.py graph 2025-10-11T22:22:36-07:00_0d7e
./cli.py graph 2025-10-11T22:22:36-07:00_0d7e --depth 2
```

### System Stats
```bash
./cli.py stats
```

Shows:
- Total notes by context/folder
- Top people mentioned
- Top topics
- Emotional distribution
- Graph statistics (links, connections)

### Consolidate
```bash
./cli.py consolidate
```

Analyzes today's notes and creates links based on:
- Shared people, topics, projects
- Shared tags
- Semantic relationships

### List
```bash
./cli.py list
```

Lists all notes organized by context folder.

---

## Example Workflows

### Daily Review Workflow
```bash
# 1. See what you've captured today
./cli.py list

# 2. Check system stats
./cli.py stats

# 3. Run consolidation to link related notes
./cli.py consolidate

# 4. Explore connections
./cli.py search --emotion excited
```

### Research Workflow
```bash
# 1. Capture research notes
./cli.py capture "Found interesting paper on vector embeddings by Sarah Chen"

# 2. Find all related notes
./cli.py search --entity topic:"vector embeddings"

# 3. See connections
./cli.py graph <note-id>
```

### People-Centric Workflow
```bash
# 1. Find all interactions with Sarah
./cli.py search --person Sarah

# 2. Filter by context
./cli.py search --person Sarah --context meetings

# 3. Explore the graph
./cli.py graph <note-id>
```

---

## Tips & Tricks

### 1. Smart Search is Powerful
The smart search understands natural language and automatically routes to the right endpoint:
```bash
./cli.py search "meetings about FAISS"
# Parses: context=meetings, entity=FAISS
# Routes to: search_by_entity("FAISS", context="meetings")
```

### 2. Use Graph Explorer to Understand Connections
After consolidation, explore note relationships:
```bash
./cli.py consolidate
./cli.py graph <note-id>
```

### 3. System Stats for Overview
Check your knowledge base health:
```bash
./cli.py stats
```

### 4. Combine Filters
```bash
./cli.py search --person Sarah --context meetings
./cli.py search --entity topic:FAISS --context ideas --limit 20
```

---

## Display Features

### Enhanced Search Results
Results now show:
- Note title and metadata (folder, created date)
- Snippet with highlighted matches
- Entity metadata (people, topics)
- Link count
- Match type (exact vs relaxed)

### Graph Visualization (ASCII)
```
📄 Brainstorming vector embeddings (ideas)
   2025-10-11T22:22:36-07:00

   Entities:
   • topic: vector embeddings, FAISS, ChromaDB
   • person: Sarah

   🔗 Connections:
   ├─[spawned]→ Follow-up on memory research
   └─[related]→ Evaluate vector DB options
```

### System Stats Dashboard
```
Knowledge Base:
  Total Notes: 21

By Context:
  📋 tasks        9 notes (43%)  [█████████░░░░░░░]
  🤝 meetings     1 note  (5%)   [██░░░░░░░░░░░░░░]
  💡 ideas        3 notes (14%)  [████░░░░░░░░░░░░]

Top People:
  👤 Sarah       5 notes
  👤 Alex        3 notes

Top Topics:
  🏷️ memory consolidation    8 notes
  🏷️ vector search           5 notes

Emotions:
  😊 excited     5 notes
  🤔 curious     4 notes

Graph:
  🔗 Total Links: 3
  📊 Avg Links per Note: 0.21
```

---

## What's New (v3)

### Phase 1 Features ✅
- ✅ Search submenu with all Phase 3.1 filters
- ✅ Consolidation trigger
- ✅ Fixed list_notes (correct folder names)
- ✅ Improved result display formatting

### Phase 2 Features ✅
- ✅ Graph explorer with ASCII visualization
- ✅ System stats dashboard
- ✅ Enhanced search result metadata

### Phase 3 Features ✅
- ✅ Command-line args support (hybrid mode)
- ✅ Help text and examples
- ✅ Better error handling

### Coming Soon
- ⏳ Task status management (update task status from CLI)
- ⏳ Export graph to JSON/GraphML
- ⏳ Interactive result navigation (jump to note)

---

## Troubleshooting

### Backend Not Running
```
✗ Backend not running! Start with: python3 -m api.main
```

**Solution:**
```bash
# Terminal 1: Start backend
python3 -m api.main

# Terminal 2: Use CLI
./cli.py
```

### No Results Found
- Check that notes exist: `./cli.py list`
- Try smart search: `./cli.py search "your query"`
- Run consolidation: `./cli.py consolidate`

### Graph Shows No Connections
- Run consolidation first: `./cli.py consolidate`
- Check if notes have shared entities
- System prefers precision - it's conservative with links

---

## Need Help?

```bash
./cli.py --help
./cli.py search --help
./cli.py graph --help
```

Or just run `./cli.py` for the interactive menu!
