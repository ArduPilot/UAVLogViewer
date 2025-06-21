from __future__ import annotations

"""Documentation Retrieval Tools for ArduPilot docs.

This module provides LLM-callable tools that query the vector index
(`doc_chunks` table) built by ``services.doc_indexer``.
"""

import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from services.tool_registry import BaseTool
from services.types import ToolResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model Singleton helpers
# ---------------------------------------------------------------------------

_MODEL: Optional[SentenceTransformer] = None
_MODEL_NAME = "all-MiniLM-L6-v2"


def _get_model() -> SentenceTransformer:
    """Load SBERT model once per process."""
    global _MODEL
    if _MODEL is None:
        logger.info(
            "Loading sentence-transformer model '%s' for doc search", _MODEL_NAME
        )
        _MODEL = SentenceTransformer(_MODEL_NAME)
    return _MODEL


class ArduDocSearchTool(BaseTool):
    """Semantic search over embedded ArduPilot documentation chunks."""

    # ------------------------------------------------------------------
    # Mandatory metadata for function-calling
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:  # noqa: D401 – simple property
        return "search_ardu_doc"

    @property
    def description(self) -> str:
        return (
            "Semantic search in the subset of ArduPilot documentation that has been "
            "embedded locally (log-message legend, vibration analysis, case studies). "
            "Useful for looking up meanings of log messages or troubleshooting tips. "
            "NOTE: Coverage is limited; not every topic/problem is documented."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language search query (e.g. 'What is NKF0?').",
                },
                "k": {
                    "type": "integer",
                    "description": "Number of results to return (1-10).",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 10,
                },
            },
            "required": ["query"],
        }

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(
        self, query: str, k: int = 3, **kwargs
    ) -> ToolResult:  # noqa: D401 – async signature mandated
        """Perform semantic search and return top-k doc chunks."""
        # Guardrails – enforce bounds even if schema missed
        k = max(1, min(10, k))

        try:
            model = _get_model()

            # Embed query in background thread to avoid blocking event-loop
            loop = asyncio.get_running_loop()
            query_vec: np.ndarray = await loop.run_in_executor(
                None, lambda: model.encode(query, convert_to_numpy=True)
            )

            conn = self.duckdb_manager.get_connection()

            rows = conn.execute(
                """
                SELECT heading,
                       text,
                       source,
                       embedding <-> ? AS score
                FROM doc_chunks
                ORDER BY score ASC
                LIMIT ?
                """,
                [query_vec.tolist(), k],
            ).fetchall()

            if not rows:
                return ToolResult(
                    tool_name=self.name,
                    call_id=None,
                    success=False,
                    data=None,
                    metadata={"reason": "no_results"},
                    execution_time=0.0,
                    error_message="No documentation chunks matched the query.",
                )

            # Build response
            results: List[Dict[str, Any]] = []
            scores: List[float] = []
            for heading, text, source, score in rows:
                results.append(
                    {
                        "heading": heading,
                        "snippet": (text[:300] + ("…" if len(text) > 300 else "")),
                        "url": source,
                    }
                )
                scores.append(float(score))

            metadata = {"k": k, "scores": scores}

            return ToolResult(
                tool_name=self.name,
                call_id=None,
                success=True,
                data=results,
                metadata=metadata,
                execution_time=0.0,  # filled by _safe_execute wrapper
            )

        except Exception as e:
            logger.exception("ArduDocSearchTool failed: %s", e)
            raise
