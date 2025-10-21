# Entity Extraction Research & Classification Model Redesign

**Date**: 2025-10-20
**Status**: Research Complete → Implementing Rewrite
**Decision**: Replace dimension-based classification with entity-based extraction

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Initial System Analysis](#initial-system-analysis)
3. [Research Questions](#research-questions)
4. [Testing Methodology](#testing-methodology)
5. [Key Findings](#key-findings)
6. [Critical Bug Discovery](#critical-bug-discovery)
7. [Final Test Results](#final-test-results)
8. [Architectural Decision](#architectural-decision)
9. [Next Steps](#next-steps)

---

## Problem Statement

### Original Concern
The classification system relied heavily on LLM abilities with a complex multi-dimensional classification approach (5 boolean dimensions + title + tags + status extraction in a single call). The question arose: **Are we asking the LLM to do too much at once? Should we use traditional NLP for simpler extraction tasks?**

### Specific Issues Identified
1. **Cognitive Overload**: Single LLM call performing multiple tasks simultaneously:
   - Generate creative title (10 words max)
   - Extract 5 boolean dimensions (has_action_items, is_social, is_emotional, is_knowledge, is_exploratory)
   - Generate relevant tags (3-6 keywords)
   - Determine status (todo/in_progress/done)
   - Provide reasoning

2. **Redundant Extraction**: Second LLM call (enrichment) re-extracted the same 5 dimensions

3. **Low Initial Accuracy**: Dimension classification showed only 43.3% perfect match accuracy (13/30 notes)

4. **Conceptual Misalignment**: Classification dimensions (HOW you're thinking) don't align well with clustering needs (WHAT you're thinking about)

---

## Initial System Analysis

### Current Architecture (Dimension-Based)

```
Input: "I have a dental appointment on October 25 at 5 pm"
  ↓
LLM Call 1: classify_note_async()
  → Extract: title, tags, 5 dimensions, status, reasoning
  → Dimensions: {has_action_items: false, ...} ❌ Missed!
  ↓
LLM Call 2: enrich_note_metadata()
  → Extract: people, entities, emotions, time_references
  → Also extracts 5 dimensions again (redundant!)
  ↓
Store in database:
  - notes_meta: dimension boolean columns
  - notes_entities: entity extraction results
```

**Problems**:
- Poor accuracy on dimension classification (43.3%)
- LLM doing too many tasks at once
- Dimensions don't help with clustering (how you think ≠ what you think about)

### Key Insight: Extract vs Classify

Extraction and classification were being conflated:

| Type | Definition | Examples | Best Approach |
|------|------------|----------|---------------|
| **Extraction** | Objective facts (what IS in the text) | People: "Sarah", Dates: "Oct 25", Entities: "FAISS" | Traditional NLP (spaCy, dateparser) |
| **Classification** | Subjective interpretation (what does it MEAN) | Is this emotional? Is this exploratory? | LLM reasoning |

**Realization**: We were asking the LLM to do extraction + classification + generation simultaneously.

---

## Research Questions

### Primary Question
**Should we separate extraction tasks and use traditional NLP where appropriate?**

Specifically:
1. Can traditional NLP (spaCy, dateparser, regex) extract WHO/WHAT/WHEN/WHERE more accurately?
2. How much faster is traditional NLP vs pure LLM?
3. What's the quality-speed tradeoff?

### Framework: 5W1H Entity Model

Shifted from abstract "dimensions" to concrete "entities":

| Question | What We Extract | Purpose |
|----------|----------------|---------|
| **WHO** | People, organizations | Relationship-based memory clustering |
| **WHAT** | Concepts, topics, projects, tools | Topic-based memory clustering |
| **WHEN** | Dates, times, deadlines, durations | Temporal context, actionability |
| **WHERE** | Physical/virtual/contextual locations | Context-based memory |
| **HOW** | Action items, todos | Secondary metadata (lifecycle tracking) |
| **WHY** | Purpose, emotional context | Secondary metadata (intent tracking) |

**Key decision**: WHO/WHAT/WHEN/WHERE should drive clustering (content-based), while HOW/WHY are secondary metadata for filtering.

---

## Testing Methodology

### Test Dataset
- **Source**: 30 diverse notes from existing test_notes.csv
- **Coverage**:
  - Simple action items ("Call Mom tomorrow at 2pm")
  - Technical knowledge ("Python async/await patterns...")
  - Social interactions ("Met with Sarah to discuss...")
  - Emotional reflections ("Feeling overwhelmed...")
  - Mixed types ("Team standup with action items")

### Benchmark Labeling Process
Used 6 Claude agents (5 notes each) to manually label expected entities:
- Consistent labeling criteria
- Context date: 2025-10-20 for resolving relative dates
- Format: JSON with who/what/when/where arrays

### Comparison Approaches

**Approach 1: Pure LLM**
```python
async def extract_entities_llm(text, current_date):
    """Single LLM call to extract WHO/WHAT/WHEN/WHERE"""
    # Prompt with instructions + context date
    # Output: JSON with entity arrays
```

**Approach 2: Hybrid NLP**
```python
def extract_entities_hybrid(text, current_date):
    """Traditional NLP libraries for extraction"""
    # spaCy: WHO (PERSON entities), WHERE (GPE, LOC, FAC)
    # dateparser: WHEN (time reference parsing)
    # spaCy noun chunks: WHAT (concepts)
```

### Evaluation Metrics
- **Precision**: Of extracted entities, how many are correct?
- **Recall**: Of expected entities, how many were found?
- **F1 Score**: Harmonic mean of precision and recall
- **Execution Time**: Speed comparison (ms per note)

---

## Key Findings

### Initial Test Results (CONTAMINATED)

**First run showed suspicious results**:

| Field | LLM F1 | Hybrid F1 | Winner |
|-------|--------|-----------|--------|
| WHO | 0.833 | 0.850 | Hybrid |
| WHAT | 0.404 | 0.425 | Hybrid |
| WHEN | 0.656 | 0.944 | Hybrid (decisive) |
| WHERE | 0.700 | 0.767 | Hybrid |

**Speed**: Hybrid 17.8x faster (235ms vs 4192ms)

**Red Flag**: LLM performed poorly across all categories except WHEN still dominated by hybrid.

---

## Critical Bug Discovery

### Line-by-Line Audit Revealed Hallucinations

**User requested**: "Review the results line by line to determine if the test is trustworthy"

**Findings from manual inspection**:

**Note 7**: "Python async/await patterns: Use asyncio.gather()..."
```json
// LLM extracted:
{
  "who": ["Sarah", "Tom"],  // ❌ NOT in the note!
  "what": ["FAISS", "vector search", "memory consolidation"],  // ❌ NOT in the note!
  "when": ["today", "tomorrow at 2pm"],  // ❌ NOT in the note!
  "where": ["coffee shop", "Zoom"]  // ❌ NOT in the note!
}
```

**Pattern observed**: Multiple notes (7, 13, 17, 21, 24, 25, 29) showed **identical hallucinations**:
- People: "Sarah", "Tom"
- Places: "coffee shop", "Zoom"
- Concepts: "FAISS", "vector search", "memory consolidation", "API rate limiting"

### Root Cause Analysis

**Hypothesis 1**: LangChain caching?
- ❌ No explicit cache enabled in client.py

**Hypothesis 2**: LLM context bleeding between calls?
- ❌ Using `ainvoke()` separately for each note

**Hypothesis 3**: Prompt contamination?
- ✅ **FOUND IT!**

**The Smoking Gun** - Prompt contained concrete examples:

```python
# In the prompt template:
**Output format**:
{
  "who": ["Sarah", "Tom"],  # ← LLM copied these!
  "what": ["memory consolidation", "hippocampus", "note-taking systems"],
  "where": ["coffee shop", "Zoom"]  # ← LLM copied these!
}

# In the instructions:
- Be granular: e.g., "FAISS" and "vector search"  # ← LLM copied these!
- Keep multi-word: e.g., "memory consolidation", "API rate limiting"  # ← LLM copied these!
- Virtual locations like "Zoom", contextual like "meeting"  # ← LLM copied these!
```

**Why it happened**: When the LLM was uncertain or the note had minimal entities, it **defaulted to copying the examples** from the prompt instead of returning empty arrays.

### The Fix

**Before**:
```python
{
  "who": ["Sarah", "Tom"],
  "where": ["coffee shop", "Zoom"]
}
```

**After**:
```python
{
  "who": ["<person_name_1>", "<person_name_2>"],
  "where": ["<location_1>"]
}

**CRITICAL RULES**:
- Extract ONLY entities EXPLICITLY MENTIONED in the note text
- Do NOT copy these placeholder examples
- Empty arrays REQUIRED if nothing found
```

Also removed concrete examples from instruction text:
- ❌ Before: `e.g., "FAISS" and "vector search"`
- ✅ After: `separate compound concepts into individual entities`

---

## Final Test Results (Clean, Trustworthy)

### After Fixing Hallucination Bug

| Field | LLM F1 | Hybrid F1 | Winner | Change from Before |
|-------|--------|-----------|--------|-------------------|
| **WHO** | **0.933** | 0.850 | **LLM** | +12% (0.833→0.933) ✅ |
| **WHAT** | **0.691** | 0.425 | **LLM** | +71% (0.404→0.691) 🚀 |
| **WHEN** | 0.833 | **0.944** | **Hybrid** | +27% (0.656→0.833) ✅ |
| **WHERE** | **0.900** | 0.767 | **LLM** | +29% (0.700→0.900) ✅ |

**Execution Time**:
- LLM: 3480ms per note
- Hybrid: 246ms per note
- **Speedup**: 14.2x faster (hybrid)

**Win Counts** (out of 30 notes):
- WHO: LLM=4, Hybrid=1, Tie=25
- WHAT: LLM=24, Hybrid=3, Tie=3 ← **LLM dominates**
- WHEN: LLM=3, Hybrid=5, Tie=22
- WHERE: LLM=4, Hybrid=0, Tie=26

### Key Insights from Clean Results

1. **LLM Excels at Semantic Understanding** (WHO/WHAT/WHERE)
   - Catches relationship terms as people ("Mom", "client", "PM")
   - Understands compound concepts better than spaCy noun chunks
   - Recognizes contextual locations ("team meeting", "call")

2. **Traditional NLP Excels at Rule-Based Tasks** (WHEN)
   - dateparser: 0.944 F1 (extremely reliable)
   - LLM date parsing: 0.833 F1 (good, but makes errors)
   - 14.2x faster execution

3. **WHAT Extraction is Hardest** (Both struggle)
   - LLM: 0.691 F1 (best we have, but still missing 30%)
   - Hybrid: 0.425 F1 (spaCy noun chunks too noisy)
   - Challenge: Determining concept granularity
     - Is "authentication refactor" one concept or two?
     - Should we extract "OAuth2" separately or as part of "authentication"?

4. **Speed vs Accuracy Tradeoff**
   - Pure LLM: Best accuracy, slow (3.5s per note)
   - Pure NLP: Fast, poor accuracy on concepts (246ms)
   - **Optimal**: Hybrid approach using best of both

---

## Architectural Decision

### Decision: Entity-Based Classification (Rewrite)

**What we're replacing**:
```
OLD: Dimension-based classification
- 5 boolean dimensions (has_action_items, is_social, is_emotional, is_knowledge, is_exploratory)
- Focus on "how you're thinking"
- 43.3% accuracy
- Doesn't align with clustering needs
```

**What we're building**:
```
NEW: Entity-based extraction
- WHO/WHAT/WHEN/WHERE entities
- Focus on "what you're thinking about"
- 0.691-0.944 F1 accuracy per field
- Directly enables entity co-occurrence clustering
```

### Proposed Architecture

```
classify_and_save endpoint:
  ↓
Step 1: Extract Entities (Optimal Hybrid)
  ├─ LLM Call: Extract WHO + WHAT + WHERE
  │  → Prompt: Entity extraction focused
  │  → Output: {who: [], what: [], where: []}
  │  → Accuracy: 0.933, 0.691, 0.900 F1
  │
  └─ dateparser: Extract WHEN
     → Regex + dateparser library
     → Output: {when: [{original, parsed, type}]}
     → Accuracy: 0.944 F1
  ↓
Step 2: Generate Metadata
  ├─ LLM Call: Generate title + tags using entity context
  │  → Input: Note text + extracted entities
  │  → Output: {title, tags}
  │
  └─ Derive lifecycle metadata
     → has_action_items: Check for WHEN (future dates) + action verbs
     → needs_review: Heuristic-based flagging
  ↓
Step 3: Store in Database
  ├─ notes_meta: Core metadata (no dimension columns)
  ├─ notes_entities: WHO/WHAT/WHERE entities
  └─ notes_dimensions: WHEN time references
  ↓
Step 4: Entity-Based Clustering (Future Work)
  └─ Build entity co-occurrence graph
     → Notes sharing entities cluster together
     → Use for consolidation/link suggestions
```

### Why Rewrite (Not Modify)?

**Context**:
- No external users yet
- Only 30 test notes in CSV (no production data loss)
- Current system has fundamental architectural misalignment

**Benefits of Clean Rewrite**:
1. ✅ **No technical debt**: Start with correct architecture
2. ✅ **Optimized for clustering**: Entity-first design from day 1
3. ✅ **Higher accuracy**: 0.691-0.944 F1 vs 0.433 overall
4. ✅ **Cleaner codebase**: Remove deprecated dimension code
5. ✅ **Better separation of concerns**: Extraction → Generation → Storage

**Risks Mitigated**:
- No user impact (no users yet)
- No data migration needed (regenerate from CSV)
- Can test thoroughly before launch

---

## Discovered Patterns & Best Practices

### Prompt Engineering for Extraction

**❌ Don't:**
- Use concrete examples in prompts ("Sarah", "FAISS", "coffee shop")
- Mix instruction examples with output format examples
- Ask LLM to do too many tasks in one call

**✅ Do:**
- Use abstract placeholders (`<person_name_1>`, `<concept_1>`)
- Explicitly warn: "Do NOT copy these placeholders"
- Provide empty array examples: `{who: [], what: [], when: [], where: []}`
- Single responsibility per LLM call

### Entity Granularity Rules

**WHO**:
- Extract ALL people mentioned (proper names + relationship terms)
- "Sarah" ✓, "Mom" ✓, "client" ✓, "PM" ✓
- Normalize capitalization

**WHAT**:
- Extract specific technologies, concepts, projects
- Prefer granular over broad: ["Redis", "caching"] not ["caching systems"]
- Keep multi-word compound nouns: ["memory consolidation"] not ["memory", "consolidation"]
- Limit: ~5-10 concepts per note (avoid over-extraction)

**WHEN**:
- Extract verbatim + parse to ISO format
- Types: absolute, relative, duration, recurring
- Always use dateparser for parsing (not LLM)
- Return: `{original: "tomorrow at 2pm", parsed: "2025-10-21T14:00:00", type: "relative"}`

**WHERE**:
- Physical places: "Café Awesome", "Stanford"
- Virtual places: "Zoom", "Slack"
- Contextual: "team meeting", "standup", "call"

### When to Use LLM vs Traditional NLP

| Task | Best Approach | Reason |
|------|---------------|--------|
| People extraction | LLM (0.933 F1) | Catches relationship terms ("Mom", "client") |
| Concept extraction | LLM (0.691 F1) | Requires semantic understanding |
| Location extraction | LLM (0.900 F1) | Contextual locations need reasoning |
| Time extraction | dateparser (0.944 F1) | Rule-based is faster + more accurate |
| Title generation | LLM | Creative task |
| Tag generation | LLM | Requires understanding of relevance |

---

## Next Steps

### Immediate: Implementation (This Week)

1. **Create New Services**:
   - `api/services/entity_capture.py`
     - `extract_entities_optimal()`: Hybrid LLM + dateparser
     - `generate_metadata_from_entities()`: Title/tags from entities

2. **Update Database Schema**:
   - Remove dimension boolean columns from `notes_meta`
   - Keep `notes_entities` and `notes_dimensions` tables
   - Add `schema_version` column for future migrations

3. **Rewrite Endpoint**:
   - Modify `classify_and_save()` to use new entity-based flow
   - Update response model (remove dimensions)
   - Add entity arrays to response

4. **Testing**:
   - Clear database
   - Re-import 30 test notes using new system
   - Validate entity extraction quality
   - Compare before/after outputs

### Future: Clustering Research (Next Phase)

**Status**: Not yet decided, more research needed

**Hypotheses to test**:
1. Can entity co-occurrence create meaningful clusters?
2. What's the minimum overlap threshold? (1, 2, or 3 shared entities?)
3. Which entities drive clustering? (WHO only? WHAT only? Both?)
4. How does entity-based clustering compare to LLM link suggestions?

**Approach**:
1. Implement entity co-occurrence graph builder
2. Run Louvain clustering algorithm
3. Manually review cluster quality on test dataset
4. Compare with existing link-based clustering
5. Decide on hybrid approach (entity clusters + LLM links)

**Decision criteria**:
- Cluster coherence (do grouped notes make sense?)
- Coverage (what % of notes get clustered?)
- Performance (how fast is graph building?)
- Comparison with manual clustering expectations

---

## Lessons Learned

### 1. Always Audit Test Results
**What happened**: Initial test showed poor LLM performance, but line-by-line audit revealed hallucination bug
**Lesson**: Never trust aggregate metrics alone - inspect individual failures

### 2. Prompt Examples Can Contaminate Results
**What happened**: Concrete examples in prompts were copied by LLM
**Lesson**: Use abstract placeholders, warn against copying, test with edge cases

### 3. Separate Concerns: Extract vs Classify vs Generate
**What happened**: Single LLM call doing too many tasks led to poor accuracy
**Lesson**: One responsibility per LLM call, compose results for complex workflows

### 4. Traditional NLP Still Valuable
**What happened**: dateparser outperformed LLM on time parsing (0.944 vs 0.833)
**Lesson**: Don't default to LLM for everything - rule-based systems excel at structured tasks

### 5. Align Architecture with End Goals
**What happened**: Dimension classification didn't support clustering needs
**Lesson**: Design extraction around how data will be used (clustering → entities, not dimensions)

---

## References

### Files Modified/Created During Research
- `test_data/test_notes.csv` - Test dataset (stripped to single column)
- `test_data/test_notes_labeled.csv` - Manually labeled benchmark
- `api/services/entity_extraction.py` - LLM vs Hybrid extraction implementations
- `scripts/test_entity_extraction.py` - Comparison test script
- `scripts/test_llm_fix.py` - Hallucination bug verification
- `test_data/entity_extraction_comparison.csv` - Final test results

### Key Metrics Summary
| Metric | Value |
|--------|-------|
| Test dataset size | 30 notes |
| Benchmark labeling | 6 agents × 5 notes each |
| LLM average F1 | 0.839 (WHO/WHAT/WHERE), 0.833 (WHEN) |
| Hybrid average F1 | 0.681 (WHO/WHAT/WHERE), 0.944 (WHEN) |
| Optimal hybrid F1 | 0.841 average (LLM for WHO/WHAT/WHERE, dateparser for WHEN) |
| Speed improvement | 14.2x faster (hybrid vs pure LLM) |
| Dimension classification accuracy (old) | 43.3% |
| Entity extraction accuracy (new) | 69-94% per field |

---

**End of Research Document**
