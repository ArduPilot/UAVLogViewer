import os
import sys 
import uuid
import shutil
from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
import json 
from dotenv import load_dotenv 
from werkzeug.utils import secure_filename

# Set up project root directory and add it to sys.path if not already present
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
    print(f"Added to sys.path: {PROJECT_ROOT}")

# Load environment variables from .env file
dotenv_path_main = os.path.join(PROJECT_ROOT, '.env') 
if os.path.exists(dotenv_path_main):
    load_dotenv(dotenv_path=dotenv_path_main)
    print(f".env file loaded from main.py (path: {dotenv_path_main})")
else:
    load_dotenv() 
    print("main.py: Attempted to load .env from default location or environment variables are already set.")

# Import internal modules
from app.models import FileUploadResponse, ChatRequest, ChatResponse, ChatMessageOutput, ChatMessageInput
from app.Services.mavlink_parser import parse_mavlink_log 
from app.Services.llm_service import call_llm_api 

# Constants for file handling
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads") 
MAX_FILE_SIZE_MB = 200  
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize FastAPI app
app = FastAPI(title="UAV Log Chatbot Backend")

# Enable CORS for all origins and methods
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# In-memory store for parsed MAVLink logs
parsed_log_data_store: Dict[str, Dict[str, Any]] = {}

# Endpoint to upload .bin log file
@app.post("/upload_log/", response_model=FileUploadResponse)
async def upload_log_file(file: UploadFile = File(...)):
    # Basic file validation
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected.")
    if not file.filename.lower().endswith('.bin'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .bin files are allowed.")
    
    # Read file contents and validate size
    file_contents = await file.read() 
    if len(file_contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413, 
            detail=f"File too large. Maximum size allowed is {MAX_FILE_SIZE_MB}MB."
        )

    # Generate unique ID and save file securely
    generated_file_id = uuid.uuid4().hex 
    safe_filename = secure_filename(file.filename)
    temp_filename = f"{generated_file_id}_{safe_filename}" 
    temp_filepath = os.path.join(UPLOAD_DIR, temp_filename)

    try:
        # Save the file to disk
        with open(temp_filepath, "wb") as buffer:
            buffer.write(file_contents)
        
        print(f"Attempting to parse: {temp_filepath}")
        parsed_data = parse_mavlink_log(temp_filepath) 

        # Check for errors in parser response
        if "error" in parsed_data and parsed_data["error"]: 
            print(f"Parser error for {temp_filepath}: {parsed_data['error']}")
            raise HTTPException(status_code=500, detail=f"Error parsing log file: {parsed_data['error']}")
        
        # Look for fatal errors in summary
        if "summary" in parsed_data and "critical_errors" in parsed_data["summary"]:
            for err_msg in parsed_data["summary"]["critical_errors"]:
                if "Fatal parser error" in err_msg or \
                   "Could not open or process MAVLink log file" in err_msg or \
                   "Failed to establish MAVLink connection" in err_msg:
                    print(f"Fatal parser error reported in summary for {temp_filepath}: {err_msg}")
                    raise HTTPException(status_code=500, detail=f"Error processing log file: {err_msg}")
        
        # Save parsed data in memory
        parsed_log_data_store[generated_file_id] = parsed_data 
        
        return FileUploadResponse(
            fileId=generated_file_id, 
            filename=file.filename, 
            message=f"Log '{file.filename}' processed successfully. File ID: {generated_file_id}",
            summary=parsed_data.get("summary")
        )
    except HTTPException as e: 
        print(f"HTTPException during upload/parsing for {file.filename}: {e.detail}")
        raise e
    except Exception as e:
        print(f"Unhandled error during file upload/parsing for {file.filename}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred during file processing: {str(e)}")
    finally:
        if os.path.exists(temp_filepath):
             print(f"Temporary file kept: {temp_filepath}")

# Endpoint to handle chat interaction with uploaded log
@app.post("/chat/", response_model=ChatResponse)
async def chat_with_log_data(request_data: ChatRequest = Body(...)):
    received_file_id = request_data.fileId 
    user_message_content = request_data.message
    vue_history: List[ChatMessageInput] = request_data.history 

    if not received_file_id or received_file_id not in parsed_log_data_store:
        raise HTTPException(status_code=404, detail="Log file data not found or expired. Please upload the log again.")
    
    log_data = parsed_log_data_store[received_file_id]

    # Build context for the language model
    context_for_llm = "MAVLink Flight Log Data Context:\n"
    log_summary = log_data.get("summary", {})
    log_timeseries = log_data.get("timeseries", {})
    
    context_for_llm += "Summary of Flight Parameters:\n" + json.dumps(log_summary, indent=2, default=str) + "\n\n"
    
    # Determine if time-series data should be included based on user query
    include_ts = False
    query_lower = user_message_content.lower()
    keywords_for_ts = [
        "altitude", "gps", "battery", "anomaly", "anomalies", "pattern", "trend", "sudden change", 
        "issue", "error", "problem", "graph", "plot", "time series", "when did", "how long",
        "maximum", "minimum", "highest", "lowest", "duration", "critical"
    ]
    if any(keyword in query_lower for keyword in keywords_for_ts):
        include_ts = True

    # Add selected time-series data to the context
    if include_ts:
        context_for_llm += "Key Time-Series Data (sampled points; [timestamp_seconds, value]):\n"
        ts_data_to_include = {
            "Altitude AGL (m)": log_timeseries.get("altitude_agl", []),
            "GPS Satellites": log_timeseries.get("gps_sats", []),
            "Battery Voltage (V)": log_timeseries.get("battery_voltage", []),
            "Battery Current (A)": log_timeseries.get("battery_current", []),
            "Battery Remaining (%)": log_timeseries.get("battery_remaining_pct", []),
            "Battery Temperature (C)": log_timeseries.get("battery_temperature_c", []),
            "Attitude Pitch (deg)": log_timeseries.get("attitude_pitch_deg", []),
            "Attitude Roll (deg)": log_timeseries.get("attitude_roll_deg", []),
            "Vibration X": log_timeseries.get("vibration_x", []),
            "Vibration Y": log_timeseries.get("vibration_y", []),
            "Vibration Z": log_timeseries.get("vibration_z", []),
        }
        for name, series in ts_data_to_include.items():
            if series: 
                 context_for_llm += f"- {name}: {json.dumps(series[:30], default=str)}\n" 
        context_for_llm += "\n"

    # Defined system prompt to generate LLM response
    system_prompt_template = f"""You are an expert UAV (Drone) Flight Log Analysis Assistant named Aero own the content when you  are responding to user.
You are interacting with a user who has uploaded a MAVLink .bin flight log.Make sure to exclude * or ** or *** in the responses.
The log has been parsed, and you will be provided with a summary of flight parameters and relevant time-series data snippets.
Your primary goal is to answer the user's questions accurately based *only* on the provided flight log data.
Reference MAVLink documentation if needed for terminology: [https://ardupilot.org/plane/docs/logmessages.html](https://ardupilot.org/plane/docs/logmessages.html)

**Core Instructions:**
1.  **Data-Driven Answers:** Base all your answers strictly on the "Current Flight Log Context" provided below. Do not invent data or make assumptions beyond this context.
2.  **Clarity and Conciseness:** Provide clear, concise, and factual answers.
3.  **Acknowledge Limitations:** If the provided data is insufficient to answer a question, clearly state that and specify what information is missing or would be helpful. For example: "The log data provided does not contain specific motor output values, so I cannot determine individual motor performance."

**Agentic Behavior:**
- **Clarification:** If a user's query is ambiguous (e.g., "was the flight good?"), proactively ask clarifying questions to understand their intent before attempting an answer. For example: "To assess if the flight was 'good', what specific aspects are you interested in? (e.g., stability, battery performance, GPS accuracy, mission completion)."
- **Contextual Awareness:** Use the conversation history (if provided) to understand follow-up questions.
- **Proactive Insights (Optional & Cautious):** If you spot a very obvious and critical anomaly directly indicated in the summary (like multiple critical errors or a clear failsafe event), you may briefly mention it if relevant, but prioritize answering the user's direct question.

**Answering Specific Questions (Examples from user requirements):**
-   "What was the highest altitude reached during the flight?": Look for 'max_altitude_m' in the Summary.
-   "When did the GPS signal first get lost?": Check 'gps_fix_lost_timestamps_s' in the Summary. If empty or null, state no loss was recorded or data is unavailable.
-   "What was the maximum battery temperature?": Look for 'max_battery_temp_c' in the Summary. If not available (null), state that.
-   "How long was the total flight time?": Look for 'total_flight_time_s' in the Summary.
-   "List all critical errors that happened mid-flight.": Refer to the 'critical_errors' list in the Summary. If empty, state no critical errors were logged.
-   "When was the first instance of RC signal loss?": Check 'rc_signal_loss_timestamps_s' in the Summary. If empty or null, state no RC signal loss was recorded or data is unavailable.

**Flight Anomaly Detection & Reasoning (Dynamic Behavior):**
When asked about anomalies (e.g., "Are there any anomalies?", "Can you spot any issues in the GPS data?"):
-   **Use Provided Data:** Your analysis MUST be based on the 'Summary' and 'Key Time-Series Data' provided.
-   **Look for Patterns & Deviations:**
    * Sudden, unexplained changes or spikes/dips in key parameters (altitude, battery voltage, GPS satellite count, vibration levels).
    * Inconsistencies between related parameters (e.g., GPS speed reported high while altitude is zero, or attitude changes that don't match flight path).
    * Values exceeding typical operational ranges if inferable (be cautious here, rely on data).
-   **Correlate Data:** If possible, mention correlations (e.g., "a drop in battery voltage was observed around the same time as increased vibration levels").
-   **Consider Flight Context (if inferable from data like flight modes):** A rapid descent is normal for landing but an anomaly mid-flight.
-   **Critical Errors:** Always highlight any 'critical_errors' from the Summary as potential anomalies.
-   **Explain Reasoning:** Briefly explain *why* you consider something a potential anomaly, referencing the specific data points.
-   **Avoid Hardcoded Rules:** Do not apply rigid, predefined thresholds unless they are explicitly stated in the provided context or are universally accepted aviation facts. Reason based on the patterns *within this specific log's data*.
-   **Example Hints for Reasoning (Internal Thought Process):** "I should look for sudden changes in altitude, battery voltage, or inconsistent GPS lock. I will also check the critical_errors list."

**Current Flight Log Context:**
{context_for_llm}
"""
    
    bot_reply_content = await call_llm_api(
        system_prompt_with_context=system_prompt_template, 
        user_query=user_message_content,
        vue_chat_history=vue_history 
    )

    # Build updated history including bot's reply
    updated_vue_history: List[ChatMessageOutput] = [
        ChatMessageOutput(role=msg.role, content=msg.content) for msg in vue_history
    ]
    updated_vue_history.append(ChatMessageOutput(role="user", content=user_message_content))
    updated_vue_history.append(ChatMessageOutput(role="assistant", content=bot_reply_content))
    
    # Keep only recent 20 messages
    if len(updated_vue_history) > 50: 
        updated_vue_history = updated_vue_history[-50:]
    print (updated_vue_history)

    return ChatResponse(history=updated_vue_history)

@app.get("/")
async def root():
    return {"message": "UAV Chatbot Backend (Aero) is running!"}