#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test script for refactored invenio-aisearch resource pattern."""

import sys
from pathlib import Path

print("=" * 60)
print("Testing Refactored invenio-aisearch")
print("=" * 60)

# Test 1: Import checks
print("\n[1/6] Testing imports...")
try:
    from invenio_aisearch.ext import InvenioAISearch
    from invenio_aisearch.resources import AISearchResource, AISearchResourceConfig
    from invenio_aisearch.services import (
        AISearchService,
        AISearchServiceConfig,
        SearchResult,
        SimilarResult,
        StatusResult,
    )
    from invenio_aisearch.blueprints import create_ai_search_api_bp
    print("   ✓ All imports successful")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Service instantiation
print("\n[2/6] Testing service instantiation...")
try:
    service = AISearchService(config=AISearchServiceConfig)
    print("   ✓ AISearchService created")
except Exception as e:
    print(f"   ✗ Service instantiation failed: {e}")
    sys.exit(1)

# Test 3: Resource instantiation
print("\n[3/6] Testing resource instantiation...")
try:
    resource = AISearchResource(
        config=AISearchResourceConfig,
        service=service,
    )
    print("   ✓ AISearchResource created")
except Exception as e:
    print(f"   ✗ Resource instantiation failed: {e}")
    sys.exit(1)

# Test 4: Extension initialization
print("\n[4/6] Testing extension initialization...")
try:
    from flask import Flask
    app = Flask(__name__)

    # Set embeddings file path
    embeddings_file = Path(__file__).parent / "embeddings.json"
    app.config["INVENIO_AISEARCH_EMBEDDINGS_FILE"] = str(embeddings_file)

    ext = InvenioAISearch(app)
    print("   ✓ InvenioAISearch extension initialized")
    print(f"   ✓ Extension has search_service: {hasattr(ext, 'search_service')}")
    print(f"   ✓ Extension has search_resource: {hasattr(ext, 'search_resource')}")
except Exception as e:
    print(f"   ✗ Extension initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Blueprint creation
print("\n[5/6] Testing blueprint creation...")
try:
    blueprint = create_ai_search_api_bp(app)
    print(f"   ✓ Blueprint created: {blueprint.name}")
    print(f"   ✓ Blueprint URL prefix: {blueprint.url_prefix}")
except Exception as e:
    print(f"   ✗ Blueprint creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Check URL rules
print("\n[6/6] Testing URL rules...")
try:
    url_rules = resource.create_url_rules()
    print(f"   ✓ Created {len(url_rules)} URL rules:")
    for rule_dict in url_rules:
        # flask-resources returns dicts with 'rule' and 'methods' keys
        rule = rule_dict.get('rule', 'unknown')
        methods = rule_dict.get('methods', [])
        print(f"      - {rule} [{', '.join(methods) if methods else 'GET'}]")
except Exception as e:
    print(f"   ✗ URL rules creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Result objects
print("\n[7/7] Testing result objects...")
try:
    # Test SearchResult
    search_result = SearchResult(
        query="test query",
        parsed={"intent": "search"},
        results=[{"id": "1", "title": "Test"}],
        total=1,
    )
    search_dict = search_result.to_dict()
    assert search_dict["query"] == "test query"
    print("   ✓ SearchResult works")

    # Test SimilarResult
    similar_result = SimilarResult(
        record_id="123",
        similar=[{"id": "456", "similarity": 0.9}],
        total=1,
    )
    similar_dict = similar_result.to_dict()
    assert similar_dict["record_id"] == "123"
    print("   ✓ SimilarResult works")

    # Test StatusResult
    status_result = StatusResult(
        status="ready",
        embeddings_loaded=True,
        embeddings_count=10,
    )
    status_dict = status_result.to_dict()
    assert status_dict["status"] == "ready"
    print("   ✓ StatusResult works")

except Exception as e:
    print(f"   ✗ Result objects test failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ All tests passed! Refactoring successful!")
print("=" * 60)
print("\nThe resource pattern is working correctly:")
print("  - Extension initializes services and resources")
print("  - Blueprint factory function works")
print("  - URL rules are created properly")
print("  - Result objects serialize correctly")
print("\nReady to commit!")
