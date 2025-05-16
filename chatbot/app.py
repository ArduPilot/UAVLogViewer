import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from log_parser import parse_log

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")
BASE_URL = "https://api.groq.com/openai/v1"
TIMEOUT = 15

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY missing")

app = FastAPI()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []


@app.post("/chat")
async def chat(request: ChatRequest):
    telemetry = parse_log(os.path.join(
        os.path.dirname(__file__), "flight.tlog"))
    try:
        answer = ask_llm(request.question, request.history, telemetry)
        return {
            "question": request.question,
            "answer": answer,
            "altitude_preview": telemetry.get("altitudes", [])[:2],
            "gps_preview": telemetry.get("gps_status", [])[:2],
        }
    except Exception as e:
        return {"question": request.question, "answer": "Error", "error": str(e)}


def ask_llm(question: str, history: list, telemetry: dict) -> str:
    altitudes = telemetry.get("altitudes", [])
    gps = telemetry.get("gps_status", [])
    errors = telemetry.get("errors", [])
    rc_loss = telemetry.get("rc_loss", [])
    rc_loss_times = telemetry.get("rc_loss_times", [])
    battery_temps = telemetry.get("battery_temps", [])
    gps_times = telemetry.get("gps_times", [])

    alt_values = [a.get("alt_amsl")
                  for a in altitudes if a.get("alt_amsl") is not None]
    max_altitude = max(alt_values) if alt_values else "N/A"
    flight_duration = (gps_times[-1] - gps_times[0]) / \
        1e6 if len(gps_times) >= 2 else "N/A"

    summary = f"""Summary of parsed telemetry data:
        - Total altitude samples: {len(altitudes)}
        - Max altitude (AMSL): {max_altitude}
        - GPS samples: {len(gps)}
        - First GPS fix: {gps[0] if gps else 'N/A'}
        - Battery temperatures (°C): {battery_temps[:5] if battery_temps else 'None'}
        - RC signal losses (count): {len(rc_loss)}
        - First RC loss timestamp: {rc_loss_times[0] if rc_loss_times else 'None'}
        - Error messages: {errors[:5] if errors else 'None'}
        - Estimated flight duration (s): {flight_duration}

        Anomaly Detection Hints:
        - Look for sudden drops or spikes in altitude.
        - Check for high battery temperatures (> 60°C).
        - Detect if GPS fix was lost or inconsistent.
        - Consider any 'fail', 'error', or 'lost' messages as potential issues.
        - RC signal loss indicates a critical control problem.
        """

    system_prompt = {
        "role": "system",
        "content": (
            "You are an expert UAV flight assistant with deep knowledge of MAVLink telemetry. "
            "You analyze parsed flight data and assist users in understanding flight performance and anomalies. "
            "Maintain conversation state across turns; ask clarifying questions if user queries are ambiguous. "
            "Reference the provided telemetry summary dynamically. "
            "You can answer questions like 'What was the highest altitude reached during the flight?', "
            "'When did the GPS signal first get lost?', 'What was the maximum battery temperature?', "
            "'How long was the total flight time?', 'List all critical errors that happened mid-flight.', "
            "'When was the first instance of RC signal loss?' "
            "Additionally, you are flight-aware: reason about anomalies without hard-coded rules, infer patterns, thresholds, and inconsistencies. "
            "Explain your reasoning clearly, and if data is insufficient, ask the user for more information."
        )
    }

    messages = [system_prompt] + history + [
        {"role": "user", "content": f"{question}\n\n{summary}"}
    ]

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {"model": GROQ_MODEL, "messages": messages}

    response = requests.post(
        f"{BASE_URL}/chat/completions",
        json=body,
        headers=headers,
        timeout=TIMEOUT
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
