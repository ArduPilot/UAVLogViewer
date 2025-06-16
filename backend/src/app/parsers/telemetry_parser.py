from __future__ import annotations
import tempfile
from collections import defaultdict
from typing import Dict

import pandas as pd
from pymavlink import mavutil

from models.telemetry_data import TelemetryData


class TelemetryParser:
    """Converts raw .bin bytes into TelemetryData."""

    @staticmethod
    def parse(bin_bytes: bytes) -> TelemetryData:
        # --- write to temp file (pymavlink API needs a path) -----------
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as fh:
            fh.write(bin_bytes)
            file_path = fh.name

        reader = mavutil.mavlink_connection(
            file_path,
            dialect="ardupilotmega",
            notimestamps=True,
        )

        buckets: Dict[str, list[dict]] = defaultdict(list)

        while True:
            msg = reader.recv_match(blocking=False)
            if msg is None:
                break
            if msg.get_type() == "BAD_DATA":
                continue
            buckets[msg.get_type()].append(msg.to_dict())

        by_type: Dict[str, pd.DataFrame] = {}
        for mtype, rows in buckets.items():
            df = pd.DataFrame(rows)
            if "TimeUS" in df.columns:
                df["TimeUS"] = pd.to_datetime(df["TimeUS"], unit="us")
                df = df.set_index("TimeUS")
            by_type[mtype] = df

        return TelemetryData(by_type=by_type)
