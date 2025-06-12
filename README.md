# Assessment Overview:

In this assessment I have implemented 2 features:

-   ChatBot that gives basic answer from the user uploaded bin file
-   Made ChatBot flight aware so it will provide answer of users high level questions.

TechStack used: Python for backend and Vue for frontend

Challenges faced:

-   Initially I tried to implement OLLAMA with local Llama models, hoping for a free and private LLM solution.
-   But unfortunately I faced a lot of lagging and stability issue. So after struggling for 1 whole day I have used OPEN AI API LLM for chatbot implementation.
-   This assessment was really interesting for me as I learned a lot from this like parsing the data, structuring the bin file and integrating LLM.

[Video Demo](https://drive.google.com/file/d/1vRbxJHXVAvmdelqUmR7pjvXWpJ8gg538/view?usp=sharing).

# UAV Log Viewer

![log seeking](preview.gif "Logo Title Text 1")

This is a Javascript based log viewer for Mavlink telemetry and dataflash logs.
[Live demo here](http://plot.ardupilot.org).

## Build Setup

```bash
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

```bash
docker run -p 8080:8080 -d ghcr.io/ardupilot/uavlogviewer:latest

```

or build the docker file locally:

```bash

# Build Docker Image
docker build -t <your username>/uavlogviewer .

# Run Docker Image
docker run -e VUE_APP_CESIUM_TOKEN=<Your cesium ion token> -it -p 8080:8080 -v ${PWD}:/usr/src/app <your username>/uavlogviewer

# Navigate to localhost:8080 in your web browser

# changes should automatically be applied to the viewer

```
