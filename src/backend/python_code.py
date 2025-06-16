
import json

def analyze_telemetry(file_path="parsed_telemetry.json"):
    """
    Analyzes flight telemetry data for potential anomalies.

    Args:
        file_path (str): Path to the JSON file containing telemetry data.

    Returns:
        str: A summary of detected anomalies.
    """

    try:
        with open(file_path, 'r') as f:
            telemetry_data = json.load(f)
    except FileNotFoundError:
        return "Error: Telemetry file not found."
    except Exception as e:
        return f"Error: Could not load telemetry data. {e}"

    anomalies = []
    battery_anomalies = []
    imu_anomalies = []
    altitude_anomalies = []

    for entry in telemetry_data:
        try:
            if entry["type"] == "SYS_STATUS":
                voltage_battery = entry["data"]["voltage_battery"]
                current_battery = entry["data"]["current_battery"]
                battery_remaining = entry["data"]["battery_remaining"]

                if voltage_battery == 0:
                    battery_anomalies.append("Battery voltage is zero.")
                if current_battery < 0:
                     battery_anomalies.append("Battery current is negative.")
                if battery_remaining < 0:
                    battery_anomalies.append("Battery remaining is negative.")

            elif entry["type"] in ("RAW_IMU", "SCALED_IMU2"):
                xacc = entry["data"]["xacc"]
                yacc = entry["data"]["yacc"]
                zacc = entry["data"]["zacc"]

                if abs(xacc) > 2000 or abs(yacc) > 2000 or abs(zacc) > 2000:
                    imu_anomalies.append(f"High acceleration detected: x={xacc}, y={yacc}, z={zacc}")

            elif entry["type"] == "SCALED_PRESSURE":
                pressure_abs = entry["data"]["press_abs"]
                temperature = entry["data"]["temperature"]

                if pressure_abs < 100:
                    altitude_anomalies.append(f"Low absolute pressure: {pressure_abs}")
                if temperature < 0 or temperature > 10000:
                    altitude_anomalies.append(f"Unusual temperature: {temperature}")
        except KeyError as e:
             print(f"KeyError: {e} in entry {entry.get('type', 'Unknown')}")
        except Exception as e:
            print(f"An error occurred while processing entry {entry.get('type', 'Unknown')}: {e}")

    if battery_anomalies:
        anomalies.append(f"Battery Issues: {', '.join(battery_anomalies)}")
    if imu_anomalies:
        anomalies.append(f"IMU Issues: {', '.join(imu_anomalies)}")
    if altitude_anomalies:
        anomalies.append(f"Altitude/Pressure Issues: {', '.join(altitude_anomalies)}")

    if not anomalies:
        return "No anomalies detected."
    else:
        return "; ".join(anomalies)


result = analyze_telemetry()
