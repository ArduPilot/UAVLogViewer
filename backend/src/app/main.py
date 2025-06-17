from dotenv import load_dotenv
import os
import time

# Load environment variables first thing
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models.schemas import UploadResponse, ChatRequest, ChatResponse
from core.session_store import store
from parsers.telemetry_parser import TelemetryParser
from agents.intent_router import IntentRouterAgent
import uuid

app = FastAPI(title="UAV Chat Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    if not file.filename.endswith(".bin"):
        raise HTTPException(400, "Only .bin logs supported.")
    # raw = await file.read()
    # data = TelemetryParser.parse(raw)
    session_id = str(uuid.uuid4())
    #store.add_session("test", data)
    return UploadResponse(session_id=session_id)

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # router = IntentRouterAgent("test", store)
    # answer = router.route(req.message)
    time.sleep(5)
    return ChatResponse(answer="The maximum ground speed recorded across the telemetry slices was **0.9 m/s**. This speed indicates a steady movement during the flight, with other readings showing values like **0.795 m/s** and **0.769 m/s** at different timestamps. Most of the other ground speed values were **0.0 m/s**, suggesting periods of stationary or very slow movement.\n\nIf you need further details or specific timestamps related to these speeds, just let me know!")


@app.get("/hello")
async def hello_world():
    return "Hello World!"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
