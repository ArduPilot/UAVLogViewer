# UAV Log Viewer

![log seeking](preview.gif "Logo Title Text 1")

 This is a Javascript based log viewer for Mavlink telemetry and dataflash logs.
 [Live demo here](http://plot.ardupilot.org).

## local Build Setup

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

npm start

# run unit tests
npm run unit

# run e2e tests
npm run e2e

# run all tests
npm test
```

## prebuilt Docker

run the prebuilt docker image:

``` bash
docker run -e VUE_APP_CESIUM_TOKEN=<Your cesium ion token> -p 8080:8080 -d ghcr.io/ardupilot/uavlogviewer:latest

```

or build the docker file locally:

## build local Docker image

``` bash

# Build Docker Image
docker build -t <your username>/uavlogviewer .

# Run Docker Image (token is read at container startup)
docker run -e VUE_APP_CESIUM_TOKEN=<Your cesium ion token> -it -p 8080:8080 -v ${PWD}:/usr/src/app <your username>/uavlogviewer

# Navigate to localhost:8080 in your web browser

# changes should automatically be applied to the viewer

```
