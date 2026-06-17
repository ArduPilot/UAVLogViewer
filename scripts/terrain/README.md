# SRTM → Cesium quantized-mesh tiler

Builds a Cesium `quantized-mesh-1.0` terrain tileset (`layer.json` + `{z}/{x}/{y}.terrain`)
from ArduPilot's existing SRTM `.hgt.zip` cells, so the log viewer can serve its own 3D
terrain instead of paying for Cesium ion. This is the server-side ("Path B") half of the
ion-removal work; the client change is `CesiumTerrainProvider.fromUrl('/quantized/')` in
`CesiumViewer.vue`.

Reads cells via GDAL `/vsizip/` (no unzip). Output is EPSG:4326 / TMS with oct-encoded
vertex normals (for lighting) and per-level availability in `layer.json` (so
`sampleTerrainMostDetailed` keeps working). Parallel and **resumable** — existing `.terrain`
files are skipped unless `--force`, so a long run can be re-run after an interruption.

## Mesher

Each tile is meshed on a **regular `--grid` (default 65×65) lattice** whose samples land
exactly on the tile's corners and edges. Because neighbouring tiles then share identical
edge vertices, there are **no seam cracks / "walls"** (the failure mode of an adaptive
per-tile TIN). The window is read one half-step oversized and uses rasterio `boundless`
reads only where the tile pokes past the DEM extent, which keeps interior tiles fast and
edge-aligned. `pydelatin` (`--max-error`) is still imported for an experimental adaptive
path but is **not** the default.

## Setup (Ubuntu 24.04 / Python 3.12)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt   # rasterio wheel bundles GDAL; no apt needed
```

## Build (two steps for a whole-world / large run)

Low zooms read many cells at once, so for anything large first bake a **coarse global DEM**
(1 arcmin GeoTIFF, tiled + overviews) and feed it in for the low levels — `srtm_to_qmesh.py`
then never does huge multi-cell full-res reads:

```bash
. .venv/bin/activate

# 1. coarse global DEM (once), used as the source for z <= --coarse-max-zoom
./build_coarse.py --srtm-dir /path/to/SRTM3 --out /path/to/quantized_coarse.tif --jobs 4

# 2a. small test area — a single SRTM3 cell, no coarse DEM needed
./srtm_to_qmesh.py --cell S36E149 --srtm-dir /path/to/SRTM3 --out /path/to/quantized

# 2b. region by radius (SRTM1, higher detail)
./srtm_to_qmesh.py --center -35.28 149.13 --radius-km 40 --srtm-res 1 \
    --srtm-dir /path/to/SRTM1 --out /path/to/quantized --jobs 4

# 2c. whole world (SRTM1 to z11; coarse DEM supplies z0..z8). Long; re-run to resume:
./srtm_to_qmesh.py --srtm-res 1 --srtm-dir /path/to/SRTM1 --out /path/to/quantized \
    --max-zoom 11 --jobs 4 \
    --coarse-dem /path/to/quantized_coarse.tif --coarse-max-zoom 8
```

Area selection (mutually exclusive): `--cell S36E149 [...]`, `--bbox W S E N`, or
`--center LAT LON --radius-km R`. With none, the whole local SRTM cell set is used
(oceans skipped). Other flags: `--srtm-res {1,3}` (default 3), `--max-zoom`
(default 13 for res 1, 11 for res 3), `--min-zoom` (>0 merges into existing availability
for incremental upgrades), `--grid` (default 65), `--max-error` (adaptive path only),
`--force` (rebuild existing tiles), `--jobs` (default = CPU count),
`--max-tasks-per-child` (recycle each worker after N chunks; default 400),
`--start-index N` (skip the first N sorted tiles, to resume mid-run),
`--no-layer-json` (don't write `layer.json`, e.g. when availability is hand-managed).

## Memory / long runs

Workers read windows from a single VRT mosaicking *all* SRTM cells, so GDAL would
otherwise accumulate block + `/vsizip` cache unbounded as high-zoom tiles march across
the globe (seen growing to ~2 GB/worker over hours). The fix is to cap GDAL in the parent
(inherited by forked workers): `GDAL_CACHEMAX` (block cache) and
`GDAL_MAX_DATASET_POOL_SIZE` (open `/vsizip` sources). On a small box also keep `--jobs`
modest (each worker needs ~0.5 GB).

`--max-tasks-per-child` (recycle workers) is **off by default and best left off**: if a
worker errors while tearing down its open dataset, the result it was computing is never
returned and `ProcessPoolExecutor.map` deadlocks the whole run. The GDAL caps bound memory
without needing recycling. If you must reclaim more, prefer restarting the process in
batches via `--start-index` (a full exit frees everything cleanly).

Tile writes are atomic (temp file + `os.replace`), so the build is **kill-safe** — a `.terrain`
file is never half-written. To resume after a kill: sweep stray `*.tmp*` files, then re-run
with `--start-index` set just below the last logged counter (with `--force`, since the tiles
already exist on disk).

## Serving (nginx)

```nginx
location /quantized/ {
    root /mnt/terrain_data/data;     # serves /mnt/terrain_data/data/quantized/...
    autoindex on;
    gzip off;                        # tiles are already gzipped
    add_header Access-Control-Allow-Origin *;
    location ~ \.terrain$ {
        root /mnt/terrain_data/data;
        add_header Content-Encoding gzip;
        default_type application/octet-stream;
        add_header Access-Control-Allow-Origin *;
    }
}
```

Client: `CesiumTerrainProvider.fromUrl('/quantized/')` (served under the app origin, or
reverse-proxied there to avoid cross-subdomain CORS). `.terrain` files and `layer.json` are
written gzip-compressed.

## Notes / caveats

- **Disk**: SRTM3 global ≈ 20–40 GB. SRTM1 to z11 global is far larger (hundreds of GB) —
  size the target before a world run.
- **Heights** are raw SRTM (orthometric / EGM96), not ellipsoidal — a tens-of-metres global
  offset vs strict WGS84. Fine for visualisation; revisit for precise AMSL overlay.
- **Availability vs reality**: `layer.json` must only advertise levels/rects that actually
  exist on disk — over-claiming makes Cesium fetch missing/old tiles (and is how stale
  high-zoom tiles can surface as walls during a partial rebuild). Cap availability to the
  finished levels while a long rebuild is in flight.
- Coverage is SRTM's 56°S–60°N; outside that there are no cells (client falls back to the
  ellipsoid).
- `/vsizip` re-reads the zip per tile; pre-unzipping cells to `.hgt` speeds up an I/O-bound
  world build.
```
