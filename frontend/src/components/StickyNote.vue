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
  background: #E8A896;  /* Original coral/salmon */
  border: 1px solid #C97A6B;
  border-radius: 2px;
  padding: v-bind('spacing[6]');
  min-height: 300px;
  display: flex;
  flex-direction: column;
  box-shadow:
    0 2px 4px rgba(0, 0, 0, 0.08),
    0 6px 12px rgba(0, 0, 0, 0.04);

  /* Rough paper texture using generated noise image */
  background-color: #E8A896;
  background-image: url('@/assets/paper-texture.png');
  background-repeat: repeat;
  background-size: 200px 200px;
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

/* Prevent text selection while dragging */
.sticky-note--dragging * {
  user-select: none;
}
</style>
