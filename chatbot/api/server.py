from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from chatbot.api.routes import websocket_chat

app = FastAPI()

app.websocket("/ws/chat")(websocket_chat)

@app.get("/health")
async def health_check():
    return {"message": "UAV Chatbot API is running"}