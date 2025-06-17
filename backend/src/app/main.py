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
    print("reading file")
    raw = await file.read()
    print("parsing file")
    data = TelemetryParser.parse(raw)
    print("parsing done")
    session_id = str(uuid.uuid4())
    store.add_session(session_id, data)
    print("session added")
    return UploadResponse(session_id=session_id)

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not store.has_session(req.session_id):
        raise HTTPException(
            status_code=400,
            detail="No file has been uploaded for this session. Please upload a file first."
        )
    router = IntentRouterAgent(req.session_id, store)
    answer = router.route(req.message)
    return ChatResponse(answer=answer)


@app.get("/hello")
async def hello_world():
    return "Hello World!"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
