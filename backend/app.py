from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pymavlink import mavutil
import os
import tempfile
import uuid
import json

# Load environment variables
load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI API client setup
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ArduPilot log message documentation
ARDUPILOT_CONTEXT = """
ArduPilot Log Message Reference (from https://ardupilot.org/plane/docs/logmessages.html):

KEY MESSAGE TYPES:
- GPS: Position, velocity, and GPS status information
- IMU: Inertial Measurement Unit data (accelerometer, gyroscope)
- BARO: Barometric pressure and altitude data
- MAG: Magnetometer/compass readings
- RCIN: Radio control input values
- RCOU: Radio control output/servo values
- ATTITUDE: Roll, pitch, yaw angles and rates
- MODE: Flight mode changes
- CMD: Mission command execution
- ERR: Error messages and subsystem failures
- BATT: Battery telemetry (voltage, current, temperature, capacity)
- BATTERY: Battery voltage, current, and remaining capacity
- VIBRATION: Vehicle vibration levels
- EKF: Extended Kalman Filter status and health
- GPS2: Secondary GPS data (if available)
- TERRAIN: Terrain following data
- AIRSPEED: Indicated and true airspeed measurements
- WIND: Wind speed and direction estimates

CRITICAL PARAMETERS TO ANALYZE:
- GPS.Status: GPS fix quality (0=no GPS, 3=3D fix, 4=DGPS, 5=RTK)
- EKF.Flags: Navigation filter health status
- BARO.Alt: Barometric altitude
- GPS.Alt: GPS altitude
- ATTITUDE.Roll/Pitch/Yaw: Vehicle orientation
- RCIN channels: Pilot control inputs
- VIBRATION.Clip: Accelerometer clipping (indicates excessive vibration)
- ERR.Subsys/ECode: System errors and their codes
- MODE.Mode: Current flight mode
- BATT.Volt/Curr/CurrTot: Power system health
- BATT.Temp: Battery temperature (critical for LiPo safety)

COMMON ISSUES TO LOOK FOR:
- GPS glitches (sudden position jumps)
- High vibration levels (VIBRATION.Clip > 0)
- EKF errors or innovations
- Low battery voltage
- Battery overheating (BATT.Temp > 45°C)
- Radio control failsafe events
- Barometer vs GPS altitude disagreement
- Compass/magnetometer interference
- Excessive attitude angles or rates

BATTERY TEMPERATURE SAFETY RANGES:
- Normal: < 35°C (Good thermal performance)
- Warm: 35-45°C (Monitor closely)
- Hot: 45-60°C (Warning - reduce load)
- Critical: > 60°C (Emergency - land immediately)
"""

sessions = {}

@app.post("/api/upload-log")
async def upload_log(file: UploadFile = File(...)):
    contents = await file.read()
    file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        mlog = mavutil.mavlink_connection(tmp_path)
        telemetry = []
        while True:
            msg = mlog.recv_match(blocking=False)
            if msg is None:
                break
            telemetry.append({
                "type": msg.get_type(),
                "time": getattr(msg, "_timestamp", None),
                "params": msg.to_dict()
            })
    except Exception as e:
        os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"Error parsing flight log: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    session_id = str(uuid.uuid4())
    sessions[session_id] = {"telemetry": telemetry, "history": []}
    return {"sessionId": session_id, "messageCount": len(telemetry)}

def extract_telemetry_summary(telemetry):
    """Extract key telemetry data for OpenAI analysis without exceeding token limits."""
    if not telemetry:
        return {}
    
    summary = {
        "total_messages": len(telemetry),
        "message_types": {},
        "flight_data": {
            "gps_data": [],
            "battery_data": [],
            "altitude_data": [],
            "attitude_data": [],
            "mode_changes": [],
            "errors": []
        },
        "flight_timespan": {}
    }
    
    start_time = None
    end_time = None
    
    # Sample every 100th message to reduce size
    sample_rate = max(1, len(telemetry) // 1000)  # Get ~1000 samples max
    
    for i, msg in enumerate(telemetry):
        msg_type = msg.get('type')
        params = msg.get('params', {})
        timestamp = msg.get('time')
        
        # Count all message types
        if msg_type in summary["message_types"]:
            summary["message_types"][msg_type] += 1
        else:
            summary["message_types"][msg_type] = 1
        
        # Track time range
        if timestamp:
            if start_time is None:
                start_time = timestamp
            end_time = timestamp
        
        # Sample key data points
        if i % sample_rate == 0:
            if msg_type == 'GPS' and params.get('Alt'):
                summary["flight_data"]["gps_data"].append({
                    'time': timestamp,
                    'lat': params.get('Lat', 0),
                    'lng': params.get('Lng', 0),
                    'alt': params.get('Alt', 0),
                    'satellites': params.get('NSats', 0),
                    'status': params.get('Status', 0)
                })
                summary["flight_data"]["altitude_data"].append({
                    'time': timestamp,
                    'altitude': params.get('Alt', 0),
                    'source': 'GPS'
                })
            
            elif msg_type == 'GLOBAL_POSITION_INT':
                # MAVLink global position data (includes altitude)
                alt_msl = params.get('alt', 0) / 1000.0  # Convert mm to meters
                relative_alt = params.get('relative_alt', 0) / 1000.0  # Convert mm to meters
                lat = params.get('lat', 0) / 1e7  # Convert to degrees
                lng = params.get('lon', 0) / 1e7  # Convert to degrees
                
                summary["flight_data"]["gps_data"].append({
                    'time': timestamp,
                    'lat': lat,
                    'lng': lng,
                    'alt': alt_msl,
                    'relative_alt': relative_alt
                })
                summary["flight_data"]["altitude_data"].append({
                    'time': timestamp,
                    'altitude': alt_msl,
                    'relative_altitude': relative_alt,
                    'source': 'GLOBAL_POSITION_INT'
                })
            
            elif msg_type == 'SCALED_PRESSURE':
                # Barometric altitude data
                if 'press_abs' in params:
                    # Calculate approximate altitude from pressure if not directly available
                    # Standard atmosphere: altitude ≈ (1 - (P/P0)^0.1903) * 44330
                    press_abs = params.get('press_abs', 0)
                    if press_abs > 0:
                        # Using standard sea level pressure of 1013.25 hPa
                        altitude_baro = (1 - (press_abs / 1013.25) ** 0.1903) * 44330
                        summary["flight_data"]["altitude_data"].append({
                            'time': timestamp,
                            'altitude': altitude_baro,
                            'pressure': press_abs,
                            'temperature': params.get('temperature', 0) / 100.0,  # Convert to Celsius
                            'source': 'BAROMETRIC'
                        })
            
            elif msg_type == 'BARO':
                # ArduPilot BARO message type (different from SCALED_PRESSURE)
                if 'Alt' in params:
                    summary["flight_data"]["altitude_data"].append({
                        'time': timestamp,
                        'altitude': params.get('Alt', 0),
                        'pressure': params.get('Press', 0),
                        'temperature': params.get('Temp', 0),
                        'source': 'BARO'
                    })
            
            elif msg_type == 'POS':
                # ArduPilot POS message type
                if 'Alt' in params:
                    summary["flight_data"]["altitude_data"].append({
                        'time': timestamp,
                        'altitude': params.get('Alt', 0),
                        'lat': params.get('Lat', 0),
                        'lng': params.get('Lng', 0),
                        'source': 'POS'
                    })
                    summary["flight_data"]["gps_data"].append({
                        'time': timestamp,
                        'lat': params.get('Lat', 0),
                        'lng': params.get('Lng', 0),
                        'alt': params.get('Alt', 0)
                    })
            
            elif msg_type == 'BATT':
                summary["flight_data"]["battery_data"].append({
                    'time': timestamp,
                    'voltage': params.get('Volt', 0),
                    'current': params.get('Curr', 0),
                    'temperature': params.get('Temp', 0),
                    'remaining': params.get('RemPct', 0)
                })
            
            elif msg_type == 'ATTITUDE':
                summary["flight_data"]["attitude_data"].append({
                    'time': timestamp,
                    'roll': params.get('Roll', 0),
                    'pitch': params.get('Pitch', 0),
                    'yaw': params.get('Yaw', 0)
                })
        
        # Always capture mode changes and errors
        if msg_type == 'MODE':
            summary["flight_data"]["mode_changes"].append({
                'time': timestamp,
                'mode': params.get('Mode', 0)
            })
        
        elif msg_type == 'ERR':
            summary["flight_data"]["errors"].append({
                'time': timestamp,
                'subsystem': params.get('Subsys', 0),
                'error_code': params.get('ECode', 0)
            })
    
    # Flight timespan
    if start_time and end_time:
        summary["flight_timespan"] = {
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": end_time - start_time
        }
    
    return summary

@app.post("/api/chat")
async def chat(data: dict):
    session_id = data.get("sessionId")
    user_msg = data.get("message")

    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session = sessions[session_id]
    telemetry = session.get("telemetry")

    if not telemetry:
        return {"reply": "No telemetry data available. Please upload a flight log."}

    # Extract summarized telemetry data instead of raw data
    telemetry_summary = extract_telemetry_summary(telemetry)
    
    system_prompt = f"""
You are an expert ArduPilot flight log analyst with comprehensive knowledge of UAV telemetry.

{ARDUPILOT_CONTEXT}

FLIGHT LOG SUMMARY:
{json.dumps(telemetry_summary, indent=2)}

CRITICAL INSTRUCTIONS:
1. IMMEDIATELY analyze the provided flight data and calculate specific answers when asked.
2. DO NOT suggest analysis or say you'll analyze - PERFORM THE ANALYSIS NOW.
3. When asked for specific values (highest/lowest/duration/etc.), calculate and provide the exact answer immediately.
4. Use the sampled data points in the flight_data section to perform calculations.
5. Always show your calculation process and the specific data you used.
6. Reference ArduPilot message types and terminology when relevant.
7. If you need to find max/min/average values, scan through the provided data arrays and calculate them.

EXAMPLE: If asked "What was the highest altitude?", scan through altitude_data array, find the maximum value, and state: "The highest altitude was X meters at time Y, based on analysis of Z data points from [SOURCE] messages."
"""

    # Include conversation history
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history
    for h in session.get("history", []):
        messages.append(h)
    
    messages.append({"role": "user", "content": user_msg})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        reply = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

    session["history"].append({"role": "user", "content": user_msg})
    session["history"].append({"role": "assistant", "content": reply})

    return {"reply": reply}

@app.post("/api/debug-messages")
async def debug_messages(data: dict):
    """Debug endpoint to inspect message structures"""
    session_id = data.get("sessionId")
    message_type = data.get("messageType")
    
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    
    session = sessions[session_id]
    telemetry = session.get("telemetry")
    
    if not telemetry:
        return {"error": "No telemetry data available"}
    
    # Find samples of the requested message type
    samples = []
    for msg in telemetry:
        if msg.get('type') == message_type:
            samples.append(msg)
            if len(samples) >= 3:  # Return first 3 samples
                break
    
    return {"samples": samples}
