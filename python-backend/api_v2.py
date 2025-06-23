import os
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import logging
from mav_chatbot import MAVChatbot
import shutil
import tempfile
from typing import Optional, Dict, Any, List
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="UAV Logger Chatbot API", version="2.0.0")

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global chatbot instance
chatbot = MAVChatbot()

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "UAV Logger Agentic Chatbot API",
        "version": "2.0.0",
        "endpoints": {
            "upload_and_chat": "POST /upload-and-chat",
            "chat": "POST /chat",
            "upload_log": "POST /upload-log",
            "flight_summary": "GET /flight-summary",
            "conversation_history": "GET /conversation-history",
            "clear_conversation": "POST /clear-conversation",
            "health": "GET /health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "chatbot_initialized": chatbot.is_initialized,
        "current_log_file": chatbot.current_log_file
    }

@app.post("/upload-log")
async def upload_log(file: UploadFile = File(...)):
    """
    Upload a MAVLink log file (.bin) for analysis.
    This endpoint loads and analyzes the log file for use with the chatbot.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.bin'):
            raise HTTPException(status_code=400, detail="Only .bin files are supported")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name
        
        # Load and analyze the log file
        success = chatbot.load_and_analyze_log(temp_path)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to analyze log file")
        
        # Get flight summary
        summary = chatbot.get_flight_summary()
        
        return {
            "message": "Log file uploaded and analyzed successfully",
            "filename": file.filename,
            "file_size": file.size,
            "analysis_complete": True,
            "flight_summary": summary.get('summary_stats', {})
        }
        
    except Exception as e:
        logger.error(f"Error uploading log file: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing log file: {str(e)}")

@app.post("/chat")
async def chat(message: str = Form(...)):
    """
    Send a message to the chatbot and get a response.
    Requires a log file to be uploaded first.
    """
    try:
        if not chatbot.is_initialized:
            raise HTTPException(
                status_code=400, 
                detail="No log file loaded. Please upload a log file first using /upload-log"
            )
        
        response = chatbot.get_response(message)
        
        return {
            "response": response,
            "message": message,
            "timestamp": "2024-01-01T00:00:00Z"  # You could add actual timestamp here
        }
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing chat message: {str(e)}")

@app.post("/upload-and-chat")
async def upload_and_chat(message: str = Form(...), file: UploadFile = File(None)):
    """
    Upload a log file and send a chat message in one request.
    This is a convenience endpoint that combines upload and chat functionality.
    """
    try:
        # If file is provided, upload and analyze it
        if file:
            if not file.filename.endswith('.bin'):
                raise HTTPException(status_code=400, detail="Only .bin files are supported")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as temp_file:
                shutil.copyfileobj(file.file, temp_file)
                temp_path = temp_file.name
            
            # Load and analyze the log file
            success = chatbot.load_and_analyze_log(temp_path)
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to analyze log file")
        
        # Check if chatbot is initialized
        if not chatbot.is_initialized:
            raise HTTPException(
                status_code=400, 
                detail="No log file loaded. Please provide a log file or upload one first."
            )
        
        # Get response from chatbot
        response = chatbot.get_response(message)
        
        return {
            "response": response,
            "message": message,
            "file_uploaded": file is not None,
            "filename": file.filename if file else None,
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"Error in upload_and_chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/flight-summary")
async def get_flight_summary():
    """
    Get a comprehensive summary of the loaded flight data.
    """
    try:
        if not chatbot.is_initialized:
            raise HTTPException(
                status_code=400, 
                detail="No log file loaded. Please upload a log file first."
            )
        
        summary = chatbot.get_flight_summary()
        
        return {
            "flight_summary": summary,
            "analysis_complete": True
        }
        
    except Exception as e:
        logger.error(f"Error getting flight summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving flight summary: {str(e)}")

@app.get("/conversation-history")
async def get_conversation_history():
    """
    Get the current conversation history with the chatbot.
    """
    try:
        history = chatbot.get_conversation_history()
        
        return {
            "conversation_history": [
                {"role": role, "content": content} 
                for role, content in history
            ],
            "total_exchanges": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation history: {str(e)}")

@app.post("/clear-conversation")
async def clear_conversation():
    """
    Clear the conversation history while keeping the loaded log data.
    """
    try:
        chatbot.clear_conversation()
        
        return {
            "message": "Conversation history cleared successfully",
            "log_file_loaded": chatbot.is_initialized
        }
        
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing conversation: {str(e)}")

@app.get("/example-questions")
async def get_example_questions():
    """
    Get example questions that users can ask about the flight data.
    """
    return {
        "example_questions": [
            "What was the highest altitude reached during the flight?",
            "When did the GPS signal first get lost?",
            "What was the maximum battery temperature?",
            "How long was the total flight time?",
            "List all critical errors that happened mid-flight.",
            "When was the first instance of RC signal loss?",
            "Are there any anomalies in this flight?",
            "Can you spot any issues in the GPS data?",
            "What was the average climb rate during the flight?",
            "Did the battery voltage show any concerning patterns?",
            "What was the maximum number of satellites visible?",
            "Were there any sudden altitude changes?",
            "What was the flight mode during takeoff?",
            "Did the aircraft experience any vibration issues?",
            "What was the maximum airspeed recorded?"
        ],
        "categories": {
            "basic_flight_data": [
                "What was the highest altitude reached during the flight?",
                "How long was the total flight time?",
                "What was the maximum airspeed recorded?"
            ],
            "system_health": [
                "What was the maximum battery temperature?",
                "List all critical errors that happened mid-flight.",
                "Did the aircraft experience any vibration issues?"
            ],
            "signal_quality": [
                "When did the GPS signal first get lost?",
                "When was the first instance of RC signal loss?",
                "What was the maximum number of satellites visible?"
            ],
            "anomaly_detection": [
                "Are there any anomalies in this flight?",
                "Can you spot any issues in the GPS data?",
                "Were there any sudden altitude changes?",
                "Did the battery voltage show any concerning patterns?"
            ]
        }
    }

if __name__ == '__main__':
    uvicorn.run("api_v2:app", host="0.0.0.0", port=8001, reload=True)
