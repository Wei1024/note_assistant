<script setup lang="ts">
import { ref } from 'vue'
import { colors } from '@/design/colors'
import { typography } from '@/design/typography'
import MomoEating from '@/components/MomoEating.vue'

const isProcessing = ref(false)

const toggleProcessing = () => {
  isProcessing.value = !isProcessing.value
}
</script>

<template>
  <div class="search-view">
    <h2 :style="{ fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.semibold }">
      Search & Synthesis
    </h2>
    <p :style="{ color: colors.text.muted, fontSize: typography.fontSize.base, marginTop: '1rem' }">
      Coming soon: Smart search with streaming synthesis
    </p>

    <!-- Momo Dream Eater Preview -->
    <div class="momo-preview" :style="{ marginTop: '3rem', textAlign: 'center' }">
      <MomoEating :isProcessing="isProcessing" :size="150" />
      <p :style="{ marginTop: '1rem', color: colors.text.muted }">
        {{ isProcessing ? 'Momo is eating notes...' : 'Momo is resting' }}
      </p>
      <button
        @click="toggleProcessing"
        :style="{
          marginTop: '1rem',
          padding: '0.5rem 1rem',
          backgroundColor: colors.accent.primary,
          color: 'white',
          border: 'none',
          borderRadius: '0.5rem',
          cursor: 'pointer',
          fontSize: typography.fontSize.sm
        }"
      >
        {{ isProcessing ? 'Stop' : 'Test Animation' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.search-view {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
