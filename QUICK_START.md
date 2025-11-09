# Quick Start Guide - AI Search

## Start Development Servers

```bash
# Terminal 1: Start backend services
invenio-cli services start

# Terminal 2: Start UI server (port 5000)
invenio-cli run

# Terminal 3: Start API server (port 5001)
FLASK_APP="invenio_app.wsgi_rest:application" \
  pipenv run flask run \
  --cert docker/nginx/test.crt \
  --key docker/nginx/test.key \
  --host 127.0.0.1 \
  --port 5001
```

## API Examples

### Check Status
```bash
curl -k "https://127.0.0.1:5001/api/aisearch/status" | jq
```

### Search for Books
```bash
# Female protagonists
curl -k "https://127.0.0.1:5001/api/aisearch/search?q=books+with+female+protagonists&limit=3" | jq

# Social injustice
curl -k "https://127.0.0.1:5001/api/aisearch/search?q=social+injustice&limit=5" | jq

# Adventures
curl -k "https://127.0.0.1:5001/api/aisearch/search?q=adventure+stories&limit=5" | jq

# With summaries (placeholder)
curl -k "https://127.0.0.1:5001/api/aisearch/search?q=romance&limit=3&summaries=true" | jq
```

### Find Similar Books
```bash
# Similar to Little Women
curl -k "https://127.0.0.1:5001/api/aisearch/similar/e907e-y9j50?limit=5" | jq
```

## Generate Embeddings

```bash
# Generate for all records
python3 scripts/generate_embeddings.py \
  --api-url https://127.0.0.1:5000/api \
  --output embeddings.json

# Check the output
ls -lh embeddings.json  # Should be ~976KB for 92 books
```

## Test Search Locally

```bash
# Standalone demo
python3 scripts/demo_search.py \
  --query "books about friendship" \
  --limit 5 \
  --summaries

# Test server (port 8000)
pipenv run python test_ai_search_server.py
# Then: curl -k "https://localhost:8000/api/aisearch/status"
```

## CLI Commands

```bash
# Generate embeddings via Celery
invenio aisearch generate-embeddings

# Check configuration
invenio aisearch config

# Rebuild embeddings for specific record
invenio aisearch rebuild-record <record-id>
```

## Troubleshooting

### API returns 404
- Make sure both UI server (5000) and API server (5001) are running
- API endpoints only work on port 5001 in development mode
- Check `invenio.cfg` has `INVENIO_AISEARCH_EMBEDDINGS_FILE` set

### No results returned
- Verify embeddings.json exists and is readable
- Check the file path in `invenio.cfg`
- Ensure embeddings were generated for your records

### Import errors
- Run `pipenv install -e ../invenio-aisearch`
- Restart both servers after installing

## File Locations

- **Config**: `invenio.cfg`
- **Embeddings**: `embeddings.json` (976 KB)
- **Module**: `../invenio-aisearch/`
- **Scripts**: `scripts/generate_embeddings.py`, `scripts/demo_search.py`
- **Tests**: `test_ai_search_server.py`, `test_live_app.py`

## API Response Format

```json
{
  "query": "books with female protagonists",
  "parsed": {
    "search_terms": ["female", "protagonist"],
    "attributes": ["female_protagonist"],
    "intent": "search",
    "semantic_query": "books with female protagonists"
  },
  "results": [
    {
      "record_id": "e907e-y9j50",
      "title": "Little Women",
      "creators": "Alcott, Louisa May, 1832-1888",
      "description": "...",
      "semantic_score": 0.4860,
      "metadata_score": 0.25,
      "hybrid_score": 0.4152,
      "subjects": ["..."]
    }
  ],
  "total": 3
}
```

## Configuration Options

In `invenio.cfg`:

```python
# Required
INVENIO_AISEARCH_EMBEDDINGS_FILE = "/path/to/embeddings.json"

# Optional (with defaults)
INVENIO_AISEARCH_API_URL = "https://127.0.0.1:5000/api"
INVENIO_AISEARCH_SEMANTIC_WEIGHT = 0.7  # 70% semantic, 30% metadata
INVENIO_AISEARCH_METADATA_WEIGHT = 0.3
INVENIO_AISEARCH_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
```

## Next Steps

1. **Fix Docker build** - Resolve dependency issues
2. **Create UI** - Add search interface to InvenioRDM
3. **Auto-embeddings** - Hook into record creation/update
4. **Add GPT summaries** - Real AI-generated descriptions
5. **Performance** - Add caching and optimization
