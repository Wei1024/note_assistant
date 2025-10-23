<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useNoteCapture } from '@/composables/useNoteCapture'
import { useToast } from '@/composables/useToast'
import Button from '@/components/shared/Button.vue'
import TagAutocomplete from '@/components/TagAutocomplete.vue'
import { colors } from '@/design/colors'
import { typography } from '@/design/typography'
import { spacing, borderRadius } from '@/design/spacing'

const noteText = ref('')
const { isLoading, error, capture } = useNoteCapture()
const { success, info } = useToast()

// Textarea ref for direct manipulation
const textareaRef = ref<HTMLTextAreaElement | null>(null)

// Autocomplete state
const showAutocomplete = ref(false)
const autocompleteQuery = ref('')
const autocompletePosition = ref({ top: 0, left: 0 })

const handleSave = async () => {
  const text = noteText.value

  const result = await capture(text, (_noteId, title) => {
    // Called when background classification completes
    success(`✨ Classification complete: "${title}"`, 5000)
  })

  if (result) {
    // Show immediate success
    success(`✓ Note saved: "${result.title}"`)

    // Clear textarea immediately for next note
    noteText.value = ''

    // Show info about background processing
    setTimeout(() => {
      info('⏳ Adding dimensions and tags...', 4000)
    }, 500)
  }
}

// Keyboard shortcut: Cmd/Ctrl+Enter to save
const handleKeydown = (event: KeyboardEvent) => {
  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
    event.preventDefault()
    handleSave()
  }
}

// Handle input to detect hashtag autocomplete
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

// Calculate cursor position for autocomplete dropdown
function calculateCursorPosition(textarea: HTMLTextAreaElement) {
  // Create invisible mirror div to measure cursor position
  const div = document.createElement('div')
  const computed = window.getComputedStyle(textarea)

  // Copy styles
  const stylesToCopy = [
    'fontSize', 'fontFamily', 'fontWeight', 'fontStyle',
    'letterSpacing', 'textTransform', 'wordSpacing',
    'textIndent', 'whiteSpace', 'lineHeight',
    'padding', 'border', 'boxSizing'
  ]

  stylesToCopy.forEach(style => {
    div.style[style as any] = computed[style as any]
  })

  div.style.position = 'absolute'
  div.style.visibility = 'hidden'
  div.style.whiteSpace = 'pre-wrap'
  div.style.wordWrap = 'break-word'
  div.style.width = textarea.offsetWidth + 'px'

  // Copy text up to cursor
  const textBeforeCursor = textarea.value.substring(0, textarea.selectionStart)
  div.textContent = textBeforeCursor

  // Add to DOM, measure, remove
  document.body.appendChild(div)
  const rect = textarea.getBoundingClientRect()

  // Get scroll position
  const scrollTop = textarea.scrollTop
  const scrollLeft = textarea.scrollLeft

  // Calculate position
  const divHeight = div.offsetHeight
  const divWidth = div.offsetWidth

  document.body.removeChild(div)

  return {
    top: rect.top + divHeight - scrollTop + 5,  // 5px below cursor
    left: rect.left + divWidth - scrollLeft
  }
}

// Handle tag selection from autocomplete
function handleTagSelect(tagName: string) {
  if (!textareaRef.value) return

  const textarea = textareaRef.value
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
</script>

<template>
  <div class="capture-view">
    <div class="capture-view__header">
      <h2 :style="{ fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.semibold }">
        Capture Your Thoughts
      </h2>
      <p :style="{ color: colors.text.muted, fontSize: typography.fontSize.base }">
        Write naturally. Notes are saved instantly and enriched with AI-powered classification.
      </p>
    </div>

    <div class="capture-view__content">
      <!-- Textarea - never disabled, always ready -->
      <textarea
        ref="textareaRef"
        v-model="noteText"
        placeholder="Type your note here... Meeting notes, ideas, tasks, or anything else on your mind.

Tip: Press Cmd+Enter (Mac) or Ctrl+Enter (Windows) to save quickly.
Use #tags for organization (e.g., #project/alpha, #health/fitness)"
        class="capture-textarea"
        :style="textareaStyle as any"
        @input="handleInput"
        @keydown="handleKeydown"
        autofocus
      />

      <!-- Tag Autocomplete Dropdown -->
      <TagAutocomplete
        v-if="showAutocomplete"
        :query="autocompleteQuery"
        :position="autocompletePosition"
        @select="handleTagSelect"
        @close="showAutocomplete = false"
      />

      <!-- Action button -->
      <div class="capture-actions">
        <Button
          variant="primary"
          size="lg"
          icon="note"
          :loading="isLoading"
          :disabled="!noteText.trim()"
          @click="handleSave"
        >
          Save Note
        </Button>

        <span
          v-if="noteText.trim()"
          :style="{
            fontSize: typography.fontSize.sm,
            color: colors.text.muted,
            alignSelf: 'center'
          }"
        >
          or press ⌘+Enter
        </span>
      </div>

      <!-- Error message -->
      <div
        v-if="error"
        class="capture-status capture-status--error"
        :style="statusErrorStyle"
      >
        ✗ {{ error }}
      </div>

      <!-- Info message -->
      <div
        v-if="!error"
        :style="{
          marginTop: spacing[4],
          fontSize: typography.fontSize.sm,
          color: colors.text.muted
        }"
      >
        💡 Your notes are automatically enriched with dimensions, tags, and metadata.
        View classification results in the Search view.
      </div>
    </div>
  </div>
</template>

<script lang="ts">
const textareaStyle = {
  width: '100%',
  minHeight: '400px',
  padding: spacing[4],
  fontSize: typography.fontSize.base,
  fontFamily: typography.fontFamily.sans,
  lineHeight: typography.lineHeight.relaxed,
  backgroundColor: colors.background.card,
  color: colors.text.primary,
  border: `1px solid ${colors.border.default}`,
  borderRadius: borderRadius.lg,
  resize: 'vertical' as const,
  transition: 'all 200ms ease',
}

const statusErrorStyle = {
  padding: spacing[4],
  backgroundColor: colors.status.error + '15',
  color: colors.status.error,
  border: `1px solid ${colors.status.error}`,
  borderRadius: borderRadius.lg,
  marginTop: spacing[4],
}
</script>

<style scoped>
.capture-view {
  max-width: 900px;
  margin: 0 auto;
}

.capture-view__header {
  margin-bottom: v-bind('spacing[8]');
}

.capture-view__header p {
  margin-top: v-bind('spacing[2]');
}

.capture-view__content {
  display: flex;
  flex-direction: column;
}

.capture-textarea:focus {
  outline: none;
  border-color: v-bind('colors.accent.primary');
  box-shadow: 0 0 0 3px rgba(212, 122, 68, 0.1);
}

.capture-actions {
  display: flex;
  gap: v-bind('spacing[4]');
  align-items: center;
  margin-top: v-bind('spacing[4]');
}

.capture-status {
  animation: slideIn 200ms ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
