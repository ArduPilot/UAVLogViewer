from fastapi import FastAPI, Request
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
from agent import Agent

load_dotenv()

app = FastAPI()

agent = Agent()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your frontend domain for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    message: str  # This is the message field in the request body

@app.post("/chat")
async def chat(request: Message):
    try:
        response = agent.chat(request.message)
        print(response)
        return {"response": response}
    except Exception as e:
        return {"error": str(e)}
