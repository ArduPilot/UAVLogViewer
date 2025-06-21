from openai import OpenAI
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
from tools.flight_data_db import FlightDataDB
from typing import Dict, List, Any, Optional
from models import Message, FlightData, AgentResponse
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

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

class QueryClassifierAgent:
    """Classifies user queries to determine which agent should handle them."""
    
    def __init__(self):
        self.system_prompt = """You are a query classification expert for UAV flight data analysis. Your role is to determine whether a query requires simple data retrieval (SQL) or complex data analysis.
        
        Guidelines:
        1. Classify as SQL if the query:
           - Asks for specific data points
           - Requests simple aggregations (count, sum, avg)
           - Asks about specific events or parameters
           - Requires basic filtering or sorting
        
        2. Classify as 'ANALYSIS' if the query:
           - Asks for patterns or trends
           - Requires statistical analysis
           - Asks for correlations between parameters
           - Involves clustering or classification
           - Requires complex data transformations
           - Asks for performance metrics or insights

        3. Classify as 'NONE' if the query is not related to the UAV's flight data.
        
        Respond with either 'SQL', 'ANALYSIS', or 'NONE' only."""

    def classify_query(self, query: str) -> str:
        """Classifies the query and returns either 'SQL' or 'ANALYSIS'."""
        try:
            logger.info(f"\n\n\n\n\nClassifying query: {query}\n\n\n")
            messages: List[ChatCompletionMessageParam] = [
                ChatCompletionSystemMessageParam(role="system", content=self.system_prompt),
                ChatCompletionUserMessageParam(role="user", content=f"Classify this query: {query}")
            ]
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.1,
                max_tokens=10
            )
            
            classification = response.choices[0].message.content
            if classification is None:
                raise Exception("No content received from OpenAI API")
            classification = classification.strip().upper()
            logger.info(f"Query classified as: {classification}")
            
            if classification not in ['SQL', 'ANALYSIS']:
                logger.warning(f"Invalid classification received: {classification}, defaulting to NONE")
                return 'NONE'
                
            return classification
            
        except Exception as e:
            logger.error(f"Error classifying query: {str(e)}")
            return 'NONE'