from pydantic import BaseModel

class UploadResponse(BaseModel):
    session_id: str
    message: str = "File parsed successfully. Ask me anything about the flight!"

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    answer: str
