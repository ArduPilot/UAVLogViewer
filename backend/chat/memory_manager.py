from typing import Dict, List, Optional, Any, Tuple, Union
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
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class EnhancedMemoryManager:
    """
    Enhanced memory manager that combines multiple memory types for optimal context management:
    
    1. Short-term memory: Recent conversations via buffer memory
    2. Long-term memory: Historical context via vector store
    3. Entity memory: Extracted key entities and their attributes
    4. Summary memory: Compressed representation of conversation history
    
    Features:
    - Semantic search for retrieving relevant historical context
    - Time-weighted recency bias for fresher information prioritization
    - Importance scoring for critical information retention
    - Automatic extraction and tracking of entities
    - Conversation summarization for compact memory representation
    """
    
    def __init__(
        self,
        session_id: str,
        max_tokens_per_context: int = 4000,
        summary_max_tokens: int = 2000,
        llm: Optional[ChatOpenAI] = None,
        embeddings: Optional[OpenAIEmbeddings] = None
    ):
        """
        Initialize the enhanced memory manager.
        
        Args:
            session_id: Unique session identifier
            max_tokens_per_context: Maximum tokens to include in context
            summary_max_tokens: Maximum tokens for summary buffer
            llm: Language model for summarization and entity extraction
            embeddings: Embedding model for vector storage
        """
        self.session_id = session_id
        self.max_tokens_per_context = max_tokens_per_context
        
        # Initialize LLM with appropriate timeout and error handling
        self.llm = llm or ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            max_retries=3,
            request_timeout=30
        )
        
        # Initialize embeddings for semantic search
        self.embeddings = embeddings or OpenAIEmbeddings(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            max_retries=3,
            request_timeout=15
        )
        
        # Initialize vector store with initial empty document
        try:
            self.vector_store = FAISS.from_texts(
                ["Initial memory entry for UAV flight analysis system."], 
                embedding=self.embeddings,
                metadatas=[{
                    "role": "system",
                    "timestamp": datetime.now(timezone.utc).timestamp(),
                    "importance_score": 0.5,
                    "session_id": session_id
                }]
            )
            
            # Initialize retriever with time weighting for recency bias
            self.retriever = TimeWeightedVectorStoreRetriever(
                vectorstore=self.vector_store,
                other_score_keys=["importance_score"],
                k=8,  # Retrieve more documents for better filtering
                decay_rate=0.05  # Slower decay rate to maintain important older memories
            )
            
            # Initialize vector store memory
            self.vector_memory = VectorStoreRetrieverMemory(
                retriever=self.retriever,
                memory_key="semantic_memory",
                input_key="input"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize vector memory: {str(e)}")
            raise RuntimeError(f"Vector memory initialization failed: {str(e)}")
        
        # Initialize summary buffer memory with moderate token limit
        self.summary_buffer_memory = ConversationSummaryBufferMemory(
            llm=self.llm,
            max_token_limit=summary_max_tokens,
            return_messages=True,
            memory_key="chat_history",
            input_key="input",
            output_key="output"
        )
        
        # Initialize entity memory with higher k for better recall
        self.entity_memory = ConversationEntityMemory(
            llm=self.llm,
            return_messages=False,
            k=15,
            memory_key="entity_store",
            input_key="input"
        )
        
        # Combine memories with appropriate weights
        self.memory = CombinedMemory(
            memories=[
                self.summary_buffer_memory,
                self.entity_memory,
                self.vector_memory
            ],
            return_messages=True,
            input_key="input"
        )
        
        # Message history storage
        self.messages = []
        
        logger.info(f"Initialized EnhancedMemoryManager for session {session_id}")

    def _compute_importance_score(self, content: str, metadata: Dict) -> float:
        """
        Compute importance score for memory prioritization based on content and metadata.
        
        Factors affecting score:
        - Message length (longer messages often contain more information)
        - Content type (anomalies, metrics, tool outputs are more important)
        - Presence of numerical values (often indicates specific data)
        - Special tags (critical flags, error reports)
        
        Args:
            content: Message content
            metadata: Message metadata with type information
            
        Returns:
            Importance score between 0.1 and 2.0
        """
        # Base score
        score = 1.0
        
        # Content length scoring - longer messages may contain more information
        words = len(content.split())
        if words > 100:
            score *= 1.4
        elif words > 50:
            score *= 1.2
        
        # Content type scoring
        if metadata.get("is_final_answer", False):
            score *= 1.5  # Final answers are important for context
        elif metadata.get("is_query", False):
            score *= 1.3  # User queries are important for context
        elif metadata.get("tool") == "detailed_altitude_analysis":
            score *= 1.4  # Altitude analysis is frequently needed
        elif metadata.get("tool") == "detect_anomalies":
            score *= 1.5  # Anomalies are critical information
        elif metadata.get("has_metrics", False):
            score *= 1.3  # Metrics are important reference information
        
        # Content-based heuristics
        if "error" in content.lower() or "warning" in content.lower():
            score *= 1.3  # Errors and warnings are important
        
        # Check for numerical data presence (often important specific measurements)
        import re
        if len(re.findall(r'\d+\.\d+|\d+', content)) > 3:  # Contains several numbers
            score *= 1.2
            
        # Critical information scoring
        if metadata.get("has_error", False) or metadata.get("is_critical", False):
            score *= 1.5
            
        # Normalize to reasonable range
        return min(max(score, 0.5), 2.0)
    
    async def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Add a message to all memory systems.
        
        Args:
            role: Message role (user, assistant, tool, system)
            content: Message content
            metadata: Additional metadata for importance scoring and retrieval
        """
        try:
            # Initialize metadata dict if not provided
            if metadata is None:
                metadata = {}
                
            # Add session_id to metadata
            metadata["session_id"] = self.session_id
            
            # Compute importance score
            importance_score = self._compute_importance_score(content, metadata)
            metadata["importance_score"] = importance_score
            metadata["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Create message object for memory systems
            if role == "user":
                # Add to conversation summary buffer memory
                self.summary_buffer_memory.chat_memory.add_user_message(content)
                
                # Add to entity memory
                if len(content) > 10:  # Only process substantial messages
                    try:
                        self.entity_memory.save_context(
                            {"input": content}, 
                            {"output": "User message processed for entities."}
                        )
                    except Exception as entity_err:
                        logger.warning(f"Entity memory processing failed: {str(entity_err)}")
                
            elif role == "assistant":
                # Add to conversation summary buffer
                self.summary_buffer_memory.chat_memory.add_ai_message(content)
                
            # Workaround for system and tool messages (not directly supported by LangChain memory)
            elif role == "system":
                # System messages typically don't need to be in the conversational flow
                pass
                
            elif role == "tool":
                # Tool messages are stored in vector store but not in conversation summary
                # They'll be retrieved when relevant to the query
                pass
            
            # Add to in-memory message history with timestamp
            self.messages.append({
                "role": role,
                "content": content,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata
            })
            
            # Add to vector store for semantic search
            try:
                # Skip empty or very short content
                if content and len(content) > 5:
                    # Create unique ID for document
                    doc_id = hashlib.md5(f"{content}-{len(self.messages)}".encode()).hexdigest()
                    
                    # Create document with metadata
                    document = Document(
                        page_content=content,
                        metadata={
                            **metadata,
                            "role": role,
                            "timestamp": datetime.now(timezone.utc).timestamp(),
                            "importance_score": importance_score,
                            "session_id": self.session_id
                        }
                    )
                    
                    # Add to vector store with timeout protection
                    try:
                        self.vector_store.add_documents([document])
                    except Exception as vec_err:
                        logger.error(f"Error adding to vector store: {str(vec_err)}")
            except Exception as vec_err:
                logger.error(f"Error in vectorization process: {str(vec_err)}")
                
        except Exception as e:
            logger.error(f"Error in add_message: {str(e)}")
    
    async def get_context(self, query: str) -> Dict[str, Any]:
        """
        Get comprehensive context for a query using hybrid memory retrieval.
        
        The method provides optimized context retrieval by:
        1. Analyzing the query to determine information needs
        2. Retrieving relevant messages from vector store based on semantic similarity
        3. Including recent conversation history for continuity
        4. Extracting relevant entities from entity memory
        5. Including the conversation summary for high-level context
        
        Args:
            query: The user's query to contextualize
            
        Returns:
            Dictionary containing different types of context information
        """
        context = {}
        
        try:
            # 1. Get summary buffer memory (recent conversation)
            context["chat_history"] = self.summary_buffer_memory.chat_memory.messages
            
            # 2. Get semantic search results from vector store
            semantic_results = []
            try:
                # Retrieve semantically relevant documents
                retrieval_results = await self._async_retrieve(query)
                
                # Filter to current session only
                retrieval_results = [
                    doc for doc in retrieval_results 
                    if doc.metadata.get("session_id") == self.session_id
                ]
                
                # Process semantic results for better usability
                for doc in retrieval_results:
                    semantic_results.append({
                        "content": doc.page_content,
                        "score": doc.metadata.get("importance_score", 1.0),
                        "role": doc.metadata.get("role", "unknown"),
                        "timestamp": doc.metadata.get("timestamp"),
                        "metadata": doc.metadata
                    })
                    
                # Sort by importance score * recency
                current_time = datetime.now(timezone.utc).timestamp()
                for result in semantic_results:
                    timestamp = result.get("timestamp", current_time - 86400)  # Default to 1 day ago
                    if isinstance(timestamp, str):
                        try:
                            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
                        except:
                            timestamp = current_time - 86400
                            
                    # Compute recency factor (1.0 for current, decreasing with age)
                    time_diff_hours = (current_time - timestamp) / 3600
                    recency_factor = 1.0 / (1.0 + 0.05 * time_diff_hours)
                    
                    # Combined score based on importance and recency
                    result["combined_score"] = result.get("score", 1.0) * recency_factor
                
                # Sort by combined score
                semantic_results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
                
                # Limit to top results
                semantic_results = semantic_results[:5]
                
            except Exception as e:
                logger.error(f"Error in semantic retrieval: {str(e)}")
                semantic_results = []
            
            # 3. Get entity memory
            entity_memory = {}
            try:
                entity_result = await self._async_entity_memory(query)
                entity_memory = entity_result.get("entity_store", {})
            except Exception as e:
                logger.error(f"Error retrieving entity memory: {str(e)}")
            
            # 4. Perform query analysis to understand information needs
            query_analysis = await self._async_analyze_query(query)
            
            # Add all components to context
            context["semantic_context"] = semantic_results
            context["entity_memory"] = entity_memory
            context["query_analysis"] = query_analysis
            
            return context
            
        except Exception as e:
            logger.error(f"Error in get_context: {str(e)}")
            
            # Return minimal context to avoid breaking the application flow
            return {
                "chat_history": [],
                "semantic_context": [],
                "entity_memory": {},
                "query_analysis": f"Query about {query[:30]}..."
            }
    
    async def _async_retrieve(self, query: str):
        """
        Asynchronously retrieve relevant documents from vector store.
        
        Args:
            query: The search query
            
        Returns:
            List of relevant documents
        """
        try:
            # Add a timeout for the retrieval operation
            retrieval_task = asyncio.create_task(
                self._perform_retrieval(query)
            )
            results = await asyncio.wait_for(retrieval_task, timeout=5.0)
            return results
        except asyncio.TimeoutError:
            logger.warning(f"Vector retrieval timed out for query: {query[:50]}...")
            return []
        except Exception as e:
            logger.error(f"Error in vector retrieval: {str(e)}")
            return []
    
    async def _perform_retrieval(self, query: str):
        """Helper method to perform the actual retrieval operation."""
        # This runs in an async context but calls the synchronous retriever
        return self.retriever.invoke(query)
    
    async def _async_entity_memory(self, query: str) -> Dict:
        """
        Asynchronously retrieve relevant entities from entity memory.
        
        Args:
            query: The search query
            
        Returns:
            Dictionary containing entity information
        """
        try:
            # Add a timeout for the operation
            entity_task = asyncio.create_task(
                self._perform_entity_retrieval(query)
            )
            results = await asyncio.wait_for(entity_task, timeout=3.0)
            return results
        except asyncio.TimeoutError:
            logger.warning(f"Entity memory retrieval timed out for query: {query[:50]}...")
            return {"entity_store": {}}
        except Exception as e:
            logger.error(f"Error in entity retrieval: {str(e)}")
            return {"entity_store": {}}
    
    async def _perform_entity_retrieval(self, query: str) -> Dict:
        """Helper method to perform the actual entity retrieval."""
        # This calls the synchronous entity memory
        return self.entity_memory.load_memory_variables({"input": query})
    
    async def _async_analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query to determine information needs.
        
        This helps optimize context retrieval by understanding what
        kind of information is most relevant to the query.
        
        Args:
            query: The user's query
            
        Returns:
            Dictionary with query analysis results
        """
        try:
            # Simplified query analysis to determine information needs
            analysis_prompt = f"""
            Analyze this query about UAV flight data: '{query}'
            
            What type of information would be needed to answer it effectively?
            What telemetry data fields would be most relevant?
            
            Return JSON in this format:
            {{
              "information_type": ["altitude", "battery", "gps", etc],
              "telemetry_fields": ["relevant field names"],
              "requires_historical_context": true/false,
              "key_terms": ["important terms from the query"]
            }}
            """
            
            # Use a task with timeout
            analysis_task = asyncio.create_task(
                self._perform_query_analysis(analysis_prompt)
            )
            analysis_result = await asyncio.wait_for(analysis_task, timeout=3.0)
            
            try:
                # Try to parse as JSON
                return json.loads(analysis_result)
            except:
                # Return as plain text if JSON parsing fails
                return {
                    "analysis_text": analysis_result,
                    "key_terms": query.lower().split()
                }
                
        except asyncio.TimeoutError:
            logger.warning(f"Query analysis timed out for: {query[:50]}...")
            return {"key_terms": query.lower().split()}
        except Exception as e:
            logger.error(f"Error in query analysis: {str(e)}")
            return {"key_terms": query.lower().split()}
    
    async def _perform_query_analysis(self, prompt: str) -> str:
        """Helper method to perform the actual query analysis."""
        # This calls the synchronous LLM
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content
    
    def get_session_messages(self, limit: int = 50) -> List[Dict]:
        """
        Get the most recent messages for the session.
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of message dictionaries
        """
        return self.messages[-limit:] if self.messages else []
    
    def clear(self) -> None:
        """
        Clear all memory systems.
        
        This removes all stored messages, summaries, and vectors
        """
        try:
            # Clear in-memory message history
            self.messages = []
            
            # Clear conversation summary buffer
            self.summary_buffer_memory.clear()
            
            # Clear entity memory
            self.entity_memory.clear()
            
            # Reinitialize vector store with empty memory marker
            self.vector_store = FAISS.from_texts(
                ["Memory cleared. New session started."], 
                embedding=self.embeddings,
                metadatas=[{
                    "role": "system",
                    "timestamp": datetime.now(timezone.utc).timestamp(),
                    "importance_score": 0.5,
                    "session_id": self.session_id
                }]
            )
            
            # Update retriever with new vector store
            self.retriever = TimeWeightedVectorStoreRetriever(
                vectorstore=self.vector_store,
                other_score_keys=["importance_score"],
                k=8,
                decay_rate=0.05
            )
            
            # Update vector memory with new retriever
            self.vector_memory = VectorStoreRetrieverMemory(
                retriever=self.retriever,
                memory_key="semantic_memory",
                input_key="input"
            )
            
            # Update combined memory with new components
            self.memory = CombinedMemory(
                memories=[
                    self.summary_buffer_memory,
                    self.entity_memory,
                    self.vector_memory
                ],
                return_messages=True,
                input_key="input"
            )
            
            logger.info(f"Successfully cleared all memory for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error clearing memory: {str(e)}")
            raise 