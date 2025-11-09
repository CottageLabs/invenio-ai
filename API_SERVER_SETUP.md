# InvenioRDM API Server Setup for Development

## Problem

InvenioRDM uses separate applications for UI and API:
- **UI App** (`create_app()`): Loads `invenio_base.blueprints` entry points
- **API App** (`create_api()`): Loads `invenio_base.api_blueprints` entry points

In production, nginx routes:
- `/api/*` requests → API server (port 5000, using `create_api()`)
- Other requests → UI server (port 5000, using `create_app()`)

However, `invenio-cli run` only starts the UI server, so API blueprints aren't accessible.

## Solution

Start both servers in development mode:

### 1. Start UI Server (default)
```bash
invenio-cli run
```
This runs on `https://127.0.0.1:5000`

### 2. Start API Server (manual)
```bash
FLASK_APP="invenio_app.wsgi_rest:application" \
  pipenv run flask run \
  --cert docker/nginx/test.crt \
  --key docker/nginx/test.key \
  --host 127.0.0.1 \
  --port 5001
```
This runs on `https://127.0.0.1:5001`

## Testing AI Search API

With both servers running:

```bash
# Status check
curl -k "https://127.0.0.1:5001/api/aisearch/status"

# Natural language search
curl -k "https://127.0.0.1:5001/api/aisearch/search?q=books+with+female+protagonists&limit=3"

# Find similar records
curl -k "https://127.0.0.1:5001/api/aisearch/similar/e907e-y9j50?limit=5"
```

## Production Deployment

In production with docker-compose, nginx automatically handles routing:
- UI container: `web-ui:5000` (uses `create_app()`)
- API container: `web-api:5000` (uses `create_api()`)
- Nginx routes `/api/*` to API container, everything else to UI container

No manual server management needed.
