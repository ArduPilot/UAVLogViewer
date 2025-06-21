"""
ArduPilot Documentation Indexer

Vectorizes markdown documentation and stores in DuckDB with embeddings
for semantic search and retrieval.

Usage:
    from backend.services.doc_indexer_fixed import run_index
    run_index()
"""

import hashlib
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from db import get_duckdb_manager

logger = logging.getLogger(__name__)


class DocIndexer:
    """Document indexer for ArduPilot documentation."""

    def __init__(self, docs_dir: Path = None, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the document indexer.

        Args:
            docs_dir: Directory containing markdown files
            model_name: Name of sentence transformer model to use
        """
        self.docs_dir = docs_dir or Path("data/docs")
        self.model_name = model_name
        self.duckdb_manager = get_duckdb_manager()
        self._model = None

    def _load_model(self) -> SentenceTransformer:
        """Load sentence transformer model (cached)."""
        if self._model is None:
            logger.info(f"Loading sentence transformer model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _setup_database(self) -> None:
        """Setup DuckDB with VSS extension and doc_chunks table."""
        conn = self.duckdb_manager.get_connection()

        try:
            # Install and load VSS extension (idempotent)
            conn.execute("INSTALL vss")
            conn.execute("LOAD vss")
            logger.debug("VSS extension loaded")

            # Create doc_chunks table with FLOAT array for embeddings
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS doc_chunks (
                    id INTEGER,
                    content_hash VARCHAR UNIQUE,
                    source VARCHAR NOT NULL,
                    heading VARCHAR,
                    text VARCHAR NOT NULL,
                    embedding FLOAT[384]
                )
            """
            )

            logger.info("Database schema initialized")

        except Exception as e:
            logger.error(f"Failed to setup database: {e}")
            raise

    def _extract_source_url(self, markdown_content: str) -> Optional[str]:
        """Extract source URL from markdown header."""
        # Look for **Source:** [url](url) pattern
        source_match = re.search(
            r"\*\*Source:\*\*\s*\[([^\]]+)\]\(([^)]+)\)", markdown_content
        )
        if source_match:
            return source_match.group(2)
        return None

    def _split_into_chunks(
        self, markdown_content: str, source_url: str
    ) -> List[Dict[str, str]]:
        """
        Split markdown content into semantic chunks.

        Args:
            markdown_content: Raw markdown text
            source_url: Original source URL

        Returns:
            List of chunk dictionaries with source, heading, and text
        """
        chunks = []

        # Split by headings (# ## ###)
        sections = re.split(r"\n(#{1,3})\s+(.+?)(?:\n|$)", markdown_content)

        current_heading = None
        current_text = ""

        for i, section in enumerate(sections):
            if i == 0:
                # Content before first heading
                if section.strip():
                    # Extract title from first line if it's a heading
                    lines = section.strip().split("\n")
                    if lines[0].startswith("#"):
                        current_heading = lines[0].replace("#", "").strip()
                        current_text = "\n".join(lines[1:]).strip()
                    else:
                        current_heading = "Introduction"
                        current_text = section.strip()
                continue

            if section.startswith("#"):
                # Save previous chunk if we have content
                if current_text.strip():
                    chunks.append(
                        {
                            "source": source_url,
                            "heading": current_heading or "Unknown",
                            "text": current_text.strip(),
                        }
                    )

                # Start new heading
                if i + 1 < len(sections):
                    current_heading = sections[i + 1].strip()
                    current_text = ""
                    # Skip the heading text in next iteration
                    continue
            else:
                # Accumulate text content
                current_text += section

        # Don't forget the last chunk
        if current_text.strip():
            chunks.append(
                {
                    "source": source_url,
                    "heading": current_heading or "Unknown",
                    "text": current_text.strip(),
                }
            )

        # Filter out very short chunks (less than 50 characters)
        chunks = [chunk for chunk in chunks if len(chunk["text"]) >= 50]

        return chunks

    def _compute_content_hash(self, heading: str, text: str) -> str:
        """Compute MD5 hash of heading + text for deduplication."""
        content = f"{heading}||{text}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _chunk_exists(self, content_hash: str) -> bool:
        """Check if chunk already exists in database."""
        conn = self.duckdb_manager.get_connection()
        result = conn.execute(
            "SELECT COUNT(*) FROM doc_chunks WHERE content_hash = ?", [content_hash]
        ).fetchone()
        return result[0] > 0

    def _get_next_id(self) -> int:
        """Get next available ID for the table."""
        conn = self.duckdb_manager.get_connection()
        result = conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM doc_chunks"
        ).fetchone()
        return result[0]

    def _insert_chunk(self, chunk: Dict[str, str], embedding: np.ndarray) -> None:
        """Insert chunk with embedding into database."""
        conn = self.duckdb_manager.get_connection()

        content_hash = self._compute_content_hash(chunk["heading"], chunk["text"])

        # Skip if already exists
        if self._chunk_exists(content_hash):
            logger.debug(f"Skipping existing chunk: {chunk['heading'][:50]}...")
            return

        try:
            # Get next ID manually
            next_id = self._get_next_id()

            conn.execute(
                """
                INSERT INTO doc_chunks (id, content_hash, source, heading, text, embedding)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                [
                    next_id,
                    content_hash,
                    chunk["source"],
                    chunk["heading"],
                    chunk["text"],
                    embedding.tolist(),  # Convert numpy array to list for FLOAT array
                ],
            )
            logger.debug(f"Inserted chunk: {chunk['heading'][:50]}...")

        except Exception as e:
            logger.error(f"Failed to insert chunk '{chunk['heading']}': {e}")
            raise

    def index_file(self, markdown_file: Path) -> int:
        """
        Index a single markdown file.

        Args:
            markdown_file: Path to markdown file

        Returns:
            Number of chunks indexed
        """
        if not markdown_file.exists():
            logger.warning(f"File not found: {markdown_file}")
            return 0

        logger.info(f"Indexing file: {markdown_file}")

        # Read markdown content
        try:
            content = markdown_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read {markdown_file}: {e}")
            return 0

        # Extract source URL
        source_url = self._extract_source_url(content)
        if not source_url:
            logger.warning(f"No source URL found in {markdown_file}")
            source_url = f"file://{markdown_file}"

        # Split into chunks
        chunks = self._split_into_chunks(content, source_url)
        if not chunks:
            logger.warning(f"No chunks extracted from {markdown_file}")
            return 0

        logger.info(f"Extracted {len(chunks)} chunks from {markdown_file}")

        # Load model and compute embeddings
        model = self._load_model()

        indexed_count = 0
        for chunk in chunks:
            # Compute embedding
            text_to_embed = f"{chunk['heading']}\n{chunk['text']}"
            embedding = model.encode(text_to_embed, convert_to_numpy=True)

            # Insert into database
            try:
                self._insert_chunk(chunk, embedding)
                indexed_count += 1
            except Exception as e:
                logger.error(f"Failed to index chunk from {markdown_file}: {e}")
                continue

        logger.info(
            f"Indexed {indexed_count}/{len(chunks)} chunks from {markdown_file}"
        )
        return indexed_count

    def index_all(self) -> Dict[str, int]:
        """
        Index all markdown files in docs directory.

        Returns:
            Dictionary mapping filenames to number of chunks indexed
        """
        if not self.docs_dir.exists():
            logger.error(f"Docs directory not found: {self.docs_dir}")
            return {}

        # Setup database
        self._setup_database()

        # Find all markdown files
        markdown_files = list(self.docs_dir.glob("*.md"))
        if not markdown_files:
            logger.warning(f"No markdown files found in {self.docs_dir}")
            return {}

        logger.info(f"Found {len(markdown_files)} markdown files to index")

        results = {}
        total_chunks = 0

        for md_file in markdown_files:
            try:
                chunk_count = self.index_file(md_file)
                results[md_file.name] = chunk_count
                total_chunks += chunk_count
            except Exception as e:
                logger.error(f"Failed to index {md_file}: {e}")
                results[md_file.name] = 0

        logger.info(f"Indexing complete: {total_chunks} total chunks indexed")
        return results

    def get_stats(self) -> Dict[str, int]:
        """Get indexing statistics."""
        conn = self.duckdb_manager.get_connection()

        try:
            # Total chunks
            total_result = conn.execute("SELECT COUNT(*) FROM doc_chunks").fetchone()
            total_chunks = total_result[0] if total_result else 0

            # Unique sources
            sources_result = conn.execute(
                "SELECT COUNT(DISTINCT source) FROM doc_chunks"
            ).fetchone()
            unique_sources = sources_result[0] if sources_result else 0

            return {"total_chunks": total_chunks, "unique_sources": unique_sources}
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"total_chunks": 0, "unique_sources": 0}


def run_index(docs_dir: Path = None) -> Dict[str, int]:
    """
    Convenience function to run indexing.

    Args:
        docs_dir: Directory containing markdown files

    Returns:
        Dictionary mapping filenames to number of chunks indexed
    """
    indexer = DocIndexer(docs_dir)
    return indexer.index_all()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Index ArduPilot documentation for vector search"
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("data/docs"),
        help="Directory containing markdown files (default: data/docs)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run indexing
    results = run_index(docs_dir=args.docs_dir)

    # Print results
    print(f"\nIndexing Results:")
    print(f"================")
    for filename, count in results.items():
        print(f"{filename}: {count} chunks")

    # Get stats
    indexer = DocIndexer(docs_dir=args.docs_dir)
    stats = indexer.get_stats()
    print(f"\nTotal chunks: {stats['total_chunks']}")
    print(f"Unique sources: {stats['unique_sources']}")


if __name__ == "__main__":
    main()
