from typing import Dict, List, Any, Optional
from openai import OpenAI
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import logging

from models import Message, FlightData, AgentResponse
from agents.query_classifier_agent import QueryClassifierAgent
from agents.sql_query_agent import SQLQueryAgent
from agents.data_analysis_agent import DataAnalysisAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logging.getLogger("openai").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class AgentOrchestrator:
    """Orchestrates multiple AI agents for comprehensive flight data analysis."""
    
    def __init__(self, flight_db):
        logger.info("Initializing AgentOrchestrator")
        self.sql_agent = SQLQueryAgent()
        self.data_analysis_agent = DataAnalysisAgent()
        self.conversations: Dict[str, List[Message]] = {}
        self.flight_db = flight_db
        
    def _get_conversation_history(self, session_id: str) -> List[Message]:
        """Get or create conversation history for a session."""
        logger.debug(f"Getting conversation history for session {session_id}")
        if session_id not in self.conversations:
            logger.info(f"Creating new conversation history for session {session_id}")
            self.conversations[session_id] = []
        return self.conversations[session_id]
        
    def process_message(self, message: str, session_id: str) -> AgentResponse:
        """Process a user message and coordinate agent responses."""
        logger.info(f"Processing message for session {session_id}: {message}")
        
        conversation = self._get_conversation_history(session_id)
        
        # Add user message to conversation history
        conversation.append(Message(role="user", content=message))
        
        try:
            # Get database connection and schema
            logger.debug(f"Getting database information for session {session_id}")
            db_schema = self.flight_db.get_database_information(session_id)
            
            # Classify query
            query_classifier = QueryClassifierAgent()
            classification = query_classifier.classify_query(message)
            logger.info(f"Query classified as: {classification}")

            if classification == 'SQL':
                # Process the question using SQL agent
                logger.info("Processing question through SQL agent")
                response = self.sql_agent.process_question(
                    session_id,
                    message,
                    db_schema,
                    conversation, 
                    self.flight_db
                )
            elif classification == 'ANALYSIS':
                # Process the question using data analysis agent
                logger.info("Processing question through data analysis agent")
                response = self.data_analysis_agent.analyze(
                    message,
                    self.flight_db,
                    session_id,
                    conversation
                )
            else:
                response = "I can help you with questions about the UAV's flight data. Ask me something like 'What was the average altitude during the flight?'."
            
            # Add assistant response to conversation history
            conversation.append(Message(role="assistant", content=response))
            
            logger.info(f"Successfully processed message for session {session_id}")
            logger.info(f"Response: {response}")
            return AgentResponse(
                message=response,
                sessionId=session_id,
                error=None
            )
            
        except Exception as e:
            error_message = f"Error processing message. Please try again."
            logger.error(f"Error in process_message: {str(e)}", exc_info=True)
            conversation.append(Message(role="assistant", content=error_message))
            return AgentResponse(
                message=error_message,
                sessionId=session_id,
                error=error_message
            )