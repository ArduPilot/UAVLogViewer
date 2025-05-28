
def get_task_design_prompt(query):
    task_instruction_prompt = """
    ### Task
    We have raw mavlink data and the following extractor functions that extract
    information from mavlink data. We have to answer a user query using the raw
    mavlink data we have access to. Given a user query, and the following set of data extractor functions,
    determine which of the following extractor functions need to be called, to
    get necessary data for answering the user query.

    ### Guidelines:
    - We alreeady have access to mavlink data but need to understand which data to extract
    from the raw mavlink data, to answer the user query.
    - The Extractors are description of purpose of each extractor function and the data it returns.
    - Return the final response, adhering strictly to the JSON format instructions for output.

    ### Extractors
    {
        "extract_attitude": {
            "purpose": "Extracts Euler angles (roll, pitch, yaw) from ATTITUDE messages.",
            "returns": "Dictionary mapping time_boot_ms to [roll, pitch, yaw]."
        },
        "extract_flight_modes": {
            "purpose": "Extracts flight mode changes using HEARTBEAT messages.",
            "returns": "List of [time_boot_ms, flight_mode_string] when mode changes."
        },
        "extract_events": {
            "purpose": "Extracts arming/disarming events from HEARTBEAT message's base_mode field.",
            "returns": "List of [time_boot_ms, 'Armed' or 'Disarmed'] based on mode changes."
        },
        "extract_mission": {
            "purpose": "Extracts mission waypoints (lat, lon, alt) from CMD messages.",
            "returns": "List of [lon, lat, alt] waypoints."
        },
        "extract_vehicle_type": {
            "purpose": "Identifies the vehicle type from HEARTBEAT.craft messages.",
            "returns": "First defined entry in messages.HEARTBEAT.craft."
        },
        "extract_trajectory_sources": {
            "purpose": "Detects available sources for trajectory data.",
            "returns": "List of available source keys such as GLOBAL_POSITION_INT, GPS_RAW_INT, AHRS2, AHRS3."
        },
        "extract_trajectory": {
            "purpose": "Extracts trajectory data (lon, lat, alt, time) from one of the supported sources.",
            "returns": "Dictionary with source as key and values including startAltitude, trajectory (list), and timeTrajectory (dict)."
        },
        "extract_text_messages": {
            "purpose": "Extracts status messages from STATUSTEXT messages.",
            "returns": "List of [time_boot_ms, severity, text]."
        },
        "extract_named_value_float_names": {
            "purpose": "Returns unique parameter names from NAMED_VALUE_FLOAT in messages.",
            "returns": "List of string parameter names."
        }
    }

    ### Input Format:
    Query - <query_text>

    ### Output Format:
    {
        "extractors": <list of extractor functions to be called to fetch necessary data>
    }

    ### Input for your task:
    """

    task_instruction_prompt = task_instruction_prompt + f"\nQuery: {query}"

    return task_instruction_prompt
