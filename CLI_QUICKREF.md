# CLI Quick Reference Card

## Interactive Mode
```bash
./cli.py
```
Launches menu with numbered choices.

---

## Direct Commands

### Capture
```bash
./cli.py capture "Your note text here"
```

### Search
```bash
# Smart search (natural language)
./cli.py search "what did I discuss with Sarah"

# By person
./cli.py search --person Sarah
./cli.py search --person Sarah --context meetings

# By emotion
./cli.py search --emotion excited

# By entity
./cli.py search --entity topic:FAISS
./cli.py search --entity project:"memory consolidation"

# By context
./cli.py search --context tasks
```

### Graph
```bash
./cli.py graph <note-id>
./cli.py graph <note-id> --depth 2
```

### Stats
```bash
./cli.py stats
```

### Consolidate
```bash
./cli.py consolidate
```

### List
```bash
./cli.py list
```

---

## Help
```bash
./cli.py --help
./cli.py search --help
./cli.py graph --help
```

---

## Common Workflows

### Daily Review
```bash
./cli.py stats
./cli.py consolidate
./cli.py list
```

### Find Person Mentions
```bash
./cli.py search --person <name>
./cli.py graph <note-id>
```

### Explore Topic
```bash
./cli.py search --entity topic:<topic>
./cli.py graph <note-id>
```

---

## Tips

- **Smart search understands natural language** - Try "meetings about FAISS"
- **Use `--help` on any command** for full options
- **Run consolidate regularly** to build the knowledge graph
- **Check stats** to understand your knowledge base
- **Graph explorer** shows note connections visually

---

## Requirements

Backend must be running:
```bash
python3 -m api.main
```
