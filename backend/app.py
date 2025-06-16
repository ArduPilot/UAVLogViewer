from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv
from agent_orchestrator import AgentOrchestrator
from typing import Optional, Dict, Any
from tools.flight_data_db import FlightDataDB
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    try:
        flight_db.close()
        print("Flight database connections closed successfully")
    except Exception as e:
        print(f"Error closing flight database connections: {str(e)}")

app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize agent orchestrator and flight data database
flight_db = FlightDataDB("data/flight_data")  # Using a file-based database for persistence
orchestrator = AgentOrchestrator(flight_db)

class ChatRequest(BaseModel):
    message: str
    sessionId: Optional[str] = None
    flightData: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    message: str
    sessionId: str
    error: Optional[str] = None

@app.get("/")
async def index():
    return {"message": "Server is running"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        if not request.message:
            raise HTTPException(status_code=400, detail="No message provided")
            
        # Generate new session ID if none provided
        session_id = request.sessionId or str(uuid.uuid4())
        print(f"Received flight data? : {'Yes' if request.flightData else 'No'}")

        if request.flightData and session_id not in flight_db.connections:
            # TODO: Remove logging
            # Also save to file for backup
            os.makedirs('logs', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'logs/flight_data_{timestamp}.txt'
            print(f"Saving flight data to {filename}")
            
            # Write flight data to file
            with open(filename, 'w') as f:
                f.write(f"Session ID: {session_id}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write("Flight Data:\n")
                f.write(json.dumps(request.flightData, indent=2))

            # Store flight data in DuckDB
            try:
                flight_db.store_flight_data(session_id, request.flightData)
                print(f"Stored flight data in DuckDB")
                
            except Exception as e:
                error_msg = f"Failed to store flight data: {str(e)}"
                print(error_msg)
                print(f"Session ID: {session_id}")
                print(f"Flight data type: {type(request.flightData)}")
                print(f"Flight data keys: {request.flightData.keys() if isinstance(request.flightData, dict) else 'Not a dictionary'}")
                raise HTTPException(status_code=500, detail=error_msg)
        

        print(f"Data logged, now processing message")
        try:
            response = orchestrator.process_message(
                request.message, 
                session_id,
            )
            
            return response
        except Exception as e:
            error_msg = f"Failed to process message: {str(e)}"
            print(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error in chat endpoint: {str(e)}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=True) 