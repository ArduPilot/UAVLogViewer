from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import os
import json
import hashlib
import asyncio
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
        
        # Initialize LLM if not provided, with timeout handling
        self.llm = llm or ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            max_retries=2,
            request_timeout=30  # 30 seconds timeout to avoid hanging
        )
        
        # Initialize embeddings if not provided
        self.embeddings = embeddings or OpenAIEmbeddings(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            max_retries=2,
            request_timeout=10  # 10 seconds timeout for embeddings
        )
        
        # Initialize in-memory vector store for semantic search
        try:
            self.vector_store = FAISS.from_texts(
                ["Initial memory entry for UAV system."], 
                embedding=self.embeddings
            )
        except Exception as e:
            print(f"ERROR: Failed to initialize vector store: {str(e)}")
            import traceback
            print(f"TRACEBACK: {traceback.format_exc()}")
            # No fallback - propagate the error to prevent silent failures
            raise
        
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
        # Simplified scoring to avoid computation bottlenecks
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
            try:
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
                    
                    # Add to vector store with timeout protection
                    try:
                        self.vector_store.add_documents([document])
                    except Exception as vec_err:
                        print(f"Error adding to vector store, continuing without vectorization: {str(vec_err)}")
                        import traceback
                        print(f"VECTORIZATION ERROR: {traceback.format_exc()}")
                        # Don't continue with a fallback, but don't crash the message storage either
                        # as this is non-critical for the user experience
            except Exception as vec_err:
                print(f"Error in vectorization process: {str(vec_err)}")
                # Continue anyway, as this is non-critical
                
        except Exception as e:
            print(f"Error in add_message: {str(e)}")
            import traceback
            print(f"TRACEBACK: {traceback.format_exc()}")
    
    async def get_context(self, query: str) -> Dict[str, Any]:
        """Get comprehensive context for a query using ReAct principles."""
        try:
            # Create task with timeout for memory variables
            memory_context = {}
            
            # Skip potentially slow memory operations for initial simplicity
            # and to avoid hanging on the first requests
            skip_complex_memory = False
            
            if not skip_complex_memory:
                try:
                    # Get memory variables from combined memory with timeout
                    memory_task = asyncio.create_task(
                        self._async_load_memory_variables(query)
                    )
                    memory_context = await asyncio.wait_for(memory_task, timeout=5.0)
                except asyncio.TimeoutError:
                    print("Memory variables retrieval timed out, using fallback")
                    # Fallback to just the summary memory which is typically faster
                    try:
                        memory_context = {"chat_history": self.summary_buffer_memory.chat_memory.messages}
                    except Exception as mem_err:
                        print(f"Error getting summary memory: {str(mem_err)}")
                        memory_context = {"chat_history": []}
                except Exception as e:
                    print(f"Error loading memory variables: {str(e)}")
                    memory_context = {"chat_history": []}
            else:
                # Simple fallback when skipping complex memory
                memory_context = {"chat_history": self.summary_buffer_memory.chat_memory.messages}
            
            # Get semantic search results directly from vector store
            semantic_results = []
            try:
                semantic_task = asyncio.create_task(self._async_retrieve(query))
                semantic_results = await asyncio.wait_for(semantic_task, timeout=3.0)
            except (asyncio.TimeoutError, Exception) as e:
                print(f"Error in semantic retrieval: {str(e)}")
                import traceback
                print(f"SEMANTIC RETRIEVAL ERROR: {traceback.format_exc()}")
                # Return empty results rather than a fallback with potentially misleading data
                semantic_results = []
            
            # Perform reasoning about information needs - with a timeout
            reasoning_content = "Basic query analysis: The query relates to flight data."
            try:
                reasoning_task = asyncio.create_task(self._async_reasoning(query))
                reasoning_content = await asyncio.wait_for(reasoning_task, timeout=5.0)
            except (asyncio.TimeoutError, Exception) as e:
                print(f"Reasoning timed out or failed: {str(e)}")
                # Use a basic generic reasoning content as fallback
            
            # Process semantic results for context
            semantic_context = []
            for doc in semantic_results:
                semantic_context.append({
                    "content": doc.page_content,
                    "score": doc.metadata.get("importance_score", 1.0),
                    "metadata": doc.metadata
                })
            
            # Safely get entity memory with fallback - simplified to avoid delays
            entity_memory = {}
            if not skip_complex_memory:
                try:
                    entity_memory_vars = {}
                    entity_task = asyncio.create_task(self._async_entity_memory(query))
                    entity_memory_vars = await asyncio.wait_for(entity_task, timeout=3.0)
                    entity_memory = entity_memory_vars.get("entity_store", {})
                except (asyncio.TimeoutError, Exception) as e:
                    print(f"Entity memory retrieval timed out or failed: {str(e)}")
            
            # Construct final context with reasoning
            context = {
                **memory_context,
                "semantic_context": semantic_context,
                "query_reasoning": reasoning_content,
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
    
    async def _async_load_memory_variables(self, query: str) -> Dict[str, Any]:
        """Async wrapper for memory variable loading with error protection."""
        try:
            # This will primarily load the chat history
            memory_vars = self.summary_buffer_memory.load_memory_variables({"input": query})
            return memory_vars
        except Exception as e:
            print(f"Error in _async_load_memory_variables: {str(e)}")
            return {"chat_history": []}
    
    async def _async_retrieve(self, query: str):
        """Async wrapper for semantic retrieval with error protection."""
        try:
            # This may cause hanging if the vector store operations are slow
            results = self.retriever.invoke(query)
            return results
        except Exception as e:
            print(f"Error in _async_retrieve: {str(e)}")
            import traceback
            print(f"ASYNC RETRIEVE ERROR: {traceback.format_exc()}")
            # Return empty results rather than fabricating data
            return []
    
    async def _async_reasoning(self, query: str) -> str:
        """Async wrapper for reasoning with error protection."""
        try:
            # Simplified reasoning prompt to minimize tokens and processing time
            reasoning_prompt = f"Analyze this query about UAV flight data: '{query}'. What information would be needed to answer it effectively? Keep your analysis concise."
            
            # Direct call to keep it simple and fast
            reasoning_response = self.llm.invoke([HumanMessage(content=reasoning_prompt)])
            return reasoning_response.content
        except Exception as e:
            print(f"Error in _async_reasoning: {str(e)}")
            return f"Basic analysis: Query about {query[:20]}..."
    
    async def _async_entity_memory(self, query: str) -> Dict:
        """Async wrapper for entity memory loading with error protection."""
        try:
            entity_memory_vars = self.entity_memory.load_memory_variables({"input": query})
            return entity_memory_vars
        except Exception as e:
            print(f"Error in _async_entity_memory: {str(e)}")
            return {"entity_store": {}}
            
    def get_session_messages(self, limit: int = 50) -> List[Dict]:
        """Get the most recent messages for the session."""
        return self.messages[-limit:] if self.messages else []
    
    def clear(self) -> None:
        """Clear all memory systems."""
        try:
            self.messages = []
            self.summary_buffer_memory.clear()
            self.entity_memory.clear()
            
            # Recreate vector store - if this fails, let the error propagate
            self.vector_store = FAISS.from_texts(
                ["Memory cleared. New session started."], 
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
            # Recreate combined memory
            self.memory = CombinedMemory(
                memories=[
                    self.summary_buffer_memory,
                    self.entity_memory,
                    self.vector_memory
                ],
                return_messages=True,
                input_key="input"
            )
        except Exception as e:
            print(f"ERROR in clear_memory: {str(e)}")
            import traceback
            print(f"TRACEBACK: {traceback.format_exc()}")
            # Propagate the error
            raise 