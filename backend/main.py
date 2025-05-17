from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import uuid

from agents.flight_agent import FlightAgent
from telemetry.parser import TelemetryParser
from telemetry.analyzer import TelemetryAnalyzer
from models.database import init_db, User, FlightSession, get_database_url
from chat.memory_manager import EnhancedMemoryManager

# Load environment variables
load_dotenv()

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080").split(",")
ALLOWED_METHODS = os.getenv("ALLOWED_METHODS", "GET,POST,PUT,DELETE").split(",")
ALLOWED_HEADERS = os.getenv("ALLOWED_HEADERS", "Authorization,Content-Type,Accept,Origin,X-Requested-With").split(",")
CORS_MAX_AGE = int(os.getenv("CORS_MAX_AGE", "3600"))

# File upload configuration
TEMP_UPLOAD_DIR = os.getenv("TEMP_UPLOAD_DIR", "temp")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize database
SessionLocal = init_db(get_database_url())

app = FastAPI()

# Add CORS middleware with explicit method and header restrictions
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["*"],  # Headers that can be exposed to the browser
    max_age=CORS_MAX_AGE,  # Maximum time to cache pre-flight requests (in seconds)
)

# Store active flight sessions
flight_sessions: Dict[str, FlightAgent] = {}

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    password: str

class ChatMessage(BaseModel):
    session_id: uuid.UUID
    message: str

class ChatResponse(BaseModel):
    response: str
    analysis: Optional[Dict[str, Any]] = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = pwd_context.hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    
    return {"message": "User created successfully"}

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")

@app.post("/upload")
async def upload_log(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Save file temporarily
        file_path = f"{TEMP_UPLOAD_DIR}/{file.filename}"
        os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Parse telemetry data
        parser = TelemetryParser(file_path)
        telemetry_data = parser.parse()
        
        # Create analyzer
        analyzer = TelemetryAnalyzer(telemetry_data)
        
        # Create new flight session
        new_session = FlightSession(user_id=current_user.id, telemetry_data=telemetry_data)
        db.add(new_session)
        db.flush()  # This will generate the UUID
        
        # Create flight agent with db_session instead of history_manager
        flight_sessions[str(new_session.id)] = FlightAgent(
            session_id=str(new_session.id),
            telemetry_data=telemetry_data,
            analyzer=analyzer,
            db_session=db
        )
        
        # Cleanup
        os.remove(file_path)
        
        return {"session_id": str(new_session.id), "message": "Log file processed successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(
    message: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session_id_str = str(message.session_id)
    if session_id_str not in flight_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify session belongs to user
    session = db.query(FlightSession).filter_by(id=message.session_id, user_id=current_user.id).first()
    if not session:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Process message with flight agent
    result = await flight_sessions[session_id_str].process_message(message.message)
    
    return ChatResponse(
        response=result["answer"],
        analysis=result.get("analysis")
    )

@app.get("/session/{session_id}/messages")
async def get_session_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify session belongs to user
    session = db.query(FlightSession).filter_by(id=session_id, user_id=current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get session messages using memory manager
    memory_manager = EnhancedMemoryManager(str(session_id), db)
    messages = memory_manager.get_session_messages()
    
    return {"messages": messages}

@app.get("/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get user sessions directly from the database
    sessions = db.query(FlightSession).filter_by(user_id=current_user.id).all()
    
    return {
        "sessions": [
            {
                "id": str(session.id),
                "created_at": session.created_at.isoformat(),
                "has_telemetry": bool(session.telemetry_data)
            } for session in sessions
        ]
    }

@app.delete("/session/{session_id}")
async def end_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify session belongs to user
    session = db.query(FlightSession).filter_by(id=session_id, user_id=current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Clean up session resources
    if str(session_id) in flight_sessions:
        flight_sessions[str(session_id)].clear_memory()
        del flight_sessions[str(session_id)]
    
    # Delete session from database
    db.delete(session)
    db.commit()
    
    return {"message": "Session ended successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT) 