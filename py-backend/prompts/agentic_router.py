
def get_routing_prompt(query: str) -> str:

    routing_instruction_prompt = """
    ### Task:
    You are a UAV analysis query router. Given a user query, select the most relevant data extraction
    step from the given extractor functions. If the query is broad or needs everything,
    return ['get_all']

    ### Guidlines:
    - To determine if an extractor can fetch useful data or not, refer to its purpose
    return_values information given below for each extractor.
    - Also refer to the possible_use_cases for the extractor to determine if data fetched from it, can be useful.
    But keep note that the use cases are not limited to the ones listed in the prompt.
    - If trajectory data is needed, look for instruction in the query about the source to be used. If it's
    not explicitly stated, return the extractor that uses GPS_RAW_INT as the trajectory source.

    
    ### Data Extractors:
    {
        "get_attitudes": {
            "purpose": "Extracts the roll, pitch, and yaw attitude angles over time from ATTITUDE messages.",
            "return_values": "Dictionary with timestamps as keys and [roll, pitch, yaw] lists as values.",
            "possible_use_cases": [
                "Visualizing UAV orientation over time",
                "Detecting instability or erratic attitude changes",
                "Supporting flight dynamics analysis and simulation validation"
            ]
        },
        "get_flight_modes": {
            "purpose": "Identifies and tracks changes in the UAV flight modes over time from HEARTBEAT messages.",
            "return_values": "List of [timestamp, flight_mode] pairs indicating mode changes.",
            "possible_use_cases": [
                "Analyzing transition patterns between flight modes",
                "Verifying adherence to autonomous or manual flight plans",
                "Detecting unauthorized mode switches"
            ]
        },
        "get_events": {
            "purpose": "Tracks arming and disarming events of the UAV based on HEARTBEAT messages.",
            "return_values": "List of [timestamp, 'Armed' or 'Disarmed'] indicating mode transitions.",
            "possible_use_cases": [
                "Identifying when the UAV was armed for flight",
                "Correlating mission events with arming states",
                "Security auditing of takeoff/landing events"
            ]
        },
        "get_mission": {
            "purpose": "Extracts waypoint coordinates from CMD messages that describe the UAV's mission.",
            "return_values": "List of [longitude, latitude, altitude] for each mission waypoint.",
            "possible_use_cases": [
                "Mapping planned mission trajectory",
                "Validating mission planning tools",
                "Comparing planned versus actual flight paths"
            ]
        },
        "get_vehicle_type": {
            "purpose": "Determines the type of vehicle (e.g., quadrotor, fixed-wing) based on HEARTBEAT 'craft' fields.",
            "return_values": "String representing the UAV vehicle type or null if not found.",
            "possible_use_cases": [
                "Tailoring analytics based on vehicle type",
                "Filtering logs by UAV model",
                "Adapting control strategies to vehicle architecture"
            ]
        },
        "get_trajectory_sources": {
            "purpose": "Identifies which trajectory-related message types are available in the dataset.",
            "return_values": "List of strings among ['GLOBAL_POSITION_INT', 'GPS_RAW_INT', 'AHRS2', 'AHRS3'].",
            "possible_use_cases": [
                "Selecting best available source for trajectory extraction",
                "Adapting preprocessing pipelines to available data",
                "Validating sensor presence across datasets"
            ]
        },
        "get_trajectory_with_gps": {
            "purpose": "Generates normalized UAV trajectory data using GPS_RAW_INT as the sensor type.",
            "return_values": "Dictionary containing 'startAltitude', full trajectory list, and time-aligned trajectory keyed by timestamp.",
            "possible_use_cases": [
                "Visualizing 3D flight path of UAV",
                "Detecting anomalies like abrupt altitude drops",
                "Calculating flight metrics such as distance and duration"
            ]
        },
        "get_trajectory_with_globalposition": {
            "purpose": "Generates normalized UAV trajectory data using GLOBAL_POSITION_INT as the sensor type.",
            "return_values": "Dictionary containing 'startAltitude', full trajectory list, and time-aligned trajectory keyed by timestamp.",
            "possible_use_cases": [
                "Visualizing 3D flight path of UAV",
                "Detecting anomalies like abrupt altitude drops",
                "Calculating flight metrics such as distance and duration"
            ]
        },
        "get_trajectory_with_ahrs2": {
            "purpose": "Generates normalized UAV trajectory data using AHRS2 as the sensor type.",
            "return_values": "Dictionary containing 'startAltitude', full trajectory list, and time-aligned trajectory keyed by timestamp.",
            "possible_use_cases": [
                "Visualizing 3D flight path of UAV",
                "Detecting anomalies like abrupt altitude drops",
                "Calculating flight metrics such as distance and duration"
            ]
        },
        "get_trajectory_with_ahrs3": {
            "purpose": "Generates normalized UAV trajectory data using AHRS3 as the sensor type.",
            "return_values": "Dictionary containing 'startAltitude', full trajectory list, and time-aligned trajectory keyed by timestamp.",
            "possible_use_cases": [
                "Visualizing 3D flight path of UAV",
                "Detecting anomalies like abrupt altitude drops",
                "Calculating flight metrics such as distance and duration"
            ]
        },
        "get_text_messages": {
            "purpose": "Extracts UAV status messages such as errors or logs from STATUSTEXT messages.",
            "return_values": "List of [timestamp, severity, message] entries.",
            "possible_use_cases": [
                "Diagnosing onboard system errors",
                "Correlating warnings with flight events",
                "Monitoring flight health and telemetry logs"
            ]
        }
    }

    ### Input Format:
    Query: <query text>

    ### Output Format:
    {
        "extractors": [<list of data relevant data extractors>]
    }

    ### Input for your task:
    """

    routing_instruction_prompt = routing_instruction_prompt + f"\nQuery: {query}"

    return routing_instruction_prompt

    