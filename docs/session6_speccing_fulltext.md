# Session 6 - Full-Text Semantic Search Specification

## Context

This session focused on expanding the AI search capabilities from metadata-only search to full-text semantic search of book contents. The goal is to enable users to search for specific themes, passages, and concepts within the actual text of books, not just their titles and descriptions.

## Strategic Decision: Full-Text vs. Similarity Explanation

Two potential features were considered for the upcoming presentation:

1. **Similarity Explanation**: Show why records are similar
2. **Full-Text Analysis**: Search within book contents using semantic embeddings

**Decision**: Full-text analysis was chosen for higher impact because:
- Demonstrates AI doing something impossible with traditional search
- Creates "wow factor" demos: "Find passages about moral dilemmas" works across all books
- Shows real-world value of semantic search
- More visually impressive for presentations
- Infrastructure already exists (book texts downloaded, embedding system working, OpenSearch with KNN)

## Chunking Strategy

### Requirements
- Books average ~200k-430k words (Don Quixote: 430,289 words)
- Need manageable passage sizes for semantic search
- Must preserve context at chunk boundaries
- Need to maintain metadata linking chunks to source books

### Design Decisions

**Chunk Size**: 600 words (~3-4 paragraphs)
- Large enough to capture complete thoughts and context
- Small enough for focused results
- Aligns with typical semantic embedding capabilities

**Overlap**: 150 words (25%)
- Prevents losing context at chunk boundaries
- Ensures concepts split across chunks are still captured
- 25% overlap is standard for text chunking

**Metadata Preserved**:
- `chunk_id`: Unique identifier (format: `{record_id}_{chunk_index}`)
- `record_id`: Link to InvenioRDM record
- `book_title`: For display in results
- `author`: For filtering and display
- `chunk_index`: Position in book (0-based)
- `chunk_count`: Total chunks in book
- `text`: The actual passage text
- `char_start`, `char_end`: Character positions in original text
- `word_count`: Words in this chunk

## Implementation

### Script: `scripts/chunk_books.py`

Created a Python script that:
1. Fetches all records from InvenioRDM API
2. Downloads attached text files for each book
3. Cleans Project Gutenberg headers/footers using regex patterns
4. Splits text into overlapping chunks
5. Creates structured chunk documents with metadata
6. Outputs to JSONL format (one chunk per line)

**Key Features**:
- Automatic Gutenberg header/footer removal
- Handles books with no text files gracefully
- Progress reporting during processing
- Statistics on chunk sizes and counts
- Skip very small end chunks (<100 words)

### Execution Results

```
Books processed: 89/89
Total chunks: 28,877
Failed: 0
Average chunk size: 599 words
Chunk size range: 105-600 words
```

**Notable Examples**:
- Don Quixote: 950 chunks
- War and Peace: 1,252 chunks
- Les Misérables: 1,257 chunks
- Complete Works of William Shakespeare: 2,141 chunks
- King James Bible: 1,826 chunks
- The Yellow Wallpaper: 14 chunks
- A Modest Proposal: 8 chunks

### Output Format

JSONL file (`book_chunks.jsonl`) with one JSON object per line:

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
  "word_count": 600
}
```

## Index Architecture Discussion

### The Question
Should chunks be stored in the existing `rdmrecords` index (used by `invenio-aisearch`) or a separate index?

### Why Separate Index is Necessary

**1. Scale Problem (Primary Reason)**
- Current approach: 89 records × 1 embedding = 89 embeddings
- If chunks added to records: 89 records × 324 avg chunks = 28,877 embeddings embedded in 89 documents
- Don Quixote alone would contain 950 embeddings in one record
- Record API responses would balloon from kilobytes to megabytes
- Risk hitting OpenSearch document size limits

**2. Different Search Paradigm**
- **Metadata search**: "Find books about X" → returns books
- **Full-text search**: "Find passages about X" → returns **passages with book context**
- The chunk IS the result, not the book
- Result format: "Here's a passage from Chapter 5 of Don Quixote..."

**3. Performance**
- KNN search on 28,877 individual documents: Fast, direct vector comparison
- KNN search on 89 documents with 324 embeddings each: Complex nested queries, slower
- Would need to search every embedding in every record, then aggregate results

**4. Maintainability**
- Updating a chunk doesn't require reindexing entire book record
- Can rebuild chunk index independently
- Can have different retention/versioning strategies
- Cleaner separation of concerns

### Alternative Architecture (Rejected)

Could use same index with chunks as separate documents referencing parent records via parent-child relationships:
- Still requires separate documents (same storage cost)
- More complex queries
- Mixing two document types in one index is messy
- No real benefit over separate index

### Final Architecture

**Two indexes, two purposes:**

1. **`rdmrecords-rdmrecords-record-v6.0.0`** (existing)
   - Book-level metadata search
   - One document per book record
   - Embedding from metadata + description
   - Query: "Find books about social injustice"
   - Result: List of book records

2. **`book-chunks-v1`** (new)
   - Passage-level full-text search
   - One document per chunk (28,877 documents)
   - Embedding from actual passage text
   - Query: "Find passages where characters discuss redemption"
   - Result: List of passages with book context

## Next Steps

1. ✅ Design chunking strategy
2. ✅ Create chunking script
3. ✅ Generate chunks (28,877 chunks created)
4. ⏳ Create OpenSearch index for chunks with KNN vectors
5. ⏳ Generate embeddings for all chunks
6. ⏳ Index chunks with embeddings in OpenSearch
7. ⏳ Update search service to support passage search
8. ⏳ Create UI to display passage results with context
9. ⏳ Test with demo queries for presentation

## Technical Specifications

### OpenSearch Index Requirements

```json
{
  "settings": {
    "index": {
      "knn": true,
      "knn.algo_param.ef_search": 512
    }
  },
  "mappings": {
    "properties": {
      "chunk_id": {"type": "keyword"},
      "record_id": {"type": "keyword"},
      "book_title": {"type": "text"},
      "author": {"type": "text"},
      "chunk_index": {"type": "integer"},
      "text": {"type": "text", "analyzer": "english"},
      "embedding": {
        "type": "knn_vector",
        "dimension": 384,
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimil",
          "engine": "faiss"
        }
      }
    }
  }
}
```

### Embedding Model

Using same model as metadata search for consistency:
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Why**: Fast, good quality, already integrated

### Estimated Storage

- 28,877 chunks × 384 dimensions × 4 bytes = ~44 MB for vectors
- Plus text and metadata: ~100-150 MB total
- Reasonable for demonstration and production use

## Demo Query Ideas for Presentation

These queries showcase capabilities impossible with traditional keyword search:

1. "Books where characters face moral dilemmas"
2. "Passages about redemption and forgiveness"
3. "Descriptions of social injustice"
4. "Characters struggling with identity"
5. "Scenes of transformation or change"
6. "Discussions of power and corruption"
7. "Moments of sacrifice"
8. "Philosophical reflections on death"

Each query would return specific passages from multiple books, showing the exact text that matches semantically, with links back to the full book record.
