# UAV Logger Backend

This is the backend service for the UAV Logger application, providing telemetry analysis and chat functionality with advanced memory capabilities.

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- OpenSearch (for vector embeddings and semantic search)
- Poetry (optional, for dependency management)

## Setup

1. Install PostgreSQL if you haven't already:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install postgresql postgresql-contrib

   # macOS with Homebrew
   brew install postgresql
   ```

2. Install OpenSearch (required for vector storage):
   ```bash
   # Using Docker (recommended)
   docker run -d --name opensearch -p 9200:9200 -p 9600:9600 -e "discovery.type=single-node" opensearchproject/opensearch:latest
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   # Copy the example environment file
   cp .env.example .env

   # Edit the .env file with your settings
   # Make sure to set a secure SECRET_KEY, your database credentials, and OpenAI API key
   ```

5. Set up the database:
   ```bash
   # Run the database setup script
   python setup_db.py
   ```

6. Start the server:
   ```bash
   python main.py
   ```

   Or using uvicorn directly:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Environment Variables

### Database Configuration
- `DATABASE_URL`: PostgreSQL connection string (default: postgresql://postgres:postgres@localhost:5432/uav_logger)
- `DB_USER`: PostgreSQL username (default: postgres)
- `DB_PASSWORD`: PostgreSQL password (default: postgres)
- `DB_HOST`: Database host (default: localhost)
- `DB_PORT`: Database port (default: 5432)
- `DB_NAME`: Database name (default: uav_logger)

### Server Configuration
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)

### Security Configuration
- `SECRET_KEY`: JWT secret key (required, no default)
- `JWT_ALGORITHM`: Algorithm used for JWT tokens (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token expiration time in minutes (default: 30)

### CORS Configuration
- `ALLOWED_ORIGINS`: Comma-separated list of allowed CORS origins (default: http://localhost:8080)
- `ALLOWED_METHODS`: Comma-separated list of allowed HTTP methods (default: GET,POST,PUT,DELETE)
- `ALLOWED_HEADERS`: Comma-separated list of allowed HTTP headers (default: Authorization,Content-Type,Accept,Origin,X-Requested-With)
- `CORS_MAX_AGE`: Maximum age for CORS preflight requests in seconds (default: 3600)

### OpenAI Configuration
- `OPENAI_API_KEY`: OpenAI API key (required for LLM functionality)
- `OPENAI_MODEL`: OpenAI model to use (default: gpt-4o)
- `OPENAI_EMBEDDING_MODEL`: Model for embeddings (default: text-embedding-ada-002)
- `OPENAI_EMBEDDING_DIMENSIONS`: Dimensions for embeddings (default: 1536)

### OpenSearch Configuration
- `OPENSEARCH_HOST`: OpenSearch host (default: localhost)
- `OPENSEARCH_PORT`: OpenSearch port (default: 9200)

### File Upload Configuration
- `TEMP_UPLOAD_DIR`: Directory for temporary file uploads (default: temp)

## API Documentation

Once the server is running, you can access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Features

- User authentication with JWT
- Flight session management
- Real-time telemetry analysis
- Advanced ReAct-based agentic AI for flight analysis
- Multi-tiered memory system:
  - Short-term conversational memory
  - Long-term summary memory via ConversationSummaryBufferMemory
  - Entity tracking with ConversationEntityMemory
  - Semantic search with OpenSearch vector embeddings
- Persistent chat history with SQL storage
- Importance-based memory prioritization
- Temporal decay for memory relevance
- Session management and cleanup

## Architecture

### Memory System

The backend implements a sophisticated memory system with multiple components:

1. **Summary Buffer Memory**: Maintains a summary of past conversations while preserving recent interactions
2. **Entity Memory**: Tracks and stores information about specific entities (flight parameters, events)
3. **SQL Storage**: Persists all messages with metadata in PostgreSQL
4. **Vector Store**: Enables semantic search using OpenSearch and embeddings
5. **Memory Manager**: Orchestrates these components with importance scoring and deduplication

### Flight Agent

The system uses a ReAct (Reasoning + Action) based agent that:

1. **Thinks**: Reasons about user queries to understand their intent
2. **Analyzes**: Examines relevant flight data based on reasoning
3. **Recalls**: Retrieves relevant memories from conversation history
4. **Responds**: Provides detailed answers based on analysis and memory

This architecture enables the agent to provide detailed flight analysis with contextual awareness of past interactions.

## CORS Configuration

The backend implements a restricted CORS policy for enhanced security:

### Allowed Methods
- GET
- POST
- PUT
- DELETE

### Allowed Headers
- Authorization
- Content-Type
- Accept
- Origin
- X-Requested-With

### Additional CORS Settings
- Pre-flight cache duration: 1 hour (3600 seconds)
- Credentials: Allowed
- Origins: Configurable via ALLOWED_ORIGINS environment variable

## API Endpoints

### POST /register
Create a new user account.

Request:
```json
{
    "username": "user1",
    "password": "password123"
}
```

### POST /token
Login and get access token.

Request:
```bash
curl -X POST http://localhost:8000/token -d "username=user1&password=password123"
```

### POST /upload
Upload a MAVLink log file for analysis. Requires authentication.

Request:
- Header: `Authorization: Bearer <token>`
- Body: MAVLink log file (.bin)

### POST /chat
Send a message to the chatbot. Requires authentication.

Request:
```json
{
    "session_id": "unique_session_id",
    "message": "What was the highest altitude reached?"
}
```

### GET /sessions
List all flight sessions for the authenticated user.

### GET /session/{session_id}/messages
Get chat messages for a specific session.

### DELETE /session/{session_id}
End a chat session and clean up resources.

## Security Features

- JWT-based authentication
- Per-user data isolation
- Password hashing with bcrypt
- Restricted CORS policy
- Environment-based configuration
- Automatic session cleanup
- Pre-flight request caching
- Explicit method and header restrictions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 