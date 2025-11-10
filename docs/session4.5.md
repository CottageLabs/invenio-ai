# Session 4.5: Fixing AI Search API 500 Error

## Problem Statement

After implementing the OpenSearch k-NN refactoring, the AI search functionality was returning a 500 error when accessed via the UI and API endpoints.

## Root Cause Analysis

### Initial Investigation

1. **API Endpoint Test**: Testing `/api/aisearch/search?q=vampire` returned a 500 error
2. **Error Message**: `AISearchService.search() got an unexpected keyword argument 'semantic_weight'`

### Root Cause

The resource layer (`ai_search_resource.py`) was still passing deprecated parameters from the old hybrid search implementation:
- `semantic_weight`
- `metadata_weight`

These parameters were removed when we refactored to use pure OpenSearch k-NN search, but the resource methods weren't updated.

Additionally, the `status()` method was incorrectly passing an `identity` parameter that the service method doesn't accept.

## Solution

### Files Modified

**`/home/steve/code/cl/Invenio/invenio-aisearch/invenio_aisearch/resources/resource/ai_search_resource.py`**

#### 1. Fixed `search_get()` method (lines 43-81)

Removed parameter extraction and passing:
```python
# REMOVED: semantic_weight and metadata_weight extraction
limit = args.get('limit')
summaries = args.get('summaries', False)

# Updated service call - removed semantic_weight and metadata_weight
result = self.service.search(
    identity=g.identity,
    query=query,
    limit=limit,
    include_summaries=summaries,
)
```

#### 2. Fixed `search_post()` method (lines 83-120)

Removed deprecated parameters from service call:
```python
# Updated service call - removed semantic_weight and metadata_weight
result = self.service.search(
    identity=g.identity,
    query=query,
    limit=data.get('limit'),
    include_summaries=data.get('summaries', False),
)
```

#### 3. Fixed `status()` method (lines 161-176)

Removed identity parameter that service doesn't accept:
```python
# Fixed: removed identity parameter
result = self.service.status()
return result.to_dict(), 200
```

### Correct Service Signature

The `AISearchService.search()` method signature after k-NN refactoring:
```python
def search(self, identity, query: str, limit: int = None, include_summaries: bool = True):
    """Search records using AI-powered semantic search with OpenSearch k-NN.

    Args:
        identity: User identity for access control
        query: Natural language search query
        limit: Maximum number of results (default from config)
        include_summaries: Whether to include AI-generated summaries

    Returns:
        SearchResult object with matching records
    """
```

## Testing Results

### API Endpoint Success

After fixing and restarting the server:
```bash
curl -k -s "https://127.0.0.1:5000/api/aisearch/search?q=vampire" | python3 -m json.tool
```

**Results**:
- Top result: "Dracula" with semantic score of 0.643
- Position 8: "Carmilla" (another vampire story) with score of 0.547
- OpenSearch k-NN semantic search working correctly
- 10 results returned with proper scoring

## Additional Discovery: Main Index Issue

While testing, we discovered a separate issue with the main InvenioRDM functionality:

### Problem
- Record landing pages return 404
- Normal search returns 0 results
- `/api/records/{record_id}` returns "The persistent identifier does not exist"

### Investigation Results
```bash
# Database has records
pipenv run invenio shell -c "from invenio_rdm_records.records.api import RDMRecord; print(f'Total records in DB: {RDMRecord.model_cls.query.count()}')"
# Output: Total records in DB: 92

# But main search index is empty
curl -s "http://localhost:9200/v13-ai-rdmrecords-records-record-v6.0.0/_count"
# Output: "count": 0
```

### Root Cause
The 92 records exist in the PostgreSQL database but have not been indexed into the main InvenioRDM search index (`v13-ai-rdmrecords-records-record-v6.0.0`). They only appear in AI search results because they exist in the AI-specific index (`v13-ai-aisearch`).

### Required Fix
Records need to be reindexed into the main search index:
```bash
pipenv run invenio index reindex --yes-i-know -t recid
```

This will:
1. Index all 92 records into the main search index
2. Enable record landing pages to work
3. Enable normal InvenioRDM search functionality
4. Allow both AI search and regular search to function

## Summary

### What Was Fixed
1. **AI Search API 500 Error**: Removed deprecated `semantic_weight` and `metadata_weight` parameters from resource methods
2. **Status Method Error**: Removed incorrect `identity` parameter from `status()` method call
3. **Confirmed Working**: AI search API endpoint now works correctly with OpenSearch k-NN

### Outstanding Issues
1. **Main Index Empty**: Need to reindex records into main InvenioRDM search index
2. **Impact**: Record landing pages and normal search non-functional until reindexing completes

### Key Learnings

1. **Service Contract Changes**: When refactoring service methods, must update all calling code (resources, tasks, etc.)
2. **Parameter Validation**: Resource layer must match service layer method signatures exactly
3. **Multiple Indexes**: InvenioRDM uses separate indexes for different purposes:
   - Main index: `v13-ai-rdmrecords-records-record-v6.0.0` (standard search + landing pages)
   - AI index: `v13-ai-aisearch` (AI semantic search)
4. **Reindexing Required**: After index recreation or schema changes, both indexes need reindexing

## Next Steps

1. Reindex all records into main search index: `pipenv run invenio index reindex --yes-i-know -t recid`
2. Verify record landing pages work after reindexing
3. Verify normal search functionality works
4. Test complete workflow: AI search → click result → view landing page
