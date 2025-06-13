#!/usr/bin/env python3
"""upload_log.py – simple CLI helper to POST a flight log to the FastAPI backend.

Usage
-----
    python backend/upload_log.py [path_to_log] [--url http://localhost:8000]

If no path is given, defaults to '~/Downloads/1980-01-08 09-44-08.bin'.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

try:
    import requests  # type: ignore
except ImportError:
    sys.exit("The 'requests' package is required: pip install requests")

DEFAULT_URL = "http://localhost:8000/upload-log"
DEFAULT_PATH = Path.home() / "Downloads/1980-01-08 09-44-08.bin"


def upload_log(file_path: Path, endpoint: str) -> None:
    if not file_path.exists():
        sys.exit(f"File not found: {file_path}")

    with file_path.open("rb") as fh:
        files = {"file": (file_path.name, fh, "application/octet-stream")}
        print(f"Uploading {file_path} to {endpoint} …")
        resp = requests.post(endpoint, files=files, timeout=300)

    if resp.status_code == 200:
        data = resp.json()
        print("Upload succeeded → Session ID:", data.get("session_id"))
    else:
        print("Upload failed: HTTP", resp.status_code)
        try:
            print(resp.json())
        except Exception:
            print(resp.text)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload a flight log to the UAV backend"
    )
    parser.add_argument(
        "path", nargs="?", default=str(DEFAULT_PATH), help="Path to .bin or .tlog file"
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Upload endpoint URL")
    args = parser.parse_args()

    upload_log(Path(args.path).expanduser(), args.url)


if __name__ == "__main__":
    main()
