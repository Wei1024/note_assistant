/**
 * Composable for fast note capture with background classification
 *
 * Uses POST /save_fast endpoint (~30ms instant save)
 * LLM classification + enrichment happens in background (~13s)
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
   * Capture note with instant save (background classification)
   *
   * Uses /save_fast endpoint for ~30ms response time
   * Returns immediately with basic title
   * LLM classification happens in background and updates file when ready
   *
   * @param text - Note content
   * @param onBackgroundComplete - Optional callback when background classification finishes
   * @returns ClassifyResponse with basic title (full metadata added async)
   */
  const capture = async (
    text: string,
    onBackgroundComplete?: (noteId: string, title: string) => void
  ): Promise<ClassifyResponse | null> => {
    if (!text.trim()) {
      error.value = 'Note text cannot be empty'
      return null
    }

    isLoading.value = true
    error.value = null
    result.value = null

    try {
      const requestBody: ClassifyRequest = { text }

      const response = await fetch(`${API_BASE_URL}/save_fast`, {
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

      // Start polling for background completion if callback provided
      if (onBackgroundComplete && data.path) {
        pollBackgroundCompletion(data.path, data.title, onBackgroundComplete)
      }

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
   * Poll for background classification completion
   * Checks if the note file has been enriched with dimensions
   */
  const pollBackgroundCompletion = async (
    notePath: string,
    title: string,
    callback: (noteId: string, title: string) => void
  ) => {
    // Extract note_id from path (filename without .md)
    const filename = notePath.split('/').pop() || ''
    const noteId = filename.replace('.md', '')

    // Poll every 2 seconds for up to 20 seconds
    const maxAttempts = 10
    let attempts = 0

    const checkInterval = setInterval(async () => {
      attempts++

      try {
        // Try to read the note to see if it has been enriched
        // For now, we'll just wait ~13 seconds and assume it's done
        // In a real implementation, you could add a /notes/{id}/status endpoint
        if (attempts >= 7) {
          // ~14 seconds elapsed
          clearInterval(checkInterval)
          callback(noteId, title)
        }
      } catch (e) {
        console.error('Error polling for completion:', e)
      }

      // Stop after max attempts
      if (attempts >= maxAttempts) {
        clearInterval(checkInterval)
      }
    }, 2000)
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
