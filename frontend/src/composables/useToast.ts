/**
 * Simple toast notification system
 */

import { ref } from 'vue'

export interface Toast {
  id: string
  message: string
  type: 'success' | 'info' | 'error'
  duration?: number
}

const toasts = ref<Toast[]>([])

let toastIdCounter = 0

export function useToast() {
  const showToast = (
    message: string,
    type: Toast['type'] = 'info',
    duration = 3000
  ) => {
    const id = `toast-${++toastIdCounter}`
    const toast: Toast = { id, message, type, duration }

    toasts.value.push(toast)

    // Auto-dismiss
    if (duration > 0) {
      setTimeout(() => {
        dismissToast(id)
      }, duration)
    }

    return id
  }

  const dismissToast = (id: string) => {
    const index = toasts.value.findIndex((t) => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  const success = (message: string, duration = 3000) => {
    return showToast(message, 'success', duration)
  }

  const info = (message: string, duration = 3000) => {
    return showToast(message, 'info', duration)
  }

  const error = (message: string, duration = 5000) => {
    return showToast(message, 'error', duration)
  }

  return {
    toasts,
    showToast,
    dismissToast,
    success,
    info,
    error,
  }
}
