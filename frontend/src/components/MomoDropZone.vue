<script setup lang="ts">
import { ref, computed } from 'vue'
import { MomoState } from '@/types/momo'
import MomoEating from './MomoEating.vue'

interface Props {
  size?: number
  isProcessing?: boolean
  hasContent?: boolean  // Is user typing something?
  showSuccess?: boolean  // Show success sparkles?
}

interface Emits {
  (e: 'note-dropped', noteText: string): void
}

const props = withDefaults(defineProps<Props>(), {
  size: 150,
  isProcessing: false,
  hasContent: false,
  showSuccess: false
})

const emit = defineEmits<Emits>()

const isHovering = ref(false)

// Determine Momo's state based on interaction
const momoState = computed(() => {
  if (props.showSuccess) return MomoState.SUCCESS
  if (props.isProcessing) return MomoState.CHEWING
  if (isHovering.value) return MomoState.MOUTH_OPEN
  if (props.hasContent) return MomoState.HAPPY
  return MomoState.DEFAULT
})

// Drag event handlers
const handleDragOver = (event: DragEvent) => {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
  isHovering.value = true
}

const handleDragEnter = (event: DragEvent) => {
  event.preventDefault()
  isHovering.value = true
}

const handleDragLeave = () => {
  isHovering.value = false
}

const handleDrop = (event: DragEvent) => {
  event.preventDefault()
  isHovering.value = false

  const noteText = event.dataTransfer?.getData('text/plain')
  if (noteText) {
    emit('note-dropped', noteText)
  }
}
</script>

<template>
  <div
    class="momo-drop-zone"
    :class="{ 'momo-drop-zone--hovering': isHovering }"
    @dragover="handleDragOver"
    @dragenter="handleDragEnter"
    @dragleave="handleDragLeave"
    @drop="handleDrop"
  >
    <!-- Animated border when hovering -->
    <div v-if="isHovering" class="momo-drop-zone__pulse"></div>

    <!-- Momo with state-based animation -->
    <MomoEating :state="momoState" :size="size" />

    <!-- Drop hint -->
    <div v-if="isHovering" class="momo-drop-zone__hint">
      Feed me! 🍴
    </div>
  </div>
</template>

<style scoped>
.momo-drop-zone {
  position: relative;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
  border-radius: 50%;
  transition: all 0.3s ease;
}

.momo-drop-zone--hovering {
  transform: scale(1.1);
}

.momo-drop-zone__pulse {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border: 4px dashed #f4a261;
  border-radius: 50%;
  animation: pulse-border 1s ease-in-out infinite;
  pointer-events: none;
}

@keyframes pulse-border {
  0%, 100% {
    transform: scale(1);
    opacity: 0.8;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.4;
  }
}

.momo-drop-zone__hint {
  position: absolute;
  bottom: -2rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #f4a261;
  animation: bounce 0.5s ease-in-out infinite alternate;
  white-space: nowrap;
}

@keyframes bounce {
  from {
    transform: translateY(0);
  }
  to {
    transform: translateY(-5px);
  }
}
</style>
