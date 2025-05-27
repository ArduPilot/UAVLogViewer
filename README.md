# UAV Log Viewer

![log seeking](preview.gif "Logo Title Text 1")

This is a Javascript-based log viewer for MAVLink telemetry and dataflash logs with an **AI-powered analysis chatbot**.
[Live demo here](http://plot.ardupilot.org).

## ✨ New Features

### 🤖 AI-Powered Flight Analysis Chat
- **Intelligent Analysis**: Ask natural language questions about your flight data
- **Real-time Streaming**: Get responses as they're generated with WebSocket streaming
- **Comprehensive Insights**: Analyze altitude, battery, GPS, RC signals, speed, and anomalies
- **Export Conversations**: Download chat history in TXT, JSON, or CSV formats
- **Session Management**: Secure, isolated analysis sessions for each uploaded log

**Example Questions:**
- *"What was the maximum altitude reached?"*
- *"Were there any GPS signal dropouts?"*
- *"Give me a complete flight summary"*
- *"What about the RC signal loss?"*

## Build Setup

### Frontend Setup

``` bash
# install dependencies
npm install

# serve with hot reload at localhost:8080
npm run dev

# build for production with minification
npm run build

# run unit tests
npm run unit

# run e2e tests
npm run e2e

# run all tests
npm test
```

### 🤖 AI Backend Setup (Optional but Recommended)

To enable the AI chat features, you'll need to set up the backend:

``` bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (requires OpenAI API key)
cp .env.example .env
# Edit .env file with your OpenAI API key

# Start backend server
python main.py
```

The backend will run on `http://localhost:8000`. The frontend will automatically connect to it for AI chat features.

**Frontend Configuration:**
You can configure the backend URL by setting the `VUE_APP_BACKEND_URL` environment variable:

```bash
# For development
export VUE_APP_BACKEND_URL=http://localhost:8000

# Then start frontend
npm run dev
```

### 🌟 Using the AI Chat Feature

1. **Upload a Log File**: Drag and drop or browse for your MAVLink log file (.bin, .log, .tlog, .ulg)
2. **Start Chatting**: Ask questions about your flight data in natural language
3. **Real-time Responses**: Watch as the AI analyzes your data and responds in real-time
4. **Export Results**: Download your conversation and analysis results for documentation

**Supported Log Formats:**
- MAVLink Binary Logs (.bin)
- MAVLink Text Logs (.log, .tlog)
- ULog Format (.ulg) - PX4 format

## 🎯 Features

### Core Features
- **3D Flight Visualization**: Interactive 3D flight path visualization with Cesium
- **Advanced Plotting**: Multi-parameter telemetry plotting with time-series analysis
- **Data Export**: Export flight data and visualizations
- **File Management**: Upload and manage multiple log files
- **Expression Editor**: Custom data expressions and calculations

### AI Chat Features
- **Drag & Drop Upload**: Easy log file uploading with visual feedback
- **Natural Language Queries**: Ask questions in plain English about your flight
- **Real-time Streaming**: See AI responses generated in real-time
- **Quick Questions**: Pre-defined common questions for fast analysis
- **Analysis Cards**: Structured display of flight analysis results
- **Chat History Export**: Download conversations in multiple formats (TXT, JSON, CSV)
- **Session Management**: Isolated analysis sessions with automatic cleanup
- **Connection Status**: Visual indicators for WebSocket and REST API connectivity

## 🛠️ Technical Stack

### Frontend
- **Vue.js 2**: Progressive JavaScript framework
- **Bootstrap Vue**: Responsive UI components
- **Cesium**: 3D geospatial visualization
- **Plotly.js**: Interactive charting and plotting
- **Axios**: HTTP client for API communication
- **WebSocket**: Real-time bidirectional communication

### Backend

* **🛰 MAVLink** –
  Lightweight messaging protocol for communicating with drones; used as the telemetry data standard for parsing `.tlog` files.

* **🧠 OpenAI (GPT-4o, ada-002)** –
  Powering the agent’s reasoning (`gpt-4o`) and semantic memory embeddings (`text-embedding-ada-002`) for both planning and answer generation.

* **🦜 LangChain** –
  Used for tool abstraction, agent orchestration (`BaseTool`, `ChatOpenAI`), and memory integration (Buffer, FAISS, Entity, CombinedMemory).

* **⚡ FastAPI** –
  Fast, async-ready Python web framework powering the backend API and WebSocket chat streaming.

* **🔍 FAISS (Facebook AI Similarity Search)** –
  High-performance similarity search for time-weighted memory retrieval and context-aware long-term recall.

* **📈 pandas & numpy** –
  Backbone of all telemetry data processing, statistical analysis, and time-series metric computation.

* **🧰 scikit-learn (IsolationForest)** –
  Used for anomaly detection in UAV signal metrics (e.g., voltage drops, GPS fix instability, RC link losses).

* **📚 Pydantic** –
  For request/response validation and serialization in FastAPI endpoints.

* **🌐 HTTPX** –
  Async HTTP client for OpenAI API calls, streaming completions, and retry-resilient embedding generation.

* **🧪 watchfiles** –
  Dev-time hot-reloading of FastAPI and agent modules with minimal latency.

* **🔧 dotenv & os** –
  For clean environment management and configuration loading across API and agent layers.

* **🔄 LangGraph** –
  Graph-based agentic planning and execution pipeline with support for conditional branching (`StateGraph`, `ainvoke`).

* **🗃 JSON & Regex** –
  Used extensively for prompt I/O extraction, sanitization, and handling LangChain tool JSON parsing.

* **🧼 Uvicorn** –
  ASGI server for running FastAPI with support for auto-reloading, WebSockets, and streaming endpoints.


# Docker

``` bash

# Build Docker Image
docker build -t <your username>/uavlogviewer .

# Run Docker Image
docker run -p 8080:8080 -d <your username>/uavlogviewer

# View Running Containers
docker ps

# View Container Log
docker logs <container id>

# Navigate to localhost:8080 in your web browser

```
