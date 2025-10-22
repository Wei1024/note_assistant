<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick, computed } from 'vue'
import * as d3 from 'd3'
import { marked } from 'marked'
import { useKnowledgeGraph } from '@/composables/useKnowledgeGraph'
import { colors, getClusterColor } from '@/design/colors'
import { typography } from '@/design/typography'
import { spacing } from '@/design/spacing'
import { graph, getNodeRadius } from '@/design/graph'
import type { GraphNode } from '@/types/api'

// ========================================
// State Management
// ========================================
const {
  graphData,
  selectedNode,
  selectedNodeId,
  selectedNodeContent,
  loading,
  loadingContent,
  error,
  filteredEdges,
  filterRelation,
  loadFullGraph,
  selectNode,
  clearSelection,
  setRelationFilter,
} = useKnowledgeGraph()

const svgRef = ref<SVGSVGElement | null>(null)
const showClusters = ref(false) // Toggle cluster view (Phase 2.5)

// Floating card position
const cardPosition = ref({ x: 0, y: 0 })
const cardVisible = ref(false)

/**
 * Render markdown content as HTML
 */
const renderedContent = computed(() => {
  if (!selectedNodeContent.value) return ''
  return marked(selectedNodeContent.value)
})

// ========================================
// D3 Simulation & Rendering
// ========================================
let simulation: d3.Simulation<d3.SimulationNodeDatum, undefined> | null = null
let currentZoom: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null
let currentSvg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null

/**
 * Get node color based on entity types (GraphRAG)
 */
function getNodeColor(node: GraphNode): string {
  // Cluster mode: color by cluster_id (Phase 2.5)
  if (showClusters.value && node.cluster_id !== undefined) {
    return getClusterColor(node.cluster_id)
  }

  // Color by entity richness
  const entityCount = (node.who?.length || 0) + (node.what?.length || 0) + (node.where?.length || 0)

  if (entityCount === 0) {
    return colors.mutedSage // No entities
  } else if (entityCount >= 5) {
    return colors.vibrantGold // Rich metadata
  } else if (entityCount >= 3) {
    return colors.deepPurple // Medium metadata
  } else {
    return colors.softBlue // Sparse metadata
  }
}

/**
 * Truncate text to max length
 */
function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength - 3) + '...'
}

/**
 * Extract title from file path or ID
 */
function getNodeTitle(node: GraphNode): string {
  const filename = node.file_path?.split('/').pop() || node.id
  const title = filename.replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/\.md$/, '')
  return truncateText(title, 20)
}

/**
 * Position floating card near clicked node
 */
function positionCard(event: MouseEvent) {
  if (!svgRef.value) return

  const cardWidth = 400 // Approximate card width
  const cardHeight = 500 // Approximate card height
  const offset = 20 // Offset from node

  // Get click position relative to viewport
  const clickX = event.clientX
  const clickY = event.clientY

  // Calculate initial position (offset to the right and down)
  let x = clickX + offset
  let y = clickY + offset

  // Check if card would go off-screen on the right
  if (x + cardWidth > window.innerWidth) {
    x = clickX - cardWidth - offset // Position to the left instead
  }

  // Check if card would go off-screen on the bottom
  if (y + cardHeight > window.innerHeight) {
    y = window.innerHeight - cardHeight - 20 // Position at bottom with margin
  }

  // Keep card within bounds
  x = Math.max(20, x) // Minimum 20px from left edge
  y = Math.max(20, y) // Minimum 20px from top edge

  cardPosition.value = { x, y }
  cardVisible.value = true
}

/**
 * Cleanup graph resources
 */
function cleanupGraph() {
  if (simulation) {
    simulation.stop()
    simulation = null
  }
  currentZoom = null
  currentSvg = null
}

/**
 * Hide floating card
 */
function hideCard() {
  cardVisible.value = false
  clearSelection()
}

/**
 * Center and zoom to a clicked node
 */
function centerOnNode(node: GraphNode) {
  if (!node.x || !node.y || !currentSvg || !currentZoom || !svgRef.value) return

  const width = svgRef.value.clientWidth
  const height = svgRef.value.clientHeight
  const scale = 1.5

  const transform = d3.zoomIdentity
    .translate(width / 2, height / 2)
    .scale(scale)
    .translate(-node.x, -node.y)

  currentSvg.transition()
    .duration(750)
    .call(currentZoom.transform, transform)
}

/**
 * Render force-directed graph with D3
 */
function renderGraph() {
  if (!svgRef.value || !graphData.value) return

  // Cleanup old simulation before creating new one
  cleanupGraph()

  const svg = d3.select(svgRef.value)
  currentSvg = svg
  const width = svgRef.value.clientWidth
  const height = svgRef.value.clientHeight

  // Clear existing content
  svg.selectAll('*').remove()

  // Create container group for zoom/pan
  const g = svg.append('g')

  // Add zoom behavior
  const zoom = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([graph.canvas.minZoom, graph.canvas.maxZoom])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    })

  currentZoom = zoom
  svg.call(zoom)

  const { nodes, edges } = graphData.value

  // Edges are already in D3 format (source/target) from GraphRAG backend
  const d3Links = edges.map(edge => ({
    source: edge.source,
    target: edge.target,
    relation: edge.relation,
    weight: edge.weight
  }))

  // Calculate connection counts for sizing
  const connectionCounts = new Map<string, number>()
  nodes.forEach(node => {
    const count = edges.filter(e => e.source === node.id || e.target === node.id).length
    connectionCounts.set(node.id, count)
  })

  // ========================================
  // Create Force Simulation
  // ========================================
  simulation = d3.forceSimulation(nodes as any)
    .force('link', d3.forceLink(d3Links)
      .id((d: any) => d.id)
      .distance(graph.edge.linkDistance)
      .strength(graph.force.linkStrength)
    )
    .force('charge', d3.forceManyBody()
      .strength(graph.force.chargeStrength)
      .distanceMin(graph.force.chargeDistanceMin)
      .distanceMax(graph.force.chargeDistanceMax)
    )
    .force('center', d3.forceCenter(width / 2, height / 2)
      .strength(graph.force.centerStrength)
    )
    .force('collision', d3.forceCollide()
      .radius(graph.force.collisionRadius)
      .strength(graph.force.collisionStrength)
    )
    .alphaDecay(graph.animation.simulationAlphaDecay)
    .velocityDecay(graph.animation.simulationVelocityDecay)

  // ========================================
  // Draw Edges
  // ========================================
  const link = g.append('g')
    .selectAll('line')
    .data(d3Links)
    .enter()
    .append('line')
    .attr('stroke', colors.text.muted)
    .attr('stroke-width', graph.edge.strokeWidth)
    .attr('stroke-opacity', graph.edge.opacity)
    .attr('stroke-dasharray', (d: any) => {
      const linkType = d.type as 'related' | 'spawned' | 'references' | 'contradicts'
      return graph.edge.strokeDasharray[linkType]
    })

  // ========================================
  // Draw Nodes
  // ========================================
  const node = g.append('g')
    .selectAll('circle')
    .data(nodes)
    .enter()
    .append('circle')
    .attr('r', (d: GraphNode) => getNodeRadius(connectionCounts.get(d.id) || 0))
    .attr('fill', (d: GraphNode) => getNodeColor(d))
    .attr('stroke', colors.background.card)
    .attr('stroke-width', graph.node.strokeWidth)
    .style('cursor', 'pointer')
    .on('click', (event: MouseEvent, d: GraphNode) => {
      event.stopPropagation() // Prevent event bubbling
      selectNode(d.id)
      updateSelection()
      positionCard(event)
      centerOnNode(d)
    })
    .on('mouseenter', function(this: SVGCircleElement) {
      d3.select(this)
        .transition()
        .duration(graph.animation.transitionDuration)
        .attr('opacity', graph.node.opacityHover)
    })
    .on('mouseleave', function(this: SVGCircleElement) {
      d3.select(this)
        .transition()
        .duration(graph.animation.transitionDuration)
        .attr('opacity', graph.node.opacity)
    })
    .call(d3.drag<SVGCircleElement, GraphNode>()
      .on('start', dragStarted)
      .on('drag', dragged)
      .on('end', dragEnded) as any
    )

  // ========================================
  // Draw Labels
  // ========================================
  const label = g.append('g')
    .selectAll('text')
    .data(nodes)
    .enter()
    .append('text')
    .text((d: GraphNode) => getNodeTitle(d))
    .attr('font-size', graph.label.fontSize)
    .attr('font-weight', graph.label.fontWeight)
    .attr('fill', colors.text.primary)
    .attr('text-anchor', 'middle')
    .attr('dy', graph.label.offsetY)
    .attr('opacity', graph.label.opacity)
    .style('pointer-events', 'none')
    .style('user-select', 'none')

  // ========================================
  // Simulation Tick
  // ========================================
  simulation!.on('tick', () => {
    link
      .attr('x1', (d: any) => d.source.x)
      .attr('y1', (d: any) => d.source.y)
      .attr('x2', (d: any) => d.target.x)
      .attr('y2', (d: any) => d.target.y)

    node
      .attr('cx', (d: any) => d.x)
      .attr('cy', (d: any) => d.y)

    label
      .attr('x', (d: any) => d.x)
      .attr('y', (d: any) => d.y)
  })

  // Update selection styling
  updateSelection()

  // ========================================
  // Drag Handlers
  // ========================================
  function dragStarted(event: d3.D3DragEvent<SVGCircleElement, GraphNode, GraphNode>) {
    if (!event.active && simulation) simulation.alphaTarget(0.3).restart()
    event.subject.fx = event.subject.x
    event.subject.fy = event.subject.y
  }

  function dragged(event: d3.D3DragEvent<SVGCircleElement, GraphNode, GraphNode>) {
    event.subject.fx = event.x
    event.subject.fy = event.y
  }

  function dragEnded(event: d3.D3DragEvent<SVGCircleElement, GraphNode, GraphNode>) {
    if (!event.active && simulation) simulation.alphaTarget(0)
    event.subject.fx = null
    event.subject.fy = null
  }

  /**
   * Update visual selection state
   */
  function updateSelection() {
    if (!selectedNodeId.value) {
      // No selection - reset all
      node.attr('opacity', graph.node.opacity)
        .attr('stroke-width', graph.node.strokeWidth)
      link.attr('stroke-opacity', graph.edge.opacity)
      label.attr('opacity', graph.label.opacity)
    } else {
      // Highlight selected node and connected nodes
      const connectedNodeIds = new Set<string>()
      connectedNodeIds.add(selectedNodeId.value)

      edges.forEach(edge => {
        if (edge.source === selectedNodeId.value) connectedNodeIds.add(edge.target)
        if (edge.target === selectedNodeId.value) connectedNodeIds.add(edge.source)
      })

      node
        .attr('opacity', (d: GraphNode) =>
          connectedNodeIds.has(d.id) ? graph.node.opacity : graph.node.opacityInactive
        )
        .attr('stroke-width', (d: GraphNode) =>
          d.id === selectedNodeId.value ? graph.node.strokeWidthSelected : graph.node.strokeWidth
        )
        .attr('stroke', (d: GraphNode) =>
          d.id === selectedNodeId.value ? colors.accent.primary : colors.background.card
        )

      link
        .attr('stroke-opacity', (d: any) => {
          const sourceId = typeof d.source === 'string' ? d.source : d.source.id
          const targetId = typeof d.target === 'string' ? d.target : d.target.id
          return sourceId === selectedNodeId.value || targetId === selectedNodeId.value
            ? graph.edge.opacityHover
            : graph.edge.opacityInactive
        })

      label
        .attr('opacity', (d: GraphNode) =>
          connectedNodeIds.has(d.id) ? graph.label.opacityHover : graph.node.opacityInactive
        )
    }
  }
}

// ========================================
// Cluster Interaction
// ========================================
function handleClusterClick(clusterId: number, event: MouseEvent) {
  selectCluster(clusterId)
  positionCard(event)
  cardVisible.value = true
}

// ========================================
// Lifecycle & Watchers
// ========================================
onMounted(async () => {
  // Load full graph on mount
  await loadFullGraph()
})

onBeforeUnmount(() => {
  // Cleanup graph resources
  cleanupGraph()
})

watch(graphData, async () => {
  if (graphData.value) {
    await nextTick()
    renderGraph()
  }
})
</script>

<template>
  <div class="graph-view">
    <!-- Header -->
    <header class="header">
      <h2 :style="{ fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.semibold, margin: 0 }">
        Knowledge Graph
      </h2>
    </header>

    <!-- Controls -->
    <div class="controls" :style="{ marginTop: spacing[4], display: 'flex', gap: spacing[6], alignItems: 'center', justifyContent: 'space-between' }">
      <!-- Node count info -->
      <div v-if="graphData" :style="{ fontSize: typography.fontSize.sm, color: colors.text.secondary }">
        {{ graphData.nodes.length }} notes, {{ graphData.edges.length }} connections
      </div>

      <!-- Edge type filter -->
      <div :style="{ display: 'flex', gap: spacing[2] }">
        <button
          @click="setRelationFilter(null)"
          :style="{
            padding: `${spacing[2]} ${spacing[3]}`,
            backgroundColor: filterRelation === null ? colors.accent.primary : colors.background.hover,
            color: filterRelation === null ? colors.text.onDark : colors.text.primary,
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: typography.fontSize.sm
          }"
        >
          All
        </button>
        <button
          @click="setRelationFilter('semantic')"
          :style="{
            padding: `${spacing[2]} ${spacing[3]}`,
            backgroundColor: filterRelation === 'semantic' ? colors.vibrantGold : colors.background.hover,
            color: filterRelation === 'semantic' ? colors.text.onDark : colors.text.primary,
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: typography.fontSize.sm
          }"
        >
          Semantic
        </button>
        <button
          @click="setRelationFilter('entity_link')"
          :style="{
            padding: `${spacing[2]} ${spacing[3]}`,
            backgroundColor: filterRelation === 'entity_link' ? colors.deepPurple : colors.background.hover,
            color: filterRelation === 'entity_link' ? colors.text.onDark : colors.text.primary,
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: typography.fontSize.sm
          }"
        >
          Entity
        </button>
        <button
          @click="setRelationFilter('tag_link')"
          :style="{
            padding: `${spacing[2]} ${spacing[3]}`,
            backgroundColor: filterRelation === 'tag_link' ? colors.softBlue : colors.background.hover,
            color: filterRelation === 'tag_link' ? colors.text.onDark : colors.text.primary,
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: typography.fontSize.sm
          }"
        >
          Tags
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state" :style="{ padding: spacing[8], textAlign: 'center', color: colors.text.muted }">
      Loading graph...
    </div>

    <!-- Error State -->
    <div v-if="error" class="error-state" :style="{ padding: spacing[4], color: colors.status.error, backgroundColor: '#FEE', borderRadius: '8px', marginTop: spacing[4] }">
      {{ error }}
    </div>

    <!-- Main Content: Graph -->
    <div class="main-content" :style="{ marginTop: spacing[4], position: 'relative' }">
      <!-- Graph Canvas -->
      <div class="graph-canvas" :style="{
        flex: 1,
        position: 'relative',
        backgroundColor: colors.background.primary,
        borderRadius: '8px',
        overflow: 'hidden',
        minHeight: '600px'
      }">
        <svg
          ref="svgRef"
          width="100%"
          height="100%"
          :style="{ display: 'block', minHeight: '600px' }"
        ></svg>
      </div>

      <!-- Floating Card: Node or Cluster Details -->
      <aside
        v-if="(selectedNode || selectedCluster) && cardVisible"
        class="details-panel floating-card"
        :style="{
          position: 'fixed',
          left: `${cardPosition.x}px`,
          top: `${cardPosition.y}px`,
          width: '400px',
          maxHeight: '500px',
          padding: spacing[4],
          backgroundColor: colors.background.card,
          borderRadius: '8px',
          border: `1px solid ${colors.border.subtle}`,
          boxShadow: '0 10px 30px rgba(0, 0, 0, 0.2)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'auto',
          zIndex: 1000,
          transition: 'left 200ms ease, top 200ms ease'
        }"
      >
        <!-- Card Header -->
        <div :style="{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: spacing[3] }">
          <h3 :style="{ fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold, margin: 0, flex: 1 }">
            {{ selectedNode ? getNodeTitle(selectedNode) : '' }}
          </h3>
          <button
            @click="hideCard"
            :style="{
              padding: `${spacing[1]} ${spacing[2]}`,
              backgroundColor: 'transparent',
              color: colors.text.secondary,
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: typography.fontSize.sm,
              fontWeight: typography.fontWeight.medium
            }"
            title="Close"
          >
            ✕
          </button>
        </div>

        <!-- Node Content -->
        <template v-if="selectedNode">
          <p :style="{ fontSize: typography.fontSize.sm, color: colors.text.secondary, marginBottom: spacing[3] }">
            📅 {{ new Date(selectedNode.created).toLocaleString() }}
          </p>

          <!-- Episodic Metadata -->
          <div :style="{ marginBottom: spacing[4], fontSize: typography.fontSize.sm }">
            <!-- WHO -->
            <div v-if="selectedNode.who?.length" :style="{ marginBottom: spacing[2] }">
              <span :style="{ fontWeight: typography.fontWeight.semibold, color: colors.text.secondary }">👥 WHO:</span>
              <span :style="{ marginLeft: spacing[2], color: colors.text.primary }">
                {{ selectedNode.who.join(', ') }}
              </span>
            </div>

            <!-- WHAT -->
            <div v-if="selectedNode.what?.length" :style="{ marginBottom: spacing[2] }">
              <span :style="{ fontWeight: typography.fontWeight.semibold, color: colors.text.secondary }">💡 WHAT:</span>
              <span :style="{ marginLeft: spacing[2], color: colors.text.primary }">
                {{ selectedNode.what.join(', ') }}
              </span>
            </div>

            <!-- WHERE -->
            <div v-if="selectedNode.where?.length" :style="{ marginBottom: spacing[2] }">
              <span :style="{ fontWeight: typography.fontWeight.semibold, color: colors.text.secondary }">📍 WHERE:</span>
              <span :style="{ marginLeft: spacing[2], color: colors.text.primary }">
                {{ selectedNode.where.join(', ') }}
              </span>
            </div>

            <!-- Tags -->
            <div v-if="selectedNode.tags?.length" :style="{ display: 'flex', gap: spacing[2], flexWrap: 'wrap', marginTop: spacing[3] }">
              <span
                v-for="tag in selectedNode.tags"
                :key="tag"
                :style="{
                  padding: `${spacing[1]} ${spacing[3]}`,
                  backgroundColor: colors.deepPurple,
                  color: colors.text.onDark,
                  borderRadius: '9999px',
                  fontSize: typography.fontSize.xs,
                  fontWeight: typography.fontWeight.medium
                }"
              >
                #{{ tag }}
              </span>
            </div>
          </div>

          <div :style="{
            flex: 1,
            padding: spacing[3],
            backgroundColor: colors.background.hover,
            borderRadius: '4px',
            fontSize: typography.fontSize.sm,
            lineHeight: '1.6',
            overflowY: 'auto'
          }">
            <p v-if="loadingContent" :style="{ color: colors.text.secondary, fontStyle: 'italic' }">
              Loading content...
            </p>
            <div
              v-else-if="renderedContent"
              class="markdown-content"
              v-html="renderedContent"
              :style="{ color: colors.text.primary }"
            ></div>
            <p v-else :style="{ color: colors.text.muted, fontStyle: 'italic' }">
              No content available
            </p>
          </div>
        </template>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.graph-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.controls {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.radio-group {
  display: flex;
  gap: 1rem;
}

.radio-group label {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  cursor: pointer;
  font-size: 14px;
}

.radio-group input[type="radio"] {
  cursor: pointer;
}

.graph-canvas {
  box-shadow: 0 1px 3px 0 rgba(52, 52, 52, 0.1);
}

.details-panel {
  box-shadow: 0 1px 3px 0 rgba(52, 52, 52, 0.1);
}

.cluster-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.cluster-list::-webkit-scrollbar {
  width: 6px;
}

.cluster-list::-webkit-scrollbar-thumb {
  background: #d4cfc4;
  border-radius: 3px;
}

.cluster-list::-webkit-scrollbar-track {
  background: transparent;
}

/* Markdown content styling */
.markdown-content {
  line-height: 1.6;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4) {
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  font-weight: 600;
}

.markdown-content :deep(h1) {
  font-size: 1.5rem;
}

.markdown-content :deep(h2) {
  font-size: 1.25rem;
}

.markdown-content :deep(h3) {
  font-size: 1.125rem;
}

.markdown-content :deep(p) {
  margin-bottom: 1rem;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin-bottom: 1rem;
  padding-left: 1.5rem;
}

.markdown-content :deep(li) {
  margin-bottom: 0.25rem;
}

.markdown-content :deep(code) {
  background-color: #f5f2ed;
  padding: 0.125rem 0.25rem;
  border-radius: 3px;
  font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
  font-size: 0.875em;
}

.markdown-content :deep(pre) {
  background-color: #f5f2ed;
  padding: 1rem;
  border-radius: 6px;
  overflow-x: auto;
  margin-bottom: 1rem;
}

.markdown-content :deep(pre code) {
  background: none;
  padding: 0;
}

.markdown-content :deep(blockquote) {
  border-left: 3px solid #9ca89a;
  padding-left: 1rem;
  margin-left: 0;
  margin-bottom: 1rem;
  color: #6b6b6b;
}

.markdown-content :deep(a) {
  color: #d47a44;
  text-decoration: none;
}

.markdown-content :deep(a:hover) {
  text-decoration: underline;
}

.markdown-content :deep(hr) {
  border: none;
  border-top: 1px solid #e8e4db;
  margin: 1.5rem 0;
}
</style>
