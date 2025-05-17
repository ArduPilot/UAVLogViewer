from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import uuid

from agents.flight_agent import FlightAgent
from telemetry.parser import TelemetryParser
from telemetry.analyzer import TelemetryAnalyzer
from chat.memory_manager import EnhancedMemoryManager

# Load environment variables
load_dotenv()

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080").split(",")
ALLOWED_METHODS = os.getenv("ALLOWED_METHODS", "GET,POST,PUT,DELETE").split(",")
ALLOWED_HEADERS = os.getenv("ALLOWED_HEADERS", "Content-Type,Accept,Origin,X-Requested-With").split(",")
CORS_MAX_AGE = int(os.getenv("CORS_MAX_AGE", "3600"))

# File upload configuration
TEMP_UPLOAD_DIR = os.getenv("TEMP_UPLOAD_DIR", "temp")

app = FastAPI()

# Add CORS middleware with explicit method and header restrictions
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["*"],  # Headers that can be exposed to the browser
    max_age=CORS_MAX_AGE,  # Maximum time to cache pre-flight requests (in seconds)
)

# In-memory storage
flight_sessions = {}
active_sessions = {}

class FlightSession(BaseModel):
    id: str
    created_at: datetime
    telemetry_data: Dict

class ChatMessage(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    analysis: Optional[Dict[str, Any]] = None

@app.post("/upload")
async def upload_log(file: UploadFile = File(...)):
    try:
        # Save file temporarily
        file_path = f"{TEMP_UPLOAD_DIR}/{file.filename}"
        os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Parse telemetry data
        parser = TelemetryParser(file_path)
        telemetry_data = parser.parse()
        
        # Create analyzer
        analyzer = TelemetryAnalyzer(telemetry_data)
        
        # Create new flight session
        session_id = str(uuid.uuid4())
        
        # Store session info
        flight_sessions[session_id] = FlightSession(
            id=session_id,
            created_at=datetime.now(timezone.utc),
            telemetry_data=telemetry_data
        )
        
        # Create flight agent with in-memory setup
        active_sessions[session_id] = FlightAgent(
            session_id=session_id,
            telemetry_data=telemetry_data,
            analyzer=analyzer
        )
        
        # Cleanup
        os.remove(file_path)
        
        return {"session_id": session_id, "message": "Log file processed successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    session_id = message.session_id
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Process message with flight agent
    result = await active_sessions[session_id].process_message(message.message)
    
    # Ensure analysis is a dictionary with actual data
    analysis_data = {
        "type": "Flight Analysis",
        "metrics": result.get("analysis", {}).get("metrics", "N/A"),
        "anomalies": result.get("analysis", {}).get("anomalies", "N/A")
    }
    
    return ChatResponse(
        response=result["answer"],
        analysis=analysis_data
    )

@app.get("/session/{session_id}/messages")
async def get_session_messages(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get session messages using memory manager
    messages = active_sessions[session_id].memory_manager.get_session_messages()
    
    return {"messages": messages}

@app.get("/sessions")
async def list_sessions():
    # Return all available flight sessions
    return {
        "sessions": [
            {
                "id": session_id,
                "created_at": session.created_at.isoformat(),
                "has_telemetry": bool(session.telemetry_data)
            } for session_id, session in flight_sessions.items()
        ]
    }

@app.delete("/session/{session_id}")
async def end_session(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Clean up session resources
    if session_id in active_sessions:
        active_sessions[session_id].clear_memory()
        del active_sessions[session_id]
    
    return {"message": "Session ended successfully"}

if __name__ == "__main__":
    import uvicorn
    print(f"Starting server on {HOST}:{PORT}")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True) 