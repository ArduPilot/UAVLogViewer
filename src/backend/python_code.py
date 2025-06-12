
import json

def analyze_gps_data(file_path):
    """
    Analyzes GPS data from a JSON file for potential issues like signal loss,
    sudden jumps in coordinates, or a low number of satellites.

    Args:
        file_path (str): The path to the JSON file containing flight telemetry data.

    Returns:
        str: A summary of any identified GPS issues. Returns "No GPS issues found."
             if no issues are detected.
    """

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        return "Error: File not found."
    except Exception as e:
        return f"Error: Could not parse JSON data. {e}"

    gps_data = []
    for item in data:
        if item["type"] == "GPS":
            gps_data.append(item["data"])

    if not gps_data:
        return "No GPS data found in the file."

    issues = []
    previous_location = None
    satellite_threshold = 6  # Minimum number of satellites for a good fix
    large_distance_threshold = 0.001 # Significant change in coordinates (adjust as needed, in degrees)

    for entry in gps_data:
        num_satellites = entry.get("satellites_visible", 0)
        latitude = entry.get("lat", None)
        longitude = entry.get("lon", None)

        if num_satellites < satellite_threshold:
            issues.append(f"Low number of satellites: {num_satellites}")

        if latitude is not None and longitude is not None:
            current_location = (latitude, longitude)
            if previous_location:
                distance = ((current_location[0] - previous_location[0])**2 + (current_location[1] - previous_location[1])**2)**0.5
                if distance > large_distance_threshold:
                    issues.append(f"Sudden jump in coordinates. Distance: {distance:.4f} degrees")

            previous_location = current_location

    if issues:
        return ". ".join(issues)
    else:
        return "No GPS issues found."


file_path = 'parsed_telemetry.json'
result = analyze_gps_data(file_path)
