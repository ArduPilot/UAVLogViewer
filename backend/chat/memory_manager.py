from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import os
import json
import hashlib
from opensearchpy import OpenSearch
from langchain.memory import (
    CombinedMemory,
    ConversationSummaryBufferMemory,
    ConversationEntityMemory
)
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.schema import Document, BaseMessage, AIMessage, HumanMessage, SystemMessage
from sqlalchemy.orm import Session
from models.database import ChatMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SQLChatMessageHistory:
    """SQL-based storage for chat message history."""
    
    def __init__(self, session_id: str, db_session: Session):
        self.session_id = session_id
        self.db_session = db_session

    def add_message(self, message: BaseMessage, metadata: Optional[Dict] = None) -> None:
        """Add a message to the history."""
        role = self._get_role(message)
        content = message.content
        
        if metadata is None:
            metadata = {}
            
        # Add message hash for deduplication
        metadata["message_hash"] = self._generate_message_hash(content)
        metadata["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        chat_message = ChatMessage(
            session_id=self.session_id,
            role=role,
            content=content,
            metadata=metadata
        )
        self.db_session.add(chat_message)
        self.db_session.commit()
    
    def _get_role(self, message: BaseMessage) -> str:
        """Map langchain message type to role string."""
        if isinstance(message, HumanMessage):
            return "user"
        elif isinstance(message, AIMessage):
            return "assistant"
        elif isinstance(message, SystemMessage):
            return "system"
        else:
            return "other"
    
    def _generate_message_hash(self, content: str) -> str:
        """Generate a unique hash for message deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()

    def get_messages(self, limit: int = 50) -> List[BaseMessage]:
        """Get messages as LangChain message objects."""
        messages = self.db_session.query(ChatMessage)\
            .filter_by(session_id=self.session_id)\
            .order_by(ChatMessage.created_at.asc())\
            .limit(limit)\
            .all()
        
        result = []
        for msg in messages:
            if msg.role == "user":
                result.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                result.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                result.append(SystemMessage(content=msg.content))
        
        return result
    
    def get_session_messages(self, limit: int = 50) -> List[Dict]:
        """Get messages as dictionaries for API responses."""
        messages = self.db_session.query(ChatMessage)\
            .filter_by(session_id=self.session_id)\
            .order_by(ChatMessage.created_at.desc())\
            .limit(limit)\
            .all()
        
        return [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "metadata": msg.metadata
            } for msg in messages
        ]
    
    def clear(self) -> None:
        """Clear all messages for this session."""
        self.db_session.query(ChatMessage)\
            .filter_by(session_id=self.session_id)\
            .delete()
        self.db_session.commit()

class OpenSearchVectorStore:
    """OpenSearch-based vector store for semantic search."""
    
    def __init__(
        self, 
        session_id: str,
        embeddings: Optional[OpenAIEmbeddings] = None,
        opensearch_host: Optional[str] = None,
        opensearch_port: Optional[int] = None
    ):
        self.session_id = session_id
        
        # Initialize embeddings if not provided
        self.embeddings = embeddings or OpenAIEmbeddings(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"),
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize OpenSearch client
        opensearch_host = opensearch_host or os.getenv("OPENSEARCH_HOST", "localhost")
        opensearch_port = opensearch_port or int(os.getenv("OPENSEARCH_PORT", 9200))
        
        self.client = OpenSearch(
            hosts=[{"host": opensearch_host, "port": opensearch_port}],
            http_compress=True,
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False
        )
        
        self.index_name = f"semantic_memory_{session_id}"
        self._ensure_index()
    
    def _ensure_index(self):
        """Ensure OpenSearch index exists with proper mappings."""
        if not self.client.indices.exists(index=self.index_name):
            embedding_dim = int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", 1536))
            
            mapping = {
                "mappings": {
                    "properties": {
                        "content": {"type": "text"},
                        "embedding": {"type": "dense_vector", "dims": embedding_dim},
                        "metadata": {"type": "object"},
                        "timestamp": {"type": "date"},
                        "importance_score": {"type": "float"}
                    }
                }
            }
            
            self.client.indices.create(index=self.index_name, body=mapping)
    
    async def add_texts(
        self, 
        texts: List[str], 
        metadatas: Optional[List[Dict]] = None,
        importance_scores: Optional[List[float]] = None
    ) -> List[str]:
        """Add texts to the vector store."""
        if metadatas is None:
            metadatas = [{} for _ in texts]
            
        if importance_scores is None:
            importance_scores = [1.0 for _ in texts]
        
        # Generate embeddings
        embeddings = self.embeddings.embed_documents(texts)
        
        # Add documents to OpenSearch
        ids = []
        for i, (text, embedding, metadata, importance_score) in enumerate(zip(texts, embeddings, metadatas, importance_scores)):
            doc_id = hashlib.md5(f"{text}-{i}".encode()).hexdigest()
            
            self.client.index(
                index=self.index_name,
                id=doc_id,
                body={
                    "content": text,
                    "embedding": embedding,
                    "metadata": metadata,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "importance_score": importance_score
                }
            )
            
            ids.append(doc_id)
        
        return ids
    
    async def similarity_search_with_score(
        self, 
        query: str, 
        k: int = 5,
        filter_metadata: Optional[Dict] = None,
        recency_boost: bool = True
    ) -> List[tuple[Document, float]]:
        """Search for documents similar to the query."""
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        
        # Prepare script for scoring
        script_source = """
            float score = cosineSimilarity(params.query_vector, 'embedding') + doc['importance_score'].value;
            
            if (params.recency_boost) {
                // Apply time decay factor - more recent documents get higher scores
                long hoursDiff = ChronoUnit.HOURS.between(
                    Instant.parse(doc['timestamp'].value), 
                    Instant.parse(params.current_time)
                );
                
                score += 0.5 * (1.0 / (1.0 + Math.max(0.1, hoursDiff)));
            }
            
            return score;
        """
        
        # Prepare query
        query_body = {
            "size": k,
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": script_source,
                        "params": {
                            "query_vector": query_embedding,
                            "current_time": datetime.now(timezone.utc).isoformat(),
                            "recency_boost": recency_boost
                        }
                    }
                }
            }
        }
        
        # Add filter if provided
        if filter_metadata:
            query_body["query"]["script_score"]["query"] = {
                "bool": {
                    "must": {"match_all": {}},
                    "filter": [
                        {"term": {f"metadata.{key}": value}}
                        for key, value in filter_metadata.items()
                    ]
                }
            }
        
        # Execute search
        response = self.client.search(index=self.index_name, body=query_body)
        
        # Process results
        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            doc = Document(
                page_content=source["content"],
                metadata={
                    **source.get("metadata", {}),
                    "score": hit["_score"],
                    "timestamp": source.get("timestamp")
                }
            )
            results.append((doc, hit["_score"]))
        
        return results
    
    def clear(self):
        """Clear all vectors for this session."""
        if self.client.indices.exists(index=self.index_name):
            self.client.indices.delete(index=self.index_name)
            self._ensure_index()

class EnhancedMemoryManager:
    """
    Enhanced memory manager that combines LangChain memories with custom vectorstore
    for comprehensive short and long-term memory capabilities.
    """
    
    def __init__(
        self,
        session_id: str,
        db_session: Session,
        window_size: int = 10,
        max_tokens_per_context: int = 4000,
        llm: Optional[ChatOpenAI] = None,
        embeddings: Optional[OpenAIEmbeddings] = None
    ):
        self.session_id = session_id
        self.db_session = db_session
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
        
        # Initialize SQL message history
        self.message_history = SQLChatMessageHistory(session_id, db_session)
        
        # Initialize vector store for semantic search
        self.vector_store = OpenSearchVectorStore(
            session_id=session_id,
            embeddings=self.embeddings
        )
        
        # Initialize enhanced memory components
        self.summary_buffer_memory = ConversationSummaryBufferMemory(
            llm=self.llm,
            max_token_limit=max_tokens_per_context // 2,
            return_messages=True,
            memory_key="chat_history"
        )
        
        self.entity_memory = ConversationEntityMemory(
            llm=self.llm,
            return_messages=False,
            k=10,
            memory_key="entity_store"
        )
        
        # Combine memories
        self.memory = CombinedMemory(
            memories=[
                self.summary_buffer_memory,
                self.entity_memory
            ],
            return_messages=True
        )
        
        # Initialize entity cache
        self.entity_cache = {}
        
        # Load previous messages into memory
        self._load_previous_messages()
    
    def _load_previous_messages(self):
        """Load previous messages from database into memory."""
        messages = self.message_history.get_messages(limit=100)
        
        for message in messages:
            if isinstance(message, HumanMessage):
                self.memory.chat_memory.add_user_message(message.content)
            elif isinstance(message, AIMessage):
                self.memory.chat_memory.add_ai_message(message.content)
    
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
        if metadata is None:
            metadata = {}
        
        # Deduplicate messages
        message_hash = hashlib.sha256(content.encode()).hexdigest()
        existing = self.db_session.query(ChatMessage).filter_by(
            session_id=self.session_id,
            metadata={"message_hash": message_hash}
        ).first()
        
        if existing:
            return
        
        # Compute importance score
        importance_score = self._compute_importance_score(content, metadata)
        metadata["importance_score"] = importance_score
        
        # Create appropriate message object
        if role == "user":
            message = HumanMessage(content=content)
            self.memory.chat_memory.add_user_message(content)
        elif role == "assistant":
            message = AIMessage(content=content)
            self.memory.chat_memory.add_ai_message(content)
        else:
            message = SystemMessage(content=content)
        
        # Add to SQL history
        self.message_history.add_message(message, metadata)
        
        # Add to vector store for semantic search
        if role in ["user", "assistant"]:
            await self.vector_store.add_texts(
                texts=[content],
                metadatas=[{**metadata, "role": role}],
                importance_scores=[importance_score]
            )
    
    async def get_context(self, query: str) -> Dict[str, Any]:
        """Get comprehensive context for a query using ReAct principles."""
        # Step 1: Get basic memory variables
        memory_variables = self.memory.load_memory_variables({"input": query})
        
        # Step 2: Get semantic search results
        semantic_results = await self.vector_store.similarity_search_with_score(
            query=query,
            k=5,
            recency_boost=True
        )
        
        # Step 3: Perform reasoning about information needs using ReAct approach
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
        
        reasoning_response = self.llm([HumanMessage(content=reasoning_prompt)])
        
        # Process semantic results for context
        semantic_context = []
        for doc, score in semantic_results:
            semantic_context.append({
                "content": doc.page_content,
                "score": score,
                "metadata": doc.metadata
            })
        
        # Construct final context with reasoning
        context = {
            **memory_variables,
            "semantic_context": semantic_context,
            "query_reasoning": reasoning_response.content,
            "entity_memory": self.entity_memory.load_memory_variables({})["entity_store"]
        }
        
        return context
    
    def get_session_messages(self, limit: int = 50) -> List[Dict]:
        """Get messages for API responses."""
        return self.message_history.get_session_messages(limit)
    
    def clear(self) -> None:
        """Clear all memory components."""
        self.message_history.clear()
        self.vector_store.clear()
        self.memory.clear()
        self.entity_cache = {} 