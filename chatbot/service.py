# from fastapi import FastAPI, WebSocket
# from pydantic import BaseModel

# app = FastAPI()

# class ChatMessage(BaseModel):
#     message: str
#     session_id: str

# @app.websocket("/ws/chat")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()