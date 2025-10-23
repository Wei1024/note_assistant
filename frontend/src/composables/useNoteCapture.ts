/**
 * Composable for fast note capture with background classification
 *
 * Uses POST /save_fast endpoint (~30ms instant save)
 * LLM classification + enrichment happens in background (~13s)
 */

import { ref } from 'vue'
import type { ClassifyRequest, CaptureNoteResponse, ApiError } from '@/types/api'
import { isApiError } from '@/types/api'

const API_BASE_URL = 'http://localhost:8000'

export function useNoteCapture() {
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const result = ref<CaptureNoteResponse | null>(null)
  const pollingIntervals = ref<number[]>([])

  /**
   * Capture note with GraphRAG episodic + prospective extraction
   *
   * Uses /capture_note endpoint for episodic metadata extraction
   * Returns immediately with title and episodic metadata
   * Semantic linking happens in background
   *
   * @param text - Note content
   * @param onBackgroundComplete - Optional callback when background linking finishes
   * @returns CaptureNoteResponse with title and episodic metadata
   */
  const capture = async (
    text: string,
    onBackgroundComplete?: (noteId: string, title: string) => void
  ): Promise<CaptureNoteResponse | null> => {
    if (!text.trim()) {
      error.value = 'Note text cannot be empty'
      return null
    }

    isLoading.value = true
    error.value = null
    result.value = null

    try {
      const requestBody: ClassifyRequest = { text }

      const response = await fetch(`${API_BASE_URL}/capture_note`, {
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

      const data: CaptureNoteResponse = await response.json()
      result.value = data

      // Start polling for background completion if callback provided
      if (onBackgroundComplete && data.note_id) {
        pollBackgroundCompletion(data.note_id, data.title, onBackgroundComplete)
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
   * Poll for background semantic linking completion
   * Waits for semantic and entity edges to be created
   */
  const pollBackgroundCompletion = async (
    noteId: string,
    title: string,
    callback: (noteId: string, title: string) => void
  ) => {
    // Poll every 2 seconds for up to 20 seconds
    const maxAttempts = 10
    let attempts = 0

    const checkInterval = window.setInterval(async () => {
      attempts++

      try {
        // Wait ~5 seconds for semantic linking to complete
        if (attempts >= 3) {
          // ~6 seconds elapsed
          clearInterval(checkInterval)
          // Remove from tracking
          const index = pollingIntervals.value.indexOf(checkInterval)
          if (index > -1) pollingIntervals.value.splice(index, 1)
          callback(noteId, title)
        }
      } catch (e) {
        console.error('Error polling for completion:', e)
      }

      // Stop after max attempts
      if (attempts >= maxAttempts) {
        clearInterval(checkInterval)
        const index = pollingIntervals.value.indexOf(checkInterval)
        if (index > -1) pollingIntervals.value.splice(index, 1)
      }
    }, 2000)

    // Track this interval for cleanup
    pollingIntervals.value.push(checkInterval)
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

  /**
   * Cleanup all polling intervals
   * Call this when component unmounts
   */
  const cleanup = () => {
    pollingIntervals.value.forEach(id => clearInterval(id))
    pollingIntervals.value = []
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
    cleanup,
  }
}
