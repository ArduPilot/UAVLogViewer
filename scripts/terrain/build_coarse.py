#!/usr/bin/env python3
"""Build a coarse global DEM GeoTIFF from SRTM3, used as the source for low-zoom
quantized-mesh tiles (so srtm_to_qmesh.py never reads huge multi-cell windows from
full-res SRTM at low zoom). Parallel per-cell (4 cores) with progress; output is
tiled + has internal overviews for fast windowed reads.

  ./build_coarse.py --srtm-dir /mnt/terrain_data/data/SRTM3 \
      --out /mnt/terrain_data/data/quantized_coarse.tif --jobs 4
"""
import argparse
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import rasterio
from rasterio import Affine
from rasterio.enums import Resampling

from srtm_to_qmesh import find_cells, cell_name

_PPD = 60  # output px per degree (60 = 1 arcmin)


def _read_cell(c):
    lat0, lon0, path = c
    inner = cell_name(lat0, lon0) + '.hgt'
    src = ('/vsizip/%s/%s' % (path, inner)) if path.endswith('.zip') else path
    try:
        with rasterio.open(src) as ds:
            a = ds.read(1, out_shape=(_PPD, _PPD), resampling=Resampling.average)
    except Exception:
        return (lat0, lon0, None)
    a = a.astype(np.int16)
    a[a < -1000] = 0
    return (lat0, lon0, a)


def main():
    global _PPD
    ap = argparse.ArgumentParser()
    ap.add_argument('--srtm-dir', required=True)
    ap.add_argument('--out', required=True, help='output GeoTIFF')
    ap.add_argument('--ppd', type=int, default=60, help='px per degree (60 = 1 arcmin)')
    ap.add_argument('--jobs', type=int, default=os.cpu_count())
    args = ap.parse_args()
    _PPD = args.ppd

    cells = list(find_cells(args.srtm_dir).values())
    lon0s = [c[1] for c in cells]
    lat0s = [c[0] for c in cells]
    min_lon, max_lon = min(lon0s), max(lon0s)
    min_lat, max_lat = min(lat0s), max(lat0s)
    W = (max_lon + 1 - min_lon) * args.ppd
    H = (max_lat + 1 - min_lat) * args.ppd
    print('cells=%d  grid=%dx%d (ppd=%d)  jobs=%d' % (len(cells), W, H, args.ppd, args.jobs),
          flush=True)

    grid = np.zeros((H, W), np.int16)
    t0 = time.time()
    done = 0
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for (lat0, lon0, a) in ex.map(_read_cell, cells, chunksize=32):
            done += 1
            if a is not None:
                col = (lon0 - min_lon) * args.ppd
                row = (max_lat - lat0) * args.ppd
                grid[row:row + args.ppd, col:col + args.ppd] = a
            if done % 2000 == 0 or done == len(cells):
                print('  %d/%d cells  %.0fs' % (done, len(cells), time.time() - t0), flush=True)

    transform = Affine(1.0 / args.ppd, 0, min_lon, 0, -1.0 / args.ppd, max_lat + 1)
    profile = dict(driver='GTiff', dtype='int16', count=1, width=W, height=H,
                   crs='EPSG:4326', transform=transform, nodata=-32768,
                   tiled=True, blockxsize=512, blockysize=512, compress='deflate')
    print('writing %s' % args.out, flush=True)
    with rasterio.open(args.out, 'w', **profile) as dst:
        dst.write(grid, 1)
        dst.build_overviews([2, 4, 8, 16, 32], Resampling.average)
    print('done in %.0fs' % (time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
