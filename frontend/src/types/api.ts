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
 * Response from /classify_and_save endpoint (legacy)
 */
export interface ClassifyResponse {
  title: string
  dimensions: Dimensions
  tags: string[]
  path: string
}

/**
 * Response from /capture_note endpoint (GraphRAG)
 */
export interface CaptureNoteResponse {
  note_id: string
  title: string
  episodic: EpisodicMetadata
  path: string
}

/**
 * Search result hit (Phase 4 - GraphRAG hybrid search)
 */
export interface SearchResultModel {
  note_id: string
  title: string
  snippet: string        // Query-highlighted excerpt
  score: number          // Fused score (0-1)
  fts_score: number      // FTS5 component score
  vector_score: number   // Vector similarity score
  episodic: EpisodicMetadata
  file_path: string
  text_preview: string
}

/**
 * Expanded graph node from search (Phase 4)
 */
export interface ExpandedNodeModel {
  note_id: string
  title: string
  text_preview: string
  relation: 'semantic' | 'entity_link' | 'tag_link'  // Edge type
  hop_distance: number
  relevance_score: number
  connected_to: string[]  // Seed note IDs
}

/**
 * Cluster summary for search context (Phase 4)
 */
export interface ClusterSummaryModel {
  cluster_id: number
  title: string
  summary: string
  size: number
}

/**
 * Search response from /search endpoint (Phase 4)
 */
export interface SearchResponse {
  query: string
  primary_results: SearchResultModel[]
  expanded_results: ExpandedNodeModel[]
  cluster_summaries: ClusterSummaryModel[]
  total_results: number
  execution_time_ms: number
}

/**
 * Similarity search response from /search/similar/{note_id}
 */
export interface SimilarityResponse {
  query_note_id: string
  similar_notes: SearchResultModel[]
  total: number
}

/**
 * Synthesis response from /synthesize endpoint (Phase 4+)
 */
export interface SynthesisResponse {
  query: string
  summary: string
  notes_analyzed: number
  search_results: SearchResultModel[]
  expanded_results: ExpandedNodeModel[]
  cluster_summaries: ClusterSummaryModel[]
}

/**
 * Streaming synthesis event types (Phase 4+ SSE)
 */
export type SynthesisStreamEvent =
  | { type: 'metadata'; query: string; notes_analyzed: number; has_clusters: boolean; has_expanded: boolean }
  | { type: 'chunk'; content: string }
  | { type: 'results'; search_results: SearchResultModel[]; expanded_results: ExpandedNodeModel[]; cluster_summaries: ClusterSummaryModel[] }
  | { type: 'done' }

// ========================================
// Legacy Types (kept for backward compatibility)
// ========================================

/**
 * Search result hit (legacy)
 * @deprecated Use SearchResultModel instead
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
 * Episodic metadata for GraphRAG nodes
 */
export interface EpisodicMetadata {
  who: string[]         // WHO entities (people, organizations)
  what: string[]        // WHAT entities (topics, projects, technologies)
  where: string[]       // WHERE entities (locations, platforms)
  when: TimeReference[] // WHEN time references
  tags: string[]        // User-defined tags
}

/**
 * Knowledge graph node (GraphRAG schema)
 */
export interface GraphNode {
  id: string            // Note ID (e.g., "note_20251021_143022_abc123")
  text: string          // Full note text
  created: string       // ISO timestamp
  file_path: string     // Path to markdown file
  who: string[]         // WHO entities
  what: string[]        // WHAT entities
  where: string[]       // WHERE entities
  when: TimeReference[] // WHEN time references
  tags: string[]        // Tags
  cluster_id?: number   // Cluster assignment (Phase 2.5)
  // D3 simulation properties (added at runtime)
  x?: number
  y?: number
  vx?: number
  vy?: number
  fx?: number | null
  fy?: number | null
}

/**
 * Knowledge graph edge (GraphRAG schema)
 */
export interface GraphEdge {
  source: string        // Source note ID (D3 convention)
  target: string        // Target note ID (D3 convention)
  relation: 'semantic' | 'entity_link' | 'tag_link' | 'time_next' | 'reminder'
  weight: number        // Relationship strength
  metadata?: Record<string, any>  // Additional edge metadata
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

/**
 * Person entity extracted from notes
 */
export interface PersonEntity {
  name: string
  role?: string
  relation?: string
}

/**
 * Concept/entity with frequency count
 */
export interface ConceptEntity {
  concept: string
  frequency: number
}

/**
 * Time reference (deadline, meeting, event)
 */
export interface TimeReference {
  type?: string
  datetime?: string
  description?: string
}

/**
 * Cluster summary with aggregated metadata
 */
export interface ClusterSummary {
  cluster_id: number
  size: number
  theme: string
  people: PersonEntity[]
  key_concepts: ConceptEntity[]
  emotions: string[]
  time_references: TimeReference[]
  dimensions: Dimensions
  action_count: number
}

/**
 * Clustered graph data from /graph/clusters
 */
export interface ClusteredGraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  clusters: ClusterSummary[]
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
