#!/usr/bin/env python3
"""
Complete AI search demo combining NL parsing + semantic search + summaries.

This demonstrates the full pipeline:
1. Natural language query parsing
2. Semantic search using embeddings
3. Metadata filtering
4. AI-generated summaries
"""

import json
import sys
from pathlib import Path
import numpy as np

# Add invenio-aisearch to path
aisearch_path = Path(__file__).parent.parent.parent.parent / "invenio-aisearch" / "invenio_aisearch"
sys.path.insert(0, str(aisearch_path.parent))

# Import directly from files to avoid full module dependencies
import importlib.util

# Load models.py
models_spec = importlib.util.spec_from_file_location("models", aisearch_path / "models.py")
models = importlib.util.module_from_spec(models_spec)
models_spec.loader.exec_module(models)
get_model_manager = models.get_model_manager

# Load query_parser.py
parser_spec = importlib.util.spec_from_file_location("query_parser", aisearch_path / "query_parser.py")
parser_module = importlib.util.module_from_spec(parser_spec)
parser_spec.loader.exec_module(parser_module)
QueryParser = parser_module.QueryParser


def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors."""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)

    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    return dot_product / (norm1 * norm2)


class AISearchDemo:
    """Demonstrate AI-powered search over Gutenberg books."""

    def __init__(self, embeddings_file: str = "embeddings.json"):
        """Initialize search demo.

        Args:
            embeddings_file: Path to embeddings JSON file
        """
        self.query_parser = QueryParser()
        self.model_manager = get_model_manager()

        # Load embeddings
        print("Loading embeddings...")
        with open(embeddings_file, 'r') as f:
            self.embeddings = json.load(f)
        print(f"✓ Loaded {len(self.embeddings)} book embeddings\n")

    def search(self, query: str, include_summaries: bool = True):
        """Perform AI-powered search.

        Args:
            query: Natural language query
            include_summaries: Whether to generate AI summaries

        Returns:
            List of search results with scores and summaries
        """
        print("=" * 70)
        print(f"Query: \"{query}\"")
        print("=" * 70)
        print()

        # Step 1: Parse query
        print("Step 1: Parsing natural language query...")
        parsed = self.query_parser.parse(query)

        print(f"  Intent: {parsed['intent']}")
        print(f"  Limit: {parsed['limit']}")
        print(f"  Attributes: {parsed['attributes']}")
        print(f"  Search terms: {parsed['search_terms']}")
        print(f"  Semantic query: \"{parsed['semantic_query']}\"")
        print()

        # Step 2: Generate query embedding
        print("Step 2: Generating query embedding...")
        query_embedding = self.model_manager.generate_embedding(
            parsed['semantic_query']
        )
        print(f"  ✓ Generated {len(query_embedding)}-dimensional vector")
        print()

        # Step 3: Calculate semantic similarity
        print("Step 3: Computing semantic similarity with all books...")
        results = []

        for record_id, data in self.embeddings.items():
            # Semantic similarity
            semantic_score = cosine_similarity(query_embedding, data['embedding'])

            # Metadata matching (if search terms specified)
            metadata_score = 0.0
            if parsed['search_terms']:
                title_lower = data['title'].lower()
                matches = sum(1 for term in parsed['search_terms']
                            if term.lower() in title_lower)
                metadata_score = matches / len(parsed['search_terms'])

            # Hybrid score (70% semantic, 30% metadata)
            hybrid_score = 0.7 * semantic_score + 0.3 * metadata_score

            results.append({
                'record_id': record_id,
                'title': data['title'],
                'semantic_score': semantic_score,
                'metadata_score': metadata_score,
                'hybrid_score': hybrid_score,
            })

        # Sort by hybrid score
        results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        print(f"  ✓ Ranked {len(results)} books")
        print()

        # Step 4: Apply limit
        limit = parsed['limit'] or 10  # Default to 10 if not specified
        results = results[:limit]

        print(f"Step 4: Returning top {len(results)} results")
        print()

        # Step 5: Generate summaries (if requested)
        if include_summaries:
            print("Step 5: Generating AI summaries...")
            for result in results:
                title = result['title']
                # Generate summary from title (in real implementation, use full text)
                summary_text = f"A classic work titled '{title}'"
                try:
                    summary = self.model_manager.generate_summary(
                        summary_text,
                        max_length=50,
                        min_length=10
                    )
                    result['summary'] = summary
                except Exception as e:
                    result['summary'] = f"Summary unavailable: {str(e)[:50]}"
            print("  ✓ Generated summaries")
            print()

        return results

    def display_results(self, results, show_scores: bool = False):
        """Display search results in formatted output.

        Args:
            results: List of result dictionaries
            show_scores: Whether to show similarity scores
        """
        print("=" * 70)
        print("SEARCH RESULTS")
        print("=" * 70)
        print()

        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")

            if show_scores:
                print(f"   Semantic: {result['semantic_score']:.3f} | "
                      f"Metadata: {result['metadata_score']:.3f} | "
                      f"Hybrid: {result['hybrid_score']:.3f}")

            if 'summary' in result:
                print(f"   Summary: {result['summary']}")

            print()

        print("=" * 70)


def main():
    """Run demo searches."""
    import argparse

    parser = argparse.ArgumentParser(
        description='AI Search Demo - Natural Language + Semantic Search'
    )
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Run in interactive mode with pauses between demos'
    )
    parser.add_argument(
        '-q', '--query',
        type=str,
        help='Run a single custom query'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("AI Search Demo - Natural Language + Semantic Search + Summaries")
    print("=" * 70)
    print()

    # Initialize search
    demo = AISearchDemo()

    # Custom query or demo queries
    if args.query:
        demo_queries = [args.query]
    else:
        demo_queries = [
            "show me 3 books with female protagonists",
            "find me 5 books about social injustice",
            "get me adventure stories",
        ]

    # Run each demo query
    for query in demo_queries:
        results = demo.search(query, include_summaries=False)
        demo.display_results(results, show_scores=True)

        print("\n" + "=" * 70)
        print("KEY INSIGHTS")
        print("=" * 70)
        print()

        # Analyze results
        avg_semantic = sum(r['semantic_score'] for r in results) / len(results)
        avg_metadata = sum(r['metadata_score'] for r in results) / len(results)

        print(f"Average semantic similarity: {avg_semantic:.3f}")
        print(f"Average metadata match: {avg_metadata:.3f}")
        print()

        if avg_semantic > 0.4:
            print("✓ Strong semantic matches - query meaning well understood")
        elif avg_semantic > 0.3:
            print("✓ Moderate semantic matches - related content found")
        else:
            print("! Weak semantic matches - query may need refinement")

        if avg_metadata > 0:
            print(f"✓ Found books matching {int(avg_metadata * 100)}% of search terms")
        else:
            print("ℹ No direct metadata matches - purely semantic results")

        print()

        if args.interactive and query != demo_queries[-1]:
            input("Press Enter to continue to next demo...")
            print("\n\n")

    # Summary
    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print()
    print("This demo showed:")
    print("  1. Natural language query parsing")
    print("  2. Semantic search using embeddings")
    print("  3. Hybrid scoring (semantic + metadata)")
    print("  4. Ranked results by relevance")
    print()
    print("Next steps:")
    print("  - Add to invenio-aisearch as REST API endpoint")
    print("  - Create web UI for search interface")
    print("  - Enable full-text summaries from book content")
    print()


if __name__ == "__main__":
    main()
