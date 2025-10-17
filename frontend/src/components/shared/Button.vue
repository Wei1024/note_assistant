<script setup lang="ts">
import { computed } from 'vue'
import Icon from './Icon.vue'
import type { IconName } from '@/design/icons'
import { colors } from '@/design/colors'
import { typography } from '@/design/typography'
import { spacing, borderRadius } from '@/design/spacing'

interface Props {
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'sm' | 'base' | 'lg'
  icon?: IconName
  iconPosition?: 'left' | 'right'
  disabled?: boolean
  loading?: boolean
  fullWidth?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'base',
  iconPosition: 'left',
  disabled: false,
  loading: false,
  fullWidth: false,
})

const buttonStyle = computed(() => {
  const base = {
    fontFamily: typography.fontFamily.sans,
    fontWeight: typography.fontWeight.medium,
    borderRadius: borderRadius.lg,
    cursor: props.disabled || props.loading ? 'not-allowed' : 'pointer',
    opacity: props.disabled || props.loading ? '0.5' : '1',
    width: props.fullWidth ? '100%' : 'auto',
    transition: 'all 150ms ease',
  }

  // Size-specific styles
  const sizes = {
    sm: {
      fontSize: typography.fontSize.sm,
      padding: `${spacing[2]} ${spacing[4]}`,
    },
    base: {
      fontSize: typography.fontSize.base,
      padding: `${spacing[3]} ${spacing[6]}`,
    },
    lg: {
      fontSize: typography.fontSize.lg,
      padding: `${spacing[4]} ${spacing[8]}`,
    },
  }

  // Variant-specific styles
  const variants = {
    primary: {
      backgroundColor: colors.accent.primary,
      color: colors.text.onDark,
      border: 'none',
    },
    secondary: {
      backgroundColor: 'transparent',
      color: colors.text.primary,
      border: `1px solid ${colors.border.default}`,
    },
    ghost: {
      backgroundColor: 'transparent',
      color: colors.text.primary,
      border: 'none',
    },
  }

  return {
    ...base,
    ...sizes[props.size],
    ...variants[props.variant],
  }
})
</script>

<template>
  <button
    :style="buttonStyle"
    :disabled="disabled || loading"
    class="button"
    :class="[`button--${variant}`, `button--${size}`]"
  >
    <Icon
      v-if="icon && iconPosition === 'left' && !loading"
      :name="icon"
      size="sm"
      :style="{ marginRight: spacing[2] }"
    />

    <Icon
      v-if="loading"
      name="loading"
      size="sm"
      :style="{ marginRight: spacing[2] }"
      class="button__loading"
    />

    <span class="button__label">
      <slot />
    </span>

    <Icon
      v-if="icon && iconPosition === 'right' && !loading"
      :name="icon"
      size="sm"
      :style="{ marginLeft: spacing[2] }"
    />
  </button>
</template>

<style scoped>
.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  outline: none;
  text-decoration: none;
  user-select: none;
}

.button:not(:disabled):hover.button--primary {
  background-color: v-bind('colors.accent.primaryHover');
  transform: translateY(-1px);
}

.button:not(:disabled):hover.button--secondary {
  background-color: v-bind('colors.background.hover');
  border-color: v-bind('colors.accent.primary');
}

.button:not(:disabled):hover.button--ghost {
  background-color: v-bind('colors.background.hover');
}

.button:not(:disabled):active {
  transform: scale(0.98);
}

.button__loading {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
