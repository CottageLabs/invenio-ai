#!/usr/bin/env python
"""Test passage boosting for AI search."""

from flask import Flask
from invenio_app.factory import create_app
from invenio_aisearch.services.service.ai_search_service import AISearchService

def test_passage_boosting():
    """Test that passage boosting improves Odyssey ranking."""
    app = create_app()

    with app.app_context():
        service = AISearchService()

        # Test query
        query = "a tale of a sea voyage"

        print(f"\n{'='*80}")
        print(f"Testing passage boosting for query: '{query}'")
        print(f"{'='*80}\n")

        # Execute search with passage boosting
        result = service.search(
            identity=None,
            query=query,
            limit=10,
            include_summaries=False,
            include_passages=True
        )

        print(f"Total books: {result.total}")
        print(f"Total passages: {result.passage_total}")
        print(f"\nTop 10 books (passage-boosted ranking):\n")

        odyssey_rank = None
        for i, book in enumerate(result.results, 1):
            title = book['title'][:60]
            score = book['similarity_score']

            # Check for boosting metadata
            orig_score = book.get('original_book_score', 'N/A')
            passage_boost = book.get('passage_boost', 'N/A')

            if 'odyssey' in title.lower():
                odyssey_rank = i
                print(f">>> {i:2d}. [{score:.4f}] {title}")
                if passage_boost != 'N/A' and passage_boost is not None:
                    print(f"     (book: {orig_score:.4f}, passage_boost: {passage_boost:.4f})")
            else:
                print(f"    {i:2d}. [{score:.4f}] {title}")
                if passage_boost != 'N/A' and passage_boost is not None:
                    print(f"     (book: {orig_score:.4f}, passage_boost: {passage_boost:.4f})")

        print(f"\n{'='*80}")
        if odyssey_rank:
            print(f"✓ SUCCESS: The Odyssey ranks #{odyssey_rank} (previously #17)")
        else:
            print(f"✗ ISSUE: The Odyssey not in top 10 (previously #17)")
        print(f"{'='*80}\n")

if __name__ == '__main__':
    test_passage_boosting()
