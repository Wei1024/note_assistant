"""
Semantic Layer - Embedding Generation & Vector Search
Uses sentence-transformers for local embedding generation.
NumPy brute-force for similarity search (fast enough for <1K notes).

Migration path: NumPy → FAISS when scaling to 5K+ notes.
"""
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..db.graph import create_edge, get_all_nodes

# Global model cache (load once)
_embedding_model = None


def get_embedding_model() -> SentenceTransformer:
    """Load embedding model (cached globally)"""
    global _embedding_model
    if _embedding_model is None:
        print("Loading embedding model: all-MiniLM-L6-v2...")
        _embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        print("✅ Embedding model loaded")
    return _embedding_model


def generate_embedding(text: str) -> np.ndarray:
    """Generate 384-dim embedding from text

    Returns normalized vector (for cosine = dot product optimization)

    Args:
        text: Input text to embed

    Returns:
        384-dim normalized numpy array (float32)
    """
    model = get_embedding_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding


def store_embedding(note_id: str, embedding: np.ndarray, db_connection):
    """Store embedding as BLOB in graph_nodes.embedding

    Args:
        note_id: Note ID
        embedding: 384-dim numpy array
        db_connection: SQLite connection
    """
    embedding_blob = embedding.tobytes()
    db_connection.execute(
        "UPDATE graph_nodes SET embedding = ? WHERE id = ?",
        (embedding_blob, note_id)
    )


def get_embedding(note_id: str, db_connection) -> Optional[np.ndarray]:
    """Load embedding from database

    Args:
        note_id: Note ID
        db_connection: SQLite connection

    Returns:
        384-dim numpy array or None if not found
    """
    row = db_connection.execute(
        "SELECT embedding FROM graph_nodes WHERE id = ?",
        (note_id,)
    ).fetchone()

    if not row or not row[0]:
        return None

    # Deserialize BLOB to numpy array (384 dimensions, float32)
    return np.frombuffer(row[0], dtype=np.float32)


def find_similar_notes(
    note_id: str,
    threshold: float = 0.7,
    limit: int = 10,
    db_connection = None
) -> List[Dict[str, Any]]:
    """Find similar notes using NumPy brute-force cosine similarity

    Args:
        note_id: Query note ID
        threshold: Minimum cosine similarity (0.0 to 1.0)
        limit: Max results to return
        db_connection: Optional DB connection

    Returns:
        List of {note_id, similarity, text, who, what, tags} dicts
    """
    should_close = db_connection is None
    if db_connection is None:
        from ..config import get_db_connection
        con = get_db_connection()
    else:
        con = db_connection

    try:
        # Get query embedding
        query_embedding = get_embedding(note_id, con)
        if query_embedding is None:
            return []

        # Load all nodes with embeddings
        all_nodes = get_all_nodes()  # From api/db/graph.py

        # Filter: only nodes with embeddings, exclude query note
        nodes_with_embeddings = []
        embeddings_list = []

        for node in all_nodes:
            if node['id'] == note_id:
                continue  # Skip self

            emb = get_embedding(node['id'], con)
            if emb is not None:
                nodes_with_embeddings.append(node)
                embeddings_list.append(emb)

        if not embeddings_list:
            return []

        # Stack embeddings into matrix
        embeddings_matrix = np.vstack(embeddings_list)

        # Compute cosine similarity (batch)
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
                'text': nodes_with_embeddings[idx]['text'][:100] + '...',  # Preview
                'who': nodes_with_embeddings[idx]['who'],
                'what': nodes_with_embeddings[idx]['what'],
                'tags': nodes_with_embeddings[idx]['tags']
            })

        return results

    finally:
        if should_close:
            con.close()


def create_semantic_edges(note_id: str, db_connection):
    """Create semantic edges for similar notes (>= threshold)

    Stores edges unidirectionally (A→B where A.id < B.id)
    Edge weight = cosine similarity

    Args:
        note_id: Note ID to find similar notes for
        db_connection: SQLite connection
    """
    similar_notes = find_similar_notes(
        note_id,
        threshold=0.5,  # Lowered from 0.7 - real-world notes have moderate similarity
        limit=20,  # Check more candidates
        db_connection=db_connection
    )

    for similar in similar_notes:
        other_id = similar['note_id']
        similarity = similar['similarity']

        # Normalize edge direction (lexicographically smaller ID first)
        src_id = min(note_id, other_id)
        dst_id = max(note_id, other_id)

        # Create edge (or update if exists)
        create_edge(
            src_node_id=src_id,
            dst_node_id=dst_id,
            relation='semantic',
            weight=similarity,
            metadata={'similarity': similarity},
            db_connection=db_connection
        )
