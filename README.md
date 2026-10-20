# UAV Log Viewer

A browser-based log viewer for MAVLink telemetry (`.tlog`) and dataflash (`.bin`)
logs. Live demo: [plot.ardupilot.org](http://plot.ardupilot.org).

![log seeking](preview.gif "Logo Title Text 1")

## Contents

- [Quick start](#quick-start)
- [Local development](#local-development)
- [Container development](#container-development)
- [Production builds](#production-builds)
- [Offline use with 3D terrain](#offline-use-with-3d-terrain)
- [Contributor docs](#contributor-docs)

## Quick start

Prebuilt production image — no Cesium ion token needed. Uses self-hosted terrain
and keyless imagery.

```bash
docker run -p 8080:8080 -d ghcr.io/ardupilot/uavlogviewer:latest
```

Then open <http://localhost:8080>.

## Local development

Requires Node.js 24 or newer. First time only:

```bash
git submodule update --init --recursive
npm install
```

Daily commands:

| Command | Purpose |
| --- | --- |
| `npm run dev` | Vite dev server at <http://localhost:8080> with HMR |
| `npm run build` | Production build to `dist/` |
| `npm start` | Serve the built `dist/` on port 8080 |
| `npm run unit` | Vitest unit tests |
| `npm run e2e` | Nightwatch end-to-end (headless Chrome; add `-- --env edgeHeadless` for Edge) |
| `npm test` | Unit + e2e |

## Container development

The same Vite dev server, running inside a container, with the source
bind-mounted from the host. Edits reload the browser without rebuilding the
image. Works on Linux, macOS, and Windows (via Podman machine).

### Prerequisites

- Podman installed, with its machine running:

  ```bash
  podman machine start          # Windows / macOS only
  ```

- Submodules initialised on the **host** (they are bind-mounted, not cloned
  inside the container):

  ```bash
  git submodule update --init --recursive
  ```

### Build the dev image

Run once, and again whenever `Containerfile.dev` or `package*.json` change:

```bash
podman build -f Containerfile.dev -t uavlogviewer-dev:dev .
```

A correct build has **8 steps** and ends with:

```
STEP 7/8: EXPOSE 8080
STEP 8/8: CMD ["npm","run","dev","--","--host","0.0.0.0"]
```

If you see `STEP 1/9` or a `COPY .git ./.git` line, the production `Dockerfile`
was used — the `-f` flag was missed.

`EXPOSE` is 8080 because `vite.config.js` runs the dev server on 8080. The
host port is 5173 (see next section), so the container's dev server and a
local prod server never collide.

### Run the dev container

Linux / macOS:

```bash
podman run -d --name uavlogviewer-dev \
  -p 5173:8080 \
  -v "$PWD":/usr/src/app:Z \
  -v /usr/src/app/node_modules \
  -e VITE_USE_POLLING=true \
  uavlogviewer-dev:dev
```

Windows (PowerShell):

```powershell
podman run -d --name uavlogviewer-dev `
  -p 5173:8080 `
  -v ${PWD}:/usr/src/app:Z `
  -v /usr/src/app/node_modules `
  -e VITE_USE_POLLING=true `
  uavlogviewer-dev:dev
```

Open <http://localhost:5173>. Edit any file under `src/` — the browser reloads
within a second.

Notes on the flags:

- **`-p 5173:8080`** — host 5173 → container 8080. The container runs Vite on
  8080; 8080 on the host is kept free for the production build.
- **`VITE_USE_POLLING=true`** — required on Windows and macOS: file-change
  events don't cross the Podman VM boundary, so Vite must poll. Harmless on
  Linux, where inotify works natively.
- **`-v /usr/src/app/node_modules`** — an anonymous volume. It keeps the
  Linux-built dependencies inside the container so the host's macOS/Windows
  `node_modules` doesn't shadow them.

### Daily workflow

| You changed | Command |
| --- | --- |
| A file under `src/` | Nothing — Vite HMR reloads the browser |
| `Containerfile.dev` or `package*.json` | `podman build` again, then `podman rm -f uavlogviewer-dev` and re-run |
| Nothing (resume) | `podman start uavlogviewer-dev` |
| Nothing (logs) | `podman logs -f uavlogviewer-dev` |
| Nothing (shutdown) | `podman stop uavlogviewer-dev` |
| Nothing (delete) | `podman rm -f uavlogviewer-dev` |

### Optional one-command dev loop

Drop this as `dev.ps1` (Windows) at the repo root to rebuild, restart, and
tail logs in one shot:

```powershell
podman build -f Containerfile.dev -t uavlogviewer-dev:dev .
podman rm -f uavlogviewer-dev 2>$null
podman run -d --name uavlogviewer-dev `
  -p 5173:8080 `
  -v ${PWD}:/usr/src/app:Z `
  -v /usr/src/app/node_modules `
  -e VITE_USE_POLLING=true `
  uavlogviewer-dev:dev
podman logs -f uavlogviewer-dev
```

Then `.\dev.ps1` runs the whole loop. Dev server: <http://localhost:5173>.

### Troubleshooting

**`podman compose` doesn't work on Windows.** `compose.yaml` is provided and
used on Linux/macOS:

```bash
podman compose -f compose.yaml up -d --build
```

Two Windows-specific problems break that path:

- Python `podman-compose` resolves `dockerfile: Containerfile.dev` in
  `podman-compose config`, but its `up --build` silently falls back to the
  production `Dockerfile` (build log shows `STEP 1/9`, `EXPOSE 8080`).
- The Docker Compose provider requires `DOCKER_HOST` in every new shell:

  ```powershell
  $env:DOCKER_HOST = "npipe:////./pipe/podman-machine-default"
  ```

The direct `podman build` / `podman run` above avoid both. Use them on Windows.

**Container runs as root.** `Containerfile.dev` deliberately does **not** use
`USER node` before `npm ci`: `/usr/src/app` is created by `WORKDIR` as root,
and `npm ci` as a non-root user fails with EACCES on `node_modules/`. Under
rootless Podman, "root inside the container" maps to your host user, so files
under the bind mount are owned by you either way. If non-root is required
later, the correct sequence is:

```dockerfile
RUN npm ci && chown -R node:node /usr/src/app
USER node
```

…plus `--userns=keep-id` on `podman run` (otherwise the container UID does
not map back to your host user, and the bind mount becomes unwritable).

## Production builds

### Static files

```bash
git submodule update --init --recursive
npm install
npm run build
```

Upload `dist/` to any static server.

### Production container

```bash
docker build -t uavlogviewer .
docker run -d --name uavlogviewer -p 8080:8080 uavlogviewer
```

Serves the built app as a non-root user. To match your local UID/GID:

```bash
docker build --build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g) -t uavlogviewer .
```

## Offline use with 3D terrain

Without internet, the viewer still parses and plots logs, and the 3D view uses
Cesium's bundled low-resolution world imagery. For real terrain under the
flights, mount a terrain tileset into the container at
`/usr/src/app/dist/quantized`; it is then served at `/quantized/` like on
plot.ardupilot.org. Flights outside the tileset's area are placed with their
takeoff on the visible ground (adjustable in the 3D settings).

```bash
docker run -d --name uavlogviewer -p 8080:8080 \
  -v /path/to/quantized:/usr/src/app/dist/quantized:ro \
  uavlogviewer
```

### Build your own tileset

Do this once while online, with the tiler in `scripts/terrain` (see its
README). Download the SRTM1 cells that cover your flying area from
`https://terrain.ardupilot.org/SRTM1/<cell>.hgt.zip` (cells are named by their
south-west corner, e.g. `S01W079`), then run the tiler in a container:

```bash
docker run --rm \
  -v "$PWD/scripts/terrain:/tiler:ro" \
  -v /path/to/srtm:/srtm:ro \
  -v /path/to/quantized:/out \
  python:3.12-slim sh -c \
  "apt-get update && apt-get install -y --no-install-recommends libexpat1 && \
   pip install -r /tiler/requirements.txt && \
   python /tiler/srtm_to_qmesh.py --cell S01W079 N00W079 --srtm-res 1 \
     --srtm-dir /srtm --out /out --jobs 4"
```

To extend coverage later, add the new cells to `--cell` (keep the existing
ones) and run again — existing tiles are skipped and `layer.json` is rewritten
for all cells.

## Contributor docs

- [`docs/widgets.md`](docs/widgets.md) — floating widget shell, CSS classes,
  modifiers, procedure for adding or converting a widget, and the pending
  rework plan.
- [`TODO.md`](TODO.md) — current open work on the `upgrade` branch.
- `scripts/terrain/` — the offline terrain tiler.
