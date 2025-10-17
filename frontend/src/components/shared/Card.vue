<script setup lang="ts">
import { computed } from 'vue'
import { colors } from '@/design/colors'
import { spacing, borderRadius, shadows } from '@/design/spacing'

interface Props {
  padding?: keyof typeof spacing
  hoverable?: boolean
  clickable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  padding: 4,
  hoverable: false,
  clickable: false,
})

const emit = defineEmits<{
  click: []
}>()

const cardStyle = computed(() => ({
  backgroundColor: colors.background.card,
  border: `1px solid ${colors.border.subtle}`,
  borderRadius: borderRadius.lg,
  padding: spacing[props.padding],
  boxShadow: shadows.base,
  cursor: props.clickable ? 'pointer' : 'default',
  transition: 'all 200ms ease',
}))

const handleClick = () => {
  if (props.clickable) {
    emit('click')
  }
}
</script>

<template>
  <div
    :style="cardStyle"
    class="card"
    :class="{
      'card--hoverable': hoverable,
      'card--clickable': clickable,
    }"
    @click="handleClick"
  >
    <slot />
  </div>
</template>

<style scoped>
.card {
  display: block;
}

.card--hoverable:hover,
.card--clickable:hover {
  box-shadow: v-bind('shadows.md');
  border-color: v-bind('colors.accent.primary');
  transform: translateY(-2px);
}

.card--clickable:active {
  transform: translateY(0);
}
</style>
