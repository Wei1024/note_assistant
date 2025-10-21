# Phase 1: LLM Audit Logging Implementation

## What We Built

Added comprehensive LLM operation tracking to enable debugging, cost analysis, and optimization decisions.

### 1. Database Schema Changes

**New Table:** `llm_operations`
- Tracks every LLM call (classification, enrichment, consolidation)
- Stores raw prompts, responses, and parsed outputs
- Captures performance metrics (tokens, latency, cost)
- Located in: `api/db/schema.py`

### 2. Audit Logging Module

**File:** `api/llm/audit.py`

**Key Functions:**
- `track_llm_call()` - Context manager for automatic logging
- `log_llm_operation()` - Manual logging function
- `get_operation_stats()` - Query aggregated statistics
- `_estimate_cost()` - Calculate USD cost from token usage

**Usage Example:**
```python
with track_llm_call('classification', prompt, note_id) as tracker:
    response = await llm.ainvoke(prompt)
    tracker.set_response(response)
    result = json.loads(response.content)
    tracker.set_parsed_output(result)
# Auto-logged on exit!
```

### 3. Service Integration

**Modified Files:**
- `api/services/capture.py` - Classification logging
- `api/services/enrichment.py` - Enrichment logging
- `api/services/consolidation.py` - Consolidation logging

All LLM calls now automatically log:
- Full prompt text
- Raw LLM response
- Parsed/validated output
- Token counts (input + output)
- Duration in milliseconds
- Estimated cost in USD

### 4. Test Dataset

**File:** `test_data/test_notes.csv`

**30 diverse test notes covering:**
- Single dimensions (pure action, emotion, knowledge)
- Multi-dimensional (action+social, emotion+exploratory)
- Edge cases (very short, ambiguous, mixed)
- Time references (appointments, deadlines)
- People mentions (Sarah, Alex, Tom)
- Technical content (Python, Redis, SQLite)

**CSV Format:**
```csv
note_text,expected_dimensions,notes
"Text here","has_action_items,is_social","Description"
```

Easy to:
- View in spreadsheet
- Add new test cases
- Compare expected vs actual

### 5. Import Script

**File:** `scripts/import_test_notes.py`

Reads CSV and creates notes via API, enabling:
- Full LLM processing
- Audit logging
- Real-world testing

**Usage:**
```bash
# Make sure backend is running first!
python scripts/import_test_notes.py
```

### 6. Analysis Script

**File:** `scripts/analyze_llm_decisions.py` (already existed, still works!)

Query database to see:
- Classification patterns
- Entity extraction
- Link creation
- **NEW:** LLM operation stats

---

## How to Use This System

### Step 1: Start Fresh

```bash
# Already done! Database backed up and recreated
ls ~/Notes/.index/notes.sqlite.backup-*
```

### Step 2: Start Backend

```bash
# In one terminal
cd /Users/weihuahuang/dev/note_assistant
source .venv/bin/activate
python api/main.py
```

### Step 3: Import Test Notes

```bash
# In another terminal
cd /Users/weihuahuang/dev/note_assistant
source .venv/bin/activate
python scripts/import_test_notes.py
```

This will take ~2-3 minutes (30 notes × 2-4 seconds each).

### Step 4: Analyze Results

```bash
# Run analysis
python scripts/analyze_llm_decisions.py

# Or query directly
sqlite3 ~/Notes/.index/notes.sqlite "
  SELECT
    operation_type,
    COUNT(*) as count,
    AVG(duration_ms) as avg_duration,
    SUM(tokens_input) as total_input,
    SUM(tokens_output) as total_output,
    SUM(cost_usd) as total_cost
  FROM llm_operations
  GROUP BY operation_type
"
```

### Step 5: Deep Dive into Specific Operations

```bash
# See a classification decision
sqlite3 ~/Notes/.index/notes.sqlite "
  SELECT
    note_id,
    prompt_text,
    raw_response,
    parsed_output,
    duration_ms,
    tokens_input,
    tokens_output,
    cost_usd
  FROM llm_operations
  WHERE operation_type = 'classification'
  LIMIT 1
" | python -m json.tool
```

---

## What You Can Now Answer

### Debugging Questions

**"Why did this note get classified as is_knowledge=true?"**
```sql
SELECT parsed_output
FROM llm_operations
WHERE note_id = 'xxx' AND operation_type = 'classification'
```
→ See full LLM reasoning

**"What entities were extracted?"**
```sql
SELECT parsed_output
FROM llm_operations
WHERE note_id = 'xxx' AND operation_type = 'enrichment'
```
→ See complete entity list

**"Which link suggestions were rejected?"**
```sql
SELECT parsed_output
FROM llm_operations
WHERE operation_type = 'consolidation'
```
→ See all suggested links (compare with notes_links to find rejected ones)

### Performance Questions

**"How long does classification take on average?"**
```sql
SELECT AVG(duration_ms) FROM llm_operations WHERE operation_type = 'classification'
```

**"What's my total LLM cost this week?"**
```sql
SELECT SUM(cost_usd) FROM llm_operations WHERE created >= datetime('now', '-7 days')
```

**"Which operation uses the most tokens?"**
```sql
SELECT operation_type, AVG(tokens_input + tokens_output) as avg_tokens
FROM llm_operations
GROUP BY operation_type
ORDER BY avg_tokens DESC
```

### Quality Questions

**"How often does enrichment fail to extract people?"**
```sql
-- Compare parsed_output (what LLM returned) with notes_entities (what was stored)
-- Can build complex queries to analyze extraction accuracy
```

**"Are prompts getting better over time?"**
```sql
-- Add prompt_version tracking, then compare success rates
SELECT prompt_version, AVG(success) FROM llm_operations GROUP BY prompt_version
```

---

## Next Steps: Traditional NLP Integration

Now that you have **full visibility** into LLM performance, you can make data-driven decisions:

### After Analyzing Test Data:

**If entity extraction is accurate (>90%):**
→ Keep LLM-based extraction

**If entity extraction is inconsistent:**
→ Try spaCy NER for people
→ Try KeyBERT for topics
→ Compare accuracy

**If time parsing is wrong:**
→ Add dateparser as preprocessor
→ Pass parsed dates to LLM as hints

**If costs are high:**
→ Identify which operations to optimize first
→ Consider smaller models for simple tasks

### Example Decision Tree:

1. Run test dataset (30 notes)
2. Check `llm_operations` table
3. Calculate:
   - Classification accuracy (compare expected vs actual dimensions)
   - Entity extraction quality (manual review of 10 samples)
   - Total cost ($X for 30 notes = $Y for 1000 notes)
4. Decide:
   - Cost acceptable? Keep current approach
   - Entities wrong? Try spaCy
   - Time parsing wrong? Add dateparser
   - All good? Test with real usage!

---

## Files Changed

```
api/db/schema.py                    # Added llm_operations table
api/llm/audit.py                    # NEW - Audit logging helpers
api/services/capture.py             # Added tracking to classification
api/services/enrichment.py          # Added tracking to enrichment
api/services/consolidation.py       # Added tracking to consolidation
test_data/test_notes.csv            # NEW - Test dataset
scripts/import_test_notes.py        # NEW - CSV importer
scripts/analyze_llm_decisions.py    # (existing, still works)
```

---

## Success Metrics

After importing test notes, you should see:

✅ 30 notes in `notes_meta`
✅ 60 operations in `llm_operations` (30 classification + 30 enrichment)
✅ Full token counts and costs tracked
✅ All prompts and responses logged
✅ Average duration < 3 seconds per note

**Then you can confidently answer:** "Should I add traditional NLP?"

The data will tell you! 🎯
