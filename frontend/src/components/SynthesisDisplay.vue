<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import MomoEating from './MomoEating.vue'
import { ClipboardDocumentIcon, CheckIcon } from '@heroicons/vue/24/outline'

// Props
interface Props {
  text: string
  notesAnalyzed: number
  isLoading: boolean
  hasClusterContext?: boolean
  hasExpandedContext?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  hasClusterContext: false,
  hasExpandedContext: false
})

// State
const copied = ref(false)
const momoState = ref<'DEFAULT' | 'MOUTH_OPEN' | 'CHEWING' | 'SUCCESS'>('DEFAULT')

// Computed
const hasSynthesis = computed(() => props.text.length > 0)
const contextBadges = computed(() => {
  const badges = []
  if (props.notesAnalyzed > 0) {
    badges.push(`${props.notesAnalyzed} notes`)
  }
  if (props.hasClusterContext) {
    badges.push('cluster context')
  }
  if (props.hasExpandedContext) {
    badges.push('graph expansion')
  }
  return badges
})

// Methods
async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(props.text)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

// Watch loading state to animate Momo
watch(() => props.isLoading, (loading) => {
  if (loading) {
    momoState.value = 'MOUTH_OPEN'
    setTimeout(() => {
      if (props.isLoading) {
        momoState.value = 'CHEWING'
      }
    }, 500)
  } else if (hasSynthesis.value) {
    momoState.value = 'SUCCESS'
    setTimeout(() => {
      momoState.value = 'DEFAULT'
    }, 2000)
  } else {
    momoState.value = 'DEFAULT'
  }
})
</script>

<template>
  <div class="synthesis-display">
    <!-- Momo animation -->
    <div class="momo-container">
      <MomoEating :state="momoState" />
      <p v-if="isLoading" class="momo-message">
        Momo is reading your notes...
      </p>
      <p v-else-if="hasSynthesis" class="momo-message success">
        Synthesis complete!
      </p>
    </div>

    <!-- Synthesis content -->
    <div v-if="hasSynthesis" class="synthesis-content">
      <!-- Header with context badges -->
      <div class="synthesis-header">
        <div class="context-badges">
          <span
            v-for="badge in contextBadges"
            :key="badge"
            class="badge"
          >
            {{ badge }}
          </span>
        </div>

        <!-- Copy button -->
        <button
          class="copy-button"
          :class="{ copied }"
          @click="copyToClipboard"
        >
          <CheckIcon v-if="copied" class="icon" />
          <ClipboardDocumentIcon v-else class="icon" />
          <span>{{ copied ? 'Copied!' : 'Copy' }}</span>
        </button>
      </div>

      <!-- Synthesis text -->
      <div class="synthesis-text">
        <p v-for="(paragraph, index) in text.split('\n\n')" :key="index" class="paragraph">
          {{ paragraph }}
        </p>
      </div>
    </div>

    <!-- Loading state (text preview) -->
    <div v-else-if="isLoading" class="synthesis-loading">
      <div class="loading-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <p class="loading-text">Synthesizing insights from your notes...</p>
    </div>
  </div>
</template>

<style scoped>
.synthesis-display {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}

/* Momo container */
.momo-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.momo-message {
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  text-align: center;
  animation: fadeIn 0.3s ease;
}

.momo-message.success {
  color: #059669;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Synthesis content */
.synthesis-content {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  border: 1px solid #e5e7eb;
  animation: slideUp 0.4s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.synthesis-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.context-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  background: linear-gradient(135deg, #FFF4ED 0%, #FFE9DC 100%);
  color: #C26A34;
  font-size: 12px;
  font-weight: 600;
  border-radius: 6px;
  text-transform: lowercase;
}

.copy-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: transparent;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  color: #6b7280;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.copy-button:hover {
  background: #f9fafb;
  border-color: #D47A44;
  color: #D47A44;
}

.copy-button.copied {
  background: #ecfdf5;
  border-color: #059669;
  color: #059669;
}

.copy-button .icon {
  width: 16px;
  height: 16px;
}

/* Synthesis text */
.synthesis-text {
  line-height: 1.8;
  color: #1f2937;
}

.paragraph {
  margin-bottom: 16px;
  font-size: 15px;
}

.paragraph:last-child {
  margin-bottom: 0;
}

/* Loading state */
.synthesis-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 32px;
  background: white;
  border-radius: 16px;
  border: 1px solid #e5e7eb;
}

.loading-dots {
  display: flex;
  gap: 8px;
}

.loading-dots span {
  width: 8px;
  height: 8px;
  background: #D47A44;
  border-radius: 50%;
  animation: bounce 1.4s ease-in-out infinite;
}

.loading-dots span:nth-child(1) {
  animation-delay: 0s;
}

.loading-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.loading-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.loading-text {
  font-size: 14px;
  color: #6b7280;
  font-weight: 500;
}

/* Responsive */
@media (max-width: 640px) {
  .synthesis-content {
    padding: 20px;
    border-radius: 12px;
  }

  .synthesis-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .synthesis-text {
    font-size: 14px;
  }

  .paragraph {
    margin-bottom: 12px;
  }
}
</style>
