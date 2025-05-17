from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, create_engine, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    sessions = relationship("FlightSession", back_populates="user", cascade="all, delete-orphan")

    # Index for username lookups during authentication
    __table_args__ = (
        Index('idx_users_username', 'username'),
    )

class FlightSession(Base):
    __tablename__ = "flight_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_accessed = Column(DateTime(timezone=True), 
                          default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))
    telemetry_data = Column(JSONB)  # Using JSONB for better performance with JSON data
    
    user = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_flight_sessions_user_id', 'user_id'),
        Index('idx_flight_sessions_last_accessed', 'last_accessed'),
    )

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("flight_sessions.id", ondelete="CASCADE"), index=True)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', or 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    metadata = Column(JSONB)  # Using JSONB for better performance with JSON data
    
    session = relationship("FlightSession", back_populates="messages")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }

    # Indexes for common queries
    __table_args__ = (
        Index('idx_chat_messages_session_created', 'session_id', 'created_at'),
    )

def get_database_url():
    """Get database URL from environment variables."""
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "postgres")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "uav_logger")
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

def init_db(db_url: str | None = None):
    """Initialize database connection."""
    if db_url is None:
        db_url = get_database_url()
    
    engine = create_engine(
        db_url,
        pool_size=5,  # Maximum number of database connections in the pool
        max_overflow=10,  # Maximum number of connections that can be created beyond pool_size
        pool_timeout=30,  # Timeout for getting a connection from the pool
        pool_recycle=1800,  # Recycle connections after 30 minutes
    )
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    return sessionmaker(bind=engine) 