# Frontend Tag Autocomplete - Implementation Plan

**Created:** 2025-10-22
**Status:** Ready to implement

---

## Overview

Add inline `#hashtag` autocomplete to the note editor (`CaptureView.vue`).

**Goal:** When user types `#proj`, show dropdown with matching tags for quick selection.

---

## Current State

**Editor:** `frontend/src/views/CaptureView.vue`
- Simple `<textarea>` (lines 58-67)
- No syntax highlighting, no rich text
- Already has Cmd+Enter save shortcut

**API Ready:**
- ✅ `GET /tags/search?q={query}` - Working
- ✅ Returns fuzzy-matched tags sorted by use_count
- ✅ Tested with curl

---

## Design Approach

### Option A: Inline Autocomplete (Recommended)
**What:** Detect `#` in textarea, show dropdown below cursor

**Pros:**
- Lightweight (no dependencies)
- Works with existing textarea
- Fast to implement

**Cons:**
- Cursor positioning requires calculation
- No syntax highlighting for tags

### Option B: Rich Text Editor (Future)
**What:** Replace textarea with CodeMirror/Monaco

**Pros:**
- Professional editor experience
- Syntax highlighting
- Built-in autocomplete support

**Cons:**
- Heavy dependencies (~200KB+)
- Migration effort
- More complex

**Decision: Go with Option A first**, can upgrade to B later.

---

## Implementation Plan

### Step 1: Create TagAutocomplete Component

**File:** `frontend/src/components/TagAutocomplete.vue`

**Props:**
```typescript
{
  query: string        // Current search query (e.g., "proj")
  position: {          // Where to show dropdown
    top: number,
    left: number
  }
}
```

**Events:**
```typescript
@select="(tag: string) => void"  // User selected a tag
@close="() => void"              // User closed dropdown (Esc)
```

**Component Structure:**
```vue
<template>
  <div
    class="tag-autocomplete"
    :style="{ top: position.top + 'px', left: position.left + 'px' }"
  >
    <div
      v-for="tag in tags"
      :key="tag.id"
      @click="selectTag(tag.name)"
      class="tag-option"
    >
      <span class="tag-name">#{{ tag.name }}</span>
      <span class="tag-count">({{ tag.use_count }})</span>
    </div>

    <div v-if="tags.length === 0" class="no-results">
      Create "#{{ query }}"
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  query: string
  position: { top: number; left: number }
}>()

const emit = defineEmits<{
  select: [tag: string]
  close: []
}>()

const tags = ref<Tag[]>([])

// Watch query, fetch results
watch(() => props.query, async (newQuery) => {
  if (!newQuery) {
    tags.value = []
    return
  }

  const res = await fetch(`http://localhost:8000/tags/search?q=${newQuery}&limit=10`)
  const data = await res.json()
  tags.value = data.tags
})

function selectTag(tagName: string) {
  emit('select', tagName)
}

// Handle Esc key
onMounted(() => {
  const handleEsc = (e: KeyboardEvent) => {
    if (e.key === 'Escape') emit('close')
  }
  window.addEventListener('keydown', handleEsc)
  onUnmounted(() => window.removeEventListener('keydown', handleEsc))
})
</script>
```

### Step 2: Integrate with CaptureView

**File:** `frontend/src/views/CaptureView.vue`

**Changes needed:**

1. **Add state for autocomplete:**
```typescript
const showAutocomplete = ref(false)
const autocompleteQuery = ref('')
const autocompletePosition = ref({ top: 0, left: 0 })
```

2. **Detect `#` keystroke:**
```typescript
const handleInput = (event: Event) => {
  const textarea = event.target as HTMLTextAreaElement
  const text = textarea.value
  const cursorPos = textarea.selectionStart

  // Find if we're after a # character
  const textBeforeCursor = text.substring(0, cursorPos)
  const hashMatch = textBeforeCursor.match(/#([a-zA-Z0-9_/-]*)$/)

  if (hashMatch) {
    // User is typing a hashtag
    showAutocomplete.value = true
    autocompleteQuery.value = hashMatch[1] // Text after #

    // Calculate position
    autocompletePosition.value = calculateCursorPosition(textarea)
  } else {
    showAutocomplete.value = false
  }
}
```

3. **Calculate cursor position:**
```typescript
function calculateCursorPosition(textarea: HTMLTextAreaElement) {
  // Create invisible mirror div to measure cursor position
  const div = document.createElement('div')
  const computed = window.getComputedStyle(textarea)

  // Copy styles
  div.style.cssText = computed.cssText
  div.style.position = 'absolute'
  div.style.visibility = 'hidden'
  div.style.whiteSpace = 'pre-wrap'
  div.style.wordWrap = 'break-word'

  // Copy text up to cursor
  const textBeforeCursor = textarea.value.substring(0, textarea.selectionStart)
  div.textContent = textBeforeCursor

  // Add to DOM, measure, remove
  document.body.appendChild(div)
  const rect = textarea.getBoundingClientRect()
  const height = div.offsetHeight
  const width = div.offsetWidth
  document.body.removeChild(div)

  return {
    top: rect.top + height + 5,  // 5px below cursor
    left: rect.left + width
  }
}
```

4. **Handle tag selection:**
```typescript
function handleTagSelect(tagName: string) {
  const textarea = // get textarea ref
  const text = textarea.value
  const cursorPos = textarea.selectionStart

  // Find the # that started this
  const textBeforeCursor = text.substring(0, cursorPos)
  const hashMatch = textBeforeCursor.match(/#([a-zA-Z0-9_/-]*)$/)

  if (hashMatch) {
    const hashStart = cursorPos - hashMatch[1].length - 1  // -1 for #
    const before = text.substring(0, hashStart)
    const after = text.substring(cursorPos)

    // Replace with selected tag
    noteText.value = before + '#' + tagName + ' ' + after

    // Move cursor after inserted tag
    const newCursorPos = hashStart + tagName.length + 2  // +2 for # and space
    nextTick(() => {
      textarea.selectionStart = newCursorPos
      textarea.selectionEnd = newCursorPos
      textarea.focus()
    })
  }

  showAutocomplete.value = false
}
```

5. **Update template:**
```vue
<textarea
  v-model="noteText"
  @input="handleInput"
  @keydown="handleKeydown"
  ...
/>

<TagAutocomplete
  v-if="showAutocomplete"
  :query="autocompleteQuery"
  :position="autocompletePosition"
  @select="handleTagSelect"
  @close="showAutocomplete = false"
/>
```

---

## Styling

**Autocomplete dropdown:**
```css
.tag-autocomplete {
  position: fixed;
  z-index: 1000;
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  max-height: 300px;
  overflow-y: auto;
  min-width: 200px;
}

.tag-option {
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tag-option:hover {
  background: #f5f5f5;
}

.tag-name {
  font-family: monospace;
  color: #0066cc;
}

.tag-count {
  font-size: 0.85em;
  color: #999;
}

.no-results {
  padding: 12px;
  color: #666;
  font-style: italic;
}
```

---

## Edge Cases to Handle

1. **Typing fast:** Debounce API calls (300ms)
2. **Multiple # in text:** Only trigger on active #
3. **Arrow keys in dropdown:** Navigate options (up/down)
4. **Enter key:** Select highlighted option
5. **Click outside:** Close dropdown
6. **Hierarchical tags:** Show indentation for children
7. **Empty query:** Show recent/popular tags?

---

## Testing Plan

### Manual Tests

1. **Basic autocomplete:**
   - Type `#proj` → See "project", "project/graphrag"
   - Click one → Inserts into text
   - Cursor moves after inserted tag

2. **Keyboard navigation:**
   - Type `#meet`
   - Press Down → Highlight first result
   - Press Enter → Insert tag
   - Press Esc → Close dropdown

3. **Multiple hashtags:**
   - Type "Meeting notes #project/alpha about #client/acme"
   - Each `#` triggers autocomplete independently

4. **No results:**
   - Type `#nonexistent`
   - Show "Create #nonexistent" option
   - Clicking creates new tag

5. **Position calculation:**
   - Type at beginning of textarea → Dropdown below
   - Type at end of long text → Dropdown doesn't overflow screen

### Edge Cases

- Long tag names (truncate or wrap?)
- Very long dropdown list (scroll, pagination?)
- Slow network (loading state?)
- Offline (graceful fallback?)

---

## Future Enhancements

### Phase 2: Keyboard Navigation
- Arrow keys to navigate options
- Enter to select
- Tab to autocomplete first result

### Phase 3: Smart Suggestions
- Show recent tags when typing `#` with no query
- Show related tags based on note content
- Highlight matching characters in results

### Phase 4: Rich Display
- Show tag usage stats inline
- Preview notes using this tag on hover
- Color-code tags by category

### Phase 5: Hierarchical UI
- Indent child tags in dropdown
- Show parent when typing child (e.g., `#alpha` → show under "project")
- Quick navigation: typing `/` shows children

---

## Implementation Checklist

### Component Creation
- [ ] Create `frontend/src/components/TagAutocomplete.vue`
- [ ] Add TypeScript types for Tag interface
- [ ] Implement API fetch with error handling
- [ ] Add loading state
- [ ] Style dropdown with design tokens

### Integration
- [ ] Import component in CaptureView
- [ ] Add `@input` handler to textarea
- [ ] Implement hashtag detection regex
- [ ] Calculate cursor position
- [ ] Handle tag selection and insertion
- [ ] Test cursor positioning after insert

### Polish
- [ ] Add keyboard navigation (arrows, enter, esc)
- [ ] Debounce API calls (300ms)
- [ ] Handle click outside to close
- [ ] Add transitions (fade in/out)
- [ ] Test on different screen sizes
- [ ] Add empty state ("No tags found")

### Testing
- [ ] Manual test all scenarios above
- [ ] Test with 0 tags in database
- [ ] Test with 100+ tags in database
- [ ] Test on mobile (touch)
- [ ] Test with slow network

---

## Estimated Timeline

- **Component creation:** 30-45 min
- **Integration:** 30-45 min
- **Cursor positioning:** 15-30 min (trickiest part)
- **Styling:** 15-20 min
- **Testing & polish:** 30 min

**Total:** 2-2.5 hours

---

## Alternative: Simple MVP

If cursor positioning is too complex, start with simpler version:

**Dropdown at fixed position:**
- Always show at bottom of textarea
- No cursor position calculation
- Still functional, just not as polished

**Pros:** 30 min faster to implement
**Cons:** Less intuitive UX

---

## References

- **API Endpoint:** `api/routes/tags.py` (GET /tags/search)
- **Current Editor:** `frontend/src/views/CaptureView.vue` (line 58-67)
- **Design Tokens:** `frontend/src/design/` (colors, spacing, typography)
- **Similar components:** Look at existing Button, Toast components for style patterns

---

## Questions Before Starting?

1. **Debounce:** Should we debounce API calls? (Recommend: yes, 300ms)
2. **Keyboard nav:** Include in MVP or Phase 2? (Recommend: Phase 2)
3. **Create new tags:** Allow creating tags from autocomplete? (Recommend: Phase 2)
4. **Position:** Cursor-based or fixed? (Recommend: cursor-based for better UX)

Ready to implement!
