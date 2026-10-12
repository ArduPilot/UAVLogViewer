# UAV Log Viewer

![log seeking](preview.gif "Logo Title Text 1")

This is a Javascript based log viewer for Mavlink telemetry and dataflash logs.
[Live demo here](http://plot.ardupilot.org).

## prebuilt Docker

To run the prebuilt Docker image, simply run the following command. No Cesium ion token is needed: the 3D view uses self-hosted terrain and keyless imagery.

```bash
docker run -p 8080:8080 -d ghcr.io/ardupilot/uavlogviewer:latest
```

## local Build Setup

```bash
# initialize submodules
git submodule update --init --recursive

# install dependencies
npm install

# serve with hot reload at localhost:8080
npm run dev

# build for production with minification
npm run build

# run production build locally
npm start

# run unit tests
npm run unit

# run e2e tests
npm run e2e

# run all tests
npm test
```

## deployment of static files to a server

To build a static version of the application and deploy it to a server, you can use the following commands. The built files will be located in the `dist` directory, which you can then upload to your server.

```bash
git submodule update --init --recursive

npm install

npm run build
```

## build local Docker image

The image works with Docker or Podman. It serves the production build as a non-root user.

```bash
# Build the image (optionally --build-arg USER_UID=... --build-arg USER_GID=...)
docker build -t uavlogviewer .

# Run it and open http://localhost:8080
docker run -d --name uavlogviewer -p 8080:8080 uavlogviewer
```

## offline use with local 3D terrain

Without internet the viewer still parses and plots logs, and the 3D view uses Cesium's
bundled low-resolution world imagery. For real terrain under the flights, mount a terrain
tileset into the container at `/usr/src/app/dist/quantized`; it is then served at
`/quantized/` like on plot.ardupilot.org. Flights outside the tileset's area are placed with
their takeoff on the visible ground (adjustable in the 3D settings).

```bash
docker run -d --name uavlogviewer -p 8080:8080     -v /path/to/quantized:/usr/src/app/dist/quantized:ro uavlogviewer
```

Build a tileset for your flying area once, while online, with the tiler in
`scripts/terrain` (see its README). Download the SRTM1 cells that cover the area from
`https://terrain.ardupilot.org/SRTM1/<cell>.hgt.zip` (cells are named by their south-west
corner, e.g. `S01W079`), then run the tiler in a container:

```bash
docker run --rm -v "$PWD/scripts/terrain:/tiler:ro" -v /path/to/srtm:/srtm:ro     -v /path/to/quantized:/out python:3.12-slim sh -c     "apt-get update && apt-get install -y --no-install-recommends libexpat1 &&      pip install -r /tiler/requirements.txt &&      python /tiler/srtm_to_qmesh.py --cell S01W079 N00W079 --srtm-res 1          --srtm-dir /srtm --out /out --jobs 4"
```

To cover a new area later, add its cells to `--cell` (keep the old ones) and run it again:
existing tiles are skipped and `layer.json` is rewritten for all cells.
