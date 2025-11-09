#!/usr/bin/env python3
"""
Standalone test server for AI search API.

This serves the AI search endpoints independently for testing.
Run with: pipenv run python test_ai_search_server.py
"""

from flask import Flask
from flask_cors import CORS

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-secret-key'

# Configure AI search
app.config['INVENIO_AISEARCH_EMBEDDINGS_FILE'] = '/home/steve/code/cl/Invenio/v13-ai/embeddings.json'
app.config['INVENIO_AISEARCH_API_URL'] = 'https://127.0.0.1:5000/api'
app.config['INVENIO_AISEARCH_SEMANTIC_WEIGHT'] = 0.7
app.config['INVENIO_AISEARCH_METADATA_WEIGHT'] = 0.3

# Enable CORS for testing
CORS(app)

# Register AI search blueprint
from invenio_aisearch.api_views import api_blueprint
app.register_blueprint(api_blueprint)

print("=" * 60)
print("AI Search Test Server")
print("=" * 60)
print("\nRegistered endpoints:")
for rule in app.url_map.iter_rules():
    if 'aisearch' in str(rule):
        print(f"  http://localhost:8000{rule.rule}")

print("\n" + "=" * 60)
print("Starting server on http://localhost:8000")
print("=" * 60)
print("\nTest with:")
print("  curl http://localhost:8000/api/aisearch/status")
print("  curl 'http://localhost:8000/api/aisearch/search?q=female+protagonists&limit=3'")
print()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
