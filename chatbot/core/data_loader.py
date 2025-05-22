from pymavlink import mavutil
from pathlib import Path

class TelemetryDataLoader:
    def __init__(self, log_path: str):
        self.data = self._load_flight_data(log_path)
        self._compute_metrics()

    def _load_flight_data(self, path: str) -> list:
        try:
            tlog_path = Path(path).with_suffix('.tlog')
            print(f"Attempting to load .tlog file from: {tlog_path.resolve()}")
            
            if not tlog_path.exists():
                raise FileNotFoundError(f".tlog file not found at {tlog_path}")

            mlog = mavutil.mavlink_connection(str(tlog_path))
            data = []
            last_altitude = None
            last_gps_status = None
            last_battery_temp = None
            message_count = 0

            while True:
                msg = mlog.recv_match()
                if msg is None:
                    break
                message_count += 1
                msg_type = msg.get_type()
                entry = {
                    "timestamp": getattr(msg, '_timestamp', 0.0)
                }

                if msg_type == 'GLOBAL_POSITION_INT':
                    entry["altitude"] = msg.relative_alt / 1000.0
                    last_altitude = entry["altitude"]
                elif msg_type == 'GPS_RAW_INT':
                    entry["GPS_status"] = msg.fix_type
                    last_gps_status = entry["GPS_status"]
                elif msg_type == 'BATTERY_STATUS':
                    entry["battery_temp"] = msg.temperature / 100.0 if msg.temperature != -1 else None
                    last_battery_temp = entry["battery_temp"]
                    # print(f"BATTERY_STATUS at {entry['timestamp']}: temperature = {entry['battery_temp']}°C")
                elif msg_type == 'SYS_STATUS':
                    entry["errors"] = self._extract_errors(msg)
                else:
                    continue

                entry["altitude"] = entry.get("altitude", last_altitude)
                entry["GPS_status"] = entry.get("GPS_status", last_gps_status)
                entry["battery_temp"] = entry.get("battery_temp", last_battery_temp)
                entry["errors"] = entry.get("errors", [])

                if any(key in entry for key in ["altitude", "GPS_status", "battery_temp", "errors"]):
                    data.append(entry)

            print(f"Processed {message_count} messages, extracted {len(data)} entries with relevant data")
            if not data:
                raise ValueError("No relevant data (altitude, GPS_status, battery_temp, or errors) found in .tlog file.")
            return data

        except FileNotFoundError as e:
            raise ValueError(f"File error: {e}")
        except Exception as e:
            raise ValueError(f"Error loading .tlog file: {e}")

    def _extract_errors(self, msg):
        errors = []
        if hasattr(msg, 'onboard_control_sensors_health'):
            if not (msg.onboard_control_sensors_health & mavutil.mavlink.MAV_SYS_STATUS_SENSOR_RC_RECEIVER):
                errors.append("RC_LOSS")
            if not (msg.onboard_control_sensors_health & mavutil.mavlink.MAV_SYS_STATUS_SENSOR_3D_GYRO):
                errors.append("GYRO_ERROR")
        return errors if errors else []

    def _compute_metrics(self):
        """Compute additional metrics for anomaly detection."""
        # Initialize metrics
        for entry in self.data:
            entry["altitude_rate"] = 0.0
            entry["battery_temp_rate"] = 0.0
            entry["gps_transitions"] = []

        # Compute rates of change
        for i in range(1, len(self.data)):
            prev_entry = self.data[i - 1]
            curr_entry = self.data[i]
            time_diff = curr_entry["timestamp"] - prev_entry["timestamp"]

            if time_diff > 0:
                if "altitude" in prev_entry and "altitude" in curr_entry:
                    alt_diff = curr_entry["altitude"] - prev_entry["altitude"]
                    curr_entry["altitude_rate"] = alt_diff / time_diff

                # Battery temperature rate of change
                if ("battery_temp" in prev_entry and "battery_temp" in curr_entry and
                    prev_entry["battery_temp"] is not None and curr_entry["battery_temp"] is not None):
                    temp_diff = curr_entry["battery_temp"] - prev_entry["battery_temp"]
                    curr_entry["battery_temp_rate"] = temp_diff / time_diff
                else:
                    print(f"Skipping battery_temp_rate at timestamp {curr_entry['timestamp']} due to None value")

            # Track GPS status transitions
            if "GPS_status" in prev_entry and "GPS_status" in curr_entry:
                if prev_entry["GPS_status"] != curr_entry["GPS_status"]:
                    curr_entry["gps_transitions"] = [f"GPS status changed from {prev_entry['GPS_status']} to {curr_entry['GPS_status']}"]

        # Summarize error frequency
        self.error_summary = {}
        for entry in self.data:
            for error in entry.get("errors", []):
                self.error_summary[error] = self.error_summary.get(error, 0) + 1

    def get_timeseries(self, field: str) -> list:
        return [entry[field] for entry in self.data if field in entry and entry[field] is not None]

    def get_max_value(self, field: str) -> float:
        values = self.get_timeseries(field)
        return max(values) if values else None

    def find_events(self, field: str, condition: str) -> list:
        if field == "GPS_status" and condition == "lost":
            return [
                {"timestamp": entry["timestamp"], "event": "GPS signal lost"}
                for entry in self.data if entry.get("GPS_status") == 0
            ]
        elif field == "errors" and condition == "RC_LOSS":
            return [
                {"timestamp": entry["timestamp"], "event": "RC signal loss"}
                for entry in self.data if "RC_LOSS" in entry.get("errors", [])
            ]
        elif field == "errors" and condition == "critical":
            return [
                {"timestamp": entry["timestamp"], "event": error}
                for entry in self.data
                for error in entry.get("errors", [])
                if error != "RC_LOSS"
            ]
        return []

    def calculate_flight_duration(self) -> float:
        if not self.data:
            return 0.0
        start_time = self.data[0]["timestamp"]
        end_time = self.data[-1]["timestamp"]
        return end_time - start_time

    def get_anomaly_metrics(self):
        """Return structured data for anomaly detection."""
        return {
            "altitude_rates": self.get_timeseries("altitude_rate"),
            "battery_temp_rates": self.get_timeseries("battery_temp_rate"),
            "gps_transitions": [
                entry["gps_transitions"] for entry in self.data if entry.get("gps_transitions")
            ],
            "error_summary": self.error_summary,
            "gps_statuses": self.get_timeseries("GPS_status"),
            "flight_duration": self.calculate_flight_duration()
        }