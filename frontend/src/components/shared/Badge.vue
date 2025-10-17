<script setup lang="ts">
import { computed } from 'vue'
import { colors, getDimensionColor, getDimensionLabel } from '@/design/colors'
import { typography } from '@/design/typography'
import { spacing, borderRadius } from '@/design/spacing'

interface Props {
  dimension: keyof typeof colors.dimension
  label?: string
  variant?: 'default' | 'subtle'
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
})

const badgeLabel = computed(() => {
  return props.label || getDimensionLabel(props.dimension)
})

const badgeColor = computed(() => {
  return getDimensionColor(props.dimension)
})

const badgeStyle = computed(() => {
  if (props.variant === 'subtle') {
    return {
      backgroundColor: `${badgeColor.value}15`, // 15% opacity
      color: badgeColor.value,
      border: `1px solid ${badgeColor.value}30`, // 30% opacity
    }
  }

  return {
    backgroundColor: badgeColor.value,
    color: colors.text.onDark,
    border: 'none',
  }
})
</script>

<template>
  <span
    class="badge"
    :style="{
      ...badgeStyle,
      fontSize: typography.fontSize.sm,
      fontWeight: typography.fontWeight.medium,
      padding: `${spacing[1]} ${spacing[3]}`,
      borderRadius: borderRadius.full,
    }"
  >
    {{ badgeLabel }}
  </span>
</template>

<style scoped>
.badge {
  display: inline-block;
  white-space: nowrap;
  transition: all 150ms ease;
}

.badge:hover {
  transform: translateY(-1px);
  filter: brightness(1.1);
}
</style>
