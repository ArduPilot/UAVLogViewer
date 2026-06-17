#!/usr/bin/env python3
"""Convert ArduPilot SRTM .hgt(.zip) cells into a Cesium quantized-mesh tileset.

Output: <out>/layer.json + <out>/{z}/{x}/{y}.terrain (gzipped), EPSG:4326 / TMS,
with octvertexnormals (lighting) and per-level availability (so sampleTerrainMostDetailed
works). Reads cells through GDAL /vsizip (no unzip needed). Parallel and resumable
(existing tiles are skipped).

Examples:
  # Canberra test (single cell), SRTM3:
  ./srtm_to_qmesh.py --cell S36E149 --srtm-dir /mnt/terrain_data/data/SRTM3 \
      --out /mnt/terrain_data/data/quantized
  # A bbox at SRTM1:
  ./srtm_to_qmesh.py --bbox 149 -36 150 -35 --srtm-dir /mnt/terrain_data/data/SRTM1 \
      --out /mnt/terrain_data/data/quantized --jobs 4
  # Whole world from SRTM3 (cell-driven, skips oceans):
  ./srtm_to_qmesh.py --srtm-dir /mnt/terrain_data/data/SRTM3 \
      --out /mnt/terrain_data/data/quantized --jobs 4
"""
import argparse
import glob
import gzip
import io
import json
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds
from pydelatin import Delatin
from quantized_mesh_encoder import encode, VertexNormalsExtension

CELL_RE = re.compile(r'^([NS])(\d{2})([EW])(\d{3})$')

# Default max zoom by source resolution (tile ~ native block at that level).
DEFAULT_MAXZOOM = {1: 13, 3: 11}


def parse_cell(name):
    """'S36E149' -> (lat0, lon0) of the SW corner."""
    m = CELL_RE.match(name)
    if not m:
        return None
    ns, la, ew, lo = m.groups()
    lat = int(la) * (1 if ns == 'N' else -1)
    lon = int(lo) * (1 if ew == 'E' else -1)
    return lat, lon


def cell_name(lat0, lon0):
    return '%s%02d%s%03d' % ('N' if lat0 >= 0 else 'S', abs(lat0),
                             'E' if lon0 >= 0 else 'W', abs(lon0))


def tile_size_deg(z):
    return 180.0 / (1 << z)


def tile_bounds(z, x, y):
    """Geographic rect of TMS tile (y from south). Returns (west, south, east, north)."""
    s = tile_size_deg(z)
    west = -180.0 + x * s
    south = -90.0 + y * s
    return west, south, west + s, south + s


def tile_range_for_bbox(z, w, s, e, n):
    """Inclusive (x0, x1, y0, y1) tile range covering a geographic bbox at zoom z."""
    sz = tile_size_deg(z)
    nx = 2 << z  # numberOfXTiles = 2 * 2^z
    ny = 1 << z
    x0 = max(0, int((w + 180.0) / sz))
    x1 = min(nx - 1, int((e + 180.0 - 1e-9) / sz))
    y0 = max(0, int((s + 90.0) / sz))
    y1 = min(ny - 1, int((n + 90.0 - 1e-9) / sz))
    return x0, x1, y0, y1


# ---------------------------------------------------------------- source / VRT

def find_cells(srtm_dir):
    """name -> (lat0, lon0, zip_path) for every NxxExxx.hgt.zip under srtm_dir."""
    out = {}
    for p in glob.iglob(os.path.join(srtm_dir, '**', '*.hgt.zip'), recursive=True):
        name = os.path.basename(p)[:-len('.hgt.zip')]
        c = parse_cell(name)
        if c:
            out[name] = (c[0], c[1], p)
    return out


def build_vrt(cells, vrt_path):
    """Write a GDAL VRT mosaicking the given cells (list of (lat0, lon0, zip_path))."""
    # Probe the first cell for size / dtype (all SRTM cells share a grid phase).
    lat0, lon0, zp = cells[0]
    inner = cell_name(lat0, lon0) + '.hgt'
    with rasterio.open('/vsizip/%s/%s' % (zp, inner)) as ds:
        size = ds.width  # 3601 (SRTM1) or 1201 (SRTM3)
    ppd = size - 1      # posts per degree (3600 / 1200)
    res = 1.0 / ppd
    lon0s = [c[1] for c in cells]
    lat0s = [c[0] for c in cells]
    min_lon, max_lon = min(lon0s), max(lon0s)
    min_lat, max_lat = min(lat0s), max(lat0s)
    max_north = max_lat + 1
    rx = (max_lon + 1 - min_lon) * ppd + 1
    ry = (max_north - min_lat) * ppd + 1
    gleft = min_lon - 0.5 * res
    gtop = max_north + 0.5 * res
    srcs = []
    for (la, lo, zp) in cells:
        inner = cell_name(la, lo) + '.hgt'
        xoff = round((lo - min_lon) * ppd)
        yoff = round((max_north - (la + 1)) * ppd)
        srcs.append(
            '<SimpleSource><SourceFilename relativeToVRT="0">/vsizip/%s/%s'
            '</SourceFilename><SourceBand>1</SourceBand>'
            '<SrcRect xOff="0" yOff="0" xSize="%d" ySize="%d"/>'
            '<DstRect xOff="%d" yOff="%d" xSize="%d" ySize="%d"/></SimpleSource>'
            % (zp, inner, size, size, xoff, yoff, size, size))
    xml = (
        '<VRTDataset rasterXSize="%d" rasterYSize="%d">'
        '<SRS>EPSG:4326</SRS>'
        '<GeoTransform>%.10f, %.12f, 0, %.10f, 0, %.12f</GeoTransform>'
        '<VRTRasterBand dataType="Int16" band="1"><NoDataValue>-32768</NoDataValue>'
        '%s</VRTRasterBand></VRTDataset>'
        % (rx, ry, gleft, res, gtop, -res, ''.join(srcs)))
    with open(vrt_path, 'w') as f:
        f.write(xml)
    return ppd


# ---------------------------------------------------------------- tile render

# Per-worker globals (set in init so the VRT is opened once per process).
_VRT = None
_DS = None
_DS_COARSE = None
_COARSE_MAXZ = -1
_OUT = None
_MAX_ERROR = None
_TILE_PX = None
_FORCE = False
_GRID = 0
_GRID_IDX = None


def _grid_indices(g):
    """Triangle indices for a regular g x g vertex grid (row-major)."""
    r, c = np.mgrid[0:g - 1, 0:g - 1]
    v00 = (r * g + c).ravel()
    tri1 = np.stack([v00, v00 + g, v00 + g + 1], axis=1)
    tri2 = np.stack([v00, v00 + g + 1, v00 + 1], axis=1)
    return np.concatenate([tri1, tri2]).astype(np.uint32)


def _init_worker(vrt_path, out_dir, max_error, tile_px, force, coarse_dem,
                 coarse_maxz, grid):
    global _VRT, _DS, _DS_COARSE, _COARSE_MAXZ, _OUT, _MAX_ERROR, _TILE_PX, _FORCE
    global _GRID, _GRID_IDX
    _VRT, _OUT, _MAX_ERROR, _TILE_PX, _FORCE = \
        vrt_path, out_dir, max_error, tile_px, force
    _DS = rasterio.open(vrt_path)
    _COARSE_MAXZ = coarse_maxz
    _DS_COARSE = rasterio.open(coarse_dem) if coarse_dem else None
    _GRID = grid
    _GRID_IDX = _grid_indices(grid) if grid > 0 else None


def render_tile(zxy):
    z, x, y = zxy
    out_file = os.path.join(_OUT, str(z), str(x), '%d.terrain' % y)
    if not _FORCE and os.path.exists(out_file):
        return 'skip'
    # Low zoom reads the coarse global DEM (cheap, has overviews); high zoom reads
    # full-res SRTM (each tile then covers only ~1 cell, so the window is bounded).
    ds = _DS_COARSE if (_DS_COARSE is not None and z <= _COARSE_MAXZ) else _DS
    west, south, east, north = tile_bounds(z, x, y)

    if _GRID > 0:
        # Sample a regular g x g grid whose pixel centres land exactly on the tile
        # corners/edges (read window expanded half a step), so neighbouring tiles
        # share identical edge vertices -> no cracks, no exposed skirts.
        g = _GRID
        sx = (east - west) / (g - 1)
        sy = (north - south) / (g - 1)
        ew, es, ee, en = west - sx / 2, south - sy / 2, east + sx / 2, north + sy / 2
        # Only the (slow) boundless read path is needed when the window pokes past the
        # data extent (coverage edges); interior tiles read directly (~12x faster).
        db = ds.bounds
        inside = ew >= db.left and es >= db.bottom and ee <= db.right and en <= db.top
        arr = ds.read(1, window=from_bounds(ew, es, ee, en, ds.transform),
                      out_shape=(g, g), resampling=Resampling.bilinear,
                      boundless=not inside, fill_value=0).astype(np.float32)
        arr[arr < -1000.0] = 0.0
        rr, cc = np.mgrid[0:g, 0:g]
        lon = west + cc.ravel() * sx
        lat = north - rr.ravel() * sy
        pos = np.column_stack([lon, lat, arr.ravel()]).astype(np.float32)
        idx = _GRID_IDX
    else:
        # Adaptive Delatin mesh, with the read clamped to the data extent so low-zoom
        # tiles don't trigger a giant boundless read of the whole mosaic.
        db = ds.bounds
        iw, ie = max(west, db.left), min(east, db.right)
        isb, itn = max(south, db.bottom), min(north, db.top)
        if ie <= iw or itn <= isb:
            return 'empty'  # tile doesn't overlap any source data
        resx, resy = ds.res
        ow = max(2, min(int(round((east - west) / resx)) + 1, _TILE_PX))
        oh = max(2, min(int(round((north - south) / resy)) + 1, _TILE_PX))
        arr = np.zeros((oh, ow), np.float32)
        cx0 = max(0, int(np.floor((iw - west) / (east - west) * (ow - 1))))
        cx1 = min(ow - 1, int(np.ceil((ie - west) / (east - west) * (ow - 1))))
        ry0 = max(0, int(np.floor((north - itn) / (north - south) * (oh - 1))))
        ry1 = min(oh - 1, int(np.ceil((north - isb) / (north - south) * (oh - 1))))
        sw, sh = cx1 - cx0 + 1, ry1 - ry0 + 1
        if sw < 2 or sh < 2:
            return 'empty'
        bw = west + cx0 / (ow - 1) * (east - west)
        be = west + cx1 / (ow - 1) * (east - west)
        bn = north - ry0 / (oh - 1) * (north - south)
        bs = north - ry1 / (oh - 1) * (north - south)
        sub = ds.read(1, window=from_bounds(bw, bs, be, bn, ds.transform),
                      out_shape=(sh, sw), resampling=Resampling.bilinear,
                      boundless=True, fill_value=0).astype(np.float32)
        sub[sub < -1000.0] = 0.0
        arr[ry0:ry0 + sh, cx0:cx0 + sw] = sub
        tin = Delatin(arr, max_error=_MAX_ERROR)
        verts, tris = tin.vertices, tin.triangles
        if len(tris) == 0:
            return 'empty'
        W, H = ow, oh
        lon = west + verts[:, 0] / (W - 1) * (east - west)
        lat = north - verts[:, 1] / (H - 1) * (north - south)
        pos = np.column_stack([lon, lat, verts[:, 2]]).astype(np.float32)
        idx = tris.astype(np.uint32)
    ext = VertexNormalsExtension(indices=idx, positions=pos)
    buf = io.BytesIO()
    encode(buf, pos, idx, bounds=(west, south, east, north), extensions=[ext])
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    tmp = out_file + '.tmp%d' % os.getpid()
    with open(tmp, 'wb') as f:
        f.write(gzip.compress(buf.getvalue(), 6))
    os.replace(tmp, out_file)
    return 'ok'


# ---------------------------------------------------------------- work list

def build_worklist(cells, minzoom, maxzoom, clip=None):
    """Cell-driven tile set: only tiles intersecting an existing cell (oceans skipped).
    Levels minzoom..maxzoom. If clip=[W,S,E,N], tiles are restricted to that bbox."""
    tiles = set()
    per_level = {}
    for (la, lo, _zp) in cells:
        w, s, e, n = lo, la, lo + 1, la + 1
        if clip:
            w, s = max(w, clip[0]), max(s, clip[1])
            e, n = min(e, clip[2]), min(n, clip[3])
            if e <= w or n <= s:
                continue
        for z in range(minzoom, maxzoom + 1):
            x0, x1, y0, y1 = tile_range_for_bbox(z, w, s, e, n)
            lvl = per_level.setdefault(z, set())
            for x in range(x0, x1 + 1):
                for yy in range(y0, y1 + 1):
                    tiles.add((z, x, yy))
                    lvl.add((x, yy))
    return tiles, per_level


def availability(per_level, maxzoom):
    """Row-merge each level's (x,y) tiles into rectangles for layer.json."""
    out = []
    for z in range(maxzoom + 1):
        rects = []
        rows = {}
        for (x, y) in per_level.get(z, ()):
            rows.setdefault(y, []).append(x)
        for y in sorted(rows):
            xs = sorted(rows[y])
            run_start = prev = xs[0]
            for x in xs[1:] + [None]:
                if x is None or x != prev + 1:
                    rects.append({'startX': run_start, 'startY': y,
                                  'endX': prev, 'endY': y})
                    run_start = x
                prev = x if x is not None else prev
        out.append(rects)
    return out


def write_layer_json(out_dir, maxzoom, per_level, min_zoom):
    """Write layer.json. For an upgrade run (min_zoom > 0) availability is merged into
    the existing tileset so the base levels are kept (Cesium ORs the rectangle lists).
    A full run (min_zoom == 0) writes fresh availability so it never advertises stale
    tiles from a previous build."""
    path = os.path.join(out_dir, 'layer.json')
    new_avail = availability(per_level, maxzoom)
    old_avail, old_max = [], -1
    if min_zoom > 0 and os.path.exists(path):
        try:
            old = json.load(open(path))
            old_avail = old.get('available', [])
            old_max = old.get('maxzoom', len(old_avail) - 1)
        except Exception:
            pass
    final_max = max(maxzoom, old_max)
    merged = []
    for z in range(final_max + 1):
        a = old_avail[z] if z < len(old_avail) else []
        b = new_avail[z] if z < len(new_avail) else []
        merged.append(a + b)
    layer = {
        'tilejson': '2.1.0', 'format': 'quantized-mesh-1.0', 'version': '1.0.0',
        'scheme': 'tms', 'projection': 'EPSG:4326',
        'bounds': [-180, -90, 180, 90], 'minzoom': 0, 'maxzoom': final_max,
        'tiles': ['{z}/{x}/{y}.terrain'], 'extensions': ['octvertexnormals'],
        'available': merged,
    }
    with open(path, 'w') as f:
        json.dump(layer, f)


# ---------------------------------------------------------------- main

def bbox_from_center(lat, lon, radius_km):
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * max(0.1, np.cos(np.radians(lat))))
    return [lon - dlon, lat - dlat, lon + dlon, lat + dlat]


def select_cells(args, all_cells):
    """Return (cells, clip_bbox). clip_bbox tightens the tile range to an area."""
    if args.cell:
        sel = []
        for name in args.cell:
            if name not in all_cells:
                sys.exit('cell %s not found under %s' % (name, args.srtm_dir))
            sel.append(all_cells[name])
        return sel, None
    clip = None
    if args.center:
        clip = bbox_from_center(args.center[0], args.center[1], args.radius_km)
    elif args.bbox:
        clip = list(args.bbox)
    if clip:
        w, s, e, n = clip
        sel = []
        for lo in range(int(np.floor(w)), int(np.ceil(e))):
            for la in range(int(np.floor(s)), int(np.ceil(n))):
                nm = cell_name(la, lo)
                if nm in all_cells:
                    sel.append(all_cells[nm])
        return sel, clip
    return list(all_cells.values()), None  # whole world


def main():
    # Bound GDAL memory so parallel workers don't accumulate unbounded block/VSI
    # cache reading from the all-cells VRT. Set in the parent; inherited by forked
    # workers (must be set before the first GDAL open in build_vrt).
    os.environ.setdefault('GDAL_CACHEMAX', '128')              # MB block cache / proc
    os.environ.setdefault('GDAL_MAX_DATASET_POOL_SIZE', '64')  # open /vsizip sources

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--srtm-dir', required=True, help='dir of *.hgt.zip (recursive)')
    ap.add_argument('--out', required=True, help='output tileset dir')
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--cell', nargs='+', help='one or more cells, e.g. S36E149')
    g.add_argument('--bbox', nargs=4, type=float, metavar=('W', 'S', 'E', 'N'))
    g.add_argument('--center', nargs=2, type=float, metavar=('LAT', 'LON'),
                   help='upgrade an area centred on lat/lon (with --radius-km)')
    ap.add_argument('--radius-km', type=float, default=25.0,
                    help='radius for --center (km, default 25)')
    ap.add_argument('--srtm-res', type=int, choices=(1, 3), default=3,
                    help='source resolution, sets default max zoom (1=SRTM1, 3=SRTM3)')
    ap.add_argument('--max-zoom', type=int, default=None)
    ap.add_argument('--min-zoom', type=int, default=0,
                    help='lowest zoom to build (upgrades add only deep levels)')
    ap.add_argument('--max-error', type=float, default=4.0,
                    help='Delatin max vertical error (metres)')
    ap.add_argument('--tile-px', type=int, default=256, help='max sample grid per tile')
    ap.add_argument('--grid', type=int, default=65,
                    help='regular NxN vertex grid per tile (crack-free); '
                         '0 = adaptive Delatin (experimental: independent tiles can seam/crack)')
    ap.add_argument('--force', action='store_true',
                    help='overwrite existing tiles (default: skip = resume/upgrade)')
    ap.add_argument('--coarse-dem', default=None,
                    help='coarse global DEM (from build_coarse.py) for low zoom')
    ap.add_argument('--coarse-max-zoom', type=int, default=8,
                    help='use --coarse-dem for zoom <= this (default 8)')
    ap.add_argument('--jobs', type=int, default=os.cpu_count())
    ap.add_argument('--max-tasks-per-child', type=int, default=0,
                    help='recycle each worker after this many chunks (0 = never; '
                         'default). Avoid: a worker that errors on teardown can wedge '
                         'the pool. Bound memory with the GDAL caps below instead.')
    ap.add_argument('--start-index', type=int, default=0,
                    help='skip the first N tiles of the sorted worklist (resume)')
    ap.add_argument('--no-layer-json', action='store_true',
                    help='do not write layer.json (preserve hand-managed availability)')
    args = ap.parse_args()

    maxzoom = args.max_zoom if args.max_zoom is not None \
        else DEFAULT_MAXZOOM[args.srtm_res]

    all_cells = find_cells(args.srtm_dir)
    if not all_cells:
        sys.exit('no *.hgt.zip cells under %s' % args.srtm_dir)
    cells, clip = select_cells(args, all_cells)
    if not cells:
        sys.exit('no cells selected')
    print('cells=%d  zoom=%d-%d  jobs=%d  force=%s  out=%s'
          % (len(cells), args.min_zoom, maxzoom, args.jobs, args.force, args.out),
          flush=True)

    os.makedirs(args.out, exist_ok=True)
    vrt_path = os.path.join(args.out, '_source.vrt')
    build_vrt(cells, vrt_path)

    tiles, per_level = build_worklist(cells, args.min_zoom, maxzoom, clip)
    tiles = sorted(tiles)
    offset = max(0, args.start_index)
    if offset:
        tiles = tiles[offset:]
        print('resume: skipping first %d tiles' % offset, flush=True)
    print('tiles to consider: %d' % len(tiles), flush=True)

    if not args.no_layer_json:
        write_layer_json(args.out, maxzoom, per_level, args.min_zoom)  # up-front (resume-safe)

    t0 = time.time()
    counts = {'ok': 0, 'skip': 0, 'empty': 0}
    done = 0
    total = len(tiles) + offset
    pool_kw = {}
    if args.max_tasks_per_child > 0:
        pool_kw['max_tasks_per_child'] = args.max_tasks_per_child
    with ProcessPoolExecutor(max_workers=args.jobs, initializer=_init_worker,
                             initargs=(vrt_path, args.out, args.max_error,
                                       args.tile_px, args.force, args.coarse_dem,
                                       args.coarse_max_zoom, args.grid),
                             **pool_kw) as ex:
        for res in ex.map(render_tile, tiles, chunksize=16):
            counts[res] = counts.get(res, 0) + 1
            done += 1
            if done % 500 == 0 or done == len(tiles):
                dt = time.time() - t0
                rate = done / dt if dt else 0
                print('  %d/%d  ok=%d skip=%d empty=%d  %.0f tiles/s'
                      % (done + offset, total, counts['ok'], counts['skip'],
                         counts['empty'], rate), flush=True)
    print('done in %.1fs: %s' % (time.time() - t0, counts))
    print('layer.json + tiles in %s' % args.out)


if __name__ == '__main__':
    main()
