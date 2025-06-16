from fastapi import FastAPI, Request, UploadFile, File
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
from agent import Agent
import tempfile
from parser import parse_bin_file
from fastapi.responses import JSONResponse
import asyncio

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
        file_path = "parsed_telemetry.json"
        if not os.path.exists(file_path):
            return {"reply": "You must first upload a file"}
        response = agent.chat(request.message)
        print(response)
        return {"reply": response}
    except Exception as e:
        return {"error": str(e)}
    
@app.post("/parser")
async def parser(file: UploadFile = File(...)):
    try:
        file_path = "parsed_telemetry.json"
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"{file_path} removed.")
        else:
            print(f"{file_path} does not exist.")
        
        # Read the file content (as bytes)
        contents = await file.read()

        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
            tmp.write(contents)
            temp_path = tmp.name

        parse_bin_file(temp_path)
        print("success, responding back")
        return JSONResponse(content={"message": "File received successfully"}, status_code=200)

    except Exception as e:
        print("failure, responding back")
        return JSONResponse(content={"error": str(e)}, status_code=500)
    