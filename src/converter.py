from pymavlink import mavutil
import json
import numpy as np

def make_serializable(obj):
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [make_serializable(i) for i in obj]
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    elif hasattr(obj, 'tolist'):  # Catches NumPy arrays and scalars
        return obj.tolist()
    elif hasattr(obj, '__dict__'):
        return make_serializable(vars(obj))
    elif isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    else:
        return str(obj)  # Fallback: just convert to string


def parse_bin_file(bin_path):
    mav = mavutil.mavlink_connection(bin_path, dialect="ardupilotmega")
    parsed_logs = []

    while True:
        msg = mav.recv_match(blocking=False)
        if msg is None:
            break
        if msg.get_type() == "FMT":
            continue
        try:
            msg_dict = msg.to_dict()
            msg_dict['timestamp'] = msg._timestamp
            # Make all values serializable
            msg_dict = {k: make_serializable(v) for k, v in msg_dict.items()}
            parsed_logs.append({
                "type": msg.get_type(),
                "data": msg_dict
            })
        except:
            continue

    return parsed_logs

# Usage
file_path = "C:/Users/Vv27/Downloads/1980-01-08 09-44-08.bin"
logs = parse_bin_file(file_path)

with open("parsed_telemetry.json", "w") as f:
    json.dump(logs, f, indent=2)
