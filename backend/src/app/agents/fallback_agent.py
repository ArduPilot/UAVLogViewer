from typing import Any, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
import os

from agents.agents import Agent

class FallbackAgent(Agent):
    """LLM-driven agent for handling out-of-scope or unclear queries."""
    
    def __init__(self, session_id: str, session_store: Optional[Any] = None):
        self.session_id = session_id
        self.session_store = session_store
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.system_prompt = SystemMessage(content=(
            "You are a helpful assistant for a UAV flight log analysis tool. Your role is to handle queries that "
            "are outside the main scope of flight log analysis. When users ask unrelated questions:\n"
            "1. Politely explain that you're focused on UAV flight data\n"
            "2. Provide a brief, relevant response if possible\n"
            "3. Gently guide the user back to flight log topics\n"
            "4. Keep responses concise and professional\n\n"
            "For unclear queries, ask clarifying questions to better understand what the user needs help with."
        ))

    def chat(self, message: str) -> str:
        messages = [self.system_prompt]
        
        if self.session_store:
            history = self.session_store.get_history(self.session_id)[-3:]  # Get last 3 turns
            for msg in history:
                role = "user" if msg["role"] == "user" else "assistant"
                msg_class = HumanMessage if role == "user" else AIMessage
                messages.append(msg_class(content=msg["content"]))
        
        messages.append(HumanMessage(content=message))
        
        response = self.llm(messages)
        return response.content