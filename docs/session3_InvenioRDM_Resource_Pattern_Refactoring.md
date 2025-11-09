# Session 3: InvenioRDM Resource Pattern Refactoring

**Date:** November 9, 2025
**Focus:** Refactoring invenio-aisearch to follow InvenioRDM's resource/service architecture pattern

## Overview

This session focused on refactoring the `invenio-aisearch` module from a simple Flask blueprint implementation to InvenioRDM's standardized resource/service pattern. The refactoring was guided by:
- The `invenio-notify` module as a reference implementation
- InvenioRDM documentation at https://inveniordm.docs.cern.ch/maintenance/internals/resource/
- Source code from `invenio-communities` and `invenio-records-resources`

## Key Accomplishments

### 1. Architecture Refactoring

Restructured the module to follow InvenioRDM conventions:

```
invenio-aisearch/
├── invenio_aisearch/
│   ├── ext.py                    # Extension with init_services() and init_resources()
│   ├── blueprints.py             # Blueprint factory functions
│   ├── resources/
│   │   ├── __init__.py
│   │   ├── config.py             # AISearchResourceConfig
│   │   └── resource/
│   │       ├── __init__.py
│   │       └── ai_search_resource.py  # AISearchResource
│   └── services/
│       ├── __init__.py
│       ├── config.py             # AISearchServiceConfig
│       ├── results.py            # SearchResult, SimilarResult, StatusResult
│       ├── schemas.py            # Marshmallow schemas
│       └── service/
│           ├── __init__.py
│           └── ai_search_service.py   # AISearchService
```

### 2. Service Layer Implementation

**Service Classes:**
- `AISearchService` - Business logic layer
- `AISearchServiceConfig` - Service configuration

**Result Objects:**
- `SearchResult` - Encapsulates search results
- `SimilarResult` - Encapsulates similar record results
- `StatusResult` - Encapsulates service status

**Purpose:** Separation of business logic from HTTP presentation layer

### 3. Resource Layer Implementation

**Resource Classes:**
- `AISearchResource` - HTTP request/response handling
- `AISearchResourceConfig` - Resource configuration (routes, parsers, schemas)

**Request Schemas:**
- `SearchRequestSchema(MultiDictSchema)` - For search GET/POST parameters
- `SimilarRequestSchema(MultiDictSchema)` - For similar endpoint parameters

**Key Pattern:** Resources depend on services via dependency injection in constructor

### 4. Critical Technical Discoveries

#### MultiDictSchema for GET Parameters

The breakthrough fix was extending `MultiDictSchema` from `flask_resources.parsers` instead of plain Marshmallow `Schema`:

```python
from flask_resources.parsers import MultiDictSchema

class SearchRequestSchema(MultiDictSchema):
    """Schema for search request parameters."""
    q = fields.Str(required=False, allow_none=True)
    limit = fields.Int(required=False, validate=validate.Range(min=1, max=100))
    summaries = fields.Bool(required=False, missing=False)
```

**Why this matters:** `MultiDictSchema` properly handles Werkzeug's `MultiDict` objects used for URL query strings, performing type conversion automatically.

#### Request Parser Decorators

Created custom decorator for different endpoint schemas:

```python
from flask_resources.parsers import request_parser
from flask_resources.resources import from_conf

# For similar endpoint with different schema
request_similar_args = request_parser(
    from_conf("request_similar_args"),
    location="args"
)
```

**Pattern learned:** `request_parser(from_conf("config_key"), location="args")` creates decorators that:
1. Look up schema from resource config
2. Parse and validate request data
3. Populate `resource_requestctx.args` with validated dict

### 5. Extension Initialization Pattern

Followed InvenioRDM's standard extension lifecycle:

```python
class InvenioAISearch(object):
    def init_app(self, app):
        self.init_config(app)
        self.init_services(app)     # Initialize services first
        self.init_resources(app)    # Then resources (depend on services)
        app.extensions["invenio-aisearch"] = self

    def init_services(self, app):
        self.search_service = AISearchService(config=AISearchServiceConfig)
        # Load embeddings, etc.

    def init_resources(self, app):
        self.search_resource = AISearchResource(
            config=AISearchResourceConfig,
            service=self.search_service,  # Dependency injection
        )
```

### 6. Blueprint Factory Pattern

Entry point registration uses factory functions:

**pyproject.toml:**
```toml
[project.entry-points."invenio_base.api_blueprints"]
ai_search_api = "invenio_aisearch.blueprints:create_ai_search_api_bp"
```

**blueprints.py:**
```python
def create_ai_search_api_bp(app):
    """Create AI search API blueprint."""
    ext = app.extensions["invenio-aisearch"]
    return ext.search_resource.as_blueprint()
```

### 7. URL Prefix Configuration

**Important discovery:** InvenioRDM's API blueprint registration automatically adds `/api` prefix.

```python
class AISearchResourceConfig(ResourceConfig):
    blueprint_name = "ai_search_api"
    url_prefix = "/aisearch"  # NOT "/api/aisearch" - would cause /api/api/aisearch
```

Result: Endpoints accessible at `/api/aisearch/*`

### 8. Modern Python Packaging

Migrated from `setup.py`/`setup.cfg` to `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "invenio-aisearch"
version = "0.0.1"
dependencies = [
    "flask-resources>=1.0.0",
    "marshmallow>=3.0.0",
    # ... AI dependencies
]
```

## Working API Endpoints

After refactoring, all endpoints working correctly:

### Status Check
```bash
curl -k "https://127.0.0.1:5000/api/aisearch/status"
# Returns: {"status": "ready", "embeddings_loaded": true, "embeddings_count": 92}
```

### Search (GET)
```bash
curl -k "https://127.0.0.1:5000/api/aisearch/search?q=adventure&limit=3"
# Returns: hybrid search results with semantic and metadata scores
```

### Search (POST)
```bash
curl -k -X POST -H "Content-Type: application/json" \
  -d '{"query": "science fiction", "limit": 3}' \
  "https://127.0.0.1:5000/api/aisearch/search"
```

### Similar Records
```bash
curl -k "https://127.0.0.1:5000/api/aisearch/similar/e907e-y9j50?limit=5"
# Returns: top 5 most similar records based on embedding similarity
```

## Key Learning Resources

### Documentation References
1. **InvenioRDM Resource Pattern**
   https://inveniordm.docs.cern.ch/maintenance/internals/resource/

2. **Flask-Resources Library**
   Used for `Resource`, `ResourceConfig`, `MultiDictSchema`, decorators

3. **Marshmallow Schemas**
   Request/response validation and serialization

### Code References Studied

1. **invenio-notify** (our own module)
   - Reference for overall structure
   - Extension initialization pattern
   - Blueprint factory pattern

2. **invenio-communities**
   GitHub: inveniosoftware/invenio-communities
   - `CommunitiesSearchRequestArgsSchema` - schema examples
   - Resource method decorators usage
   - URL parameter handling

3. **invenio-records-resources**
   GitHub: inveniosoftware/invenio-records-resources
   - `SearchRequestArgsSchema` - base schema
   - `request_search_args` decorator definition
   - `MultiDictSchema` import location

## Debugging Journey

### Problem 1: Marshmallow Validation Errors
**Error:** `marshmallow.exceptions.ValidationError: {'q': ['Not a valid string.']}`

**Cause:** Using plain `Schema` instead of `MultiDictSchema`

**Solution:** Extend `MultiDictSchema` for GET parameter schemas

### Problem 2: dict.get() Keyword Arguments
**Error:** `dict.get() takes no keyword arguments`

**Cause:** Trying to use `args.get('limit', type=int)` on regular dict after schema validation

**Solution:** Schemas already convert types; just use `args.get('limit')` or `args.get('limit', 10)` for defaults

### Problem 3: Wrong Schema for Similar Endpoint
**Error:** Similar endpoint validated against SearchRequestSchema (requiring 'q' parameter)

**Cause:** `@request_search_args` uses config's `request_search_args` by default

**Solution:** Create custom decorator:
```python
request_similar_args = request_parser(
    from_conf("request_similar_args"),
    location="args"
)
```

## Git Commits

### Branch: `refactor/invenio_resource`

1. **"Initial resource/service structure refactoring"**
   - Created directory structure
   - Implemented service and resource layers
   - Added result objects

2. **"Migrate to pyproject.toml and remove legacy packaging"**
   - Removed setup.py, setup.cfg
   - Created modern pyproject.toml
   - Updated entry points

3. **"Fix URL prefix: remove duplicate /api"**
   - Changed `/api/aisearch` → `/aisearch`
   - Fixed 404 errors on all endpoints

4. **"Simplify GET parameter handling: extract directly from args"**
   - Removed Marshmallow validation for GET (initially)
   - Direct parameter extraction

5. **"Fix GET parameter handling with proper schema validation"**
   - Extended MultiDictSchema
   - Added @request_search_args decorator
   - Created custom request_similar_args decorator
   - Final working implementation

## Architecture Patterns Learned

### 1. Dependency Injection
Services injected into resources, not created internally:
```python
resource = AISearchResource(config=config, service=service)
```

### 2. Configuration-Based Initialization
Use `from_conf()` to reference config values in decorators:
```python
request_parser(from_conf("request_similar_args"), location="args")
```

### 3. Result Objects Pattern
Services return structured result objects, not raw dicts:
```python
def search(self, identity, query, limit=None):
    # ... business logic ...
    return SearchResult(query=query, results=results, total=len(results))
```

### 4. Schema Validation Layers
- Request schemas: Validate incoming data
- Response schemas: Serialize outgoing data (optional)
- Separate schemas for GET vs POST on same endpoint

## Next Steps

The invenio-aisearch module is now:
- ✅ Following InvenioRDM architectural patterns
- ✅ Using modern Python packaging (pyproject.toml)
- ✅ Properly separating concerns (service/resource layers)
- ✅ Fully functional with all endpoints working
- ✅ Ready for production deployment

Potential future enhancements:
- Add permissions/identity checks in service layer
- Implement response schemas for consistent serialization
- Add rate limiting for API endpoints
- Implement caching for similar records
- Add OpenAPI/Swagger documentation generation

## Technical Debt Resolved

- ❌ Removed Flask blueprint approach → ✅ InvenioRDM resource pattern
- ❌ setup.py/setup.cfg → ✅ pyproject.toml
- ❌ Direct request.args access → ✅ Schema-validated parameters
- ❌ Returning raw dicts → ✅ Structured result objects
- ❌ Business logic in views → ✅ Separated service layer

## Conclusion

This refactoring transformed invenio-aisearch from a working but non-standard Flask extension into a proper InvenioRDM module following all framework conventions. The key breakthrough was understanding how flask-resources handles request parameter validation through MultiDictSchema and the request_parser decorator system.

By studying invenio-notify, invenio-communities, and the official documentation, we successfully implemented the complete resource/service pattern, making the module maintainable and consistent with the broader InvenioRDM ecosystem.
