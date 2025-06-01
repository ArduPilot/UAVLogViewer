# UAV Log Viewer

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

## Backend Setup

The UAV Log Viewer includes an optional FastAPI backend for AI-powered flight log analysis. To use the chat functionality:

``` bash
# Navigate to the backend directory
cd backend

# Install Python dependencies
pip3 install -r requirements.txt

# Create a .env file with your OpenAI API key
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env

# Start the backend server
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000` and provides:
- `/api/upload-log` - Upload and process flight log files
- `/api/chat` - AI-powered chat about flight data

## Docker

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
