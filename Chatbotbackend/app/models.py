from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# Response model for a successful file upload
class FileUploadResponse(BaseModel):
    fileId: str = Field(..., alias="fileId") 
    filename: str
    message: str
    summary: Optional[Dict[str, Any]] = None

# Format of individual messages sent by the user or assistant (input side)
class ChatMessageInput(BaseModel):
    role: str
    content: str

# Format of messages used in the response back to the frontend
class ChatMessageOutput(BaseModel):
    role: str
    content: str

# Format of a chat request sent to the backend from the frontend
class ChatRequest(BaseModel):
    fileId: str 
    message: str
    history: List[ChatMessageInput]

# Format of the chat response returned from the backend
class ChatResponse(BaseModel):
    history: List[ChatMessageOutput]

# Optional structure for Google Gemini-compatible message part
class GeminiMessagePart(BaseModel): # Kept for potential direct API use or other models
    text: str

# Optional structure for Google Gemini-compatible message
class GeminiMessage(BaseModel): # Kept for potential direct API use or other models
    role: str
    parts: List[GeminiMessagePart]