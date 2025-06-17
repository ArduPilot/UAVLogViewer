# UAV Log Viewer & Analysis Tool

A powerful web application for analyzing UAV (Unmanned Aerial Vehicle) telemetry logs. This tool allows users to upload flight logs, visualize flight data, and get AI-powered insights about their drone's performance.

## Features

- Upload and parse UAV telemetry logs (.bin format)
- Interactive 3D flight path visualization
- AI-powered analysis of flight data
- Chat interface for querying flight data
- Anomaly detection and performance metrics

## Installation

### Prerequisites
- Python 3.10+
- Node.js 14+ (I used 18, so I recommend using that)
- npm or yarn

### Backend Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install Python dependencies:
   ```bash
   cd backend
   pip3 install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file in the `backend/src/app` directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

### Frontend Setup

1. Install Node.js dependencies:
   ```bash
   cd ../../  # Back to project root
   npm install
   ```

## Running the Application

1. Start the backend server:
   ```bash
   cd backend/src/app
   python3 main.py
   ```
   The backend will start on `http://0.0.0.0:8000`

2. In a new terminal, start the frontend:
   ```bash
   cd ../../..  # Back to project root
   npm run serve
   ```
   The frontend will be available at `http://localhost:8080`

## Architecture

### Backend (FastAPI)

The backend follows a modular architecture with clear separation of concerns:

#### Core Components
- **main.py**: Entry point that initializes the FastAPI application and routes
- **/core**: Manages session state and data storage
  - `session_store.py`: Handles session lifecycle and telemetry data storage
- **/parsers**: Converts raw telemetry formats into structured data
  - Supports multiple UAV platforms and log formats
  - Handles binary log files
- **/models**: Defines data structures and schemas
  - `telemetry_data.py`: Core data structures for flight data
  - `schemas.py`: API request/response models

#### Agent System

The system uses specialized AI agents to handle different types of user queries:

1. **Intent Router** (`IntentRouterAgent`)
   - First point of contact for all incoming messages
   - Classifies user intent into categories:
     - `greeting`: Handles basic interactions (hello, thanks, etc.)
     - `factual`: Processes queries about specific telemetry data
     - `anomaly`: Detects and analyzes unusual flight patterns
     - `clarification`: Handles follow-up questions
   - Routes queries to appropriate specialized agents

2. **Telemetry Analysis Agent** (`TelemetryAnalysisAgent`)
   - Handles factual queries about flight data
   - Uses GPT-4o-mini for natural language understanding
   - Maintains conversation context using `ConversationSummaryBufferMemory`
   - Can process complex queries about flight parameters and events

3. **Anomaly Detection Agent** (`AnomalyAgent`)
   - Specialized in identifying unusual patterns in flight data
   - Uses statistical analysis and ML models to detect anomalies
   - Provides detailed reports on potential issues

4. **Greeting Agent** (`GreetingAgent`)
   - Manages social interactions
   - Handles greetings, thanks, and other conversational elements

5. **Fallback Agent** (`FallbackAgent`)
   - Handles queries that don't fit other categories
   - Provides helpful guidance when user intent is unclear

## API Documentation

### Endpoints

#### Upload Log File
- **POST** `/upload`
  - Upload a .bin telemetry file
  - Returns: `{ "session_id": string, "message": string }`

#### Chat
- **POST** `/chat`
  - Send a message to the AI
  - Body: `{ "session_id": string, "message": string }`
  - Returns: `{ "answer": string }`


![log seeking](preview.gif "Logo Title Text 1")

 This is a Javascript based log viewer for Mavlink telemetry and dataflash logs.
 [Live demo here](http://plot.ardupilot.org).

## Build Setup

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

# Docker

run the prebuilt docker image:

``` bash
docker run -p 8080:8080 -d ghcr.io/ardupilot/uavlogviewer:latest

```

or build the docker file locally:

``` bash

# Build Docker Image
docker build -t <your username>/uavlogviewer .

# Run Docker Image
docker run -e VUE_APP_CESIUM_TOKEN=<Your cesium ion token> -it -p 8080:8080 -v ${PWD}:/usr/src/app <your username>/uavlogviewer

# Navigate to localhost:8080 in your web browser

# changes should automatically be applied to the viewer

```
