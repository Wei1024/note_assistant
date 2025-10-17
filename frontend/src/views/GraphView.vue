<script setup lang="ts">
import { colors } from '@/design/colors'
import { typography } from '@/design/typography'
</script>

<template>
  <div class="graph-view">
    <h2 :style="{ fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.semibold }">
      Knowledge Graph
    </h2>
    <p :style="{ color: colors.text.muted, fontSize: typography.fontSize.base, marginTop: '1rem' }">
      Coming soon: Interactive graph visualization
    </p>
  </div>
</template>

<style scoped>
.graph-view {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
