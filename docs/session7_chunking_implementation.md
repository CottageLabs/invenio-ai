# Session 7 - Full-Text Search Implementation: Chunking and Embeddings

## Overview

This session implemented the full infrastructure for document-level full-text semantic search, building on the specifications from Session 6. We successfully chunked 89 books into 28,877 searchable passages, generated embeddings for all chunks, and integrated everything into the `invenio-aisearch` extension using InvenioRDM patterns.

**Key Achievement**: Complete end-to-end pipeline from raw book texts to searchable, embedded document chunks ready for semantic search.

## What Was Built

### 1. Document Chunking Infrastructure

**CLI Command**: `invenio aisearch chunk-documents`

Created an integrated CLI command that:
- Fetches all records from InvenioRDM API
- Downloads attached text files from each record
- Removes Project Gutenberg headers/footers automatically
- Splits text into overlapping chunks with metadata preservation
- Outputs structured JSONL format
- Reads chunking parameters from configuration (single source of truth)

**Execution Results**:
```
Books processed: 89/89
Total chunks: 28,877
Failed: 0
Average chunk size: 599 words
Chunk size range: 105-600 words
```

**Notable Statistics**:
- Largest: Complete Works of William Shakespeare (2,141 chunks)
- King James Bible (1,826 chunks)
- War and Peace (1,252 chunks)
- Les Misérables (1,257 chunks)
- Don Quixote (950 chunks)
- Smallest: A Modest Proposal (8 chunks)

### 2. Chunk Data Structure

Each chunk document contains:

```json
{
  "chunk_id": "70hnm-ga976_0",
  "record_id": "70hnm-ga976",
  "book_title": "Don Quixote",
  "author": "Cervantes Saavedra, Miguel de",
  "chunk_index": 0,
  "chunk_count": 950,
  "text": "...",
  "char_start": 0,
  "char_end": 3247,
  "word_count": 600,
  "embedding": [0.123, -0.456, ...]  // 384-dimensional vector
}
```

### 3. Integration with invenio-aisearch

#### Configuration (`invenio_aisearch/config.py`)

Added configuration options with generic defaults:
```python
INVENIO_AISEARCH_CHUNKS_INDEX = "document-chunks-v1"
INVENIO_AISEARCH_CHUNK_SIZE = 600
INVENIO_AISEARCH_CHUNK_OVERLAP = 150
INVENIO_AISEARCH_CHUNKS_ENABLED = False
INVENIO_AISEARCH_DATA_DIR = "aisearch_data"
INVENIO_AISEARCH_CHUNKS_FILE = "document_chunks.jsonl"
```

Instance overrides in `v13-ai/invenio.cfg`:
```python
INVENIO_AISEARCH_DATA_DIR = "gutenberg_data"
INVENIO_AISEARCH_CHUNKS_FILE = "book_chunks.jsonl"
```

This allows the extension to be generic while instances can customize for their specific use cases.

#### OpenSearch Index Structure

Created `document-chunks-v1` index with:
- **KNN vectors**: 384 dimensions, cosine similarity
- **Algorithm**: HNSW with nmslib engine
- **Text analysis**: English analyzer
- **Settings**:
  - ef_construction: 128
  - m: 24
  - ef_search: 512

**Important Discovery**: The existing `rdmrecords` index uses **nmslib** engine, not faiss. Initial attempt with faiss + cosinesimil space type failed. Corrected to use nmslib for consistency.

#### CLI Commands Added

**1. Chunk Documents**
```bash
invenio aisearch chunk-documents [--output book_chunks.jsonl] [--base-url URL]
```
- Fetches records from InvenioRDM and chunks their text files
- Reads chunking parameters from configuration
- Cleans Project Gutenberg headers/footers
- Outputs structured JSONL file ready for embedding generation

**2. Create Chunks Index**
```bash
invenio aisearch create-chunks-index
```
- Creates OpenSearch index with proper KNN configuration
- Checks for existing index and offers to recreate
- Validates setup before proceeding

**3. Check Chunks Status**
```bash
invenio aisearch chunks-status
```
- Shows index statistics (doc count, size, embeddings)
- Displays sample chunk for verification
- Shows configuration settings

**4. Generate Chunk Embeddings**
```bash
invenio aisearch generate-chunk-embeddings book_chunks.jsonl [--batch-size 100] [--async]
```
- Processes chunks in configurable batches
- Generates embeddings using existing model (all-MiniLM-L6-v2)
- Bulk indexes chunks with embeddings into OpenSearch
- Supports both synchronous and asynchronous (Celery) modes
- Auto-chains batches for large datasets
- Shows progress bar in sync mode

### 4. Celery Task for Async Processing

**Task**: `generate_chunk_embeddings` (`invenio_aisearch/tasks.py`)

Features:
- Batch processing with configurable size (default: 100 chunks)
- Automatic resumption from offset (for robustness)
- Self-chaining for processing large datasets
- Bulk indexing for performance
- Error tracking and reporting
- Proper logging for monitoring

Task automatically chains to next batch until all chunks are processed, with 2-second delays between batches to avoid overwhelming the system.

### 5. Enhanced ModelManager

Added to `invenio_aisearch/models.py`:

```python
@property
def model_name(self) -> str:
    """Get the embedding model name."""
    return "sentence-transformers/all-MiniLM-L6-v2"

@property
def embedding_dim(self) -> int:
    """Get the embedding dimension."""
    return 384

def encode_batch(self, texts: list):
    """Generate embeddings for a batch of texts."""
    return self.embedding_model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False
    )
```

These additions enable:
- Batch embedding generation for efficiency
- Model introspection for configuration display
- Consistent interface with single-text embedding

## Technical Decisions

### Why Separate Index?

**Decision**: Use separate `document-chunks-v1` index instead of adding chunks to existing `rdmrecords` index.

**Rationale**:
1. **Scale**: 28,877 embeddings cannot fit in 89 record documents
2. **Search paradigm**: Chunks ARE the results, not just metadata for ranking
3. **Performance**: Direct KNN on 28,877 docs is faster than nested queries
4. **Maintainability**: Independent versioning and rebuilding

### Why "Document Chunks" Not "Book Chunks"?

**Decision**: Use generic term "document chunks" throughout.

**Rationale**:
- More extensible (works for any text document, not just books)
- Future-proof for other document types
- Professional/generic terminology
- Although we assume .txt files currently

### Chunking Parameters

**Chunk size**: 600 words
- Captures complete thoughts and context
- Aligns with semantic embedding capabilities
- Small enough for focused results

**Overlap**: 150 words (25%)
- Standard overlap ratio for text chunking
- Prevents concept loss at boundaries
- Ensures themes spanning chunk boundaries are captured

## Performance Characteristics

### Processing Time
- **Chunking**: ~5 minutes for 89 books
- **Embedding generation**: ~15-20 minutes for 28,877 chunks (synchronous, batch size 100)
- **Total pipeline**: ~25 minutes from raw texts to searchable chunks

### Storage
- **Index size**: 487.04 MB
- **Breakdown**:
  - Vector embeddings: ~44 MB (28,877 × 384 × 4 bytes)
  - Text and metadata: ~443 MB
  - Reasonable for demo and production use

### Memory Usage
- Model loading: ~500 MB (SentenceTransformer)
- Batch processing: ~100-200 MB per batch
- Sustainable on development machines

## Operational Commands

### Complete Setup Workflow

```bash
# 1. Chunk documents from InvenioRDM records (uses config defaults)
invenio aisearch chunk-documents

# 2. Create OpenSearch index
invenio aisearch create-chunks-index

# 3. Generate and index embeddings (uses config defaults)
invenio aisearch generate-chunk-embeddings

# 4. Verify
invenio aisearch chunks-status
```

**Note**: All commands use configuration defaults from `invenio.cfg`:
- Chunking parameters: `INVENIO_AISEARCH_CHUNK_SIZE`, `INVENIO_AISEARCH_CHUNK_OVERLAP`
- Data location: `INVENIO_AISEARCH_DATA_DIR`, `INVENIO_AISEARCH_CHUNKS_FILE`
- The extension has generic defaults (`aisearch_data/document_chunks.jsonl`)
- Instance config overrides for Project Gutenberg (`gutenberg_data/book_chunks.jsonl`)

### Async Processing (for Production)

```bash
# Queue as Celery task (uses config defaults)
invenio aisearch generate-chunk-embeddings --async

# Monitor Celery logs
# Check progress
invenio aisearch chunks-status
```

### Rebuilding/Updating

```bash
# Delete and recreate index
invenio aisearch create-chunks-index
# (Confirm 'yes' when prompted)

# Reprocess embeddings (uses config defaults)
invenio aisearch generate-chunk-embeddings
```

## Integration Points

### Files Modified

**invenio-aisearch extension:**
- `invenio_aisearch/config.py` - Added chunk configuration
- `invenio_aisearch/cli.py` - Added 3 new commands (create-chunks-index, chunks-status, generate-chunk-embeddings)
- `invenio_aisearch/tasks.py` - Added Celery task for async embedding generation
- `invenio_aisearch/models.py` - Enhanced ModelManager with batch encoding

**v13-ai instance:**
- `scripts/chunk_books.py` - New chunking script
- `book_chunks.jsonl` - Generated chunk data (28,877 lines, ~100 MB)

### API/Service Integration

**Implemented:**
- ✅ Passage search service (`search_passages` method in `AISearchService`)
- ✅ REST API endpoint (`/api/aisearch/passages?q=...&limit=10`)
- ✅ Tested with multiple semantic query types

**Pending:**
- UI components for displaying passage results
- Integration with existing `/aisearch` search interface

## Current Status

### ✅ Completed
1. Document chunking strategy and implementation
2. OpenSearch index creation with KNN vectors
3. Embedding generation pipeline (sync and async)
4. CLI management commands
5. Full integration with invenio-aisearch
6. All 28,877 chunks indexed with embeddings
7. Passage search service implementation
8. REST API endpoint for passage search
9. Tested with multiple semantic query types

### 🔄 Ready for Next Session
1. Build UI to display passage results with book context
2. Integrate with existing `/aisearch` search interface
3. Enable `INVENIO_AISEARCH_CHUNKS_ENABLED` config

## Demo Query Ideas

These queries will showcase capabilities impossible with traditional search:

1. **Thematic Search**:
   - "Characters facing moral dilemmas"
   - "Passages about redemption and forgiveness"
   - "Discussions of social injustice"

2. **Concept Search**:
   - "Struggles with identity"
   - "Scenes of transformation or change"
   - "Philosophical reflections on death"

3. **Emotional Search**:
   - "Moments of sacrifice"
   - "Descriptions of loneliness"
   - "Expressions of hope and resilience"

Each query will return specific passages from multiple books, showing the exact text that semantically matches, with metadata about which book and where in the book.

## API Testing Results

The `/api/aisearch/passages` endpoint has been successfully tested with various semantic query types:

### Query 1: Character Decisions
**Query**: `protagonist makes an important decision`
**Top Results**:
- **Tom Jones** by Henry Fielding (similarity: 0.665) - Blifil deciding to pursue marriage with Sophia for her fortune
- **Ferdinand Count Fathom** by Tobias Smollett (similarity: 0.647) - Ferdinand contemplating becoming a highwayman

### Query 2: Quest Beginnings
**Query**: `main character embarks on their quest`
**Top Results**:
- **Ferdinand Count Fathom** by Smollett (similarity: 0.618) - Resolving to face banditti in the woods
- **Treasure Island** by Robert Louis Stevenson (similarity: 0.615) - Jim Hawkins excited about the adventure
- **My Life** by Richard Wagner (similarity: 0.613) - Philosophical reflection on life choices

### Query 3: Thematic Search - Sacrifice
**Query**: `moments of sacrifice and selflessness`
**Top Results**:
- **War and Peace** by Leo Tolstoy (similarity: 0.682)
- **How to Observe: Morals and Manners** by Harriet Martineau (similarity: 0.680)
- **Les Misérables** by Victor Hugo (similarity: 0.678)

### Query 4: Philosophical Concepts
**Query**: `philosophical reflections on death and mortality`
**Top Results**:
- **Thus Spake Zarathustra** by Friedrich Nietzsche (similarity: 0.726)
- **Meditations** by Marcus Aurelius (similarity: 0.715)
- **Les Misérables** by Victor Hugo (similarity: 0.687)

**Key Observations**:
- Similarity scores range from 0.60-0.75 for relevant matches
- The system correctly identifies thematic content across diverse literary works
- Philosophical queries return the most relevant philosophical texts
- Character-driven queries find narrative passages about decisions and actions
- The semantic search successfully captures concepts that would be impossible to find with keyword search

## Files Created/Modified Summary

### New Files
- `/home/steve/code/cl/Invenio/v13-ai/book_chunks.jsonl` - Generated chunk data (28,877 chunks)
- `/home/steve/code/cl/Invenio/v13-ai/docs/session7_chunking_implementation.md` - This documentation

### Modified Files
- `../invenio-aisearch/invenio_aisearch/config.py` - Added chunk configuration
- `../invenio-aisearch/invenio_aisearch/cli.py` - Added 4 CLI commands:
  - `create-chunks-index` - Create OpenSearch index with KNN vectors
  - `chunks-status` - Show index statistics
  - `generate-chunk-embeddings` - Generate and index embeddings (sync/async)
  - `chunk-documents` - Chunk documents from InvenioRDM records
- `../invenio-aisearch/invenio_aisearch/tasks.py` - Added Celery task for async processing
- `../invenio-aisearch/invenio_aisearch/models.py` - Enhanced ModelManager with batch encoding
- `../invenio-aisearch/invenio_aisearch/services/service/ai_search_service.py` - Added `search_passages` method
- `../invenio-aisearch/invenio_aisearch/resources/resource/ai_search_resource.py` - Added `passages` endpoint handler
- `../invenio-aisearch/invenio_aisearch/resources/config.py` - Added passages route

### Removed Files (Consolidated into CLI)
- `scripts/chunk_books.py` - Replaced by `invenio aisearch chunk-documents`
- `scripts/create_chunks_index.py` - Replaced by `invenio aisearch create-chunks-index`

### Database/Index Changes
- Created OpenSearch index: `document-chunks-v1`
- Indexed: 28,877 documents with 384-dimensional embeddings
- Index size: 487.04 MB

## Lessons Learned

1. **Engine Compatibility**: nmslib vs faiss - Always check existing index configuration for consistency
2. **Batch Processing**: 100 chunks per batch provides good balance of memory usage and performance
3. **Progress Visibility**: Progress bars and status commands are essential for long-running operations
4. **Task Chaining**: Self-chaining Celery tasks work well for processing large datasets incrementally
5. **Generic Terminology**: Using "document chunks" instead of "book chunks" maintains flexibility
6. **Proper Integration**: Consolidating standalone scripts into CLI commands with configuration improves maintainability and follows InvenioRDM patterns

## Next Steps for Presentation

For the demo next week:

**✅ Completed**:
1. ~~Search Service~~ - `search_passages` method implemented in `AISearchService`
2. ~~API Endpoint~~ - `/api/aisearch/passages` endpoint working and tested
3. ~~Testing~~ - Multiple semantic query types tested successfully

**Remaining Work** (~2-3 hours):
1. **UI Component** (~2-3 hours)
   - Create passage results page/component
   - Show matching text with context
   - Link back to full book record
   - Display chunk position and similarity scores
   - Add simple search interface

**Total estimated time remaining**: 2-3 hours to make demo-ready

## Conclusion

We have successfully built a complete document-level full-text semantic search infrastructure with a working API. All chunks are indexed with embeddings and can be queried through the REST API. The system is properly integrated with InvenioRDM patterns using CLI commands, Celery tasks, and configuration options.

**What's Working**:
- ✅ 28,877 document chunks indexed with 384-dimensional embeddings
- ✅ OpenSearch k-NN search with nmslib engine
- ✅ Service layer (`search_passages` method)
- ✅ REST API endpoint (`/api/aisearch/passages`)
- ✅ Successfully tested with multiple semantic query types
- ✅ Similarity scores ranging from 0.60-0.75 for relevant matches

**Remaining Work**:
- UI components for displaying passage results (~2-3 hours)

**Status**: Production-ready API, demo-ready UI pending (~3 hours of work).
