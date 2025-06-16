from dotenv import load_dotenv
import os

# Load environment variables first thing
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from models.schemas import UploadResponse, ChatRequest, ChatResponse
from core.session_store import store
from parsers.telemetry_parser import TelemetryParser
from agents.intent_router import IntentRouterAgent
import uuid

app = FastAPI(title="UAV Chat Backend")

@app.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    if not file.filename.endswith(".bin"):
        raise HTTPException(400, "Only .bin logs supported.")
    raw = await file.read()
    data = TelemetryParser.parse(raw)
    #session_id = str(uuid.uuid4())
    store.add_session("test", data)
    return UploadResponse(session_id="test")

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    router = IntentRouterAgent("test", store)
    answer = router.route(req.message)
    return ChatResponse(answer=answer)


@app.get("/hello")
async def hello_world():
    return "Hello World!"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
