<script setup lang="ts">
import { computed } from 'vue'
import type { IconName } from '@/design/icons'
import { iconSizes, type IconSize } from '@/design/icons'

interface Props {
  name: IconName
  size?: IconSize | number
  color?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'base',
  color: 'currentColor'
})

const iconSize = computed(() => {
  return typeof props.size === 'number' ? props.size : iconSizes[props.size]
})

// Dynamic SVG import path (not currently used - placeholder SVG rendered instead)
// const iconPath = computed(() => `/src/assets/icons/${props.name}.svg`)
</script>

<template>
  <svg
    :width="iconSize"
    :height="iconSize"
    :style="{ color }"
    class="icon"
    role="img"
    :aria-label="name"
  >
    <!-- For now, we'll use a placeholder until actual SVGs are created -->
    <circle :cx="iconSize / 2" :cy="iconSize / 2" :r="iconSize / 3" fill="currentColor" opacity="0.3" />
  </svg>
</template>

<style scoped>
.icon {
  display: inline-block;
  vertical-align: middle;
  flex-shrink: 0;
}
</style>
