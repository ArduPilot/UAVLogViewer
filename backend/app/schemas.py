from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


class BootstrapRequest(BaseModel):
    client_session_id: Optional[str] = Field(default=None)
    summary: Dict[str, Any]
    signals: Optional[Dict[str, Any]] = Field(default=None)


class BootstrapResponse(BaseModel):
    session_id: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


