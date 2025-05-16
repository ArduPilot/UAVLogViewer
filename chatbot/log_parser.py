import os
import time
from pymavlink import mavutil

def parse_log(path):
    ext = os.path.splitext(path)[1].lower()

    if ext == ".bin":
        conn = mavutil.mavlink_connection(path, dialect="ardupilotmega", robust_parsing=True)
    elif ext == ".tlog":
        conn = mavutil.mavlink_connection(path, baud=57600, robust_parsing=True)
    else:
        return {"error": f"Unsupported: {ext}"}

    data = {
        "altitudes": [], "gps_status": [], "errors": [],
        "rc_loss": [], "battery_temps": [], "gps_times": [], "rc_loss_times": []
    }

    start, max_dur, max_msgs = time.time(), 5, 2000
    count = 0

    while count < max_msgs and (time.time() - start) < max_dur:
        msg = conn.recv_match(blocking=False)
        if not msg or msg.get_type() == "BAD_DATA":
            continue
        count += 1
        t = msg.get_type()

        if t == "GPS_RAW_INT":
            data["gps_status"].append({
                "fix_type": msg.fix_type, "satellites_visible": msg.satellites_visible,
                "eph": msg.eph, "epv": msg.epv
            })
            if hasattr(msg, "time_usec"):
                data["gps_times"].append(msg.time_usec)

        elif t == "ALTITUDE":
            data["altitudes"].append({
                "alt_amsl": msg.alt_amsl, "alt_local": msg.alt_local
            })

        elif t == "STATUSTEXT":
            text = msg.text.lower()
            if any(k in text for k in ("fail", "lost", "error")):
                data["errors"].append(text)
            if "rc" in text and "lost" in text:
                data["rc_loss"].append(text)
                if hasattr(msg, "_timestamp"):
                    data["rc_loss_times"].append(msg._timestamp)

        elif t == "BATTERY_STATUS":
            temp = msg.temperature
            if temp is not None and temp != -1:
                data["battery_temps"].append(temp / 100.0)

    return data
