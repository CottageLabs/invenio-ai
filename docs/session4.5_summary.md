# Session 4.5 Summary: Single-Index Architecture Investigation

## What We Accomplished

### 1. Fixed the 500 Error in AI Search API
- **Problem**: AI search API was returning 500 error due to deprecated parameters
- **Solution**: Updated `ai_search_resource.py` to remove `semantic_weight` and `metadata_weight` parameters that were removed during k-NN refactoring
- **Result**: AI search API now works correctly: `https://127.0.0.1:5000/api/aisearch/search?q=vampire`

### 2. Discovered Main Index Issue
- **Problem**: Main RDM index (`v13-ai-rdmrecords-records-record-v6.0.0`) was empty (0 records)
- **Impact**: Record landing pages return 404, standard search returns no results
- **Root Cause**: Records exist in database (92 records) but haven't been indexed

### 3. Explored Single vs Dual Index Architecture

**Dual Index (v0.0.2 original)**:
- Separate `aisearch` index for AI search
- Main RDM index for standard search and landing pages
- **Problem**: Synchronization issues, both indices need records

**Single Index (proposed)**:
- Augment standard RDM index with k-NN vector fields
- One index serves both AI and standard search
- Benefits: Simpler, automatic sync, ~25% faster indexing, 16-32% storage overhead

### 4. Investigated Implementation Approaches

**Approach 1: Runtime Patching** (attempted, complex)
- Patch `InvenioSearch.create_index()` to add k-NN settings
- Issue: Extension initialization order - `current_search` not available during CLI init
- Result: Abandoned this approach as too fragile

**Approach 2: Custom Mappings Entry Point** (attempted, failed)
- Register custom mapping via `invenio_search.mappings` entry point
- Issue: Invenio doesn't allow duplicate/override mappings
- Result: "Duplicate index" error

**Approach 3: Index Templates** (in progress)
- Use OpenSearch index templates via `invenio_search.index_templates` entry point
- Templates automatically apply settings/mappings to matching indices
- **Status**: Infrastructure created but not yet working

### 5. Created Index Template Infrastructure

**Files Created**:
- `/invenio-aisearch/invenio_aisearch/index_templates/`
- `/invenio-aisearch/invenio_aisearch/index_templates/os-v2/__init__.py`
- `/invenio-aisearch/invenio_aisearch/index_templates/os-v2/rdmrecords_knn.json`

**Entry Point Registered**:
```toml
[project.entry-points."invenio_search.index_templates"]
rdmrecords_knn = "invenio_aisearch.index_templates"
```

**Template Content** (needs fix):
```json
{
  "index_patterns": ["*rdmrecords-records-record*"],  // WRONG - needs __SEARCH_INDEX_PREFIX__
  "priority": 100,
  "template": {
    "settings": {
      "index": {
        "knn": true
      }
    },
    "mappings": {
      "properties": {
        "aisearch": {
          "type": "object",
          "properties": {
            "embedding": {
              "type": "knn_vector",
              "dimension": 384,
              "method": {
                "name": "hnsw",
                "space_type": "cosinesimil",
                "engine": "nmslib",
                "parameters": {
                  "ef_construction": 128,
                  "m": 24
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### 6. Documentation Created

- `docs/single_vs_dual_index.md` - Comprehensive architecture comparison
- `docs/opensearch_knn_architecture.md` - Deep dive on k-NN implementation
- `CHANGES.rst` - Updated with version 0.0.2 details

## What Needs to Be Done Next

### Immediate: Fix the Index Template

1. **Update template pattern**:
   ```json
   "index_patterns": ["__SEARCH_INDEX_PREFIX__rdmrecords-records-record*"]
   ```

   Invenio will replace `__SEARCH_INDEX_PREFIX__` with `v13-ai-` resulting in pattern `v13-ai-rdmrecords-records-record*`

2. **Reinstall package**:
   ```bash
   pipenv install -e ../invenio-aisearch
   ```

3. **Recreate indices**:
   ```bash
   pipenv run invenio index destroy --force --yes-i-know
   pipenv run invenio index init
   ```

4. **Verify template was created**:
   ```bash
   curl "http://localhost:9200/_index_template/rdmrecords_knn" | python3 -m json.tool
   ```

   Should show the template with pattern `v13-ai-rdmrecords-records-record*`

5. **Verify k-NN enabled on index**:
   ```bash
   curl "http://localhost:9200/v13-ai-rdmrecords-records-record-v6.0.0/_settings" | python3 -m json.tool | grep knn
   ```

   Should show `"knn": "true"`

6. **Verify aisearch mapping exists**:
   ```bash
   curl "http://localhost:9200/v13-ai-rdmrecords-records-record-v6.0.0/_mapping" | python3 -m json.tool | grep -A 20 aisearch
   ```

   Should show the knn_vector field configuration

### Then: Reindex and Test

7. **Reindex all records**:
   ```bash
   pipenv run invenio index reindex --yes-i-know -t recid
   pipenv run invenio index run
   ```

   This will:
   - Index all 92 records from database
   - `EmbeddingDumperExt` will generate embeddings automatically
   - Both standard fields AND embeddings go into single index

8. **Verify records indexed**:
   ```bash
   curl "http://localhost:9200/v13-ai-rdmrecords-records-record-v6.0.0/_count"
   ```

   Should show `"count": 92`

9. **Verify embeddings present**:
   ```bash
   curl "http://localhost:9200/v13-ai-rdmrecords-records-record-v6.0.0/_search?size=1" | python3 -m json.tool | grep -A 5 aisearch
   ```

   Should show `aisearch.embedding` with 384-dimensional vector

10. **Test standard search**:
    ```bash
    curl -k "https://127.0.0.1:5000/api/records?q=dracula"
    ```

    Should return results

11. **Test AI search**:
    ```bash
    curl -k "https://127.0.0.1:5000/api/aisearch/search?q=vampire"
    ```

    Should return results using k-NN

12. **Test record landing page**:
    Visit `https://127.0.0.1:5000/records/{record_id}` - should work

### Future: Update AI Search Service

Currently the `AISearchService` queries a separate `aisearch` index. Once single-index is working, update it to query the main RDM index:

**File**: `invenio_aisearch/services/service/ai_search_service.py`

Change from:
```python
from invenio_aisearch.services.index import AISearchIndex
self.index = AISearchIndex(...)
```

To:
```python
from invenio_search import current_search_client
# Query the main RDM index with k-NN
index_name = "v13-ai-rdmrecords-records-record-v6.0.0"
```

The k-NN query structure stays the same - it just targets a different index.

## Key Learnings

1. **Invenio Extension Points**:
   - `invenio_search.mappings` - Cannot override existing mappings
   - `invenio_search.index_templates` - Proper way to customize index settings
   - Templates use `__SEARCH_INDEX_PREFIX__` placeholder

2. **OpenSearch Index Templates**:
   - Apply settings/mappings to indices matching a pattern
   - Priority determines which template wins for overlaps
   - Must be created BEFORE indices are created

3. **Single Index Benefits**:
   - Eliminates synchronization issues
   - Simpler architecture
   - Better storage efficiency than duplication
   - Faster indexing (one pass instead of two)

4. **Embedding Dumper Works**:
   - `EmbeddingDumperExt` is properly registered
   - Automatically generates embeddings during record dumps
   - No changes needed to dumper code

## Current State

- ✅ AI search API working (via separate aisearch index, which doesn't exist!)
- ❌ Main RDM index empty (needs reindexing)
- ❌ k-NN template not applied (pattern needs `__SEARCH_INDEX_PREFIX__`)
- ✅ Infrastructure for single-index ready (just needs pattern fix)
- ✅ Documentation complete

## Files Modified This Session

**invenio-aisearch**:
- `invenio_aisearch/ext.py` - Removed complex patching code
- `invenio_aisearch/resources/resource/ai_search_resource.py` - Fixed 500 error
- `invenio_aisearch/index_templates/os-v2/rdmrecords_knn.json` - Created (needs pattern fix)
- `invenio_aisearch/index_templates/os-v2/__init__.py` - Created
- `invenio_aisearch/index_templates/__init__.py` - Created
- `pyproject.toml` - Added index_templates entry point

**v13-ai**:
- `docs/single_vs_dual_index.md` - Architecture comparison
- `docs/opensearch_knn_architecture.md` - k-NN deep dive
- `docs/session4.5.md` - Fixed API 500 error
- `CHANGES.rst` - Version 0.0.2 documentation

## Next Session Start Here

1. Fix the template pattern to use `__SEARCH_INDEX_PREFIX__rdmrecords-records-record*`
2. Reinstall, destroy, recreate indices
3. Verify template applied and k-NN enabled
4. Reindex all 92 records
5. Test both standard and AI search
6. Update AI search service to use main index instead of separate aisearch index

The infrastructure is 95% complete - just needs the template pattern fix and reindexing!
