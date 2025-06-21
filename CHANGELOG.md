## [0.6.0] – 2025-06-21

### ✨ New Features
* Semantic documentation search: ArduPilot docs are embedded into DuckDB and exposed via the new `search_ardu_doc` LLM tool.

### 🤖 LLM Workflow Improvements
* Chat orchestrator automatically surfaces `search_ardu_doc` when user queries match troubleshooting keywords.

### 🏗️ Infrastructure
* Automatic creation of `doc_chunks` table and loading of the DuckDB VSS extension at application start-up.
* Utility scripts `doc_scraper.py`, `doc_indexer.py`, and `doc_initialization.py` for scraping, embedding, and loading docs.

### 📝 Developer Notes
* Requires DuckDB ≥ 0.9 with the `vss` extension available.
* After pulling, run `python -m backend.services.doc_initialization` to (re)index documentation. 