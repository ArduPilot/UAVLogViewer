from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import os
import json
import hashlib
from langchain.memory import (
    CombinedMemory,
    ConversationSummaryBufferMemory,
    ConversationEntityMemory,
    VectorStoreRetrieverMemory
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.schema import Document, AIMessage, HumanMessage, SystemMessage
from langchain_community.vectorstores import FAISS
from langchain.retrievers import TimeWeightedVectorStoreRetriever
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EnhancedMemoryManager:
    """
    Enhanced memory manager that combines LangChain memories with in-memory vector store
    for comprehensive short and long-term memory capabilities.
    """
    
    def __init__(
        self,
        session_id: str,
        db_session=None,  # Kept for backward compatibility but not used
        window_size: int = 10,
        max_tokens_per_context: int = 4000,
        llm: Optional[ChatOpenAI] = None,
        embeddings: Optional[OpenAIEmbeddings] = None
    ):
        self.session_id = session_id
        self.window_size = window_size
        self.max_tokens_per_context = max_tokens_per_context
        
        # Initialize LLM if not provided
        self.llm = llm or ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize embeddings if not provided
        self.embeddings = embeddings or OpenAIEmbeddings(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"),
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize in-memory vector store for semantic search
        self.vector_store = FAISS.from_texts(
            ["Initial memory entry for UAV system."], 
            embedding=self.embeddings
        )
        
        # Initialize time-weighted retriever for recency bias
        self.retriever = TimeWeightedVectorStoreRetriever(
            vectorstore=self.vector_store,
            other_score_keys=["importance_score"],
            k=5
        )
        
        # Initialize vector store memory
        self.vector_memory = VectorStoreRetrieverMemory(
            retriever=self.retriever,
            memory_key="semantic_memory"
        )
        
        # Initialize summary buffer memory
        self.summary_buffer_memory = ConversationSummaryBufferMemory(
            llm=self.llm,
            max_token_limit=max_tokens_per_context // 2,
            return_messages=True,
            memory_key="chat_history",
            input_key="input"
        )
        
        # Initialize entity memory
        self.entity_memory = ConversationEntityMemory(
            llm=self.llm,
            return_messages=False,
            k=10,
            memory_key="entity_store",
            input_key="input"
        )
        
        # Combine memories
        self.memory = CombinedMemory(
            memories=[
                self.summary_buffer_memory,
                self.entity_memory,
                self.vector_memory
            ],
            return_messages=True,
            input_key="input"
        )
        
        # Initialize message history for the current session
        self.messages = []

    def _compute_importance_score(self, content: str, metadata: Dict) -> float:
        """Compute importance score for memory prioritization."""
        score = 1.0
        
        # Length-based scoring
        words = len(content.split())
        if words > 50:
            score *= 1.2
        
        # Content type scoring
        if metadata.get("query_type") == "anomaly":
            score *= 1.5
        elif metadata.get("has_metrics", False):
            score *= 1.3
        
        # Critical information scoring
        if metadata.get("has_error", False):
            score *= 1.6
        
        # Cap at 2.0
        return min(score, 2.0)
    
    async def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Add a message to all memory systems."""
        try:
            if metadata is None:
                metadata = {}
            
            # Compute importance score
            importance_score = self._compute_importance_score(content, metadata)
            metadata["importance_score"] = importance_score
            metadata["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Create appropriate message object for in-memory storage
            if role == "user":
                message = HumanMessage(content=content)
                # Add directly to summary buffer memory instead of through combined memory
                self.summary_buffer_memory.chat_memory.add_user_message(content)
            elif role == "assistant":
                message = AIMessage(content=content)
                # Add directly to summary buffer memory instead of through combined memory
                self.summary_buffer_memory.chat_memory.add_ai_message(content)
            else:
                message = SystemMessage(content=content)
            
            # Add to in-memory message history
            self.messages.append({
                "role": role,
                "content": content,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata
            })
            
            # Add to vector store for semantic search
            if role in ["user", "assistant"]:
                doc_id = hashlib.md5(f"{content}-{len(self.messages)}".encode()).hexdigest()
                
                # Create document with metadata
                document = Document(
                    page_content=content,
                    metadata={
                        **metadata,
                        "role": role,
                        "timestamp": datetime.now(timezone.utc).timestamp(),
                        "importance_score": importance_score
                    }
                )
                
                # Add to vector store
                self.vector_store.add_documents([document])
        except Exception as e:
            print(f"Error in add_message: {str(e)}")
            import traceback
            print(f"TRACEBACK: {traceback.format_exc()}")
    
    async def get_context(self, query: str) -> Dict[str, Any]:
        """Get comprehensive context for a query using ReAct principles."""
        try:
            # Get memory variables from combined memory
            memory_variables = self.memory.load_memory_variables({"input": query})
            
            # Get semantic search results directly from vector store
            semantic_results = self.retriever.invoke(query)
            
            # Perform reasoning about information needs using ReAct approach
            reasoning_prompt = f"""
            You are analyzing this user query about UAV flight data: "{query}"
            
            Reason step by step about what information is needed to provide the best answer.
            First, determine what the user is asking for.
            Then, decide what flight data would be most relevant.
            Finally, identify what additional context from past conversations would help.
            
            Structure your thinking as:
            - Query type: [classification of query]
            - Relevant flight parameters: [list key parameters]
            - Temporal focus: [specific time periods of interest]
            - Required context: [what past information would help]
            """
            
            reasoning_response = self.llm.invoke([HumanMessage(content=reasoning_prompt)])
            
            # Process semantic results for context
            semantic_context = []
            for doc in semantic_results:
                semantic_context.append({
                    "content": doc.page_content,
                    "score": doc.metadata.get("importance_score", 1.0),
                    "metadata": doc.metadata
                })
            
            # Safely get entity memory with fallback
            try:
                entity_memory_vars = self.entity_memory.load_memory_variables({"input": query})
                entity_memory = entity_memory_vars.get("entity_store", {})
            except Exception as e:
                print(f"Error loading entity memory: {str(e)}")
                entity_memory = {}
            
            # Construct final context with reasoning
            context = {
                **memory_variables,
                "semantic_context": semantic_context,
                "query_reasoning": reasoning_response.content,
                "entity_memory": entity_memory
            }
            
            return context
        except Exception as e:
            print(f"Error in get_context: {str(e)}")
            import traceback
            print(f"TRACEBACK: {traceback.format_exc()}")
            
            # Return minimal context to avoid breaking the flow
            return {
                "chat_history": [],
                "semantic_context": [],
                "query_reasoning": "Query analysis unavailable.",
                "entity_memory": {}
            }
    
    def get_session_messages(self, limit: int = 50) -> List[Dict]:
        """Get messages for API responses."""
        sorted_messages = sorted(
            self.messages, 
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )
        return sorted_messages[:limit]
    
    def clear(self) -> None:
        """Clear all memory components."""
        self.memory.clear()
        self.messages = []
        # Reset vector store
        self.vector_store = FAISS.from_texts(
            ["Initial memory entry for UAV system."], 
            embedding=self.embeddings
        )
        self.retriever = TimeWeightedVectorStoreRetriever(
            vectorstore=self.vector_store,
            other_score_keys=["importance_score"],
            k=5
        )
        self.vector_memory = VectorStoreRetrieverMemory(
            retriever=self.retriever,
            memory_key="semantic_memory"
        ) 