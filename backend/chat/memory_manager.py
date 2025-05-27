from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain.embeddings.base import Embeddings
from langchain.memory import (
    CombinedMemory,
    ConversationBufferWindowMemory,
    ConversationEntityMemory,
    VectorStoreRetrieverMemory,
)
from langchain_core.messages import ToolMessage, SystemMessage
from langchain.retrievers import TimeWeightedVectorStoreRetriever
from langchain.schema import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# ──────────────────────────────────────────────────────────
# Initialisation & helpers
# ──────────────────────────────────────────────────────────
load_dotenv()
logger = logging.getLogger(__name__)


def _importance(msg: str, meta: Dict[str, Any]) -> float:
    """Simple heuristic → higher score keeps docs ‘hot’ for longer."""
    score = 1.0
    w = len(msg.split())
    if w > 100:
        score *= 1.4
    elif w > 50:
        score *= 1.2
    if meta.get("is_critical"):
        score *= 1.5
    if meta.get("role") == "user":
        score *= 1.3
    return max(0.5, min(score, 2.0))


# ──────────────────────────────────────────────────────────
# Memory manager
# ──────────────────────────────────────────────────────────
class EnhancedMemoryManager:
    """
    LangChain-native hybrid memory for agentic chatbots:

    • ConversationBufferWindowMemory  (last 8 messages verbatim)
    • VectorStoreRetrieverMemory      (FAISS HNSW, time-weighted)
    • ConversationEntityMemory        (optional entity tracking)
    """

    SHORT_WINDOW = 8        # last N messages kept verbatim
    LONG_K       = 5        # max docs retrieved from FAISS

    def __init__(
        self,
        *,
        session_id: str,
        chat_id: str = "default",
        embeddings: Optional[Embeddings] = None,
        entity_k: int = 15,
    ):
        self.session_id = session_id
        self.chat_id = chat_id

        # Embeddings
        self.embedding_model = embeddings or OpenAIEmbeddings(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )

        # ── Short-term buffer (window) ───────────────────────────────────
        self.buffer_memory = ConversationBufferWindowMemory(
            k=self.SHORT_WINDOW,
            return_messages=True,
            memory_key="buffer_memory",
            input_key="input",
        )

        # ── Long-term FAISS (HNSW) store ─────────────────────────────────
        stub_doc = Document(
            page_content="memory_root",
            metadata={
                "role": "system",
                "session_id": session_id,
                "chat_id": chat_id,
                "timestamp": datetime.now(timezone.utc).timestamp(),
                "importance_score": 0.0,
            },
        )
        self.vector_store = FAISS.from_documents(
            [stub_doc], embedding=self.embedding_model
        )
        self.retriever = TimeWeightedVectorStoreRetriever(
            vectorstore=self.vector_store,
            k=self.LONG_K,
            decay_rate=0.05,
            other_score_keys=["importance_score"],
        )
        self.vector_memory = VectorStoreRetrieverMemory(
            retriever=self.retriever,
            memory_key="semantic_memory",
            input_key="input",
        )

        # ── Entity memory ────────────────────────────────────────────────
        self.entity_memory = ConversationEntityMemory(
            llm=ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                temperature=0.0
            ),
            k=entity_k,
            memory_key="entity_store",
            input_key="input",
            return_messages=False,
        )

        # ── Combined handle (if caller wants LangChain-style .load()) ────
        self.memory = CombinedMemory(
            memories=[
                self.buffer_memory,
                self.entity_memory,
                self.vector_memory,
            ],
            input_key="input",
            return_messages=True,
        )

        logger.info(
            "EnhancedMemoryManager started  session=%s  chat=%s  short=%d  HNSW32",
            session_id,
            chat_id,
            self.SHORT_WINDOW,
        )

    # -----------------------------------------------------
    # Add a message
    # -----------------------------------------------------
    async def add_message(
        self,
        *,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not content:
            return

        meta = dict(metadata or {})
        meta.update(
            {
                "role": role,
                "session_id": self.session_id,
                "chat_id": self.chat_id,
                "timestamp": datetime.now(timezone.utc).timestamp(),
            }
        )
        meta["importance_score"] = _importance(content, meta)

        if role == "user":
            self.buffer_memory.chat_memory.add_user_message(content)
            try:
                self.entity_memory.save_context({"input": content}, {"output": ""})
            except Exception:
                pass
        elif role == "assistant":
            self.buffer_memory.chat_memory.add_ai_message(content)
        elif role == "tool":
            self.buffer_memory.chat_memory.add_message(ToolMessage(content=content, tool_call_id=meta.get("tool", "unknown")))
        elif role == "system":
            self.buffer_memory.chat_memory.add_message(SystemMessage(content=content))
        else:
            self.buffer_memory.chat_memory.add_message(SystemMessage(content=f"[{role}] {content}"))


        # long-term – add to FAISS immediately
        try:
            self.vector_store.add_texts([content], metadatas=[meta])
        except Exception as e:
            logger.error("FAISS add_texts failed: %s", e)

    # -----------------------------------------------------
    # Retrieve context for a query
    # -----------------------------------------------------
    async def get_context(self, query: str) -> Dict[str, Any]:
        try:
            # short-term messages (already most-recent-first)
            short_msgs = self.buffer_memory.chat_memory.messages

            # long-term semantic hits (already recency-weighted)
            long_docs = self.retriever.invoke(query)
            long_msgs = [
                {
                    "content": d.page_content,
                    "metadata": d.metadata,
                }
                for d in long_docs
                if d.metadata.get("session_id") == self.session_id
                and d.metadata.get("chat_id") == self.chat_id
            ]

            entities = self.entity_memory.load_memory_variables({"input": query}).get(
                "entity_store", {}
            )

            return {
                "relevant_history": short_msgs + long_msgs,
                "entities": entities,
            }
        except Exception as e:
            logger.error("get_context error: %s", e)
            return {"relevant_history": [], "entities": {}}

    # -----------------------------------------------------
    # Diagnostics helper
    # -----------------------------------------------------
    def get_session_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        msgs = [
            {
                "role": m.type,
                "content": m.content,
                "timestamp": getattr(m, "additional_kwargs", {}).get("timestamp"),
            }
            for m in reversed(self.buffer_memory.chat_memory.messages)
        ]
        # Pull a few from FAISS for debugging
        try:
            docs = self.vector_store.similarity_search("", k=min(limit, 50))
            for d in docs:
                msgs.append(
                    {
                        "role": d.metadata.get("role"),
                        "content": d.page_content,
                        "timestamp": datetime.fromtimestamp(
                            d.metadata.get("timestamp", 0)
                        ).isoformat(),
                    }
                )
        except Exception:
            pass
        msgs.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
        return msgs[:limit]

    # -----------------------------------------------------
    # Clear everything
    # -----------------------------------------------------
    def clear(self) -> None:
        self.buffer_memory.clear()
        self.entity_memory.clear()
        self.__init__(
            session_id=self.session_id,
            chat_id=self.chat_id,
            embeddings=self.embedding_model,
        )
        logger.info("Memory cleared  session=%s  chat=%s", self.session_id, self.chat_id)
