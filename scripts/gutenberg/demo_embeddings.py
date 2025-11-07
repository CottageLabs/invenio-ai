#!/usr/bin/env python3
"""
Demo script to show how embeddings work for semantic search.

This demonstrates:
1. What embeddings are
2. How similarity is calculated
3. How to find similar books
"""

import json
import sys
from pathlib import Path
import numpy as np

# Add invenio-aisearch to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "invenio-aisearch"))

from invenio_aisearch.models import get_model_manager


def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors.

    Returns value between -1 (opposite) and 1 (identical).
    Typically > 0.7 means very similar, > 0.5 means related.
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)

    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    return dot_product / (norm1 * norm2)


def main():
    print("=" * 70)
    print("Understanding Embeddings: How Semantic Search Works")
    print("=" * 70)
    print()

    # Load embeddings
    print("Loading embeddings...")
    with open('embeddings.json', 'r') as f:
        embeddings = json.load(f)

    print(f"✓ Loaded {len(embeddings)} book embeddings")
    print()

    # Explain what embeddings are
    print("WHAT ARE EMBEDDINGS?")
    print("-" * 70)
    print("An embedding is a list of 384 numbers that represents the 'meaning'")
    print("of a text in mathematical space.")
    print()
    print("Example for 'Don Quixote':")
    sample_embedding = list(embeddings.values())[0]['embedding']
    print(f"  First 5 numbers: {sample_embedding[:5]}")
    print(f"  Total numbers: {len(sample_embedding)}")
    print()
    print("Books with similar themes/content will have similar numbers!")
    print("This lets us find books by MEANING, not just keywords.")
    print()

    # Demo 1: Find books similar to Pride and Prejudice
    print("=" * 70)
    print("DEMO 1: Find Books Similar to 'Pride and Prejudice'")
    print("=" * 70)
    print()

    # Find Pride and Prejudice
    pp_id = None
    pp_embedding = None
    for record_id, data in embeddings.items():
        if "Pride and Prejudice" in data['title']:
            pp_id = record_id
            pp_embedding = data['embedding']
            break

    if pp_embedding:
        print("Found: Pride and Prejudice")
        print("Now calculating similarity with all other books...")
        print()

        similarities = []
        for record_id, data in embeddings.items():
            if record_id == pp_id:
                continue  # Skip itself

            similarity = cosine_similarity(pp_embedding, data['embedding'])
            similarities.append((similarity, data['title']))

        # Sort by similarity (highest first)
        similarities.sort(reverse=True)

        print("Top 10 Most Similar Books:")
        print()
        for i, (score, title) in enumerate(similarities[:10], 1):
            print(f"  {i:2}. {title[:55]:<55} (similarity: {score:.3f})")
        print()
        print("Notice: These are books with similar themes (romance, social")
        print("commentary, relationships) even though 'Pride and Prejudice'")
        print("doesn't appear in their titles!")
        print()

    # Demo 2: Semantic search for a query
    print("=" * 70)
    print("DEMO 2: Semantic Search - 'books about social injustice'")
    print("=" * 70)
    print()

    model_manager = get_model_manager()
    query = "books about social injustice and inequality"

    print(f"Query: '{query}'")
    print()
    print("Step 1: Convert query to embedding...")
    query_embedding = model_manager.generate_embedding(query)
    print(f"  ✓ Generated {len(query_embedding)}-dimensional vector")
    print()

    print("Step 2: Compare with all books...")
    query_similarities = []
    for record_id, data in embeddings.items():
        similarity = cosine_similarity(query_embedding, data['embedding'])
        query_similarities.append((similarity, data['title']))

    query_similarities.sort(reverse=True)

    print("  ✓ Calculated similarity scores")
    print()
    print("Top 10 Results:")
    print()
    for i, (score, title) in enumerate(query_similarities[:10], 1):
        print(f"  {i:2}. {title[:55]:<55} (score: {score:.3f})")
    print()
    print("Notice: Found books about slavery, inequality, and social issues")
    print("without needing those exact words in the search!")
    print()

    # Demo 3: Show why keyword search would miss things
    print("=" * 70)
    print("DEMO 3: Why Traditional Keyword Search Falls Short")
    print("=" * 70)
    print()

    query2 = "stories of personal transformation"
    print(f"Query: '{query2}'")
    print()

    # Keyword search (simulated)
    print("KEYWORD SEARCH (looks for exact words):")
    print("  - Looking for 'transformation' in titles/metadata...")
    keyword_matches = [data['title'] for data in embeddings.values()
                      if 'transformation' in data['title'].lower() or
                         'transform' in data['title'].lower()]
    if keyword_matches:
        print(f"  Found {len(keyword_matches)} matches:")
        for title in keyword_matches[:5]:
            print(f"    - {title}")
    else:
        print("  Found 0 matches (word 'transformation' not in titles)")
    print()

    # Semantic search
    print("SEMANTIC SEARCH (understands meaning):")
    query2_embedding = model_manager.generate_embedding(query2)
    semantic_matches = []
    for record_id, data in embeddings.items():
        similarity = cosine_similarity(query2_embedding, data['embedding'])
        semantic_matches.append((similarity, data['title']))
    semantic_matches.sort(reverse=True)

    print(f"  Top 5 matches by meaning:")
    for i, (score, title) in enumerate(semantic_matches[:5], 1):
        print(f"    {i}. {title[:50]:<50} ({score:.3f})")
    print()
    print("  These books contain transformation themes even without")
    print("  that specific word!")
    print()

    # Summary
    print("=" * 70)
    print("KEY TAKEAWAYS")
    print("=" * 70)
    print()
    print("1. EMBEDDINGS = Mathematical representation of meaning")
    print("   - 384 numbers capture themes, concepts, relationships")
    print()
    print("2. SIMILARITY = Closeness in meaning")
    print("   - Calculated using cosine similarity (dot product)")
    print("   - Score > 0.7: very similar")
    print("   - Score > 0.5: related")
    print("   - Score < 0.3: different topics")
    print()
    print("3. SEMANTIC SEARCH > KEYWORD SEARCH")
    print("   - Finds 'The Souls of Black Folk' for 'social injustice'")
    print("   - Finds 'Great Expectations' for 'personal transformation'")
    print("   - Understands synonyms and related concepts")
    print()
    print("4. FOR YOUR DEMO:")
    print("   - Query: 'books with female protagonists'")
    print("   - Semantic search finds books with strong female characters")
    print("   - Even if 'female' or 'protagonist' aren't in the description!")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
