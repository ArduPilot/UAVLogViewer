# UAV Log Viewer - AI-Powered Flight Log Analysis

An intelligent chatbot interface for analyzing UAV flight logs with real-time parsing and AI-powered insights.

## Features

- **Real-time Log Parsing**: Support for `.tlog` (MAVLink telemetry) and `.bin` (ArduPilot Dataflash) files
- **AI-Powered Chat Interface**: Ask questions about flight data in natural language
- **Advanced Analytics**: Automatic detection of flight anomalies and performance metrics
- **Dual Database Architecture**: SQLite for metadata + DuckDB for time-series telemetry analytics
- **Background Processing**: Non-blocking file parsing with real-time status updates

## Quick Start

### Prerequisites

- Python 3.9+ (for backend)
- Node.js 16+ (for frontend)
- Git

### Backend Setup

1. **Navigate to backend directory and create virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env and set your OpenAI API key
   # OPENAI_API_KEY=your_actual_api_key_here
   ```

4. **Start the backend server:**
   ```bash
   cd backend && uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info
   ```

   The backend API will be available at:
   - Main API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - ReDoc documentation: http://localhost:8000/redoc

### Frontend Setup

1. **Navigate to frontend directory and install dependencies:**
   ```bash
   # From project root
   npm install
   ```

   (This installs all required packages, including the **marked** library used for Markdown rendering in the chat panel.)

2. **Start the frontend development server:**
   ```bash
   npm run dev
   ```

   The frontend will be available at: http://localhost:8080

### Alternative Backend Start (from project root)

You can also run the backend from the project root:
```bash
# Activate virtual environment first
source backend/venv/bin/activate  # On Windows: backend\venv\Scripts\activate

# Run from root directory
python -m backend.main
```

## Usage

1. **Upload a Log File**: 
   - Open http://localhost:8080 in your browser
   - Upload a `.tlog` or `.bin` flight log file
   - Wait for parsing to complete (status updates in real-time. Unfortunately, may take a few minutes due to unoptimized parsing. a TODO in the future)

2. **Chat with Your Data**:
   - Ask questions like:
     - "What was the highest altitude reached during the flight?"
     - "When did the GPS signal first get lost?"
     - "Are there any anomalies in this flight?"
     - "How long was the total flight time?"

3. **View Analytics**:
   - Real-time flight metrics and statistics
   - Automatic anomaly detection
   - Historical conversation tracking

## Architecture

### Backend (Python/FastAPI)
- **FastAPI**: High-performance async web framework
- **pymavlink**: UAV log parsing and MAVLink protocol handling
- **SQLite**: Session metadata, conversations, user preferences
- **DuckDB**: High-performance analytics on telemetry time-series data
- **Background Tasks**: Async log processing pipeline

### Frontend (Vue.js)
- **Vue 3**: Modern reactive UI framework
- **Real-time Updates**: WebSocket/polling for parsing status
- **Responsive Design**: Mobile-friendly interface

### Database Schema

**SQLite Tables:**
- `flight_sessions`: Session metadata, file info, parsing status
- `chat_conversations`: Chat history and context
- `detected_anomalies`: AI-identified flight issues
- `user_preferences`: UI settings and preferences

**DuckDB Tables:**
- `gps_telemetry`: GPS coordinates, altitude, speed over time
- `attitude_telemetry`: Roll, pitch, yaw, and rates
- `sensor_telemetry`: IMU data (accelerometer, gyroscope, magnetometer)
- `flight_events`: Time-stamped events (mode changes, errors, warnings)
- `system_status`: Battery, radio, and system health metrics

## Development

### Project Structure
```
.
├── backend/                 # Python FastAPI backend
│   ├── db.py               # Database managers (SQLite + DuckDB)
│   ├── main.py             # FastAPI application
│   ├── parsers.py          # Log parsing logic (pymavlink)
│   ├── schemas.py          # Pydantic data models
│   ├── tasks.py            # Background processing tasks
│   └── requirements.txt    # Python dependencies
├── frontend/               # Vue.js frontend (existing)
└── README.md              # This file
```

### Backend API Endpoints

- `GET /health` - Health check
- `POST /upload-log` - Upload and start parsing a log file
- `GET /sessions/{session_id}` - Get parsing status and metadata
- `POST /chat` - Chat with the AI about flight data

### Development Commands

**Backend Development:**
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run with auto-reload
cd backend && uvicorn main:app --reload --port 8000

# Run tests (when available)
pytest backend/

# Format code
black backend/
ruff backend/
```

**Frontend Development:**
```bash
# Install dependencies
npm install

# Development server
npm run dev

# Build for production
npm run build

# Run tests
npm test
```

### Environment Variables

**Important**: The system now includes AI-powered chat functionality that requires an OpenAI API key.

See [backend/readmes/ENVIRONMENT_SETUP.md](backend/readmes/ENVIRONMENT_SETUP.md) for complete environment configuration including:
- OpenAI API key setup (required for chat functionality)
- LLM provider selection (Responses API vs Chat Completions)
- Database and server configuration options

## Success Criteria

✅ **Backend Startup**: `cd backend && uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info` starts without errors  
✅ **File Upload**: `POST /upload-log` accepts `.bin/.tlog` files and returns `session_id`  
✅ **Background Parsing**: Log files are parsed and data is inserted into DuckDB tables  
✅ **Database Population**: Session metadata stored in SQLite, telemetry in DuckDB  
✅ **Frontend Integration**: Existing Vue.js frontend continues to work unchanged  

## Supported Log Formats

- **`.tlog` files**: MAVLink telemetry logs (parsed with `mavutil.mavlink_connection()`)
- **`.bin` files**: ArduPilot Dataflash logs (parsed with `DFReader()`)

Both formats are automatically detected and parsed using the pymavlink library.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
