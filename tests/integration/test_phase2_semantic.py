#!/usr/bin/env python3
"""
Test Phase 2: Semantic Service
Tests embedding generation and similarity search functionality.
"""
import numpy as np
from api.services.semantic import generate_embedding, get_embedding_model
from api.config import get_db_connection
from api.db.graph import get_all_nodes


def test_embedding_generation():
    """Test 1: Generate embeddings for sample texts"""
    print("=" * 80)
    print("TEST 1: EMBEDDING GENERATION")
    print("=" * 80)
    print()

    samples = [
        "Met with Sarah to discuss FAISS vector search implementation",
        "Sarah sent email about the FAISS library performance",
        "Had lunch with Mom at the Italian restaurant",
        "Researching Redis caching strategies for our API",
        "Team meeting about Q4 roadmap and planning"
    ]

    print("Loading embedding model...")
    model = get_embedding_model()
    print(f"✅ Model loaded: {model}\n")

    embeddings = []
    for i, text in enumerate(samples, 1):
        print(f"[{i}/5] Generating embedding...")
        print(f"  Text: {text}")

        emb = generate_embedding(text)
        embeddings.append(emb)

        print(f"  Shape: {emb.shape}")
        print(f"  Dtype: {emb.dtype}")
        print(f"  Norm: {np.linalg.norm(emb):.4f}")
        print(f"  Min/Max: [{emb.min():.4f}, {emb.max():.4f}]")
        print()

    # Test similarity between related texts
    print("=" * 80)
    print("TEST 2: SIMILARITY COMPUTATION")
    print("=" * 80)
    print()

    from sklearn.metrics.pairwise import cosine_similarity

    # Compare sample 1 and 2 (both about Sarah + FAISS)
    sim_12 = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    print(f"Similarity (Sample 1 vs 2 - both about Sarah/FAISS): {sim_12:.4f}")

    # Compare sample 1 and 3 (different topics)
    sim_13 = cosine_similarity([embeddings[0]], [embeddings[2]])[0][0]
    print(f"Similarity (Sample 1 vs 3 - different topics):     {sim_13:.4f}")

    # Compare sample 4 and 5 (both work-related)
    sim_45 = cosine_similarity([embeddings[3]], [embeddings[4]])[0][0]
    print(f"Similarity (Sample 4 vs 5 - both work-related):    {sim_45:.4f}")

    print()
    print("Expected: Sample 1-2 should have high similarity (>0.7)")
    print("Expected: Sample 1-3 should have low similarity (<0.5)")
    print()


def test_embeddings_in_db():
    """Test 3: Check embeddings stored in database"""
    print("=" * 80)
    print("TEST 3: EMBEDDINGS IN DATABASE")
    print("=" * 80)
    print()

    con = get_db_connection()

    # Count nodes with embeddings
    count = con.execute("""
        SELECT COUNT(*) FROM graph_nodes
        WHERE embedding IS NOT NULL
    """).fetchone()[0]

    print(f"Notes with embeddings in DB: {count}")

    if count > 0:
        # Show sample
        sample = con.execute("""
            SELECT id, text
            FROM graph_nodes
            WHERE embedding IS NOT NULL
            LIMIT 3
        """).fetchall()

        print("\nSample notes with embeddings:")
        for note_id, text in sample:
            preview = text[:60] + "..." if len(text) > 60 else text
            print(f"  - {note_id}: {preview}")
    else:
        print("⚠️  No embeddings found in database yet.")
        print("   Run test_phase2_linking.py to import notes and generate embeddings.")

    con.close()
    print()


if __name__ == "__main__":
    print("\n🧪 PHASE 2 SEMANTIC SERVICE TESTS\n")

    try:
        test_embedding_generation()
        test_embeddings_in_db()

        print("=" * 80)
        print("✅ ALL TESTS COMPLETE")
        print("=" * 80)
        print()

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
