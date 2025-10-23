<script setup lang="ts">
import { ref, computed, nextTick, onUnmounted } from 'vue'
import { useNoteCapture } from '@/composables/useNoteCapture'
import { useToast } from '@/composables/useToast'
import StickyNote from '@/components/StickyNote.vue'
import MomoDropZone from '@/components/MomoDropZone.vue'
import TagAutocomplete from '@/components/TagAutocomplete.vue'
import { colors } from '@/design/colors'
import { typography } from '@/design/typography'
import { spacing, borderRadius } from '@/design/spacing'

const noteText = ref('')
const { isLoading, error, capture, cleanup } = useNoteCapture()
const { success, info, error: errorToast } = useToast()

// Drag state
const isDragging = ref(false)

// Background processing state (for keeping Momo chewing during full process)
const isBackgroundProcessing = ref(false)

// Success state (show sparkles after processing)
const showSuccess = ref(false)

// Sticky note ref
const stickyNoteRef = ref<InstanceType<typeof StickyNote> | null>(null)

// Autocomplete state
const showAutocomplete = ref(false)
const autocompleteQuery = ref('')
const autocompletePosition = ref({ top: 0, left: 0 })

// Computed: Momo is processing if either initial save OR background processing
const isMomoProcessing = computed(() => isLoading.value || isBackgroundProcessing.value)

// Handle note drop on Momo
const handleNoteDrop = async (noteTextValue: string) => {
  // Start background processing
  isBackgroundProcessing.value = true

  try {
    const result = await capture(noteTextValue, (_noteId, title) => {
      // Called when background classification completes (~6 seconds)
      success(`✨ Classification complete: "${title}"`, 5000)

      // Stop background processing and show success sparkles
      isBackgroundProcessing.value = false
      showSuccess.value = true

      // Return to default after showing sparkles for 2 seconds
      setTimeout(() => {
        showSuccess.value = false
      }, 2000)
    })

    if (result) {
      // Show immediate success
      success(`✓ Note saved: "${result.title}"`)

      // Clear note immediately for next one
      noteText.value = ''

      // Show info about background processing
      setTimeout(() => {
        info('⏳ Adding dimensions and tags...', 4000)
      }, 500)
    } else {
      // If capture failed, stop background processing
      isBackgroundProcessing.value = false

      // Show error toast if we have an error message
      if (error.value) {
        errorToast(`Failed to save note: ${error.value}`)
      }
    }
  } catch (err) {
    // Unexpected error - ensure cleanup
    isBackgroundProcessing.value = false
    console.error('Unexpected error in handleNoteDrop:', err)
    errorToast('An unexpected error occurred while saving your note. Please try again.')
  }
}

// Drag handlers
const handleDragStart = () => {
  isDragging.value = true
}

const handleDragEnd = () => {
  isDragging.value = false
}

// Keyboard shortcut: Cmd/Ctrl+Enter to save
const handleKeydown = (event: KeyboardEvent) => {
  // Allow Cmd/Ctrl+Enter as keyboard alternative to drag-drop for accessibility
  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
    event.preventDefault()
    if (noteText.value.trim()) {
      handleNoteDrop(noteText.value)
    }
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

    // Calculate position (using the textarea from the event)
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

  // Split text into lines to measure the last line's width
  const lines = textBeforeCursor.split('\n')
  const lastLine = lines[lines.length - 1]

  // Add all text to measure height
  div.textContent = textBeforeCursor

  // Create a span for measuring the actual width of the last line
  const span = document.createElement('span')
  span.textContent = lastLine

  // Copy font styles to span for accurate measurement
  stylesToCopy.forEach(style => {
    span.style[style as any] = computed[style as any]
  })
  span.style.position = 'absolute'
  span.style.visibility = 'hidden'
  span.style.whiteSpace = 'pre'

  // Add to DOM, measure, remove
  document.body.appendChild(div)
  document.body.appendChild(span)

  const rect = textarea.getBoundingClientRect()

  // Get scroll position
  const scrollTop = textarea.scrollTop
  const scrollLeft = textarea.scrollLeft

  // Calculate position
  const divHeight = div.offsetHeight
  const lastLineWidth = span.offsetWidth

  document.body.removeChild(div)
  document.body.removeChild(span)

  return {
    top: rect.top + divHeight - scrollTop + 5,  // 5px below cursor
    left: rect.left + lastLineWidth - scrollLeft
  }
}

// Handle tag selection from autocomplete
function handleTagSelect(tagName: string) {
  // Get the textarea element from the StickyNote component
  const textarea = stickyNoteRef.value?.$el?.querySelector('textarea') as HTMLTextAreaElement | null
  if (!textarea) return

  const text = noteText.value
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

// Cleanup polling intervals when component unmounts
onUnmounted(() => {
  cleanup()
})
</script>

<template>
  <div class="capture-view">
    <div class="capture-view__header">
      <h2 :style="{ fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.semibold }">
        Capture Your Thoughts
      </h2>
      <p :style="{ color: colors.text.muted, fontSize: typography.fontSize.base }">
        Write on a sticky note and drag it to Momo to save!
      </p>
    </div>

    <div class="capture-view__workspace">
      <!-- Left: Sticky Note -->
      <div class="capture-view__note-area">
        <StickyNote
          ref="stickyNoteRef"
          v-model="noteText"
          placeholder="Write your note here...

Tip: Use #tags for organization
(e.g., #project/alpha, #health/fitness)

Drag to Momo when ready! →"
          :isDragging="isDragging"
          @drag-start="handleDragStart"
          @drag-end="handleDragEnd"
          @input="handleInput"
          @keydown="handleKeydown"
        />

        <!-- Tag Autocomplete Dropdown -->
        <TagAutocomplete
          v-if="showAutocomplete"
          :query="autocompleteQuery"
          :position="autocompletePosition"
          @select="handleTagSelect"
          @close="showAutocomplete = false"
        />
      </div>

      <!-- Right: Momo Drop Zone -->
      <div class="capture-view__momo-area">
        <MomoDropZone
          :size="200"
          :isProcessing="isMomoProcessing"
          :hasContent="!!noteText.trim()"
          :showSuccess="showSuccess"
          @note-dropped="handleNoteDrop"
        />

        <p :style="{
          textAlign: 'center',
          color: colors.text.muted,
          fontSize: typography.fontSize.sm,
          marginTop: spacing[4]
        }">
          {{ isMomoProcessing ? 'Nom nom nom...' : (noteText.trim() ? 'Ready to eat! 😋' : 'Drag notes here!') }}
        </p>
      </div>
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
        marginTop: spacing[6],
        fontSize: typography.fontSize.sm,
        color: colors.text.muted,
        textAlign: 'center'
      }"
    >
      💡 Your notes are automatically enriched with AI-powered classification and tags.
    </div>
  </div>
</template>

<script lang="ts">
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
  max-width: 1200px;
  margin: 0 auto;
  padding: v-bind('spacing[6]');
}

.capture-view__header {
  margin-bottom: v-bind('spacing[8]');
  text-align: center;
}

.capture-view__header p {
  margin-top: v-bind('spacing[2]');
}

.capture-view__workspace {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: v-bind('spacing[8]');
  align-items: start;
  margin-bottom: v-bind('spacing[6]');
}

.capture-view__note-area {
  position: relative;
  display: flex;
  justify-content: center;
}

.capture-view__momo-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.capture-status {
  animation: slideIn 200ms ease;
  text-align: center;
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

/* Responsive: stack on smaller screens */
@media (max-width: 768px) {
  .capture-view__workspace {
    grid-template-columns: 1fr;
    gap: v-bind('spacing[6]');
  }

  .capture-view__momo-area {
    min-height: 300px;
  }
}
</style>
