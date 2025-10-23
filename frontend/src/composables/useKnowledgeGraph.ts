/**
 * Knowledge Graph Composable - GraphRAG Schema
 *
 * Updated to use GraphRAG backend with episodic metadata (WHO/WHAT/WHERE/WHEN/tags)
 */
import { ref, computed } from 'vue'
import type { GraphData, GraphNode } from '@/types/api'

export function useKnowledgeGraph() {
  const graphData = ref<GraphData | null>(null)
  const selectedNodeId = ref<string | null>(null)
  const selectedNodeContent = ref<string | null>(null)
  const loading = ref(false)
  const loadingContent = ref(false)
  const error = ref<string | null>(null)

  // Filters
  const filterRelation = ref<string | null>(null)

  /**
   * Get the currently selected node
   */
  const selectedNode = computed<GraphNode | null>(() => {
    if (!selectedNodeId.value || !graphData.value) return null
    return graphData.value.nodes.find(node => node.id === selectedNodeId.value) || null
  })

  /**
   * Filtered edges based on relation type
   * NOTE: Default (null) shows all edges (user tags are high-quality, not noisy)
   */
  const filteredEdges = computed(() => {
    if (!graphData.value?.edges) return []
    if (!filterRelation.value) {
      // Default view: show all edges (semantic + entity + user tags)
      return graphData.value.edges
    }
    return graphData.value.edges.filter(e => e.relation === filterRelation.value)
  })

  /**
   * Load full corpus graph (all notes view) - GraphRAG schema
   */
  const loadFullGraph = async () => {
    loading.value = true
    error.value = null

    try {
      // Fetch nodes and edges in parallel
      const [nodesResponse, edgesResponse] = await Promise.all([
        fetch('http://localhost:8000/graph/nodes'),
        fetch('http://localhost:8000/graph/edges')
      ])

      if (!nodesResponse.ok || !edgesResponse.ok) {
        throw new Error('Failed to load graph data')
      }

      const nodesData = await nodesResponse.json()
      const edgesData = await edgesResponse.json()

      graphData.value = {
        nodes: nodesData.nodes,
        edges: edgesData.edges
      }

      // Clear selections
      selectedNodeId.value = null
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      graphData.value = null
    } finally {
      loading.value = false
    }
  }

  /**
   * Load graph with specific edge type filter
   */
  const loadGraphByRelation = async (relation: 'semantic' | 'entity_link' | 'tag_link') => {
    loading.value = true
    error.value = null

    try {
      const [nodesResponse, edgesResponse] = await Promise.all([
        fetch('http://localhost:8000/graph/nodes'),
        fetch(`http://localhost:8000/graph/edges?relation=${relation}`)
      ])

      if (!nodesResponse.ok || !edgesResponse.ok) {
        throw new Error('Failed to load graph data')
      }

      const nodesData = await nodesResponse.json()
      const edgesData = await edgesResponse.json()

      graphData.value = {
        nodes: nodesData.nodes,
        edges: edgesData.edges
      }

      selectedNodeId.value = null
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      graphData.value = null
    } finally {
      loading.value = false
    }
  }

  /**
   * Load note content for selected node
   */
  const loadNoteContent = async (noteId: string) => {
    loadingContent.value = true

    try {
      const response = await fetch(`http://localhost:8000/notes/${noteId}/content`)

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
   * Clear selection
   */
  const clearSelection = () => {
    selectedNodeId.value = null
    selectedNodeContent.value = null
  }

  /**
   * Reset graph state
   */
  const reset = () => {
    graphData.value = null
    selectedNodeId.value = null
    error.value = null
    filterRelation.value = null
  }

  /**
   * Set relation filter
   */
  const setRelationFilter = (relation: string | null) => {
    filterRelation.value = relation
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
    filteredEdges,

    // Filters
    filterRelation,

    // Methods
    loadFullGraph,
    loadGraphByRelation,
    selectNode,
    clearSelection,
    reset,
    setRelationFilter
  }
}
