/**
 * useSearch Composable
 * Handles search and synthesis with SSE streaming
 */
import { ref, computed } from 'vue'
import type {
  SearchResponse,
  SearchResultModel,
  ExpandedNodeModel,
  ClusterSummaryModel,
  SynthesisStreamEvent
} from '../types/api'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export function useSearch() {
  // State
  const isSearching = ref(false)
  const isSynthesizing = ref(false)
  const error = ref<string | null>(null)

  // Search results
  const primaryResults = ref<SearchResultModel[]>([])
  const expandedResults = ref<ExpandedNodeModel[]>([])
  const clusterSummaries = ref<ClusterSummaryModel[]>([])
  const executionTime = ref(0)

  // Synthesis state
  const synthesisText = ref('')
  const notesAnalyzed = ref(0)
  const hasClusterContext = ref(false)
  const hasExpandedContext = ref(false)

  // Computed
  const hasResults = computed(() => primaryResults.value.length > 0)
  const totalResults = computed(() => primaryResults.value.length + expandedResults.value.length)

  /**
   * Execute hybrid search (without synthesis)
   */
  async function search(
    query: string,
    topK: number = 10,
    expandGraph: boolean = true,
    maxHops: number = 1
  ): Promise<void> {
    if (!query.trim()) {
      error.value = 'Please enter a search query'
      return
    }

    // Reset state
    isSearching.value = true
    error.value = null
    primaryResults.value = []
    expandedResults.value = []
    clusterSummaries.value = []

    try {
      const params = new URLSearchParams({
        query: query.trim(),
        top_k: topK.toString(),
        expand_graph: expandGraph.toString(),
        max_hops: maxHops.toString()
      })

      const response = await fetch(`${API_BASE}/search?${params}`, {
        method: 'POST'
      })

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`)
      }

      const data: SearchResponse = await response.json()

      // Update state
      primaryResults.value = data.primary_results
      expandedResults.value = data.expanded_results
      clusterSummaries.value = data.cluster_summaries
      executionTime.value = data.execution_time_ms

    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Search failed'
      console.error('Search error:', err)
    } finally {
      isSearching.value = false
    }
  }

  /**
   * Execute search with LLM synthesis (non-streaming)
   */
  async function synthesize(
    query: string,
    limit: number = 10,
    expandGraph: boolean = true,
    maxHops: number = 1
  ): Promise<void> {
    if (!query.trim()) {
      error.value = 'Please enter a query'
      return
    }

    // Reset state
    isSynthesizing.value = true
    error.value = null
    synthesisText.value = ''
    primaryResults.value = []
    expandedResults.value = []
    clusterSummaries.value = []

    try {
      const params = new URLSearchParams({
        query: query.trim(),
        limit: limit.toString(),
        expand_graph: expandGraph.toString(),
        max_hops: maxHops.toString()
      })

      const response = await fetch(`${API_BASE}/synthesize?${params}`, {
        method: 'POST'
      })

      if (!response.ok) {
        throw new Error(`Synthesis failed: ${response.statusText}`)
      }

      const data = await response.json()

      // Update state
      synthesisText.value = data.summary
      notesAnalyzed.value = data.notes_analyzed
      primaryResults.value = data.search_results
      expandedResults.value = data.expanded_results
      clusterSummaries.value = data.cluster_summaries

    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Synthesis failed'
      console.error('Synthesis error:', err)
    } finally {
      isSynthesizing.value = false
    }
  }

  /**
   * Execute search with streaming synthesis (SSE)
   * This is the preferred method for better UX
   */
  async function synthesizeStream(
    query: string,
    limit: number = 10,
    expandGraph: boolean = true,
    maxHops: number = 1
  ): Promise<void> {
    if (!query.trim()) {
      error.value = 'Please enter a query'
      return
    }

    // Reset state
    isSynthesizing.value = true
    error.value = null
    synthesisText.value = ''
    primaryResults.value = []
    expandedResults.value = []
    clusterSummaries.value = []
    notesAnalyzed.value = 0
    hasClusterContext.value = false
    hasExpandedContext.value = false

    try {
      const params = new URLSearchParams({
        query: query.trim(),
        limit: limit.toString(),
        expand_graph: expandGraph.toString(),
        max_hops: maxHops.toString()
      })

      const response = await fetch(`${API_BASE}/synthesize/stream?${params}`)

      if (!response.ok) {
        throw new Error(`Synthesis stream failed: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      // Read stream
      while (true) {
        const { done, value } = await reader.read()

        if (done) break

        // Decode chunk and add to buffer
        buffer += decoder.decode(value, { stream: true })

        // Process complete SSE messages (delimited by \n\n)
        const messages = buffer.split('\n\n')
        buffer = messages.pop() || '' // Keep incomplete message in buffer

        for (const message of messages) {
          if (!message.trim() || !message.startsWith('data:')) continue

          try {
            // Parse SSE data
            const jsonStr = message.substring(5).trim() // Remove "data:" prefix
            const event: SynthesisStreamEvent = JSON.parse(jsonStr)

            // Handle different event types
            switch (event.type) {
              case 'metadata':
                notesAnalyzed.value = event.notes_analyzed
                hasClusterContext.value = event.has_clusters
                hasExpandedContext.value = event.has_expanded
                break

              case 'chunk':
                // Append synthesis chunks (typewriter effect)
                synthesisText.value += event.content
                break

              case 'results':
                // Store search results
                primaryResults.value = event.search_results
                expandedResults.value = event.expanded_results
                clusterSummaries.value = event.cluster_summaries
                break

              case 'done':
                // Synthesis complete
                break
            }
          } catch (parseError) {
            console.warn('Failed to parse SSE message:', message, parseError)
          }
        }
      }

    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Synthesis stream failed'
      console.error('Synthesis stream error:', err)
    } finally {
      isSynthesizing.value = false
    }
  }

  /**
   * Find similar notes to a given note ID
   */
  async function findSimilar(
    noteId: string,
    topK: number = 10,
    threshold: number = 0.5
  ): Promise<void> {
    isSearching.value = true
    error.value = null
    primaryResults.value = []

    try {
      const params = new URLSearchParams({
        top_k: topK.toString(),
        threshold: threshold.toString()
      })

      const response = await fetch(`${API_BASE}/search/similar/${noteId}?${params}`)

      if (!response.ok) {
        throw new Error(`Similarity search failed: ${response.statusText}`)
      }

      const data = await response.json()
      primaryResults.value = data.similar_notes

    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Similarity search failed'
      console.error('Similarity search error:', err)
    } finally {
      isSearching.value = false
    }
  }

  /**
   * Clear all search/synthesis results
   */
  function clear() {
    primaryResults.value = []
    expandedResults.value = []
    clusterSummaries.value = []
    synthesisText.value = ''
    notesAnalyzed.value = 0
    hasClusterContext.value = false
    hasExpandedContext.value = false
    executionTime.value = 0
    error.value = null
  }

  return {
    // State
    isSearching,
    isSynthesizing,
    error,
    primaryResults,
    expandedResults,
    clusterSummaries,
    synthesisText,
    notesAnalyzed,
    hasClusterContext,
    hasExpandedContext,
    executionTime,

    // Computed
    hasResults,
    totalResults,

    // Methods
    search,
    synthesize,
    synthesizeStream,
    findSimilar,
    clear
  }
}
