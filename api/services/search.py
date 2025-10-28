"""
Search Service - Hybrid Search & Graph Expansion for GraphRAG
Phase 4: Retrieval Layer

Combines:
1. FTS5 full-text search (keyword matching, BM25 ranking)
2. Vector similarity search (semantic similarity)
3. Graph expansion (contextual neighbors via edges)
4. Score fusion and re-ranking
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
import numpy as np
from sklearn.preprocessing import MinMaxScaler

from ..config import get_db_connection
from ..db.graph import get_graph_node, get_node_edges, get_all_nodes
from ..services.semantic import generate_embedding, get_embedding
from ..fts import search_notes as fts_search


# ==============================================================================
# Data Classes (will be moved to models.py)
# ==============================================================================

class SearchResult:
    """Single search result with fused scoring"""
    def __init__(
        self,
        note_id: str,
        title: str,
        snippet: str,
        score: float,
        fts_score: float,
        vector_score: float,
        episodic: Dict[str, Any],
        file_path: str,
        text_preview: str = ""
    ):
        self.note_id = note_id
        self.title = title
        self.snippet = snippet
        self.score = score
        self.fts_score = fts_score
        self.vector_score = vector_score
        self.episodic = episodic
        self.file_path = file_path
        self.text_preview = text_preview

    def to_dict(self) -> Dict[str, Any]:
        return {
            "note_id": self.note_id,
            "title": self.title,
            "snippet": self.snippet,
            "score": self.score,
            "fts_score": self.fts_score,
            "vector_score": self.vector_score,
            "episodic": self.episodic,
            "file_path": self.file_path,
            "text_preview": self.text_preview
        }


class ExpandedNode:
    """Graph-expanded result (neighbor of primary result)"""
    def __init__(
        self,
        note_id: str,
        title: str,
        text_preview: str,
        relation: str,
        hop_distance: int,
        relevance_score: float,
        connected_to: List[str]
    ):
        self.note_id = note_id
        self.title = title
        self.text_preview = text_preview
        self.relation = relation
        self.hop_distance = hop_distance
        self.relevance_score = relevance_score
        self.connected_to = connected_to

    def to_dict(self) -> Dict[str, Any]:
        return {
            "note_id": self.note_id,
            "title": self.title,
            "text_preview": self.text_preview,
            "relation": self.relation,
            "hop_distance": self.hop_distance,
            "relevance_score": self.relevance_score,
            "connected_to": self.connected_to
        }


# ==============================================================================
# Core Search Functions
# ==============================================================================

def normalize_scores(scores: List[float]) -> List[float]:
    """Normalize scores to [0, 1] range using min-max scaling

    Args:
        scores: List of raw scores

    Returns:
        List of normalized scores in [0, 1]
    """
    if not scores:
        return []

    if len(scores) == 1:
        return [1.0]

    # Handle case where all scores are the same
    if min(scores) == max(scores):
        return [0.5] * len(scores)

    # Min-max normalization
    scores_array = np.array(scores).reshape(-1, 1)
    scaler = MinMaxScaler()
    normalized = scaler.fit_transform(scores_array).flatten()

    return normalized.tolist()


async def hybrid_search(
    query: str,
    top_k: int = 10,
    fts_weight: float = 0.4,
    vector_weight: float = 0.6,
    cluster_id: Optional[int] = None
) -> List[SearchResult]:
    """Hybrid search combining FTS5 + vector similarity with score fusion

    Algorithm:
    1. Execute FTS5 search (get top 20 candidates with BM25 scores)
    2. Generate query embedding and find similar notes (top 20 candidates)
    3. Normalize both score distributions to [0, 1]
    4. Fuse scores: final = fts_weight * fts_norm + vector_weight * vector_norm
    5. Return top-K results ranked by fused score

    Args:
        query: Search query string
        top_k: Number of results to return
        fts_weight: Weight for FTS5 score (default 0.4)
        vector_weight: Weight for vector similarity (default 0.6)
        cluster_id: Optional cluster ID to restrict search

    Returns:
        List of SearchResult objects, ranked by fused score
    """
    # Step 1: FTS5 search (keyword matching)
    fts_results = fts_search(query, limit=20)  # Get more candidates for fusion

    # Step 2: Vector similarity search
    query_embedding = generate_embedding(query)
    vector_results = await vector_search(query_embedding, threshold=0.3, limit=20)

    # Step 3: Build unified result set
    # Map note_id -> (fts_score, vector_score)
    score_map: Dict[str, Dict[str, float]] = {}

    # Add FTS results
    for fts_result in fts_results:
        note_id = _extract_note_id_from_path(fts_result['path'])
        if note_id:
            # BM25 scores are negative (lower is better), convert to positive
            fts_score = abs(fts_result['score'])
            score_map[note_id] = {'fts': fts_score, 'vector': 0.0}

    # Add vector results
    for vec_result in vector_results:
        note_id = vec_result['note_id']
        vector_score = vec_result['similarity']

        if note_id in score_map:
            score_map[note_id]['vector'] = vector_score
        else:
            score_map[note_id] = {'fts': 0.0, 'vector': vector_score}

    # Filter by cluster if specified
    if cluster_id is not None:
        score_map = {
            nid: scores for nid, scores in score_map.items()
            if _get_note_cluster(nid) == cluster_id
        }

    if not score_map:
        return []

    # Step 4: Normalize scores
    note_ids = list(score_map.keys())
    fts_scores = [score_map[nid]['fts'] for nid in note_ids]
    vector_scores = [score_map[nid]['vector'] for nid in note_ids]

    fts_normalized = normalize_scores(fts_scores)
    vector_normalized = normalize_scores(vector_scores)

    # Step 5: Fuse scores
    fused_scores = []
    for i in range(len(note_ids)):
        fused = fts_weight * fts_normalized[i] + vector_weight * vector_normalized[i]
        fused_scores.append(fused)

    # Step 6: Rank by fused score and take top-K
    ranked_indices = np.argsort(fused_scores)[::-1][:top_k]

    # Step 7: Build SearchResult objects
    results = []
    for idx in ranked_indices:
        note_id = note_ids[idx]
        node = get_graph_node(note_id)

        if not node:
            continue

        # Extract title from episodic metadata or file path
        title = _extract_title_from_node(node)
        snippet = _generate_snippet(node['text'], query)

        result = SearchResult(
            note_id=note_id,
            title=title,
            snippet=snippet,
            score=fused_scores[idx],
            fts_score=fts_normalized[idx],
            vector_score=vector_normalized[idx],
            episodic={
                'who': node.get('who', []),
                'what': node.get('what', []),
                'where': node.get('where', []),
                'when': node.get('when', []),
                'tags': node.get('tags', [])
            },
            file_path=node.get('file_path', ''),
            text_preview=node['text'][:300] + '...' if len(node['text']) > 300 else node['text']
        )
        results.append(result)

    return results


async def vector_search(
    query_embedding: np.ndarray,
    threshold: float = 0.3,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Vector similarity search using cosine similarity

    Args:
        query_embedding: Query embedding vector (384-dim)
        threshold: Minimum cosine similarity
        limit: Max results to return

    Returns:
        List of {note_id, similarity, text, who, what, tags} dicts
    """
    con = get_db_connection()

    try:
        # Load all nodes with embeddings
        all_nodes = get_all_nodes()

        # Filter: only nodes with embeddings
        nodes_with_embeddings = []
        embeddings_list = []

        for node in all_nodes:
            emb = get_embedding(node['id'], con)
            if emb is not None:
                nodes_with_embeddings.append(node)
                embeddings_list.append(emb)

        if not embeddings_list:
            return []

        # Stack embeddings into matrix
        embeddings_matrix = np.vstack(embeddings_list)

        # Compute cosine similarity (batch)
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity([query_embedding], embeddings_matrix)[0]

        # Filter by threshold
        above_threshold = similarities >= threshold
        indices = np.where(above_threshold)[0]

        # Sort by similarity (descending)
        sorted_indices = indices[np.argsort(-similarities[indices])]

        # Limit results
        top_indices = sorted_indices[:limit]

        # Build result list
        results = []
        for idx in top_indices:
            results.append({
                'note_id': nodes_with_embeddings[idx]['id'],
                'similarity': float(similarities[idx]),
                'text': nodes_with_embeddings[idx]['text'],
                'who': nodes_with_embeddings[idx]['who'],
                'what': nodes_with_embeddings[idx]['what'],
                'tags': nodes_with_embeddings[idx]['tags']
            })

        return results

    finally:
        con.close()


# ==============================================================================
# Graph Expansion
# ==============================================================================

def expand_via_graph(
    seed_note_ids: List[str],
    max_hops: int = 1,
    edge_priorities: Optional[Dict[str, float]] = None,
    max_expanded: int = 20
) -> List[ExpandedNode]:
    """Expand search results via graph traversal

    Traverses graph edges to find contextual neighbors of seed results.
    Uses edge type priorities to favor stronger semantic connections.

    Args:
        seed_note_ids: Starting nodes (top-K search results)
        max_hops: Maximum traversal depth (default 1)
        edge_priorities: Edge type -> weight mapping
        max_expanded: Maximum expanded results to return

    Returns:
        List of ExpandedNode objects (neighbors not in seed set)
    """
    if edge_priorities is None:
        edge_priorities = {
            'entity_link': 1.0,   # Strongest: shared entities
            'semantic': 0.8,       # Medium: content similarity
            'tag_link': 0.6        # Weakest: thematic similarity
        }

    visited: Set[str] = set(seed_note_ids)
    expanded_nodes: Dict[str, ExpandedNode] = {}

    # BFS traversal
    current_hop = 0
    frontier = [(nid, 0, []) for nid in seed_note_ids]  # (node_id, hop, path)

    while frontier and current_hop < max_hops:
        next_frontier = []

        for node_id, hop, path in frontier:
            if hop >= max_hops:
                continue

            # Get all edges for this node
            edges = get_node_edges(node_id)

            for edge in edges:
                # Determine neighbor (handle bidirectional edges)
                neighbor_id = edge['dst'] if edge['src'] == node_id else edge['src']

                if neighbor_id in visited:
                    continue

                visited.add(neighbor_id)

                # Get neighbor node details
                neighbor_node = get_graph_node(neighbor_id)
                if not neighbor_node:
                    continue

                # Calculate relevance score (decayed by hop distance and edge priority)
                edge_type = edge['relation']
                edge_weight = edge.get('weight', 1.0)
                priority = edge_priorities.get(edge_type, 0.5)

                # Decay factor: 0.5^(hop+1)
                decay = 0.5 ** (hop + 1)
                relevance = priority * edge_weight * decay

                # Extract title
                title = _extract_title_from_node(neighbor_node)
                text_preview = neighbor_node['text'][:200] + '...' if len(neighbor_node['text']) > 200 else neighbor_node['text']

                # Track which seed nodes this connects to
                connection_path = path + [node_id]

                # Create or update expanded node
                if neighbor_id in expanded_nodes:
                    # Update if higher relevance score
                    existing = expanded_nodes[neighbor_id]
                    if relevance > existing.relevance_score:
                        existing.relevance_score = relevance
                        existing.relation = edge_type
                        existing.hop_distance = hop + 1
                    # Add connection
                    if node_id not in existing.connected_to:
                        existing.connected_to.append(node_id)
                else:
                    expanded_nodes[neighbor_id] = ExpandedNode(
                        note_id=neighbor_id,
                        title=title,
                        text_preview=text_preview,
                        relation=edge_type,
                        hop_distance=hop + 1,
                        relevance_score=relevance,
                        connected_to=[node_id]
                    )

                # Add to next frontier
                next_frontier.append((neighbor_id, hop + 1, connection_path))

        frontier = next_frontier
        current_hop += 1

    # Sort by relevance and return top results
    sorted_nodes = sorted(
        expanded_nodes.values(),
        key=lambda x: x.relevance_score,
        reverse=True
    )

    return sorted_nodes[:max_expanded]


# ==============================================================================
# Context Assembly
# ==============================================================================

def assemble_context(
    primary_results: List[SearchResult],
    expanded_results: List[ExpandedNode],
    max_context_tokens: int = 2000,
    include_cluster_summaries: bool = True
) -> Dict[str, Any]:
    """Assemble search context for LLM synthesis

    Formats primary and expanded results into structured context.
    Includes cluster summaries if results span multiple clusters.

    Args:
        primary_results: Hybrid search results
        expanded_results: Graph-expanded neighbors
        max_context_tokens: Approximate token budget (chars ~= tokens/4)
        include_cluster_summaries: Whether to include cluster context

    Returns:
        Dict with formatted context sections
    """
    max_chars = max_context_tokens * 4  # Rough approximation
    current_chars = 0

    context = {
        'primary_results': [],
        'expanded_results': [],
        'cluster_summaries': [],
        'total_notes': len(primary_results) + len(expanded_results),
        'truncated': False
    }

    # Add primary results (full text)
    for i, result in enumerate(primary_results):
        if current_chars >= max_chars:
            context['truncated'] = True
            break

        result_text = f"""
[Primary Result {i+1}] {result.title}
Score: {result.score:.3f} (FTS: {result.fts_score:.3f}, Vector: {result.vector_score:.3f})
Entities: WHO={result.episodic.get('who', [])}, WHAT={result.episodic.get('what', [])}
Tags: {result.episodic.get('tags', [])}
Text: {result.text_preview}
---
"""
        current_chars += len(result_text)
        context['primary_results'].append({
            'rank': i + 1,
            'note_id': result.note_id,
            'title': result.title,
            'score': result.score,
            'text': result.text_preview,
            'episodic': result.episodic
        })

    # Add expanded results (preview only)
    for i, node in enumerate(expanded_results):
        if current_chars >= max_chars:
            context['truncated'] = True
            break

        result_text = f"""
[Related Note {i+1}] {node.title}
Connection: {node.relation} (hop {node.hop_distance}, relevance {node.relevance_score:.3f})
Connected to: {', '.join(node.connected_to[:3])}
Text: {node.text_preview}
---
"""
        current_chars += len(result_text)
        context['expanded_results'].append({
            'rank': i + 1,
            'note_id': node.note_id,
            'title': node.title,
            'relation': node.relation,
            'hop_distance': node.hop_distance,
            'relevance_score': node.relevance_score,
            'text': node.text_preview
        })

    # Add cluster summaries if requested
    if include_cluster_summaries:
        cluster_ids = set()
        for result in primary_results:
            cluster_id = _get_note_cluster(result.note_id)
            if cluster_id is not None:
                cluster_ids.add(cluster_id)

        if cluster_ids:
            cluster_summaries = _get_cluster_summaries(list(cluster_ids))
            context['cluster_summaries'] = cluster_summaries

    return context


# ==============================================================================
# Helper Functions
# ==============================================================================

def _extract_note_id_from_path(file_path: str) -> Optional[str]:
    """Extract note ID from file path

    Queries database to find note ID by file path
    """
    con = get_db_connection()
    try:
        row = con.execute(
            "SELECT id FROM notes_meta WHERE path = ?",
            (file_path,)
        ).fetchone()
        return row[0] if row else None
    finally:
        con.close()


def _extract_title_from_node(node: Dict[str, Any]) -> str:
    """Extract title from node metadata"""
    # Try tags first (first tag often contains title-like info)
    tags = node.get('tags', [])
    if tags:
        return tags[0]

    # Fallback to first line of text
    text = node.get('text', '')
    first_line = text.split('\n')[0][:60]
    return first_line if first_line else 'Untitled Note'


def _generate_snippet(text: str, query: str, context_chars: int = 150) -> str:
    """Generate snippet with query context

    Finds query terms in text and returns surrounding context
    """
    text_lower = text.lower()
    query_lower = query.lower()

    # Find first occurrence of query
    idx = text_lower.find(query_lower)

    if idx == -1:
        # Query not found, return first N chars
        return text[:context_chars] + '...' if len(text) > context_chars else text

    # Extract context around query
    start = max(0, idx - context_chars // 2)
    end = min(len(text), idx + len(query) + context_chars // 2)

    snippet = text[start:end]

    # Add ellipsis if truncated
    if start > 0:
        snippet = '...' + snippet
    if end < len(text):
        snippet = snippet + '...'

    return snippet


def _get_note_cluster(note_id: str) -> Optional[int]:
    """Get cluster ID for a note"""
    con = get_db_connection()
    try:
        row = con.execute(
            "SELECT cluster_id FROM graph_nodes WHERE id = ?",
            (note_id,)
        ).fetchone()
        return row[0] if row else None
    finally:
        con.close()


def _get_cluster_summaries(cluster_ids: List[int]) -> List[Dict[str, Any]]:
    """Get cluster summaries for given cluster IDs"""
    if not cluster_ids:
        return []

    con = get_db_connection()
    try:
        placeholders = ','.join('?' * len(cluster_ids))
        query = f"""
            SELECT id, title, summary, size
            FROM graph_clusters
            WHERE id IN ({placeholders})
        """
        rows = con.execute(query, cluster_ids).fetchall()

        summaries = []
        for row in rows:
            summaries.append({
                'cluster_id': row[0],
                'title': row[1],
                'summary': row[2],
                'size': row[3]
            })

        return summaries
    finally:
        con.close()
