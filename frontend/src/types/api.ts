/**
 * API Type Definitions
 *
 * TypeScript interfaces matching the backend API contract.
 * Based on api/README.md specification.
 */

// ========================================
// Core Data Models
// ========================================

/**
 * Multi-dimensional classification (5 boolean dimensions)
 */
export interface Dimensions {
  has_action_items: boolean
  is_social: boolean
  is_emotional: boolean
  is_knowledge: boolean
  is_exploratory: boolean
}

/**
 * Response from /classify_and_save endpoint
 */
export interface ClassifyResponse {
  title: string
  dimensions: Dimensions
  tags: string[]
  path: string
}

/**
 * Search result hit
 */
export interface SearchHit {
  path: string
  snippet: string       // HTML with <b> highlights
  score: number         // 0-1 relevance score
  metadata: {
    created: string     // ISO timestamp
    dimensions: Dimensions
  }
}

/**
 * Synthesis response from /synthesize endpoint
 */
export interface SynthesisResponse {
  query: string
  summary: string
  notes_analyzed: number
  search_results: SearchHit[]
}

/**
 * Streaming synthesis event types
 */
export type SynthesisStreamEvent =
  | { type: 'metadata'; query: string; notes_analyzed: number }
  | { type: 'chunk'; content: string }
  | { type: 'results'; search_results: SearchHit[] }
  | { type: 'done' }

/**
 * Knowledge graph node
 */
export interface GraphNode {
  id: string            // Note ID (e.g., "2025-10-16T15:30:00-07:00_a27f")
  path: string
  created: string       // ISO timestamp
  dimensions: Dimensions
}

/**
 * Knowledge graph edge (link between notes)
 */
export interface GraphEdge {
  from: string          // Source note ID
  to: string            // Target note ID
  type: 'related' | 'spawned' | 'references' | 'contradicts'
}

/**
 * Graph traversal response from /search/graph
 */
export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

/**
 * Consolidation result from /consolidate/{note_id}
 */
export interface ConsolidationResult {
  note_id: string
  links_created: number
  candidates_found: number
  timings: {
    db_query: number
    find_candidates: number
    llm_suggest: number
    store_links: number
    total: number
  }
}

// ========================================
// Request Payloads
// ========================================

/**
 * Request for /classify_and_save
 */
export interface ClassifyRequest {
  text: string
}

/**
 * Request for search endpoints
 */
export interface SearchRequest {
  query: string
  limit?: number
}

/**
 * Request for /synthesize and /synthesize/stream
 */
export interface SynthesisRequest {
  query: string
  limit?: number
}

/**
 * Request for /search/graph
 */
export interface GraphSearchRequest {
  start_note_id: string
  depth?: number
  relationship_type?: 'related' | 'spawned' | 'references' | 'contradicts'
}

/**
 * Request for /search/dimensions
 */
export interface DimensionSearchRequest {
  dimension_type: 'context' | 'emotion' | 'time_reference'
  dimension_value: string
  query_text?: string
  limit?: number
}

/**
 * Request for /search/entities
 */
export interface EntitySearchRequest {
  entity_type: 'person' | 'topic' | 'project' | 'tech'
  entity_value: string
  context?: 'tasks' | 'meetings' | 'ideas' | 'reference' | 'journal'
  limit?: number
}

// ========================================
// Error Handling
// ========================================

/**
 * Standard API error response
 */
export interface ApiError {
  detail: string
}

/**
 * Type guard for API errors
 */
export function isApiError(response: unknown): response is ApiError {
  return (
    typeof response === 'object' &&
    response !== null &&
    'detail' in response &&
    typeof (response as ApiError).detail === 'string'
  )
}
