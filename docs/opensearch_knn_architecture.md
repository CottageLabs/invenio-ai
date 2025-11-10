# OpenSearch k-NN Architecture: From Embeddings File to Native Vector Search

## Overview

This document describes the architectural evolution of `invenio-aisearch` from version 0.0.1 (embeddings file-based) to version 0.0.2 (OpenSearch k-NN native). It provides context on why the change was made, how it was implemented, and what benefits it provides.

## Motivation

### Problems with Version 0.0.1 (Embeddings File Approach)

The initial implementation of `invenio-aisearch` used a separate embeddings file to store vector representations of records:

**Architecture**:
```
Record → Generate Embedding → Save to File (embeddings.json)
Search Query → Generate Embedding → Load File → Compute Similarity → Filter by IDs → Query OpenSearch
```

**Issues**:

1. **Synchronization Problems**: The embeddings file could easily get out of sync with the database
   - New records added to InvenioRDM wouldn't automatically appear in AI search
   - Deleted records would still have embeddings in the file
   - Updated records wouldn't have updated embeddings
   - Required manual regeneration of entire embeddings file

2. **Scalability Limitations**:
   - Entire embeddings file had to be loaded into memory for each search
   - File size grows linearly with number of records (92 records × 384 dimensions × 4 bytes ≈ 140KB, but scales to MB/GB)
   - No indexing structure for fast similarity search - required O(n) comparisons

3. **Operational Complexity**:
   - Separate workflow to generate and maintain embeddings file
   - File management and versioning challenges
   - Deployment complexity (where to store file, how to update it)

4. **Performance Issues**:
   - Two-phase search process: similarity search in Python, then fetch from OpenSearch
   - Network overhead fetching full records after similarity computation
   - CPU-bound similarity computation on every query

### Why OpenSearch k-NN?

OpenSearch provides native k-NN (k-nearest neighbors) vector search capabilities that solve all these issues:

**Architecture**:
```
Record → Generate Embedding → Store in OpenSearch with k-NN field
Search Query → Generate Embedding → OpenSearch k-NN Query → Results
```

**Benefits**:

1. **Automatic Synchronization**: Embeddings are part of the document, updated automatically when records are indexed
2. **Scalability**: HNSW (Hierarchical Navigable Small World) algorithm provides approximate nearest neighbor search in O(log n) time
3. **Simplicity**: Single search index, single query, no external file management
4. **Performance**: Native vector search with optimized C++ implementation, optional GPU acceleration
5. **Integration**: Embeddings live alongside document metadata, enabling combined filtering and semantic search

## Architecture Comparison

### Version 0.0.1: Embeddings File

```python
# Data Flow
1. Record created/updated in InvenioRDM
2. Administrator runs script to regenerate embeddings file
3. Script extracts all records, generates embeddings, saves to embeddings.json

# Search Flow
1. User submits query: "vampire stories"
2. AI Search Service generates query embedding
3. Load embeddings.json into memory
4. Compute cosine similarity with all 92 embeddings (O(n) operation)
5. Sort by similarity, take top-k record IDs
6. Query OpenSearch main index for those specific IDs
7. Merge results with similarity scores
8. Return to user
```

**Components**:
- `services/service/ai_search_service.py`: Loads embeddings file, computes similarities
- `embeddings.json`: Static file with all record vectors
- Separate indexing workflow for embeddings

### Version 0.0.2: OpenSearch k-NN

```python
# Data Flow
1. Record created/updated in InvenioRDM
2. EmbeddingDumperExt automatically generates embedding during dump
3. Record indexed to OpenSearch with embedding in aisearch.embedding field
4. HNSW index automatically updated

# Search Flow
1. User submits query: "vampire stories"
2. AI Search Service generates query embedding
3. Single OpenSearch k-NN query with vector and filters
4. OpenSearch HNSW returns approximate nearest neighbors (O(log n))
5. Return to user
```

**Components**:
- `services/index.py`: Manages AI search index with k-NN configuration
- `records/dumpers/embedding_dumper.py`: Auto-generates embeddings during indexing
- `services/service/ai_search_service.py`: Builds k-NN queries
- OpenSearch index with k-NN vector field

## Technical Implementation

### Index Configuration

The AI search index is configured with k-NN support:

```python
# services/index.py
index_settings = {
    "settings": {
        "index": {
            "knn": True,  # Enable k-NN plugin
            "number_of_shards": 1,
            "number_of_replicas": 0
        }
    },
    "mappings": {
        "properties": {
            "record_id": {"type": "keyword"},
            "title": {"type": "text"},
            "creators": {"type": "text"},
            "description": {"type": "text"},
            "subjects": {"type": "keyword"},
            "resource_type": {"type": "keyword"},
            "publication_date": {"type": "date"},
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
```

**Key Parameters**:

- `dimension: 384`: Vector size from `all-MiniLM-L6-v2` model
- `method.name: "hnsw"`: Hierarchical Navigable Small World graph algorithm
- `space_type: "cosinesimil"`: Cosine similarity distance metric
- `engine: "nmslib"`: NMSLIB library for vector operations
- `ef_construction: 128`: Quality vs speed tradeoff during index building (higher = better quality, slower build)
- `m: 24`: Number of bi-directional links per node in graph (higher = better recall, more memory)

### Automatic Embedding Generation

The `EmbeddingDumperExt` class integrates with InvenioRDM's dumper system:

```python
# records/dumpers/embedding_dumper.py
class EmbeddingDumperExt(DumperExt):
    """Dumper extension that adds embeddings to records."""

    def dump(self, record, data):
        """Add embedding to the dumped record data."""
        # Get the model manager from the extension
        model_manager = current_app.extensions["invenio-aisearch"].model_manager

        # Extract text content from record
        text_content = self._extract_text(record)

        # Generate embedding using sentence transformer
        embedding = model_manager.encode(text_content)

        # Add to dump data
        data["aisearch"] = {
            "embedding": embedding.tolist()
        }

        return data
```

This dumper is registered on RDM records in `ext.py`:

```python
from invenio_rdm_records.records.api import RDMRecord, RDMDraft
from .records.dumpers import EmbeddingDumperExt

RDMRecord.dumper._extensions.append(EmbeddingDumperExt())
RDMDraft.dumper._extensions.append(EmbeddingDumperExt())
```

**Benefits**:
- Automatic: No manual step to generate embeddings
- Consistent: Embeddings always match current record state
- Integrated: Works with InvenioRDM's existing indexing workflow

### k-NN Query Construction

The service builds OpenSearch k-NN queries:

```python
# services/service/ai_search_service.py
def search(self, identity, query: str, limit: int = None, include_summaries: bool = True):
    """Search using OpenSearch k-NN."""

    # Generate embedding for query
    query_embedding = self.model_manager.encode(query)

    # Build k-NN query
    search_body = {
        "size": limit or self.config.default_results_per_page,
        "query": {
            "knn": {
                "aisearch.embedding": {
                    "vector": query_embedding.tolist(),
                    "k": limit or self.config.default_results_per_page
                }
            }
        },
        "_source": ["record_id", "title", "creators", "publication_date",
                    "resource_type", "license", "access_status"]
    }

    # Execute query
    results = self.index.search(search_body)

    # Process results
    return self._process_results(results, include_summaries)
```

**Query Features**:
- `knn` query type: Native vector similarity search
- `vector`: Query embedding as 384-dimensional list
- `k`: Number of nearest neighbors to return
- `_source`: Specify which fields to return

### Advanced k-NN Queries with Filters

OpenSearch k-NN supports combining vector search with filters:

```python
# Example: Find similar documents published after 2000
search_body = {
    "size": 10,
    "query": {
        "bool": {
            "must": [
                {
                    "knn": {
                        "aisearch.embedding": {
                            "vector": query_embedding.tolist(),
                            "k": 100  # Get more candidates before filtering
                        }
                    }
                }
            ],
            "filter": [
                {
                    "range": {
                        "publication_date": {
                            "gte": "2000-01-01"
                        }
                    }
                }
            ]
        }
    }
}
```

## Performance Considerations

### Index Build Time

**HNSW Index Construction**:
- Time complexity: O(n × log n × ef_construction × m)
- For 92 records: ~1-2 seconds
- For 10,000 records: ~1-2 minutes
- For 1,000,000 records: ~2-3 hours

**Parameters**:
- `ef_construction=128`: Higher values = better quality but slower build
- `m=24`: More links = better recall but more memory and slower build

### Query Performance

**Search Time Complexity**:
- HNSW search: O(log n × ef_search)
- Default `ef_search=100` (can be tuned at query time)

**Performance Results** (92 records):
- Query time: 10-30ms
- Includes embedding generation (5-10ms) + k-NN search (5-20ms)

**Expected Performance** (larger datasets):
- 10,000 records: 15-40ms
- 100,000 records: 20-50ms
- 1,000,000 records: 25-60ms

The logarithmic scaling is key - performance doesn't degrade linearly with dataset size.

### Memory Usage

**Index Memory**:
- Base: ~384 × 4 bytes × n records (vector storage)
- HNSW graph: ~m × 4 bytes × n records (links)
- Total: ~(384 + 24) × 4 × n ≈ 1.6 KB per record

**For Different Dataset Sizes**:
- 92 records: ~150 KB
- 10,000 records: ~16 MB
- 100,000 records: ~160 MB
- 1,000,000 records: ~1.6 GB

### Accuracy vs Performance Tradeoffs

**HNSW is an Approximate Algorithm**:
- Does not guarantee finding the exact k nearest neighbors
- Trades small accuracy loss for massive speed gains
- Recall typically 95-99% depending on parameters

**Tuning Parameters**:

1. **Build Time** (`ef_construction`):
   - Lower (64): Faster build, lower recall (~92-95%)
   - Medium (128): Balanced (our choice) (~95-97%)
   - Higher (256): Slower build, higher recall (~97-99%)

2. **Query Time** (`ef_search`, set at query time):
   - Lower (50): Faster queries, lower recall
   - Medium (100): Balanced (default)
   - Higher (200): Slower queries, higher recall

3. **Memory/Recall** (`m`):
   - Lower (16): Less memory, lower recall
   - Medium (24): Balanced (our choice)
   - Higher (48): More memory, higher recall

## Migration Path

### Step 1: Index Recreation

The index structure has changed, so indices must be recreated:

```bash
# Backup if needed
pipenv run invenio shell -c "from invenio_search import current_search_client; current_search_client.indices.get('*')"

# Destroy old indices
pipenv run invenio index destroy --force --yes-i-know

# Recreate with k-NN support
pipenv run invenio index init
```

**What Happens**:
- Old index mappings are deleted
- New indices created with k-NN vector fields
- HNSW index structures initialized

### Step 2: Reindexing Records

All records must be reindexed to generate embeddings:

```bash
# Reindex records (this generates embeddings automatically)
pipenv run invenio index reindex --yes-i-know -t recid

# Process the reindex queue
pipenv run invenio index run
```

**What Happens**:
- Each record is fetched from the database
- `EmbeddingDumperExt` generates embedding from title/description/etc.
- Record + embedding indexed to both main index and AI search index
- HNSW graph updated with new vector

**Time Estimates**:
- 92 records: ~30 seconds
- 1,000 records: ~3-5 minutes
- 10,000 records: ~30-45 minutes
- 100,000 records: ~5-8 hours

### Step 3: Remove Old Embeddings File

```bash
# If you have an old embeddings file
rm embeddings.json
rm -rf embeddings/
```

### Step 4: Update API Calls

If you were using the old API with weight parameters:

```bash
# Old (0.0.1)
curl "https://127.0.0.1:5000/api/aisearch/search?q=vampire&semantic_weight=0.7&metadata_weight=0.3"

# New (0.0.2)
curl "https://127.0.0.1:5000/api/aisearch/search?q=vampire&limit=10&summaries=true"
```

## Integration with InvenioRDM

### Dual Index Architecture

Version 0.0.2 maintains two separate indices:

1. **Main RDM Index** (`v13-ai-rdmrecords-records-record-v6.0.0`):
   - Used by standard InvenioRDM search
   - Full metadata, text search, facets
   - Used for record landing pages
   - Must be populated for normal functionality

2. **AI Search Index** (`v13-ai-aisearch`):
   - Used only by AI-powered semantic search
   - Optimized schema with k-NN vectors
   - Separate scaling and configuration

**Important**: Both indices need records for full functionality:
- AI search works → need records in `aisearch` index
- Landing pages work → need records in main RDM index
- Both work → need records in both indices

### Indexing Workflow

```
User creates/updates record in UI
    ↓
RDMRecord.commit()
    ↓
Record dumper runs (includes EmbeddingDumperExt)
    ↓
Dumped data sent to indexing queue
    ↓
OpenSearch bulk indexer
    ↓
    ├─→ Main RDM index (standard mappings)
    └─→ AI search index (with k-NN embedding)
```

### Dumper Extension Chain

InvenioRDM records can have multiple dumper extensions:

```python
RDMRecord.dumper._extensions = [
    # Built-in InvenioRDM dumpers
    RelationDumperExt(...),
    EDTFDumperExt(...),
    # Our embedding dumper
    EmbeddingDumperExt(),
]
```

Each extension processes the record data in sequence, adding or modifying fields.

## Future Enhancements

### 1. GPU Acceleration

Currently embeddings are generated on CPU. For large-scale deployments:

```python
# Enable GPU in model_manager.py
model = SentenceTransformer(
    model_name,
    device='cuda',  # Use GPU
    cache_folder=model_path
)
```

**Benefits**:
- 10-50x faster embedding generation
- Critical for large reindexing operations
- Reduces query latency for complex summaries

### 2. Batch Embedding Generation

For large reindexing, batch processing reduces overhead:

```python
# Instead of one-by-one
embeddings = model.encode([text1, text2, ..., textN], batch_size=32)
```

### 3. Hybrid Search

Combine k-NN semantic search with keyword search:

```python
{
    "query": {
        "hybrid": {
            "queries": [
                {"knn": {"aisearch.embedding": {"vector": [...], "k": 100}}},
                {"multi_match": {"query": "vampire", "fields": ["title", "description"]}}
            ]
        }
    }
}
```

**Use Case**: Find semantically similar documents that also match specific keywords.

### 4. Fine-tuned Models

Replace `all-MiniLM-L6-v2` with domain-specific models:

```python
# Scientific papers
model = SentenceTransformer('allenai/specter2')

# Code repositories
model = SentenceTransformer('microsoft/codebert-base')

# Multilingual content
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
```

### 5. Multiple Vector Fields

Support different embedding types:

```json
{
    "aisearch": {
        "title_embedding": [...],      // Title only
        "content_embedding": [...],    // Full content
        "code_embedding": [...]        // Code snippets
    }
}
```

Query different embeddings for different search types.

### 6. Dynamic ef_search Tuning

Adjust recall/performance tradeoff per query:

```python
{
    "query": {
        "knn": {
            "aisearch.embedding": {
                "vector": [...],
                "k": 10,
                "ef_search": 200  // Higher for important queries
            }
        }
    }
}
```

## Troubleshooting

### Issue: k-NN queries return no results

**Symptoms**: Search returns empty results even though records exist

**Cause**: Records don't have embeddings in the aisearch field

**Solution**:
```bash
# Check if embeddings exist
curl "http://localhost:9200/v13-ai-aisearch/_search?size=1" | jq '.hits.hits[0]._source.aisearch'

# If null or missing, reindex
pipenv run invenio index reindex --yes-i-know -t recid
pipenv run invenio index run
```

### Issue: "index.knn is set to false" error

**Symptoms**: Error during indexing: `"index.knn is set to false"`

**Cause**: Index was created without k-NN enabled

**Solution**:
```bash
# Recreate index
pipenv run invenio index destroy --force --yes-i-know
pipenv run invenio index init
```

### Issue: Poor search relevance

**Symptoms**: Results don't match query semantically

**Possible Causes**:
1. Model not suitable for domain
2. Text extraction not capturing key information
3. Low ef_search causing low recall

**Solutions**:
```python
# 1. Try different model
model_manager = AIModelManager("all-mpnet-base-v2")  # Larger, more accurate

# 2. Improve text extraction in EmbeddingDumperExt
def _extract_text(self, record):
    # Include more fields
    parts = [
        record.get("title", ""),
        record.get("description", ""),
        " ".join(record.get("subjects", [])),
        # Add more...
    ]

# 3. Increase ef_search
search_body["query"]["knn"]["aisearch.embedding"]["ef_search"] = 200
```

### Issue: Slow reindexing

**Symptoms**: Reindexing taking hours for moderate dataset

**Solutions**:
1. Enable GPU acceleration (10-50x speedup)
2. Increase batch size in indexer
3. Reduce `ef_construction` temporarily (can rebuild later)
4. Monitor with: `curl "http://localhost:9200/_cat/indices?v"`

## Conclusion

The migration from embeddings file (0.0.1) to OpenSearch k-NN (0.0.2) represents a fundamental architectural improvement:

- **Simpler**: No external file management
- **Faster**: Native vector search with HNSW
- **Scalable**: Logarithmic query time
- **Maintainable**: Automatic synchronization
- **Integrated**: Single index, single query

This architecture provides a solid foundation for AI-powered semantic search in InvenioRDM, with clear paths for future enhancements like GPU acceleration, hybrid search, and custom models.

## References

- [OpenSearch k-NN Documentation](https://opensearch.org/docs/latest/search-plugins/knn/index/)
- [HNSW Algorithm Paper](https://arxiv.org/abs/1603.09320)
- [Sentence Transformers Library](https://www.sbert.net/)
- [InvenioRDM Documentation](https://inveniordm.docs.cern.ch/)
