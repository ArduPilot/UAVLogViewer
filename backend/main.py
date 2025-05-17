from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import uuid
import asyncio
import re  # For regex pattern matching

from agents.flight_agent import FlightAgent
from telemetry.parser import TelemetryParser
from telemetry.analyzer import TelemetryAnalyzer

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
        
        try:
            # Parse telemetry data with the updated parser (returns DataFrames with only important columns)
            print(f"Parsing telemetry data from {file.filename}...")
            parser = TelemetryParser(file_path)
            telemetry_data = parser.parse()
            
            # Verify we have meaningful data before proceeding
            if not telemetry_data or all(df.empty for df in telemetry_data.values()):
                raise ValueError("No meaningful telemetry data could be extracted from the log file")
            
            # Create analyzer with the parsed telemetry data
            print("Creating analyzer with parsed telemetry data...")
            analyzer = TelemetryAnalyzer(telemetry_data)
            
            # Create new flight session
            session_id = str(uuid.uuid4())
            
            # Store session info
            flight_sessions[session_id] = FlightSession(
                id=session_id,
                created_at=datetime.now(timezone.utc),
                telemetry_data=telemetry_data
            )
            
            # Create flight agent with the analyzer
            print(f"Creating flight agent for session {session_id}...")
            active_sessions[session_id] = FlightAgent(
                session_id=session_id,
                telemetry_data=telemetry_data,
                analyzer=analyzer
            )
            
            # Cleanup
            os.remove(file_path)
            
            print(f"Successfully created session {session_id} from {file.filename}")
            return {"session_id": session_id, "message": "Log file processed successfully"}
        
        except Exception as processing_error:
            # If file exists but processing fails, clean up the file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Log the error with stack trace
            print(f"ERROR processing log file: {str(processing_error)}")
            import traceback
            print(f"UPLOAD PROCESSING ERROR: {traceback.format_exc()}")
            
            # Return specific error for API clients
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to process log file: {str(processing_error)}"
            )
    
    except Exception as e:
        # Log the error with stack trace
        print(f"ERROR in upload endpoint: {str(e)}")
        import traceback
        print(f"UPLOAD ENDPOINT ERROR: {traceback.format_exc()}")
        
        # Return specific error for API clients
        raise HTTPException(
            status_code=400, 
            detail=f"Upload failed: {str(e)}"
        )

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    session_id = message.session_id
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Process message with flight agent with a hard timeout at API level
        try:
            # Set an overall timeout for the chat operation
            result = await asyncio.wait_for(
                active_sessions[session_id].process_message(message.message),
                timeout=90.0  # 90 seconds max at API level
            )
        except asyncio.TimeoutError:
            print(f"ERROR: Chat endpoint timed out after 90 seconds for session {session_id}")
            raise HTTPException(
                status_code=504, 
                detail="The request took too long to process. Please try a simpler query."
            )
        
        # Check if result contains an error field, which indicates a failure
        if "error" in result and result["error"]:
            print(f"ERROR returned from flight agent: {result['error']}")
            
            # Provide the error message to the client
            raise HTTPException(
                status_code=500, 
                detail=f"Error processing chat: {result['error']}"
            )
        
        # Build analysis data from the result
        analysis_data = {
            "type": "Flight Analysis",
            "metrics": {},
            "anomalies": "No anomalies detected"
        }
        
        # Extract metrics from result
        if "analysis" in result and isinstance(result["analysis"], dict):
            # Extract metrics data, prioritizing proper altitude metrics
            metrics_data = result["analysis"].get("metrics", {})
            
            # Look for altitude analysis in the result
            altitude_analysis = None
            if "altitude_analysis" in result["analysis"]:
                altitude_analysis = result["analysis"]["altitude_analysis"]
                # Store the altitude analysis in metrics explicitly
                if altitude_analysis and "statistics" in altitude_analysis:
                    metrics_data["altitude"] = altitude_analysis["statistics"]
                    # Also record if this was converted from absolute altitude
                    if "is_absolute_altitude" in altitude_analysis:
                        metrics_data["altitude"]["source_was_absolute"] = altitude_analysis["is_absolute_altitude"]
                    if "field_used" in altitude_analysis:
                        metrics_data["altitude"]["field_used"] = altitude_analysis["field_used"]
            elif "altitude" in metrics_data:
                altitude_analysis = {"statistics": metrics_data["altitude"]}
            
                            # If we have altitude analysis, make sure it's using reasonable values
                if altitude_analysis and "statistics" in altitude_analysis:
                    alt_stats = altitude_analysis["statistics"]
                    # Check if the max altitude is reasonable
                    max_alt = alt_stats.get("max")
                    if max_alt is not None and isinstance(max_alt, (int, float)) and max_alt > 1000:
                        print(f"WARNING: Unreasonably high max altitude in API response: {max_alt}")
                        # Try to apply an additional correction factor if it looks like sea level data
                        if max_alt > 100000:  # Extremely high, might be in mm or µm
                            alt_stats["max"] = max_alt / 1000.0
                            print(f"Applied mm->m conversion: {alt_stats['max']}")
                        else:
                            # Otherwise, flag this value as suspicious
                            alt_stats["max"] = f"Suspicious value: {max_alt}"
                    
                    # Verify min altitude is present
                    min_alt = alt_stats.get("min")
                    if min_alt is None:
                        print(f"WARNING: Missing min altitude in API response, attempting to calculate")
                        # If missing, try to derive from range
                        if "range" in alt_stats and max_alt is not None and isinstance(max_alt, (int, float)):
                            range_value = alt_stats.get("range")
                            if isinstance(range_value, (int, float)):
                                alt_stats["min"] = max_alt - range_value
                                print(f"Calculated min altitude: {alt_stats['min']}")
                    
                    # Use the verified altitude stats
                    metrics_data["altitude"] = alt_stats
            
            # Include up to 30 metrics fields maximum to avoid overwhelming response
            field_count = 0
            pruned_metrics = {}
            
            # First, add any altitude-related metrics
            for field_name, field_data in metrics_data.items():
                if any(term in field_name.lower() for term in ["alt", "height"]):
                    pruned_metrics[field_name] = field_data
                    field_count += 1
            
            # Then add other important metrics
            for field_name, field_data in metrics_data.items():
                if field_count >= 30:
                    break
                    
                if field_name not in pruned_metrics and any(term in field_name.lower() for term in 
                                                           ["speed", "battery", "volt", "gps", "position"]):
                    pruned_metrics[field_name] = field_data
                    field_count += 1
            
            # Finally add remaining metrics up to the limit
            for field_name, field_data in metrics_data.items():
                if field_count >= 30:
                    break
                    
                if field_name not in pruned_metrics:
                    pruned_metrics[field_name] = field_data
                    field_count += 1
            
            analysis_data["metrics"] = pruned_metrics
            
            # Extract anomalies data
            anomalies_data = result["analysis"].get("anomalies", [])
            if isinstance(anomalies_data, list) and anomalies_data:
                analysis_data["anomalies"] = f"Detected {len(anomalies_data)} anomalies"
            elif isinstance(anomalies_data, str):
                analysis_data["anomalies"] = anomalies_data
        
        # CRITICAL: Check LLM response for unreasonable altitude values and correct them
        response_text = result["answer"]
        
        # Fix incorrect statements about missing altitude data
        if "altitude" in analysis_data["metrics"] and "min" in analysis_data["metrics"]["altitude"]:
            min_alt_value = analysis_data["metrics"]["altitude"]["min"]
            if isinstance(min_alt_value, (int, float)):
                min_alt_str = f"{min_alt_value:.1f}" if min_alt_value != int(min_alt_value) else f"{int(min_alt_value)}"
                # Replace incorrect statements about min altitude not being available
                incorrect_patterns = [
                    r"(?:does not explicitly state|doesn't include|doesn't show|no data for|missing|unavailable) (?:the )?minimum altitude",
                    r"minimum altitude (?:is not available|is missing|was not provided|isn't included|isn't given)",
                    r"not (?:the|a) minimum altitude",
                    r"without the minimum (?:altitude|value)"
                ]
                for pattern in incorrect_patterns:
                    response_text = re.sub(
                        pattern, 
                        f"minimum altitude was {min_alt_str} m", 
                        response_text, 
                        flags=re.IGNORECASE
                    )
        
        # Look for absolute altitude values and replace them with relative values
        altitude_patterns = [
            r"(\d{3,})(?:\.?\d*)?(?:\s*|\-)?(?:m|meters|metre)",  # matches "644.5 meters" or "644 m"
            r"altitude(?:.+?)(?:was|of|reached)(?:.+?)(\d{3,})(?:\.?\d*)?(?:\s*|\-)?(?:m|meters|metre)", # matches "altitude was 644.5 meters"
            r"(?:max|maximum)(?:.+?)(?:altitude|height)(?:.+?)(\d{3,})(?:\.?\d*)?(?:\s*|\-)?(?:m|meters|metre)" # matches "max altitude of 644.5 meters"
        ]
        
        # Get the correct altitude value from our processed metrics
        # Look for the most reliable altitude value from our metrics
        correct_max_altitude = None
        
        # Try to get from the altitude field we trust
        if "altitude" in analysis_data["metrics"] and "max" in analysis_data["metrics"]["altitude"]:
            max_val = analysis_data["metrics"]["altitude"]["max"]
            if isinstance(max_val, (int, float)) and max_val < 1000:
                correct_max_altitude = max_val
                
        # If we still don't have a value, try other altitude fields
        if correct_max_altitude is None:
            for field_name, field_data in analysis_data["metrics"].items():
                if ("alt" in field_name.lower() or "height" in field_name.lower()) and isinstance(field_data, dict):
                    # Skip absolute altitude fields that mention "sea level" or "absolute"
                    if "sea" in field_name.lower() or "absolute" in field_name.lower():
                        continue
                        
                    if "max" in field_data:
                        max_val = field_data["max"]
                        if isinstance(max_val, (int, float)) and max_val < 1000:
                            correct_max_altitude = max_val
                            break
        
        # If we found a reasonable altitude value, use it to correct the response
        if correct_max_altitude is not None:
            for pattern in altitude_patterns:
                # Find all matches in the response
                matches = re.findall(pattern, response_text, re.IGNORECASE)
                for match in matches:
                    # Convert match to numeric value
                    try:
                        value = float(match.replace(",", ""))
                        # Only replace if it's suspiciously high
                        if value > 100:  # Higher than 100 meters might be suspicious 
                            # Replace the value
                            formatted_old = f"{value:,}" if "," in match else str(value)
                            formatted_new = f"{correct_max_altitude:.1f}"
                            response_text = response_text.replace(formatted_old, formatted_new)
                            print(f"Replaced suspicious altitude {match} with {formatted_new} meters")
                    except (ValueError, TypeError):
                        continue  # Not a valid number, skip it
        
        # Return the corrected response
        return ChatResponse(
            response=response_text,
            analysis=analysis_data
        )
    except HTTPException:
        # Re-raise HTTP exceptions without wrapping
        raise
    except asyncio.CancelledError:
        # Handle task cancellation explicitly
        print(f"CANCELLED: Chat task was cancelled for session {session_id}")
        raise HTTPException(
            status_code=504,
            detail="The request was cancelled due to server load or timeout."
        )
    except Exception as e:
        print(f"ERROR in /chat endpoint: {str(e)}")
        import traceback
        print(f"CHAT ENDPOINT ERROR TRACEBACK: {traceback.format_exc()}")
        
        # Provide a specific error message
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing chat message: {str(e)}"
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

@app.get("/")
async def root():
    return {"status": "API is running", "endpoints": ["/upload", "/chat", "/sessions", "/session/{session_id}/messages"]}

if __name__ == "__main__":
    import uvicorn
    print(f"Starting server on {HOST}:{PORT}")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True) 