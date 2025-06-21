from typing import Dict, Any, Optional
from openai.resources.chat.chat import Chat
from pydantic import BaseModel
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam

class Message(BaseModel):
    role: str
    content: str

    def to_openai_message(self) -> ChatCompletionMessageParam:
        if self.role == "system":
            return ChatCompletionSystemMessageParam(role="system", content=self.content)
        elif self.role == "user":
            return ChatCompletionUserMessageParam(role="user", content=self.content)
        elif self.role == "assistant":
            return ChatCompletionAssistantMessageParam(role="assistant", content=self.content)
        else:
            raise ValueError(f"Unsupported role: {self.role}")

class FlightData(BaseModel):
    data: Dict[str, Any]

class AgentResponse(BaseModel):
    message: str
    sessionId: str
    error: Optional[str] = None 