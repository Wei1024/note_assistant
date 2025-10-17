<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import { colors } from '@/design/colors'
import { typography } from '@/design/typography'
import { spacing, borderRadius, shadows } from '@/design/spacing'
import type { Toast } from '@/composables/useToast'

const { toasts, dismissToast } = useToast()

const getToastStyle = (toast: Toast) => {
  const baseStyle = {
    backgroundColor: colors.background.card,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    marginBottom: spacing[3],
    boxShadow: shadows.lg,
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.medium,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing[3],
    minWidth: '320px',
    maxWidth: '480px',
  }

  const typeStyles = {
    success: {
      borderLeft: `4px solid ${colors.status.success}`,
      color: colors.status.success,
    },
    error: {
      borderLeft: `4px solid ${colors.status.error}`,
      color: colors.status.error,
    },
    info: {
      borderLeft: `4px solid ${colors.accent.primary}`,
      color: colors.text.primary,
    },
  }

  return { ...baseStyle, ...typeStyles[toast.type] }
}

const getIcon = (type: Toast['type']) => {
  switch (type) {
    case 'success':
      return '✓'
    case 'error':
      return '✗'
    case 'info':
      return 'ℹ'
  }
}
</script>

<template>
  <div class="toast-container">
    <div
      v-for="toast in toasts"
      :key="toast.id"
      :style="getToastStyle(toast)"
      class="toast"
    >
      <span class="toast__icon">{{ getIcon(toast.type) }}</span>
      <span class="toast__message">{{ toast.message }}</span>
      <button
        @click="dismissToast(toast.id)"
        class="toast__close"
        :style="{
          background: 'none',
          border: 'none',
          fontSize: '20px',
          color: colors.text.muted,
          cursor: 'pointer',
          padding: '0',
          lineHeight: '1',
        }"
      >
        ×
      </button>
    </div>
  </div>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 1000;
  pointer-events: none;
}

.toast {
  pointer-events: all;
  animation: slideIn 200ms ease;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.toast__icon {
  font-size: 20px;
  flex-shrink: 0;
}

.toast__message {
  flex: 1;
  color: v-bind('colors.text.primary');
}

.toast__close:hover {
  color: v-bind('colors.text.primary');
}
</style>
