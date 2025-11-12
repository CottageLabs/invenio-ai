# Session 8: Passage-Aware Boosting and UI Refinement

**Date:** 2025-11-11
**Focus:** Hybrid search UI improvements, passage-aware book ranking, deduplication, and performance optimization

## Overview

This session continued from session 7.5 (hybrid AI search implementation) to refine the user experience and add intelligent passage-aware boosting. The work transformed the basic hybrid search into a cohesive, intelligent system that promotes books based on passage-level evidence and presents results in an intuitive grouped format.

## Key Achievements

### 1. UI Cohesion - Passages Within Books

**Problem:** Initial implementation showed passages in a separate section from books, creating visual fragmentation.

**Solution:** Reorganized display to group passages within their parent books:
- Passages appear directly under their source book
- "Orphan passages" section for passages from books outside top results
- Visual hierarchy with book icon for books, file icon for passages

**Files modified:**
- `invenio-aisearch/assets/semantic-ui/js/invenio_aisearch/search.js`

**Key code pattern:**
```javascript
// Group passages by record_id
const passagesByRecord = {};
if (data.passages && data.passages.length > 0) {
  data.passages.forEach(passage => {
    if (!passagesByRecord[passage.record_id]) {
      passagesByRecord[passage.record_id] = [];
    }
    passagesByRecord[passage.record_id].push(passage);
  });
}

// Render books with their passages inline
data.results.forEach((result, index) => {
  displayedRecords.add(result.record_id);
  // ... render book ...

  if (passagesByRecord[result.record_id]) {
    // Render passages for this book
  }
});

// Render orphan passages from books not in top results
const orphanPassages = [];
for (const recordId in passagesByRecord) {
  if (!displayedRecords.has(recordId)) {
    orphanPassages.push(...passagesByRecord[recordId]);
  }
}
```

### 2. Truncation Fix

**Problem:** Small passages were being truncated at 600 characters, hiding actual match content. User reported "off-by-one error" where displayed chunk appeared to be wrong one.

**Root cause:** `truncateText()` was cutting text at 600 chars regardless of chunk size.

**Solution:** Don't truncate chunks under 2000 characters (≈400 words):
```javascript
function truncateText(text, maxLength) {
  // Don't truncate if text is short (under 400 words ≈ 2000 chars)
  // This ensures small chunks are shown in full
  if (text.length <= 2000) {
    return text;
  }

  if (text.length <= maxLength) {
    return text;
  }

  // Try to truncate at sentence boundary
  const truncated = text.substring(0, maxLength);
  const lastSentence = Math.max(
    truncated.lastIndexOf('.'),
    truncated.lastIndexOf('?'),
    truncated.lastIndexOf('!')
  );

  if (lastSentence > maxLength * 0.7) {
    return truncated.substring(0, lastSentence + 1) + '...';
  }

  // Otherwise truncate at last space
  const lastSpace = truncated.lastIndexOf(' ');
  return truncated.substring(0, lastSpace) + '...';
}
```

### 3. Deduplication

**Problem:** Multiple editions of same work appearing in results (e.g., 3 different Frankenstein editions).

**Solution:** Normalized title + primary author matching:
```python
# Parse results with deduplication
results = []
seen_works = set()  # Track (title, primary_author) to deduplicate

for hit in response['hits']['hits']:
    # Extract title and author
    title = metadata.get('title', 'Untitled')
    primary_author = creator_names[0] if creator_names else 'Unknown'

    # Create deduplication key (normalized)
    # Remove subtitles after : or ;
    normalized_title = title.split(':')[0].split(';')[0].strip().lower()
    dedup_key = (normalized_title, primary_author.lower())

    # Skip if we've already seen this work
    if dedup_key in seen_works:
        current_app.logger.debug(f"Skipping duplicate: {title} by {primary_author}")
        continue

    seen_works.add(dedup_key)
    # ... add to results ...
```

**Files modified:**
- `invenio-aisearch/services/service/ai_search_service.py`

### 4. Passage-Aware Boosting

**Problem:** Book-level search alone missed relevant works. Query "a tale of a sea voyage" ranked The Odyssey at #17 (not displayed), even though it had strong passage matches.

**Solution:** Implemented sophisticated passage-aware re-ranking:

#### Strategy
1. **Wider initial search:** Fetch 5x more books (e.g., 50 instead of 10) to create re-ranking pool
2. **Passage evidence aggregation:** Score each book based on its passage matches
3. **Weighted combination:** Blend book-level and passage-level scores
4. **Re-rank and trim:** Sort by combined score, then trim to requested limit

#### Passage Aggregation Formula
```python
# For each book with matching passages
scores = [p['similarity_score'] for p in book_passages]
max_score = max(scores)
top3_avg = sum(sorted(scores, reverse=True)[:3]) / min(3, len(scores))
count_bonus = min(len(scores) * 0.01, 0.1)  # Cap at 0.1

passage_boost = (max_score * 0.5) + (top3_avg * 0.3) + (count_bonus * 0.2)
```

Components:
- **50%:** Best passage score (strongest evidence)
- **30%:** Average of top 3 passages (consistency)
- **20%:** Count bonus (breadth of matches, capped at 5 passages)

#### Combined Score Formula
```python
boosted_score = (book_score * 0.4) + (passage_boost * 0.6)
```

This gives more weight to passage evidence (60%) than book-level score (40%), reflecting the hypothesis that specific passage matches are stronger signals of relevance.

#### Impact Example

Query: "a tale of a sea voyage"

**Before boosting:**
- The Odyssey: Rank #17 (book score: 0.539)
- Best passage: Rank #29 globally

**After boosting:**
- The Odyssey: Rank #7 (combined score: 0.5101)
- Passage boost: 0.4906
- Final score: (0.539 * 0.4) + (0.4906 * 0.6) = 0.5101

**Files modified:**
- `invenio-aisearch/services/service/ai_search_service.py`

**Key code:**
```python
# Determine if passages will be used for boosting
should_include_passages = include_passages if include_passages is not None else current_app.config.get('INVENIO_AISEARCH_CHUNKS_ENABLED', False)

# If passages enabled, fetch MORE books initially so we can re-rank based on passage evidence
if should_include_passages:
    initial_book_limit = min(result_limit * 5, max_limit)  # Fetch 5x more books for re-ranking
else:
    initial_book_limit = result_limit

# ... perform searches ...

# Calculate passage boost for each book
passages_by_record = {}
for passage in all_passages:
    record_id = passage['record_id']
    if record_id not in passages_by_record:
        passages_by_record[record_id] = []
    passages_by_record[record_id].append(passage)

passage_boosts = {}
for record_id, record_passages in passages_by_record.items():
    scores = [p['similarity_score'] for p in record_passages]
    max_score = max(scores)
    top3_avg = sum(sorted(scores, reverse=True)[:3]) / min(3, len(scores))
    count_bonus = min(len(scores) * 0.01, 0.1)

    boost = (max_score * 0.5) + (top3_avg * 0.3) + count_bonus
    passage_boosts[record_id] = boost

# Apply passage boost to book scores
for result in results:
    record_id = result['record_id']
    original_score = result['similarity_score']

    if record_id in passage_boosts:
        passage_boost = passage_boosts[record_id]
        boosted_score = (original_score * 0.4) + (passage_boost * 0.6)
        result['boosted_score'] = boosted_score
        result['original_book_score'] = original_score
        result['passage_boost'] = passage_boost
    else:
        result['boosted_score'] = original_score
        result['original_book_score'] = original_score
        result['passage_boost'] = None

# Re-sort results by boosted score
results.sort(key=lambda r: r['boosted_score'], reverse=True)

# Trim to requested limit after re-ranking
results = results[:result_limit]
```

### 5. Passage Allocation Fix

**Problem:** After boosting brought The Odyssey to rank #7, it displayed without passages (while Moby Dick showed 5).

**Root cause:** Passages were selected from global top 20 by score. The Odyssey's best passage ranked #29 globally, so it was excluded.

**Solution:** Ensure each displayed book gets its passages (max 3 per book):
```python
if all_passages_data:
    # Get record IDs of final displayed books
    displayed_record_ids = {r['record_id'] for r in results}

    # For each displayed book, include its top passages (max 3 per book)
    max_passages_per_book = 3
    passages = []

    for record_id in displayed_record_ids:
        if record_id in all_passages_data:
            book_passages = all_passages_data[record_id][:max_passages_per_book]
            passages.extend(book_passages)

    # Sort passages by score for display
    passages.sort(key=lambda p: p['similarity_score'], reverse=True)
    passage_total = len(passages)
```

This ensures:
- Every displayed book gets its passages (if any)
- Capped at 3 passages per book to avoid overwhelming display
- Passages sorted by score within result set

### 6. Performance Optimization

**Problem:** Summary generation was processing all 50 books before filtering down to 10.

**Solution:** Move summary generation to after re-ranking and trimming:
```python
# Trim to requested limit after re-ranking
results = results[:result_limit]

# Generate summaries ONLY for final displayed results (if requested)
if include_summaries and getattr(self.config, 'enable_summaries', True):
    for result in results:
        description = result.pop('_description', '')  # Remove temp field
        if description:
            if len(description) > 500:
                # Generate AI summary for long descriptions
                summary = self.model_manager.generate_summary(description)
                result['summary'] = summary
            else:
                result['summary'] = description
```

**Impact:** Summary generation limited to 10 books instead of 50, significantly reducing response time when summaries enabled.

### 7. UI Toggle for Full-Text Search

**Problem:** Passage search always enabled with no runtime control.

**Solution:** Added checkbox to enable/disable at query time:

**HTML template changes:**
```html
<div class="field">
  <div class="ui checkbox">
    <input type="checkbox" id="include-passages" name="passages" checked>
    <label>Include full-text search</label>
  </div>
</div>
```

**JavaScript changes:**
```javascript
const includePassages = document.getElementById('include-passages').checked;

const params = new URLSearchParams({
  q: query,
  limit: limit,
  summaries: includeSummaries,
  passages: includePassages
});
```

**Schema changes:**
```python
class SearchRequestSchema(MultiDictSchema):
    summaries = fields.Bool(required=False, missing=False)
    passages = fields.Bool(required=False, allow_none=True)  # None = use config default
```

**Critical fix:** Initially the `passages` field was missing from schema, causing URL parameter `passages=false` to be sent as string "false" (truthy in Python). Adding the Boolean field fixed the checkbox.

**Files modified:**
- `invenio-aisearch/templates/invenio_aisearch/search.html`
- `invenio-aisearch/assets/semantic-ui/js/invenio_aisearch/search.js`
- `invenio-aisearch/services/schemas.py`
- `invenio-aisearch/resources/resource/ai_search_resource.py`

### 8. Score Visualization

**Problem:** Users couldn't see how passage boosting affected rankings.

**Solution:** Added colored labels showing score breakdown:

```javascript
// Show boost details if available
if (result.passage_boost !== undefined && result.passage_boost !== null) {
  html += `
    <span class="ui small blue label" title="Original book-level similarity score">
      <i class="book icon"></i>
      Book score: ${result.original_book_score.toFixed(3)}
    </span>
    <span class="ui small teal label" title="Boost from matching passages">
      <i class="arrow up icon"></i>
      Passage boost: ${result.passage_boost.toFixed(3)}
    </span>
    <span class="ui small green label" title="Final combined score">
      <i class="chart line icon"></i>
      Final: ${result.similarity_score.toFixed(3)}
    </span>`;
} else {
  // No boosting - just show single score
  html += `
    <span class="ui small primary label">
      <i class="chart line icon"></i>
      Similarity: ${result.similarity_score.toFixed(3)}
    </span>`;
}
```

**Color scheme:**
- **Blue:** Book-level score (40% weight)
- **Teal:** Passage boost score (60% weight)
- **Green:** Final combined score

### 9. Debug Logging Cleanup

**Problem:** Excessive debug output from passage boosting feature:
```
[2025-11-11 21:45:24,011] DEBUG in ai_search_service: Boosted mqrwp-c0857: 0.5393 -> 0.5101 (passage_boost=0.4906)
```

**Solution:** Removed all debug statements for passage boost feature:
1. ✅ "Passage boost for {record_id}" debug statement (line 244-247)
2. ✅ "Boosted {record_id}: {original_score} -> {boosted_score}" debug statement (line 281-284)
3. ✅ "Filtered to {passage_total} passages" debug statement (line 318-320)

Kept deduplication debug (less noisy, only logs when duplicates found).

## Technical Architecture

### Search Flow with Passage Boosting

```
User Query
    ↓
Parse Request (q, limit, summaries, passages)
    ↓
Determine initial_book_limit
    • if passages: limit * 5 (e.g., 50 for limit=10)
    • else: limit (e.g., 10)
    ↓
Parallel k-NN Searches
    • Book embeddings: ~initial_book_limit results
    • Passage embeddings: 100 results (if enabled)
    ↓
Deduplicate Books
    • Normalize titles (remove subtitles)
    • Match on (title, primary_author)
    • Keep first (highest scoring) instance
    ↓
Aggregate Passage Evidence
    • Group passages by book
    • Calculate boost per book:
      - 50% max passage score
      - 30% top-3 average
      - 20% count bonus (capped at 5 passages)
    ↓
Re-rank Books
    • Combined score = (book_score * 0.4) + (passage_boost * 0.6)
    • Sort by combined score
    • Trim to requested limit
    ↓
Allocate Passages to Displayed Books
    • For each displayed book
    • Include top 3 passages (if any)
    • Sort by passage score
    ↓
Generate Summaries (if requested)
    • Only for final displayed books (≤ limit)
    • Only if description > 500 chars
    ↓
Return SearchResult
    • results: List of books with scores/metadata
    • passages: List of passages grouped by book
    • total: Total books matched
    • passage_total: Total passages returned
```

### Data Structures

**SearchResult Object:**
```python
{
  "query": "a tale of a sea voyage",
  "parsed": {"intent": "find"},
  "total": 142,
  "results": [
    {
      "record_id": "s3xg7-xwt22",
      "title": "The Odyssey",
      "creators": ["Homer"],
      "similarity_score": 0.5101,          # Final combined score
      "original_book_score": 0.5393,       # Book-level score
      "passage_boost": 0.4906,             # Passage aggregation
      "boosted_score": 0.5101,             # Same as similarity_score
      "summary": "Epic poem about...",
      ...
    }
  ],
  "passages": [
    {
      "record_id": "s3xg7-xwt22",
      "title": "The Odyssey",
      "creators": "Homer",
      "text": "Tell me, O muse, of that ingenious hero...",
      "similarity_score": 0.4823,
      "chunk_index": 0,
      "chunk_count": 45,
      "word_count": 352
    }
  ],
  "passage_total": 23
}
```

## Key Files Modified

1. **Service Layer:**
   - `invenio-aisearch/services/service/ai_search_service.py` - Passage boosting, deduplication, performance optimization
   - `invenio-aisearch/services/results.py` - Extended SearchResult with passage fields

2. **Resource Layer:**
   - `invenio-aisearch/resources/resource/ai_search_resource.py` - Added passages parameter passing
   - `invenio-aisearch/services/schemas.py` - Added passages Boolean field

3. **Frontend:**
   - `invenio-aisearch/assets/semantic-ui/js/invenio_aisearch/search.js` - Grouped display, truncation fix, score visualization
   - `invenio-aisearch/templates/invenio_aisearch/search.html` - Added passages checkbox

4. **Configuration:**
   - `v13-ai/invenio.cfg` - `INVENIO_AISEARCH_CHUNKS_ENABLED = True`

## Testing Observations

### Query: "a tale of a sea voyage"

**Before passage boosting:**
- Top result: Moby Dick (high book-level match)
- The Odyssey: Rank #17 (not visible)

**After passage boosting:**
- Top result: Moby Dick (0.6832 combined score, 5 passages)
- The Odyssey: Rank #7 (0.5101 combined score, 3 passages)
- Other sea voyage books promoted: Two Years Before the Mast, etc.

### Query: "scary stories" / "horror books with particular emphasis on fear"

- Frankenstein deduplication working (3 editions → 1 result)
- Edgar Allan Poe collections ranked highly
- Passages showing relevant fear-themed excerpts

### Truncation Testing

- Small chunks (< 2000 chars) displayed in full
- Larger chunks truncated at sentence boundaries
- Transcriber's notes and metadata preserved when part of match

## Lessons Learned

1. **Passage evidence is powerful:** Even when book-level embeddings miss semantic nuances, passage-level search can surface relevant works through specific textual matches.

2. **Deduplication is essential:** Repository datasets often contain multiple editions. Normalized matching prevents duplicate results.

3. **UI matters:** Grouping passages within books creates much better UX than separate sections. Visual hierarchy (book icon, file icon) helps users understand granularity.

4. **Performance trade-offs:** Fetching 5x more books for re-ranking adds cost, but enables intelligent promotion. Limiting summaries to final results mitigates this.

5. **Score transparency builds trust:** Showing book score, passage boost, and final combined score helps users understand why results ranked as they did.

6. **Boolean parameters need schema validation:** URL params like `passages=false` are strings by default. Marshmallow Boolean fields parse correctly.

## Future Enhancements

1. **Configurable boost weights:** Allow tuning the 0.4/0.6 book/passage split via config
2. **Passage context expansion:** Show surrounding text from adjacent chunks
3. **Highlight matched terms:** Mark the specific phrases that drove high passage scores
4. **Query understanding:** Enhanced intent detection (searching vs browsing, topical vs similarity)
5. **Faceting:** Add filters for publication date, resource type, access status
6. **Export/citation:** Allow users to export results with passage citations
7. **Relevance feedback:** Let users mark results as relevant/not to improve ranking

## Related Sessions

- **Session 6:** Speccing full-text search architecture
- **Session 7:** Chunking implementation (passage extraction and indexing)
- **Session 7.5:** Initial hybrid AI search implementation
- **Session 8:** This session (passage boosting and UI refinement)

## Conclusion

This session transformed the basic hybrid search into a production-ready feature with intelligent passage-aware ranking, intuitive UI, and performance optimizations. The passage boosting algorithm successfully promotes books with strong textual evidence, addressing the limitations of pure book-level embeddings. The system now provides a cohesive, transparent, and effective semantic search experience over the repository's full-text content.
