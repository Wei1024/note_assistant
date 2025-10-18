<script setup lang="ts">
import { ref, onMounted, watch, nextTick, computed } from 'vue'
import * as d3 from 'd3'
import { marked } from 'marked'
import { useKnowledgeGraph } from '@/composables/useKnowledgeGraph'
import { colors, getDimensionColor } from '@/design/colors'
import { typography } from '@/design/typography'
import { spacing } from '@/design/spacing'
import { graph, getNodeRadius } from '@/design/graph'
import type { GraphNode, Dimensions } from '@/types/api'

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
  loadGraph,
  loadFullGraph,
  selectNode,
  clearSelection,
} = useKnowledgeGraph()

const svgRef = ref<SVGSVGElement | null>(null)
const depth = ref(2)
const startNoteId = ref<string>('')
const viewMode = ref<'ego' | 'full'>('ego')
const minLinks = ref(1) // For full graph: only show notes with links
const graphLimit = ref(100) // For full graph: max nodes

// Demo note ID for testing (using a real note with links)
const demoNoteId = '2025-10-12T16:01:08-07:00_ae68'

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

/**
 * Get dominant dimension color for a node
 */
function getNodeColor(dimensions: Dimensions): string {
  const activeDimensions = Object.entries(dimensions)
    .filter(([_, value]) => value === true)

  if (activeDimensions.length === 0) {
    return colors.mutedSage // No dimensions
  }

  // Return color of first active dimension
  const dimensionKey = activeDimensions[0][0] as keyof Dimensions
  const colorKey = dimensionKey.replace(/_/g, '')
    .replace(/^(.)/, (m) => m.toLowerCase())
    .replace(/([A-Z])/g, (m) => m.charAt(0).toUpperCase() + m.slice(1).toLowerCase()) as keyof typeof colors.dimension

  return getDimensionColor(colorKey)
}

/**
 * Truncate text to max length
 */
function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength - 3) + '...'
}

/**
 * Extract title from path
 */
function getNodeTitle(node: GraphNode): string {
  const filename = node.path.split('/').pop() || node.id
  const title = filename.replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/\.md$/, '')
  return truncateText(title, 20)
}

/**
 * Render force-directed graph with D3
 */
function renderGraph() {
  if (!svgRef.value || !graphData.value) return

  const svg = d3.select(svgRef.value)
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

  svg.call(zoom)

  const { nodes, edges } = graphData.value

  // Map edges to D3 format (from/to → source/target)
  const d3Links = edges.map(edge => ({
    source: edge.from,
    target: edge.to,
    type: edge.type
  }))

  // Calculate connection counts for sizing
  const connectionCounts = new Map<string, number>()
  nodes.forEach(node => {
    const count = edges.filter(e => e.from === node.id || e.to === node.id).length
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
    .attr('fill', (d: GraphNode) => getNodeColor(d.dimensions))
    .attr('stroke', colors.background.card)
    .attr('stroke-width', graph.node.strokeWidth)
    .style('cursor', 'pointer')
    .on('click', (_, d: GraphNode) => {
      selectNode(d.id)
      updateSelection()
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
        if (edge.from === selectedNodeId.value) connectedNodeIds.add(edge.to)
        if (edge.to === selectedNodeId.value) connectedNodeIds.add(edge.from)
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
// Lifecycle & Watchers
// ========================================
onMounted(async () => {
  // Load demo graph on mount
  startNoteId.value = demoNoteId
  await loadGraph(demoNoteId, depth.value)
})

watch(graphData, async () => {
  if (graphData.value) {
    await nextTick()
    renderGraph()
  }
})

watch(selectedNodeId, () => {
  if (svgRef.value) {
    renderGraph() // Re-render to update selection
  }
})

/**
 * Handle depth change (ego mode only)
 */
async function handleDepthChange() {
  if (startNoteId.value && viewMode.value === 'ego') {
    await loadGraph(startNoteId.value, depth.value)
  }
}

/**
 * Switch to ego-centric view
 */
async function switchToEgoView() {
  viewMode.value = 'ego'
  if (demoNoteId) {
    await loadGraph(demoNoteId, depth.value)
  }
}

/**
 * Switch to full corpus view
 */
async function switchToFullView() {
  viewMode.value = 'full'
  await loadFullGraph(minLinks.value, undefined, graphLimit.value)
}
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
    <div class="controls" :style="{ marginTop: spacing[4], display: 'flex', gap: spacing[6], alignItems: 'center' }">
      <!-- View Mode Toggle -->
      <div class="control-group">
        <label :style="{ fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.medium, color: colors.text.secondary }">
          View:
        </label>
        <div :style="{ display: 'flex', gap: spacing[2] }">
          <button
            @click="switchToEgoView"
            :style="{
              padding: `${spacing[2]} ${spacing[3]}`,
              backgroundColor: viewMode === 'ego' ? colors.accent.primary : 'transparent',
              color: viewMode === 'ego' ? colors.text.onDark : colors.text.primary,
              border: `1px solid ${viewMode === 'ego' ? colors.accent.primary : colors.border.default}`,
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: typography.fontSize.sm,
              fontWeight: typography.fontWeight.medium,
              transition: 'all 200ms ease'
            }"
          >
            Explore from Note
          </button>
          <button
            @click="switchToFullView"
            :style="{
              padding: `${spacing[2]} ${spacing[3]}`,
              backgroundColor: viewMode === 'full' ? colors.accent.primary : 'transparent',
              color: viewMode === 'full' ? colors.text.onDark : colors.text.primary,
              border: `1px solid ${viewMode === 'full' ? colors.accent.primary : colors.border.default}`,
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: typography.fontSize.sm,
              fontWeight: typography.fontWeight.medium,
              transition: 'all 200ms ease'
            }"
          >
            Full Corpus
          </button>
        </div>
      </div>

      <!-- Depth Control (only for ego mode) -->
      <div v-if="viewMode === 'ego'" class="control-group">
        <label :style="{ fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.medium, color: colors.text.secondary }">
          Depth:
        </label>
        <div class="radio-group">
          <label>
            <input type="radio" v-model.number="depth" :value="1" @change="handleDepthChange" />
            1
          </label>
          <label>
            <input type="radio" v-model.number="depth" :value="2" @change="handleDepthChange" />
            2
          </label>
          <label>
            <input type="radio" v-model.number="depth" :value="3" @change="handleDepthChange" />
            3
          </label>
        </div>
      </div>

      <!-- Node count info (for full mode) -->
      <div v-if="viewMode === 'full' && graphData" :style="{ fontSize: typography.fontSize.sm, color: colors.text.secondary }">
        {{ graphData.nodes.length }} notes, {{ graphData.edges.length }} connections
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

    <!-- Main Content: Graph + Details Side-by-Side -->
    <div class="main-content" :style="{ marginTop: spacing[4], display: 'flex', gap: spacing[4], alignItems: 'stretch' }">
      <!-- Graph Canvas (Left) -->
      <div class="graph-canvas" :style="{
        flex: selectedNode ? '1 1 65%' : '1 1 100%',
        position: 'relative',
        backgroundColor: colors.background.primary,
        borderRadius: '8px',
        overflow: 'hidden',
        minHeight: '600px',
        transition: 'flex 300ms ease'
      }">
        <svg
          ref="svgRef"
          width="100%"
          height="100%"
          :style="{ display: 'block', minHeight: '600px' }"
        ></svg>
      </div>

      <!-- Selected Node Details (Right Column) -->
      <aside
        v-if="selectedNode"
        class="details-panel"
        :style="{
          flex: '0 0 35%',
          padding: spacing[4],
          backgroundColor: colors.background.card,
          borderRadius: '8px',
          border: `1px solid ${colors.border.subtle}`,
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '600px',
          overflow: 'auto'
        }"
      >
        <div :style="{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: spacing[3] }">
          <h3 :style="{ fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold, margin: 0, flex: 1 }">
            {{ getNodeTitle(selectedNode) }}
          </h3>
          <button
            @click="clearSelection"
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

        <p :style="{ fontSize: typography.fontSize.sm, color: colors.text.secondary, marginBottom: spacing[3] }">
          📅 {{ new Date(selectedNode.created).toLocaleString() }}
        </p>

        <div :style="{ display: 'flex', gap: spacing[2], flexWrap: 'wrap', marginBottom: spacing[4] }">
          <span
            v-for="(value, key) in selectedNode.dimensions"
            :key="key"
            v-show="value"
            :style="{
              padding: `${spacing[1]} ${spacing[3]}`,
              backgroundColor: getDimensionColor(key as any),
              color: colors.text.onDark,
              borderRadius: '9999px',
              fontSize: typography.fontSize.sm,
              fontWeight: typography.fontWeight.medium
            }"
          >
            {{ key.replace(/^(is|has)/, '').replace(/([A-Z])/g, ' $1').trim() }}
          </span>
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
          <!-- Loading state -->
          <p v-if="loadingContent" :style="{ color: colors.text.secondary, fontStyle: 'italic' }">
            Loading content...
          </p>

          <!-- Content loaded (rendered markdown) -->
          <div
            v-else-if="renderedContent"
            class="markdown-content"
            v-html="renderedContent"
            :style="{
              color: colors.text.primary
            }"
          ></div>

          <!-- No content -->
          <p v-else :style="{ color: colors.text.muted, fontStyle: 'italic' }">
            No content available
          </p>
        </div>
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
