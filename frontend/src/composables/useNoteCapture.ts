/**
 * Composable for note capture with AI classification
 *
 * Handles POST /classify_and_save endpoint
 */

import { ref } from 'vue'
import type { ClassifyRequest, ClassifyResponse, ApiError } from '@/types/api'
import { isApiError } from '@/types/api'

const API_BASE_URL = 'http://localhost:8734'

export function useNoteCapture() {
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const result = ref<ClassifyResponse | null>(null)

  /**
   * Capture and classify a note
   *
   * @param text - Note content
   * @returns ClassifyResponse with dimensions, title, tags, and file path
   */
  const capture = async (text: string): Promise<ClassifyResponse | null> => {
    if (!text.trim()) {
      error.value = 'Note text cannot be empty'
      return null
    }

    isLoading.value = true
    error.value = null
    result.value = null

    try {
      const requestBody: ClassifyRequest = { text }

      const response = await fetch(`${API_BASE_URL}/classify_and_save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        const errorData: ApiError = await response.json()
        throw new Error(isApiError(errorData) ? errorData.detail : 'Failed to save note')
      }

      const data: ClassifyResponse = await response.json()
      result.value = data
      return data
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : 'Unknown error occurred'
      error.value = errorMessage
      console.error('Note capture error:', e)
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Clear error message
   */
  const clearError = () => {
    error.value = null
  }

  /**
   * Clear result
   */
  const clearResult = () => {
    result.value = null
  }

  /**
   * Reset all state
   */
  const reset = () => {
    isLoading.value = false
    error.value = null
    result.value = null
  }

  return {
    // State
    isLoading,
    error,
    result,

    // Actions
    capture,
    clearError,
    clearResult,
    reset,
  }
}
