<script setup lang="ts">
import { ref, computed } from 'vue'
import { typography } from '@/design/typography'
import { spacing } from '@/design/spacing'

interface Props {
  modelValue: string
  placeholder?: string
  disabled?: boolean
  isDragging?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: string): void
  (e: 'drag-start'): void
  (e: 'drag-end'): void
  (e: 'input', event: Event): void
  (e: 'keydown', event: KeyboardEvent): void
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: 'Type your note here...',
  disabled: false,
  isDragging: false
})

const emit = defineEmits<Emits>()

const textareaRef = ref<HTMLTextAreaElement | null>(null)
const isDraggingInternal = ref(false)

// Random slight rotation for sticky note effect
const rotation = ref((Math.random() - 0.5) * 4) // -2 to 2 degrees

const handleInput = (event: Event) => {
  const target = event.target as HTMLTextAreaElement
  emit('update:modelValue', target.value)
  emit('input', event)
}

const handleKeydown = (event: KeyboardEvent) => {
  emit('keydown', event)
}

// Drag handlers
const handleDragStart = (event: DragEvent) => {
  if (!props.modelValue.trim()) {
    event.preventDefault()
    return
  }

  isDraggingInternal.value = true
  emit('drag-start')

  // Set drag data
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', props.modelValue)
  }
}

const handleDragEnd = () => {
  isDraggingInternal.value = false
  emit('drag-end')
}

const isBeingDragged = computed(() => isDraggingInternal.value || props.isDragging)

// Expose focus method
defineExpose({
  focus: () => textareaRef.value?.focus()
})
</script>

<template>
  <div
    class="sticky-note"
    :class="{ 'sticky-note--dragging': isBeingDragged, 'sticky-note--empty': !modelValue.trim() }"
    :style="{ transform: `rotate(${rotation}deg)` }"
    :draggable="!!modelValue.trim()"
    @dragstart="handleDragStart"
    @dragend="handleDragEnd"
  >
    <!-- Sticky note shadow -->
    <div class="sticky-note__shadow"></div>

    <!-- Sticky note content -->
    <div class="sticky-note__paper">
      <!-- Top edge effect -->
      <div class="sticky-note__top"></div>

      <!-- Textarea -->
      <textarea
        ref="textareaRef"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        class="sticky-note__textarea"
        @input="handleInput"
        @keydown="handleKeydown"
      />

      <!-- Drag hint when note has content -->
      <div v-if="modelValue.trim()" class="sticky-note__drag-hint">
        Drag to Momo 👉
      </div>

      <!-- Momo-inspired decorative elements -->
      <!-- Teal spiral (top-left) -->
      <svg class="sticky-note__spiral sticky-note__spiral--teal" viewBox="0 0 40 40">
        <path d="M20,20 Q25,15 30,20 Q32,25 30,30 Q25,32 20,30 Q15,25 17,20 Q20,17 23,18"
              fill="none"
              stroke="#5FB5A1"
              stroke-width="3"
              stroke-linecap="round"/>
      </svg>

      <!-- Gold spiral (top-right) -->
      <svg class="sticky-note__spiral sticky-note__spiral--gold" viewBox="0 0 40 40">
        <path d="M20,20 Q15,15 10,20 Q8,25 10,30 Q15,32 20,30 Q25,25 23,20 Q20,17 17,18"
              fill="none"
              stroke="#D4A853"
              stroke-width="3"
              stroke-linecap="round"/>
      </svg>

      <!-- Decorative border pattern (braided/woven style) -->
      <svg class="sticky-note__border sticky-note__border--top" viewBox="0 0 400 20" preserveAspectRatio="none">
        <pattern id="braid-pattern-h" x="0" y="0" width="40" height="20" patternUnits="userSpaceOnUse">
          <path d="M0,10 Q10,5 20,10 T40,10" fill="none" stroke="#C97A6B" stroke-width="2" opacity="0.6"/>
          <path d="M0,10 Q10,15 20,10 T40,10" fill="none" stroke="#D4A853" stroke-width="2" opacity="0.5"/>
        </pattern>
        <rect width="400" height="20" fill="url(#braid-pattern-h)"/>
      </svg>

      <svg class="sticky-note__border sticky-note__border--bottom" viewBox="0 0 400 20" preserveAspectRatio="none">
        <pattern id="braid-pattern-h-bottom" x="0" y="0" width="40" height="20" patternUnits="userSpaceOnUse">
          <path d="M0,10 Q10,5 20,10 T40,10" fill="none" stroke="#C97A6B" stroke-width="2" opacity="0.6"/>
          <path d="M0,10 Q10,15 20,10 T40,10" fill="none" stroke="#D4A853" stroke-width="2" opacity="0.5"/>
        </pattern>
        <rect width="400" height="20" fill="url(#braid-pattern-h-bottom)"/>
      </svg>

      <svg class="sticky-note__border sticky-note__border--left" viewBox="0 0 20 300" preserveAspectRatio="none">
        <pattern id="braid-pattern-v" x="0" y="0" width="20" height="40" patternUnits="userSpaceOnUse">
          <path d="M10,0 Q5,10 10,20 T10,40" fill="none" stroke="#C97A6B" stroke-width="2" opacity="0.6"/>
          <path d="M10,0 Q15,10 10,20 T10,40" fill="none" stroke="#D4A853" stroke-width="2" opacity="0.5"/>
        </pattern>
        <rect width="20" height="300" fill="url(#braid-pattern-v)"/>
      </svg>

      <svg class="sticky-note__border sticky-note__border--right" viewBox="0 0 20 300" preserveAspectRatio="none">
        <pattern id="braid-pattern-v-right" x="0" y="0" width="20" height="40" patternUnits="userSpaceOnUse">
          <path d="M10,0 Q5,10 10,20 T10,40" fill="none" stroke="#C97A6B" stroke-width="2" opacity="0.6"/>
          <path d="M10,0 Q15,10 10,20 T10,40" fill="none" stroke="#D4A853" stroke-width="2" opacity="0.5"/>
        </pattern>
        <rect width="20" height="300" fill="url(#braid-pattern-v-right)"/>
      </svg>
    </div>
  </div>
</template>

<style scoped>
.sticky-note {
  position: relative;
  width: 100%;
  max-width: 400px;
  cursor: grab;
  transition: transform 0.3s ease, filter 0.2s ease;
}

.sticky-note--empty {
  cursor: default;
}

.sticky-note:active:not(.sticky-note--empty) {
  cursor: grabbing;
}

.sticky-note--dragging {
  opacity: 0.5;
  filter: blur(2px);
  transform: rotate(0deg) scale(0.95) !important;
}

.sticky-note__shadow {
  position: absolute;
  top: 8px;
  left: 8px;
  right: -8px;
  bottom: -8px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 2px;
  filter: blur(8px);
  z-index: -1;
}

.sticky-note__paper {
  position: relative;
  background: #E8A896;  /* Coral/salmon matching Midjourney design */
  border: 1px solid #C97A6B;
  border-radius: 2px;
  padding: v-bind('spacing[6]');
  min-height: 300px;
  display: flex;
  flex-direction: column;
  box-shadow:
    0 2px 4px rgba(0, 0, 0, 0.08),
    0 6px 12px rgba(0, 0, 0, 0.04);
}

.sticky-note__top {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 30px;
  background: linear-gradient(to bottom, rgba(255, 255, 255, 0.3), transparent);
  border-radius: 2px 2px 0 0;
  pointer-events: none;
}

.sticky-note__textarea {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  font-family: 'Segoe Print', 'Comic Sans MS', cursive;
  font-size: v-bind('typography.fontSize.base');
  line-height: v-bind('typography.lineHeight.relaxed');
  color: #4A2F2A;  /* Darker brown for better contrast on coral */
  padding: v-bind('spacing[2]');
  min-height: 250px;
}

.sticky-note__textarea::placeholder {
  color: #7A554F;
  opacity: 0.7;
}

.sticky-note__textarea:focus {
  outline: none;
}

.sticky-note__drag-hint {
  position: absolute;
  bottom: v-bind('spacing[2]');
  right: v-bind('spacing[4]');
  font-size: v-bind('typography.fontSize.xs');
  color: #7A554F;
  opacity: 0.8;
  pointer-events: none;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.8;
  }
  50% {
    opacity: 0.5;
  }
}

/* Decorative spirals */
.sticky-note__spiral {
  position: absolute;
  width: 35px;
  height: 35px;
  pointer-events: none;
  opacity: 0.85;
}

.sticky-note__spiral--teal {
  top: 8px;
  left: 8px;
}

.sticky-note__spiral--gold {
  top: 8px;
  right: 8px;
}

/* Decorative braided border */
.sticky-note__border {
  position: absolute;
  pointer-events: none;
  opacity: 0.7;
}

.sticky-note__border--top {
  top: 0;
  left: 0;
  right: 0;
  height: 16px;
}

.sticky-note__border--bottom {
  bottom: 0;
  left: 0;
  right: 0;
  height: 16px;
}

.sticky-note__border--left {
  top: 0;
  left: 0;
  bottom: 0;
  width: 16px;
}

.sticky-note__border--right {
  top: 0;
  right: 0;
  bottom: 0;
  width: 16px;
}

/* Prevent text selection while dragging */
.sticky-note--dragging * {
  user-select: none;
}
</style>
