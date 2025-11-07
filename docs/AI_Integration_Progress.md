# AI Integration with InvenioRDM: Project Progress

**Project**: AI Search over Project Gutenberg Texts in InvenioRDM v13
**Timeline**: Started October 2025
**Presentation**: < 1 month from start date

## Executive Summary

This document outlines the approach, methodology, and progress of integrating AI-powered search capabilities into an InvenioRDM repository instance, specifically for searching Project Gutenberg texts using natural language queries and AI-generated summaries.

---

## Project Goals

The project has three main objectives:

1. **Automate Gutenberg Text Ingestion**: Download and ingest Project Gutenberg texts, fully uploading them to the InvenioRDM instance with proper metadata

2. **Add AI Search Interface**: Implement an AI-enhanced search interface to InvenioRDM that supports:
   - Natural language queries (e.g., "get me 3 books with female protagonists")
   - AI-generated summaries of search results

3. **Full-Text Search**: Demonstrate full-text search capabilities, including any necessary additional indexing beyond standard InvenioRDM metadata search

---

## Methodology: AI-Assisted Development Approach

### Conversation-Driven Development

The development process followed a structured dialogue with AI (Claude Code) using these key steps:

#### 1. **Context Setting**
- Created `CLAUDE.md` to provide the AI with comprehensive project context
- Documented InvenioRDM architecture, commands, and workflows
- Established technical stack (Python 3.12, PostgreSQL, OpenSearch 2, Docker)

#### 2. **Goal Clarification**
Started with high-level goals, then refined through questions:
- **Q**: Scale? **A**: Small sample (100 texts) for testing
- **Q**: AI features? **A**: Natural language queries + summaries
- **Q**: AI backend? **A**: HuggingFace models (local, open-source)

#### 3. **Research Phase**
AI agent performed autonomous research on:
- Project Gutenberg download methods (Gutendex API, metadata formats)
- Best practices for bulk text downloads
- Available metadata fields and structures

#### 4. **Iterative Development**
- Task breakdown using todo tracking
- Code generation with built-in best practices
- Testing with small samples before full-scale deployment

---

## Technical Plan

### Phase 1: Data Acquisition & Ingestion

**Goal**: Download 100 Gutenberg texts and upload to InvenioRDM

**Approach**:
1. Use **Gutendex API** (https://gutendex.com) for metadata
   - Free JSON REST API
   - Rich metadata: title, authors, subjects, bookshelves, summaries, language
   - No authentication required

2. Download plain text UTF-8 format from Project Gutenberg
   - Pattern: `https://www.gutenberg.org/files/{id}/{id}-0.txt`
   - Strip legal headers/footers automatically

3. Create InvenioRDM records via REST API
   - Map Gutenberg metadata to InvenioRDM schema
   - Upload full text files to each record
   - Publish records

### Phase 2: AI-Powered Search

**Goal**: Enable natural language search and AI summaries

**Technology Stack**:
- **Embeddings**: `sentence-transformers` (semantic search)
- **NLU**: `facebook/bart-large-mnli` (query understanding)
- **Summaries**: `facebook/bart-large-cnn` (text summarization)
- All models from HuggingFace (local, no API costs)

**Components**:
1. **Semantic Indexing**
   - Generate embeddings for book content
   - Store embeddings in OpenSearch with dense vector support
   - Enable hybrid search (keyword + semantic)

2. **Natural Language Query Parser**
   - Parse user queries like "books with female protagonists"
   - Extract intent and entities
   - Translate to structured search queries

3. **Summary Generation**
   - Generate AI summaries of search results
   - Display context-aware excerpts

### Phase 3: Full-Text Indexing

**Goal**: Index complete book text for content-based search

**Approach**:
1. Configure OpenSearch to index file contents (not just metadata)
2. Extract and index full text from uploaded files
3. Enable search across book content
4. Combine with metadata search for comprehensive results

---

## Code Written So Far

### 1. Project Documentation (`CLAUDE.md`)

**Purpose**: Provide AI context about the InvenioRDM project

**Contents**:
- Development commands (containers, services, assets)
- Architecture overview (directory structure, configuration system)
- Extension points (blueprints, webpack, templates)
- Common workflows for customization
- Important notes (SSL, secrets, database format)

**Location**: `/CLAUDE.md`

---

### 2. Gutenberg Download Script (`scripts/gutenberg/download_books.py`)

**Purpose**: Automated download of Project Gutenberg books with metadata

**Features**:
- Fetches book metadata from Gutendex API
- Downloads plain text UTF-8 content
- Automatically strips Project Gutenberg legal headers/footers
- Saves books and metadata in organized structure
- Rate limiting (2-second delay) for respectful API usage
- Error handling and progress reporting
- Command-line interface with configurable options

**Key Components**:

```python
class GutenbergDownloader:
    - fetch_metadata(num_books, language)
    - download_book_text(book_id)
    - strip_gutenberg_headers(text)
    - save_book(book_metadata, book_text)
    - download_all(num_books, language)
```

**Usage**:
```bash
python3 scripts/gutenberg/download_books.py -n 100 -o gutenberg_data
```

**Output Structure**:
```
gutenberg_data/
├── books/               # Plain text files
│   ├── 84_Frankenstein;_Or,_The_Modern_Prometheus.txt
│   ├── 2701_Moby_Dick;_Or,_The_Whale.txt
│   └── ...
├── metadata/            # Individual JSON metadata files
│   ├── 84_Frankenstein;_Or,_The_Modern_Prometheus.json
│   └── ...
└── all_books_metadata.json  # Master metadata file
```

**Metadata Captured**:
- Book ID
- Title
- Authors (name, birth year, death year)
- Subjects (genre classifications)
- Bookshelves (categories)
- Languages
- Formats available
- Download count (popularity metric)
- AI-generated summaries (from Gutendex)

**Testing**:
- ✅ Successfully tested with 3 books
- ✅ Downloaded: Frankenstein, Moby Dick, Romeo and Juliet
- ✅ Metadata richness verified (subjects, authors, summaries)
- ✅ Headers/footers successfully stripped

**Location**: `/scripts/gutenberg/download_books.py`

---

## Progress Status

### ✅ Completed Tasks

1. ✅ Created comprehensive project documentation (CLAUDE.md)
2. ✅ Researched Project Gutenberg download methods
3. ✅ Implemented Gutenberg download script with Gutendex API
4. ✅ Tested download script with sample books
5. ✅ Verified metadata quality and structure

### 🔄 In Progress

- Research InvenioRDM records REST API and authentication

### 📋 Pending Tasks

1. Design InvenioRDM record schema for Gutenberg books
2. Implement bulk upload script for Gutenberg texts to InvenioRDM
3. Set up HuggingFace models for embeddings and NLP
4. Implement full-text indexing with embeddings in OpenSearch
5. Create natural language query parser using HuggingFace
6. Implement AI-powered summary generation for search results
7. Build custom search UI with AI features
8. Test natural language queries like "books with female protagonists"

---

## Technical Decisions & Rationale

### Why Gutendex API?
- **Simple**: JSON REST API, no authentication
- **Rich metadata**: Subjects, authors, summaries, categories
- **Reliable**: Well-maintained, free community project
- **Efficient**: Pagination support, language filtering built-in

### Why HuggingFace Models?
- **Local deployment**: No API costs, data privacy
- **Open source**: Transparent, reproducible
- **Proven models**: sentence-transformers, BART widely used
- **Python ecosystem**: Easy integration with InvenioRDM

### Why 100 Books?
- **Proof of concept**: Large enough to demonstrate AI capabilities
- **Manageable**: Quick downloads (~5-10 minutes with rate limiting)
- **Testable**: Small enough for rapid iteration
- **Scalable**: Architecture designed to handle 10,000+ books later

---

## Next Steps

### Immediate (Week 1-2)
1. Complete InvenioRDM API research
2. Implement upload script
3. Successfully ingest 100 books into InvenioRDM

### Short-term (Week 2-3)
1. Set up HuggingFace model pipeline
2. Implement basic semantic search
3. Create natural language query parser

### Final (Week 3-4)
1. Build custom search UI
2. Integrate AI summaries
3. Test and refine natural language queries
4. Prepare demo and presentation materials

---

## Demo Scenarios

### Planned Demonstrations

1. **Natural Language Query**
   - Query: "Find me 3 books with female protagonists"
   - Expected: Search interprets intent, filters by protagonist gender
   - Shows: NLP understanding, semantic search

2. **Thematic Search**
   - Query: "Books about adventure and exploration"
   - Expected: Semantic search finds relevant books beyond keyword matching
   - Shows: Embedding-based similarity search

3. **AI Summary**
   - Action: Display search results with AI-generated summaries
   - Expected: Concise, relevant summaries for each result
   - Shows: LLM integration for text summarization

---

## Repository Structure

```
v13-ai/
├── CLAUDE.md                    # AI context documentation
├── docs/                        # Project documentation
│   └── AI_Integration_Progress.md
├── scripts/
│   └── gutenberg/
│       └── download_books.py    # Gutenberg download automation
├── site/v13_ai/                 # Custom Python package
│   ├── views.py                 # Flask blueprints (future: AI search endpoint)
│   ├── webpack.py               # Frontend bundles
│   ├── assets/                  # Custom JS/CSS
│   └── templates/               # Jinja2 templates
├── invenio.cfg                  # Main configuration
├── docker-compose.yml           # Services (DB, OpenSearch, Redis, RabbitMQ)
└── ...
```

---

## Key Takeaways for Presentation

### AI-Assisted Development Process

1. **Context is King**: Providing comprehensive project documentation (CLAUDE.md) enabled the AI to understand the specific InvenioRDM environment and make informed decisions

2. **Iterative Refinement**: Starting with broad goals and refining through Q&A led to a focused, achievable scope

3. **Autonomous Research**: AI agent independently researched technical solutions (Gutendex API, HuggingFace models), saving hours of manual research

4. **Best Practices Built-In**: Generated code included:
   - Error handling
   - Rate limiting
   - Progress reporting
   - Clean code structure
   - Command-line interfaces

5. **Testing First**: Small-scale testing (3 books) before full deployment (100 books) reduced risk

### Integrating AI into Existing Systems

1. **Leverage Existing Tools**: Used InvenioRDM's extension points rather than forking
2. **Open Source AI**: HuggingFace models provide free, transparent, local deployment
3. **Hybrid Approach**: Combining keyword search (existing) with semantic search (new) for best results
4. **Incremental Enhancement**: Adding AI features without disrupting existing functionality

---

## Resources & References

- **InvenioRDM Documentation**: https://inveniordm.docs.cern.ch/
- **Gutendex API**: https://gutendex.com
- **Project Gutenberg**: https://www.gutenberg.org
- **HuggingFace**: https://huggingface.co
- **sentence-transformers**: https://www.sbert.net
- **OpenSearch Vector Search**: https://opensearch.org/docs/latest/search-plugins/knn/

---

## Presentation Outline Suggestions

### Title Ideas
- "AI-Assisted Development: Building AI Search for InvenioRDM"
- "Integrating AI Search into InvenioRDM Using AI Development Tools"
- "From Conversation to Code: AI-Powered Repository Search"

### Suggested Structure

1. **Introduction** (5 min)
   - Repository management challenges
   - The promise of AI-enhanced search
   - Project goals

2. **Methodology** (10 min)
   - AI-assisted development process
   - The role of Claude Code
   - Context documentation (CLAUDE.md)
   - Iterative refinement through dialogue

3. **Technical Implementation** (15 min)
   - Architecture overview
   - Gutenberg text acquisition
   - HuggingFace models for NLP
   - Semantic search with embeddings
   - Natural language query parsing

4. **Live Demo** (10 min)
   - Natural language search
   - AI-generated summaries
   - Full-text content search

5. **Results & Learnings** (10 min)
   - What worked well
   - Challenges encountered
   - Best practices discovered
   - Future directions

6. **Q&A** (10 min)

---

## Contact

**Project**: v13-ai InvenioRDM Instance
**Organization**: Cottage Labs
**Site**: https://invenio-ai.cottagelabs.com
**Documentation**: This repository

---

*Last Updated*: October 19, 2025
*Status*: In Progress - Phase 1 Complete (Data Acquisition)
