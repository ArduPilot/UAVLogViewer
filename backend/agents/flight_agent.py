from typing import Dict, Any, Optional, List
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from chat.memory_manager import EnhancedMemoryManager
from telemetry.analyzer import TelemetryAnalyzer
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

class FlightAgent:
    """Agent for analyzing flight data and maintaining conversation memory."""
    
    def __init__(
        self,
        session_id: str,
        telemetry_data: Dict,
        analyzer: TelemetryAnalyzer,
        db_session,
        memory_window_size: int = 10
    ):
        self.session_id = session_id
        self.telemetry_data = telemetry_data
        self.analyzer = analyzer
        
        # Initialize memory manager with configurable window size
        self.memory_manager = EnhancedMemoryManager(
            session_id=session_id,
            db_session=db_session,
            window_size=memory_window_size
        )
        
        # Initialize chat model with GPT-4o
        self.chat = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Enhanced ReAct prompt template for reasoned action
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=(
                "You are an expert UAV flight data analyst with deep knowledge of the MAVLink protocol. "
                "Your primary role is to analyze flight logs and telemetry data to provide detailed insights. "
                "\n\nAs an agentic AI, you operate on ReAct principles - Reason and Act. For each query:"
                "\n1. THINK: Reason carefully about what the user is asking and what information you need"
                "\n2. ANALYZE: Consider what flight data and telemetry is relevant to the query"
                "\n3. RECALL: Use your memory of past conversations and previous analysis"
                "\n4. RESPOND: Provide a clear, actionable response with specific evidence"
                "\n\nAvailable Knowledge:"
                "\n- MAVLink protocol expertise (messages, parameters, structure)"
                "\n- Flight dynamics and UAV systems"
                "\n- Telemetry data interpretation"
                "\n- Anomaly detection techniques"
                "\n\nAvailable Context:"
                "\n- Chat history with summary"
                "\n- Entity memory tracking key parameters"
                "\n- Semantic search results of past interactions"
                "\n- Flight data analysis tools"
                "\n\nGuidelines:"
                "\n- Focus on showing technical expertise with specific references to flight data"
                "\n- Always use evidence and metrics when making claims"
                "\n- Be proactive in identifying issues the user might not have noticed"
                "\n- Avoid generic responses - be specific to this exact flight and situation"
                "\n- Connect flight parameters to practical implications for the operator"
            )),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessage(content=(
                "User Query: {input}\n\n"
                "Step 1 - THINK: Let me reason through what's being asked and what I need to analyze...\n"
                "{query_reasoning}\n\n"
                "Step 2 - ANALYZE: Based on the telemetry data and the query intent, I can see...\n"
                "{flight_analysis}\n\n"
                "Step 3 - RECALL: From our conversation history and prior analysis, I know...\n"
                "{memory_recall}\n\n"
                "Step 4 - RESPOND: Based on my analysis, here's what I can tell you:"
            ))
        ])

    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message with enhanced ReAct framework."""
        try:
            # Get comprehensive context using memory manager
            context = await self.memory_manager.get_context(message)
            
            # Perform detailed flight data analysis based on query reasoning
            query_reasoning = context.get("query_reasoning", "No specific reasoning available.")
            flight_analysis = await self._perform_flight_analysis(message, query_reasoning)
            
            # Process memory recall from both entity memory and semantic context
            memory_recall = self._process_memory_recall(context)
            
            # Format chat history from the summary buffer memory
            chat_history = context.get("chat_history", [])
            
            # Generate response using ReAct framework
            response = self.chat(self.prompt.format_messages(
                input=message,
                query_reasoning=query_reasoning,
                flight_analysis=flight_analysis,
                memory_recall=memory_recall,
                chat_history=chat_history
            ))
            
            # Extract metadata from reasoning for storage
            metadata = self._extract_metadata_from_reasoning(query_reasoning)
            
            # Save interaction to memory with enhanced metadata
            await self.memory_manager.add_message(
                role="user",
                content=message,
                metadata=metadata
            )
            
            await self.memory_manager.add_message(
                role="assistant",
                content=response.content,
                metadata={
                    **metadata,
                    "analysis_performed": True,
                    "flight_data_analyzed": flight_analysis is not None
                }
            )
            
            return {
                "answer": response.content,
                "analysis": flight_analysis,
                "context_summary": self._summarize_context(context)
            }
            
        except Exception as e:
            # Enhanced error handling
            error_msg = f"Error processing message: {str(e)}"
            
            await self.memory_manager.add_message(
                role="system",
                content=error_msg,
                metadata={
                    "error": True,
                    "error_type": type(e).__name__,
                    "query": message
                }
            )
            
            return {
                "answer": "I apologize, but I encountered an error while processing your request. Please try again.",
                "analysis": None,
                "error": str(e)
            }
    
    async def _perform_flight_analysis(self, query: str, reasoning: str) -> str:
        """Perform targeted flight data analysis based on query and reasoning."""
        # Use reasoning to determine what to analyze
        analyzer_result = self.analyzer.analyze_for_query(query)
        
        # Format analysis result as a readable string
        if isinstance(analyzer_result, dict):
            formatted_result = "Flight Data Analysis:\n"
            
            for key, value in analyzer_result.items():
                if isinstance(value, dict):
                    formatted_result += f"- {key}:\n"
                    for sub_key, sub_value in value.items():
                        formatted_result += f"  - {sub_key}: {sub_value}\n"
                else:
                    formatted_result += f"- {key}: {value}\n"
                    
            return formatted_result
        
        return str(analyzer_result)
    
    def _process_memory_recall(self, context: Dict) -> str:
        """Process memory recall from entity memory and semantic context."""
        # Extract entity memory
        entity_memories = context.get("entity_memory", {})
        entity_str = "Entity Memory:\n"
        
        if entity_memories:
            for entity, info in entity_memories.items():
                entity_str += f"- {entity}: {info}\n"
        else:
            entity_str += "- No specific entities tracked yet.\n"
        
        # Extract semantic context
        semantic_results = context.get("semantic_context", [])
        semantic_str = "\nRelevant Past Context:\n"
        
        if semantic_results:
            for i, result in enumerate(semantic_results[:3]):  # Limit to top 3
                content = result.get("content", "")
                if len(content) > 150:
                    content = content[:147] + "..."
                semantic_str += f"- {content}\n"
        else:
            semantic_str += "- No relevant past context found.\n"
        
        return entity_str + semantic_str
    
    def _extract_metadata_from_reasoning(self, reasoning: str) -> Dict[str, Any]:
        """Extract structured metadata from reasoning output."""
        metadata = {
            "query_type": "general",
            "has_analysis": True
        }
        
        # Extract query type from reasoning if available
        if "Query type:" in reasoning:
            query_type_line = reasoning.split("Query type:")[1].split("\n")[0].strip()
            metadata["query_type"] = query_type_line
        
        # Extract relevant parameters if available
        if "Relevant flight parameters:" in reasoning:
            params_line = reasoning.split("Relevant flight parameters:")[1].split("\n")[0].strip()
            metadata["relevant_parameters"] = params_line
        
        # Extract temporal focus if available
        if "Temporal focus:" in reasoning:
            temporal_line = reasoning.split("Temporal focus:")[1].split("\n")[0].strip()
            metadata["temporal_focus"] = temporal_line
        
        return metadata

    def _summarize_context(self, context: Dict) -> Dict:
        """Create a summary of the context used in the response."""
        summary = {
            "chat_history_messages": len(context.get("chat_history", [])),
            "semantic_results": len(context.get("semantic_context", [])),
            "has_entity_memory": bool(context.get("entity_memory")),
            "reasoning_performed": bool(context.get("query_reasoning"))
        }
        
        return summary

    def clear_memory(self) -> None:
        """Clear all memory components."""
        self.memory_manager.clear() 