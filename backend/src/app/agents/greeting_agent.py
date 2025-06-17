from typing import Any, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
import os

from agents.agents import Agent

class GreetingAgent(Agent):
    """LLM-driven agent for handling greetings, farewells, and casual conversation."""
    
    def __init__(self, session_id: str, session_store: Optional[Any] = None):
        self.session_id = session_id
        self.session_store = session_store
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.system_prompt = SystemMessage(content=(
            "You are a friendly and professional UAV flight log assistant. Your role is to handle greetings, "
            "farewells, and casual conversation while gently guiding users toward flight log analysis topics. "
            "Keep responses concise (1-2 sentences) and maintain a helpful, approachable tone. "
            "If the conversation strays from flight logs, politely guide it back to UAV topics."
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