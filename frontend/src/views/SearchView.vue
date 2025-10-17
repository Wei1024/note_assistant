<script setup lang="ts">
import { colors } from '@/design/colors'
import { typography } from '@/design/typography'
</script>

<template>
  <div class="search-view">
    <h2 :style="{ fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.semibold }">
      Search & Synthesis
    </h2>
    <p :style="{ color: colors.text.muted, fontSize: typography.fontSize.base, marginTop: '1rem' }">
      Coming soon: Smart search with streaming synthesis
    </p>
  </div>
</template>

<style scoped>
.search-view {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
