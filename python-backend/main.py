import uvicorn
from api_v2 import app

if __name__ == "__main__":
    """
    This provides an alternative entry point to run the FastAPI server.
    It imports the app instance from api_v2.py and starts the uvicorn server.
    This is useful for running the application with a debugger.
    """
    print("Starting server from main.py...")
    uvicorn.run(app, host="0.0.0.0", port=8001) 