# AI Search Implementation Summary

**Project:** v13-ai InvenioRDM AI Search Integration
**Timeline:** 1 week development sprint
**Date:** November 2025

---

## Executive Summary

Successfully implemented AI-powered semantic search over Project Gutenberg texts in InvenioRDM, combining natural language query parsing, vector embeddings, and hybrid search scoring. The system demonstrates intelligent book discovery using meaning rather than just keywords.

---

## Project Goals

1. **Automate Gutenberg text ingestion** - Download and upload 100 books to InvenioRDM
2. **Add AI search interface** - Natural language queries like "show me 3 books with female protagonists"
3. **Demonstrate full-text capabilities** - Semantic search understanding content meaning

---

## Technical Approach

### Architecture Stack

- **Embedding Model:** sentence-transformers/all-MiniLM-L6-v2 (384-dim vectors, ~90MB)
- **Classification Model:** facebook/bart-large-mnli (~1.6GB)
- **Summarization Model:** facebook/bart-large-cnn (~1.6GB)
- **Search Strategy:** Hybrid scoring (70% semantic + 30% metadata)
- **Data Source:** Gutendex API for metadata, Project Gutenberg for texts

### Key Components

1. **Natural Language Parser** (`query_parser.py`)
   - Extracts intent, limits, attributes from queries
   - Maps patterns to metadata search terms
   - Example: "show me 3 books with female protagonists" → limit=3, attributes=['female_protagonist']

2. **Embedding Generation** (`generate_embeddings.py`)
   - Creates 384-dimensional vectors from book metadata
   - Combines title, description, subjects
   - Generated embeddings for 92 books (1.0 MB JSON)

3. **Semantic Search** (`demo_search.py`)
   - Cosine similarity between query and book embeddings
   - Hybrid scoring combining semantic + metadata matching
   - Configurable result limits and ranking weights

---

## Implementation Progress

### Phase 1: Data Acquisition ✅
- **Download Script:** `scripts/gutenberg/download_books.py`
  - Successfully downloaded 89/100 books (11 unavailable)
  - Rate limiting, header stripping, organized structure

- **Upload Script:** `scripts/gutenberg/upload_to_invenio.py`
  - Created 92 records in InvenioRDM (3 test + 89 new)
  - Draft → file upload → publish workflow
  - 100% success rate with proper metadata mapping

### Phase 2: AI Models Setup ✅
- **Model Management:** `invenio-aisearch/invenio_aisearch/models.py`
  - Lazy loading of 3 HuggingFace models
  - Cached to ~/.cache/invenio_aisearch (~3.3GB)
  - Successfully tested all models

### Phase 3: Natural Language Processing ✅
- **Query Parser:** `invenio-aisearch/invenio_aisearch/query_parser.py`
  - 9 attribute patterns (female_protagonist, genre_romance, theme_war, etc.)
  - Intent detection (search, count, list)
  - Limit extraction (numeric and word forms)

### Phase 4: Embeddings & Search ✅
- **Embedding Generator:** Successfully created embeddings for all 92 books
- **Demo Scripts:**
  - `demo_embeddings.py` - Educational explanation of how embeddings work
  - `demo_search.py` - Full search pipeline demonstration

---

## Demo Results

### Query 1: "show me 3 books with female protagonists"
**Results:**
1. Little Women (similarity: 0.486, hybrid: 0.415)
2. Little Women; Or, Meg, Jo, Beth, and Amy (0.454, 0.393)
3. Cranford (0.405, 0.284)

**Analysis:** Strong semantic understanding - found the classic novel about four sisters without needing explicit metadata tags.

### Query 2: "find me 5 books about social injustice"
**Results:**
1. Leviathan (0.386)
2. Narrative of the Life of Frederick Douglass (0.376)
3. The Souls of Black Folk (0.368)
4. Crime and Punishment (0.360)
5. Second Treatise of Government (0.357)

**Analysis:** Purely semantic matching - found relevant books on inequality, slavery, and social philosophy without those exact keywords.

### Query 3: "get me adventure stories"
**Results:**
1. Alice's Adventures in Wonderland (hybrid: 0.596, metadata: 1.0)
2. The Adventures of Tom Sawyer (0.577, 1.0)
3. The Adventures of Roderick Random (0.562, 1.0)
4. Adventures of Huckleberry Finn (0.559, 1.0)
5. The Adventures of Sherlock Holmes (0.524, 1.0)

**Analysis:** Perfect hybrid scoring - books with "adventure" in title got metadata boost, ranked above semantic-only matches like "Grimms' Fairy Tales".

---

## Key Technical Insights

### How Embeddings Work
- **Representation:** 384 numbers capture semantic meaning of text
- **Example:** Don Quixote → [0.0445, 0.0500, -0.0229, -0.0490, -0.0609, ...]
- **Similarity:** Books with similar themes cluster in vector space
  - Pride and Prejudice ↔ Sense and Sensibility: 0.571 similarity
  - Jane Eyre: 0.435, Wuthering Heights: 0.424

### Similarity Score Interpretation
- **>0.7** - Very similar (same genre/themes)
- **>0.5** - Related (similar elements)
- **>0.3** - Some connection
- **<0.3** - Different topics

### Semantic vs Keyword Search
**Query:** "stories of personal transformation"
- **Keyword search:** 0 matches (word "transformation" not in titles)
- **Semantic search:** Found Metamorphosis (0.383), Rip Van Winkle (0.369)

---

## Architecture Decisions

### Why Hybrid Search?
Combined approach leverages both:
- **Semantic search** - Understands meaning and concepts
- **Metadata filtering** - Uses existing InvenioRDM subjects
- **Configurable weights** - Adjustable 70/30 split

### Why These Models?
- **all-MiniLM-L6-v2** - Fast, small, good accuracy for general text
- **BART models** - Production-ready, well-documented, CPU-friendly
- **One-week constraint** - Prioritized proven models over custom training

### Why NL Parser + Semantic?
- User feedback: "I think we do need to go for NL parsing, semantic search will give us a fallback"
- Parser extracts structure (limits, intent)
- Semantic provides intelligent ranking
- Metadata provides precision when available

---

## Code Files Created

### Documentation
- `CLAUDE.md` - Project context for AI sessions
- `docs/AI_Integration_Progress.md` - Progress tracking
- `docs/Key_Conversation_Moments.md` - Methodology documentation
- `invenio-aisearch/ARCHITECTURE.md` - Technical architecture

### Data Scripts
- `scripts/gutenberg/download_books.py` - Gutenberg download automation
- `scripts/gutenberg/upload_to_invenio.py` - InvenioRDM bulk upload
- `scripts/gutenberg/setup_user.sh` - API authentication setup

### AI Module (invenio-aisearch)
- `invenio_aisearch/models.py` - AI model management (158 lines)
- `invenio_aisearch/query_parser.py` - NL query parser (233 lines)
- `scripts/setup_models.py` - Model download/testing

### Demo Scripts
- `scripts/gutenberg/generate_embeddings.py` - Embedding generation (238 lines)
- `scripts/gutenberg/demo_embeddings.py` - Educational demo (213 lines)
- `scripts/gutenberg/demo_search.py` - Full search demo (284 lines)

---

## Challenges Overcome

1. **Email validation** - InvenioRDM required .org/.com TLD, not localhost
2. **Pipenv conflicts** - Bypassed with direct pip installation of AI packages
3. **Port configuration** - Clarified dev server uses port 5000
4. **Module imports** - Used importlib for standalone demo scripts

---

## Next Steps

### Phase 5: API Integration (Pending)
- Create REST endpoint in invenio-aisearch
- Integrate with InvenioRDM search API
- Add authentication and rate limiting

### Phase 6: UI Development (Pending)
- Minimal search interface for demo
- Real-time query suggestions
- Result highlighting and summaries

### Future Enhancements
- Full-text indexing from book content files
- AI-generated summaries from actual text (not just metadata)
- User feedback loop for result relevance
- Query expansion and synonym handling
- Multi-language support

---

## Metrics & Performance

- **Books ingested:** 92 records
- **Embeddings generated:** 92 embeddings (1.0 MB)
- **Model size:** 3.3 GB total (cached locally)
- **Search latency:** ~2-3 seconds including model loading
- **Success rate:** 100% for uploads, 89% for downloads

---

## Demo Presentation Points

1. **Show the problem:** "How do I find books about social injustice without that exact phrase?"

2. **Traditional keyword search fails:**
   - Searches for exact words
   - Misses synonyms and related concepts
   - Can't understand meaning

3. **Demonstrate semantic search:**
   - Run: "show me 3 books with female protagonists"
   - Result: Little Women - perfect match!
   - Explain: AI understood "female protagonist" = stories about women

4. **Show hybrid advantage:**
   - Query: "adventure stories"
   - Books with "adventure" in title ranked higher
   - But also found Grimms' Fairy Tales (semantic match)

5. **Explain the technology:**
   - Show embedding visualization (384 numbers)
   - Explain cosine similarity
   - Demonstrate with demo_embeddings.py

6. **Live demo:** Use demo_search.py with custom queries from audience

---

## Conclusion

Successfully demonstrated that AI-powered semantic search can significantly improve discovery in digital libraries. The hybrid approach combines the precision of metadata with the flexibility of semantic understanding, enabling natural language queries that would be impossible with traditional keyword search.

**Key Achievement:** Within one week, built a working prototype that understands "show me 3 books with female protagonists" and returns Little Women - demonstrating genuine semantic comprehension.

---

## References

- **InvenioRDM:** https://inveniosoftware.org/products/rdm/
- **Project Gutenberg:** https://www.gutenberg.org/
- **Gutendex API:** https://gutendex.com/
- **Sentence Transformers:** https://www.sbert.net/
- **HuggingFace Transformers:** https://huggingface.co/transformers/

---

*This document summarizes the AI-assisted development process and serves as presentation material for demonstrating AI search capabilities in InvenioRDM.*
