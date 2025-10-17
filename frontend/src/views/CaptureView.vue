<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useNoteCapture } from '@/composables/useNoteCapture'
import Button from '@/components/shared/Button.vue'
import Badge from '@/components/shared/Badge.vue'
import { colors } from '@/design/colors'
import { typography } from '@/design/typography'
import { spacing, borderRadius } from '@/design/spacing'
import type { Dimensions } from '@/types/api'

const noteText = ref('')
const { isLoading, error, result, capture, reset } = useNoteCapture()

// Auto-clear result after 5 seconds
watch(result, (newResult) => {
  if (newResult) {
    setTimeout(() => {
      reset()
      noteText.value = ''
    }, 5000)
  }
})

const handleSave = async () => {
  await capture(noteText.value)
}

const activeDimensions = computed(() => {
  if (!result.value) return []

  const dims = result.value.dimensions
  return (Object.keys(dims) as Array<keyof Dimensions>).filter(
    (key) => dims[key] === true
  )
})

const characterCount = computed(() => noteText.value.length)
</script>

<template>
  <div class="capture-view">
    <div class="capture-view__header">
      <h2 :style="{ fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.semibold }">
        Capture Your Thoughts
      </h2>
      <p :style="{ color: colors.text.muted, fontSize: typography.fontSize.base }">
        Write naturally, AI will organize and classify your note automatically.
      </p>
    </div>

    <div class="capture-view__content">
      <!-- Textarea -->
      <textarea
        v-model="noteText"
        :disabled="isLoading"
        placeholder="Type your note here... Meeting notes, ideas, tasks, or anything else on your mind."
        class="capture-textarea"
        :style="textareaStyle"
        autofocus
      />

      <!-- Character count -->
      <div
        v-if="noteText"
        :style="{
          fontSize: typography.fontSize.sm,
          color: colors.text.muted,
          textAlign: 'right',
          marginTop: spacing[2]
        }"
      >
        {{ characterCount }} characters
      </div>

      <!-- Action buttons -->
      <div class="capture-actions">
        <Button
          variant="primary"
          size="lg"
          icon="note"
          :loading="isLoading"
          :disabled="!noteText.trim() || isLoading"
          @click="handleSave"
        >
          Save & Classify
        </Button>

        <Button
          variant="secondary"
          size="lg"
          :disabled="!noteText.trim()"
          @click="noteText = ''"
        >
          Clear
        </Button>
      </div>

      <!-- Error message -->
      <div
        v-if="error"
        class="capture-status capture-status--error"
        :style="statusErrorStyle"
      >
        ✗ {{ error }}
      </div>

      <!-- Success result -->
      <div
        v-if="result"
        class="capture-result"
        :style="resultStyle"
      >
        <div class="capture-result__header">
          <span :style="{ fontSize: typography.fontSize.lg }">✓</span>
          <h3 :style="{ fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.semibold }">
            {{ result.title }}
          </h3>
        </div>

        <!-- Dimension badges -->
        <div class="capture-result__dimensions">
          <Badge
            v-for="dimension in activeDimensions"
            :key="dimension"
            :dimension="dimension"
          />
        </div>

        <!-- Tags -->
        <div
          v-if="result.tags.length > 0"
          class="capture-result__tags"
          :style="{ marginTop: spacing[3] }"
        >
          <span :style="{ fontSize: typography.fontSize.sm, color: colors.text.muted }">
            Tags:
          </span>
          <span
            v-for="tag in result.tags"
            :key="tag"
            :style="{
              fontSize: typography.fontSize.sm,
              color: colors.text.secondary,
              padding: `${spacing[1]} ${spacing[2]}`,
              backgroundColor: colors.background.hover,
              borderRadius: borderRadius.base,
            }"
          >
            {{ tag }}
          </span>
        </div>

        <!-- File path -->
        <div :style="{ marginTop: spacing[3], fontSize: typography.fontSize.sm, color: colors.text.muted }">
          Saved to: {{ result.path.split('/').pop() }}
        </div>
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
  resize: 'vertical',
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

const resultStyle = {
  marginTop: spacing[6],
  padding: spacing[6],
  backgroundColor: colors.background.card,
  border: `2px solid ${colors.status.success}`,
  borderRadius: borderRadius.xl,
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

.capture-textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.capture-actions {
  display: flex;
  gap: v-bind('spacing[4]');
  margin-top: v-bind('spacing[4]');
}

.capture-result__header {
  display: flex;
  align-items: center;
  gap: v-bind('spacing[3]');
  color: v-bind('colors.status.success');
}

.capture-result__dimensions {
  display: flex;
  flex-wrap: wrap;
  gap: v-bind('spacing[2]');
  margin-top: v-bind('spacing[4]');
}

.capture-result__tags {
  display: flex;
  flex-wrap: wrap;
  gap: v-bind('spacing[2]');
  align-items: center;
}
</style>
