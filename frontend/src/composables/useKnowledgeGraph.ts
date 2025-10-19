/**
 * Knowledge Graph Composable
 *
 * Handles API integration for graph traversal and visualization.
 * Provides methods to load ego-centric graph data from a starting note.
 */
import { ref, computed } from 'vue'
import type { GraphData, GraphNode, GraphEdge, GraphSearchRequest, ClusteredGraphData, ClusterSummary } from '@/types/api'

export function useKnowledgeGraph() {
  const graphData = ref<GraphData | null>(null)
  const selectedNodeId = ref<string | null>(null)
  const selectedNodeContent = ref<string | null>(null)
  const loading = ref(false)
  const loadingContent = ref(false)
  const error = ref<string | null>(null)
  const clusters = ref<ClusterSummary[]>([])
  const selectedClusterId = ref<number | null>(null)

  /**
   * Get the currently selected node
   */
  const selectedNode = computed<GraphNode | null>(() => {
    if (!selectedNodeId.value || !graphData.value) return null
    return graphData.value.nodes.find(node => node.id === selectedNodeId.value) || null
  })

  /**
   * Get the currently selected cluster
   */
  const selectedCluster = computed<ClusterSummary | null>(() => {
    if (selectedClusterId.value === null || !clusters.value.length) return null
    return clusters.value.find(c => c.cluster_id === selectedClusterId.value) || null
  })

  /**
   * Load graph neighborhood from a starting note (ego-centric view)
   *
   * @param startNoteId - Note ID to start traversal from
   * @param depth - How many hops to traverse (1-3)
   * @param relationshipType - Optional filter by link type
   */
  const loadGraph = async (
    startNoteId: string,
    depth: number = 2,
    relationshipType?: 'related' | 'spawned' | 'references' | 'contradicts'
  ) => {
    loading.value = true
    error.value = null

    try {
      const payload: GraphSearchRequest = {
        start_note_id: startNoteId,
        depth,
        ...(relationshipType && { relationship_type: relationshipType })
      }

      const response = await fetch('http://localhost:8734/search/graph', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to load graph')
      }

      graphData.value = await response.json()

      // Auto-select the starting node
      selectedNodeId.value = startNoteId
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      graphData.value = null
    } finally {
      loading.value = false
    }
  }

  /**
   * Load full corpus graph (all notes view)
   *
   * @param minLinks - Only show notes with N+ connections
   * @param dimension - Filter by dimension flag
   * @param limit - Max nodes to return
   */
  const loadFullGraph = async (
    minLinks: number = 0,
    dimension?: string,
    limit: number = 500
  ) => {
    loading.value = true
    error.value = null

    try {
      const params = new URLSearchParams({
        min_links: minLinks.toString(),
        limit: limit.toString(),
        ...(dimension && { dimension })
      })

      const response = await fetch(`http://localhost:8734/graph/full?${params}`)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to load full graph')
      }

      graphData.value = await response.json()

      // Clear selection and clusters when loading full graph
      selectedNodeId.value = null
      selectedClusterId.value = null
      clusters.value = []
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      graphData.value = null
    } finally {
      loading.value = false
    }
  }

  /**
   * Load clustered graph with community detection
   *
   * @param minLinks - Only show notes with N+ connections
   * @param limit - Max nodes to return
   */
  const loadClusteredGraph = async (
    minLinks: number = 1,
    limit: number = 100
  ) => {
    loading.value = true
    error.value = null

    try {
      const params = new URLSearchParams({
        min_links: minLinks.toString(),
        limit: limit.toString()
      })

      const response = await fetch(`http://localhost:8734/graph/clusters?${params}`)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to load clustered graph')
      }

      const data: ClusteredGraphData = await response.json()

      graphData.value = {
        nodes: data.nodes,
        edges: data.edges
      }
      clusters.value = data.clusters

      // Clear selections
      selectedNodeId.value = null
      selectedClusterId.value = null
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      graphData.value = null
      clusters.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * Load note content for selected node
   *
   * @param noteId - Note ID to fetch content for
   */
  const loadNoteContent = async (noteId: string) => {
    loadingContent.value = true

    try {
      const response = await fetch(`http://localhost:8734/notes/${noteId}/content`)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to load note content')
      }

      const data = await response.json()
      selectedNodeContent.value = data.content
    } catch (err) {
      console.error('Error loading note content:', err)
      selectedNodeContent.value = null
    } finally {
      loadingContent.value = false
    }
  }

  /**
   * Select a node (for details panel) and load its content
   */
  const selectNode = async (nodeId: string) => {
    selectedNodeId.value = nodeId
    selectedNodeContent.value = null // Clear previous content
    await loadNoteContent(nodeId)
  }

  /**
   * Select a cluster
   */
  const selectCluster = (clusterId: number) => {
    selectedClusterId.value = clusterId
    selectedNodeId.value = null
    selectedNodeContent.value = null
  }

  /**
   * Clear selection
   */
  const clearSelection = () => {
    selectedNodeId.value = null
    selectedNodeContent.value = null
    selectedClusterId.value = null
  }

  /**
   * Reset graph state
   */
  const reset = () => {
    graphData.value = null
    selectedNodeId.value = null
    selectedClusterId.value = null
    clusters.value = []
    error.value = null
  }

  return {
    // State
    graphData,
    selectedNode,
    selectedNodeId,
    selectedNodeContent,
    loading,
    loadingContent,
    error,
    clusters,
    selectedCluster,
    selectedClusterId,

    // Methods
    loadGraph,
    loadFullGraph,
    loadClusteredGraph,
    selectNode,
    selectCluster,
    clearSelection,
    reset
  }
}
