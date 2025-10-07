# UAV Log Viewer

![log seeking](preview.gif "Logo Title Text 1")

 This is a Javascript based log viewer for Mavlink telemetry and dataflash logs.
 [Live demo here](http://plot.ardupilot.org).

## Build Setup

``` bash
# initialize submodules
git submodule update --init --recursive

# install dependencies
npm install

# enter Cesium token
export VUE_APP_CESIUM_TOKEN=<your token>

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

## Run Frontend with Backend (Local Dev)

In one terminal, start the backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

In another terminal, start the web app and point it at the backend:

```bash
export VUE_APP_CESIUM_TOKEN=<your token>
export VUE_APP_BACKEND_URL=http://localhost:8000
npm run dev
```

Validate the backend is up:

```bash
curl http://localhost:8000/api/health
```

Optional: bootstrap a session (send a compact summary) before chatting:

```bash
curl -X POST http://localhost:8000/api/session/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{"summary": {"meta": {"duration_s": 1100}}}'
```
