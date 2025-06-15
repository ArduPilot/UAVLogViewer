from typing import Dict, List, Any
import openai
import json
from datetime import datetime


class QueryAgent:
    """Agent responsible for answering specific questions about flight data."""
    
    def __init__(self):
        self.system_prompt = """You are a UAV flight data expert assistant. Your role is to answer specific questions about flight data.
        Guidelines:
        1. Be precise and technical in your responses
        2. Reference specific data points and timestamps
        3. Explain technical terms when used
        4. If the question is unclear, ask for clarification
        5. If you notice concerning patterns, point them out
        
        Use the ArduPilot documentation (https://ardupilot.org/plane/docs/logmessages.html) as reference."""
        
    def answer_question(self, question: str, flight_data: Dict[str, Any], conversation_history: List[Dict[str, str]]) -> str:
        """Answer a specific question about the flight data."""
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                *conversation_history,
                {"role": "user", "content": f"Flight data context:\n{json.dumps(flight_data, indent=2)}\n\nQuestion: {question}"}
            ]
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Error answering question: {str(e)}"

class AgentOrchestrator:
    """Orchestrates multiple AI agents for comprehensive flight data analysis."""
    
    def __init__(self):
        self.query_agent = QueryAgent()
        self.conversations = {}
        self.flight_data = {}
        
    def _get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """Get or create conversation history for a session."""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        return self.conversations[session_id]
        
    def process_message(self, message: str, session_id: str, flight_data: Dict[str, Any] = {}) -> Dict[str, Any]:
        """Process a user message and coordinate agent responses."""
        conversation = self._get_conversation_history(session_id)
        if flight_data:
            self.flight_data[session_id] = flight_data
        
        # Add user message to conversation history
        conversation.append({"role": "user", "content": message})
        
        try:
            # Determine if this is a general question or requires flight data analysis
            response = self.query_agent.answer_question(message, self.flight_data, conversation)
            
            # Add assistant response to conversation history
            conversation.append({"role": "assistant", "content": response})
            
            return {
                "response": response,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_message = f"Error processing message: {str(e)}"
            conversation.append({"role": "assistant", "content": error_message})
            return {
                "response": error_message,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }