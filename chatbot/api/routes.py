from fastapi import WebSocket, WebSocketDisconnect
from chatbot.core.llm_integration import LLMAnalyst

async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    analyst = LLMAnalyst()
    print("WebSocket connection accepted")
    print(f"Analyst initialized: {analyst is not None}")
    
    try:
        while True:
            message = await websocket.receive_json()
            print(f"Received message: {message}")
            response = await analyst.process_message(message)
            print(f"Sending response: {response}")
            await websocket.send_json(response)
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error in websocket_chat: {e}")
        await websocket.send_json({"message": "Error processing request", "type": "error"})