<script setup lang="ts">
import { ref, watch, onUnmounted, computed } from 'vue'
import { MomoState } from '@/types/momo'
import SparkleEffect from './SparkleEffect.vue'
import momoDefault from '@/assets/momo/momo_default.svg'
import momoHappy from '@/assets/momo/momo_happy.svg'
import momoMouthOpen from '@/assets/momo/momo_mouth_open.svg'
import momoMidChew from '@/assets/momo/momo_mouth_mid-chew.svg'
import momoChewing from '@/assets/momo/momo_chewing.svg'
import momoCheekBulge from '@/assets/momo/momo_cheek_bulge.svg'

interface Props {
  state?: MomoState
  isProcessing?: boolean  // Legacy - kept for backwards compatibility
  size?: number
}

const props = withDefaults(defineProps<Props>(), {
  state: MomoState.DEFAULT,
  isProcessing: false,
  size: 100
})

const frame = ref(0)
let intervalId: number | null = null

// Chewing animation frames
const chewingFrames = [
  momoCheekBulge,   // 0: Cheek bulges (food in mouth!)
  momoMidChew,      // 1: Mid-chew
  momoChewing,      // 2: Full chew
]

// Determine current state (support legacy isProcessing prop)
const currentState = computed(() => {
  if (props.isProcessing) return MomoState.CHEWING
  return props.state
})

// Get the image to display based on current state
const currentImage = computed(() => {
  switch (currentState.value) {
    case MomoState.HAPPY:
      return momoHappy
    case MomoState.MOUTH_OPEN:
      return momoMouthOpen
    case MomoState.CHEWING:
      return chewingFrames[frame.value]
    case MomoState.SUCCESS:
      return momoMouthOpen  // Show happy mouth with sparkles
    case MomoState.DEFAULT:
    default:
      return momoDefault
  }
})

// Show sparkles when in SUCCESS state
const showSparkles = computed(() => currentState.value === MomoState.SUCCESS)

// Watch for state changes to start/stop chewing animation
watch(currentState, (newState) => {
  // Clear any existing interval
  if (intervalId !== null) {
    clearInterval(intervalId)
    intervalId = null
  }

  if (newState === MomoState.CHEWING) {
    // Start chewing animation
    intervalId = window.setInterval(() => {
      frame.value = (frame.value + 1) % chewingFrames.length
    }, 400) // 400ms per frame
  } else {
    // Reset frame when not chewing
    frame.value = 0
  }
}, { immediate: true })

onUnmounted(() => {
  if (intervalId !== null) {
    clearInterval(intervalId)
  }
})
</script>

<template>
  <div
    class="momo-container"
    :style="{ width: `${size}px`, height: `${size}px` }"
    :aria-label="currentState === MomoState.CHEWING ? 'Momo is eating your note' : 'Momo is waiting'"
  >
    <img
      :src="currentImage"
      alt="Momo"
      class="momo-frame"
    />

    <!-- Sparkles when processing complete -->
    <SparkleEffect :show="showSparkles" />
  </div>
</template>

<style scoped>
.momo-container {
  position: relative;
  display: inline-block;
}

.momo-frame {
  width: 100%;
  height: 100%;
  pointer-events: none;
  user-select: none;
}
</style>
