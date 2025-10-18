/**
 * Knowledge Graph Visualization Tokens
 *
 * Design tokens specific to graph visualization (nodes, edges, forces).
 */

export const graph = {
  // ========================================
  // Node Sizing
  // ========================================
  node: {
    // Base radius for nodes
    radiusBase: 20,
    radiusMin: 15,
    radiusMax: 35,

    // Size multipliers based on connection count
    sizeScale: {
      isolated: 0.75,      // No connections
      small: 1.0,          // 1-3 connections
      medium: 1.25,        // 4-7 connections
      large: 1.5,          // 8+ connections
    },

    // Stroke width for node borders
    strokeWidth: 2,
    strokeWidthSelected: 3,

    // Opacity
    opacity: 1.0,
    opacityHover: 0.85,
    opacityInactive: 0.3,  // When another node is selected
  },

  // ========================================
  // Edge Styling
  // ========================================
  edge: {
    // Base stroke width for links
    strokeWidth: 2,
    strokeWidthHover: 3,

    // Opacity
    opacity: 0.4,
    opacityHover: 0.7,
    opacityInactive: 0.15,

    // Distance between connected nodes
    linkDistance: 100,
    linkDistanceMin: 60,
    linkDistanceMax: 150,

    // Dash patterns by relationship type
    strokeDasharray: {
      related: 'none',           // Solid line
      spawned: '5,5',            // Dashed
      references: '2,3',         // Dotted
      contradicts: '8,3,2,3',    // Dash-dot
    },
  },

  // ========================================
  // Force Simulation Parameters
  // ========================================
  force: {
    // Repulsion between nodes
    chargeStrength: -300,
    chargeDistanceMin: 1,
    chargeDistanceMax: 500,

    // Collision detection
    collisionRadius: 30,
    collisionStrength: 0.7,

    // Link force
    linkStrength: 0.5,

    // Center force (pulls graph to center)
    centerStrength: 0.1,
  },

  // ========================================
  // Labels
  // ========================================
  label: {
    fontSize: 12,
    fontWeight: 500,
    maxWidth: 80,           // Truncate labels longer than this
    offsetY: -25,           // Position above node
    opacity: 0.9,
    opacityHover: 1.0,
  },

  // ========================================
  // Animation & Interaction
  // ========================================
  animation: {
    transitionDuration: 200,  // ms for hover/selection
    simulationAlpha: 1.0,     // Initial simulation energy
    simulationAlphaMin: 0.001, // Stop when energy drops below this
    simulationAlphaDecay: 0.02, // Energy decay rate
    simulationVelocityDecay: 0.4, // Velocity damping
  },

  // ========================================
  // Canvas
  // ========================================
  canvas: {
    minZoom: 0.3,
    maxZoom: 3.0,
    zoomStep: 1.2,
  },
} as const

export type GraphToken = typeof graph

/**
 * Get node radius based on connection count
 */
export function getNodeRadius(connectionCount: number): number {
  let scale = graph.node.sizeScale.small

  if (connectionCount === 0) {
    scale = graph.node.sizeScale.isolated
  } else if (connectionCount >= 8) {
    scale = graph.node.sizeScale.large
  } else if (connectionCount >= 4) {
    scale = graph.node.sizeScale.medium
  }

  return graph.node.radiusBase * scale
}

/**
 * Get link distance based on node importance
 */
export function getLinkDistance(sourceConnections: number, targetConnections: number): number {
  const avgConnections = (sourceConnections + targetConnections) / 2

  if (avgConnections >= 8) {
    return graph.edge.linkDistanceMax
  } else if (avgConnections <= 2) {
    return graph.edge.linkDistanceMin
  }

  return graph.edge.linkDistance
}
