"""
ArduPilot Documentation Initialization Module

Handles automatic scraping and indexing of ArduPilot documentation
during server startup to ensure documentation search is always available.
"""

import logging
import os
import asyncio
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


async def initialize_documentation_system() -> bool:
    """
    Initialize the ArduPilot documentation system.

    This function:
    1. Checks if documentation is already available
    2. Runs scraper if docs are missing or outdated
    3. Runs indexer to build vector embeddings
    4. Verifies the system is working

    Returns:
        bool: True if initialization successful, False otherwise
    """
    logger.info("Initializing ArduPilot documentation system...")

    try:
        # Check if we need to run scraper
        docs_dir = Path("data/docs")
        needs_scraping = await _check_if_scraping_needed(docs_dir)

        if needs_scraping:
            logger.info("Running documentation scraper...")
            success = await _run_scraper()
            if not success:
                logger.error("Documentation scraper failed")
                return False
            logger.info("Documentation scraping completed")
        else:
            logger.info("Documentation files already exist, skipping scraper")

        # Check if we need to run indexer
        needs_indexing = await _check_if_indexing_needed()

        if needs_indexing:
            logger.info("Running documentation indexer...")
            success = await _run_indexer()
            if not success:
                logger.error("Documentation indexer failed")
                return False
            logger.info("Documentation indexing completed")
        else:
            logger.info("Documentation index already exists, skipping indexer")

        # Verify the system is working
        success = await _verify_documentation_system()
        if success:
            logger.info("ArduPilot documentation system initialized successfully")
            return True
        else:
            logger.error("Documentation system verification failed")
            return False

    except Exception as e:
        logger.error(f"Failed to initialize documentation system: {e}", exc_info=True)
        return False


async def _check_if_scraping_needed(docs_dir: Path) -> bool:
    """Check if we need to run the scraper."""
    if not docs_dir.exists():
        return True

    # Check if we have the expected files
    expected_files = [
        "log_messages.md",
        "common-measuring-vibration.md",
        "diagnosing.md",
        "common-imu-batchsampling.md",
        "download_analyze.md",
        "common-raw-imu-logging.md",
        "case-study-turn-rate.md",
        "case-study-fly-by-wire.md",
    ]

    for filename in expected_files:
        if not (docs_dir / filename).exists():
            logger.info(f"Missing documentation file: {filename}")
            return True

    return False


async def _check_if_indexing_needed() -> bool:
    """Check if we need to run the indexer."""
    try:
        from db import get_duckdb_manager

        db_manager = get_duckdb_manager()
        conn = db_manager.get_connection()

        # Check if doc_chunks table exists and has data
        result = conn.execute(
            """
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_name = 'doc_chunks'
        """
        ).fetchone()

        if not result or result[0] == 0:
            logger.info("doc_chunks table does not exist")
            return True

        # Check if table has data
        result = conn.execute("SELECT COUNT(*) as count FROM doc_chunks").fetchone()
        count = result[0] if result else 0

        if count == 0:
            logger.info("doc_chunks table is empty")
            return True

        logger.info(f"Found {count} existing document chunks")
        return False

    except Exception as e:
        logger.warning(f"Error checking indexing status: {e}")
        return True


async def _run_scraper() -> bool:
    """Run the documentation scraper."""
    try:
        # Import and run scraper
        from services.doc_scraper import run_scraper
        from pathlib import Path

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            run_scraper,
            Path("data/docs"),
            0.5,  # Faster delay for startup
        )

        # Check if any URLs failed
        failed_count = sum(1 for success in results.values() if not success)
        if failed_count > 0:
            logger.warning(f"Scraper completed with {failed_count} failures")

        return True

    except Exception as e:
        logger.error(f"Scraper execution failed: {e}", exc_info=True)
        return False


async def _run_indexer() -> bool:
    """Run the documentation indexer."""
    try:
        # Import and run indexer
        from services.doc_indexer import run_index
        from pathlib import Path

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, run_index, Path("data/docs"))

        # Check results
        total_chunks = sum(results.values())
        if total_chunks == 0:
            logger.error("Indexer completed but no chunks were indexed")
            return False

        logger.info(f"Indexer completed: {total_chunks} chunks indexed")
        return True

    except Exception as e:
        logger.error(f"Indexer execution failed: {e}", exc_info=True)
        return False


async def _verify_documentation_system() -> bool:
    """Verify the documentation system is working."""
    try:
        from uuid import uuid4
        from services.doc_tools import ArduDocSearchTool
        from db import get_sqlite_manager, get_duckdb_manager

        # Test the search tool
        tool = ArduDocSearchTool(uuid4(), get_sqlite_manager(), get_duckdb_manager())
        result = await tool._safe_execute(query="vibration levels", k=1)

        if result.success and result.data and len(result.data) > 0:
            logger.info("Documentation system verification passed")
            return True
        else:
            logger.error("Documentation system verification failed - no search results")
            return False

    except Exception as e:
        logger.error(f"Documentation system verification failed: {e}", exc_info=True)
        return False


def get_documentation_status() -> dict:
    """Get current status of the documentation system."""
    try:
        from db import get_duckdb_manager

        db_manager = get_duckdb_manager()
        conn = db_manager.get_connection()

        # Check doc_chunks table
        try:
            result = conn.execute("SELECT COUNT(*) as count FROM doc_chunks").fetchone()
            doc_count = result[0] if result else 0
        except:
            doc_count = 0

        # Check docs directory
        docs_dir = Path("data/docs")
        file_count = len(list(docs_dir.glob("*.md"))) if docs_dir.exists() else 0

        return {
            "docs_directory_exists": docs_dir.exists(),
            "markdown_files": file_count,
            "indexed_chunks": doc_count,
            "system_ready": doc_count > 0,
        }

    except Exception as e:
        logger.error(f"Error getting documentation status: {e}")
        return {"error": str(e), "system_ready": False}
