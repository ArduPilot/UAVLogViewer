from abc import ABC, abstractmethod
from typing import Optional
import tiktoken


class Agent(ABC):
    """Base interface for all agent implementations.
    
    All agents must implement the chat method which processes user messages
    and returns an appropriate response.
    """
    
    @abstractmethod
    def chat(self, message: str) -> str:
        """Process a user message and return the agent's response.
        
        Args:
            message: The user's input message
            
        Returns:
            str: The agent's response to the message
        """
        pass

    def split_context_into_chunks(self, ctx: str, max_tokens: int = 20000):
        enc = tiktoken.encoding_for_model("gpt-4o-mini")
        tokens = enc.encode(ctx)

        chunks = []
        for i in range(0, len(tokens), max_tokens):
            chunk = enc.decode(tokens[i:i + max_tokens])
            chunks.append(chunk)

        return chunks