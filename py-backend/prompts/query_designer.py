
def get_task_sumarization_prompt(chat_messages):
    chat_context = str(chat_messages)
    task_instruction_prompt = """
    ### Task
    You are a helpful assistant that summarizes task from a given list of exchanges between chat agent and user.
    Given a list of message exchanges between a chat agent and a user about a user task, analyze the messages
    and summarize the task given by the user.

    ### Input Format:
    Chat Messages - [<list of message exchanges about user task details>]

    ### Output Format:
    {
        "task_summary": <description of the task set forth by the user>
    }

    ### Input for your task:
    """

    task_instruction_prompt = task_instruction_prompt + f"\nChat Messages: {chat_context}"

    return task_instruction_prompt

def get_message_classification_prompt(user_message, chat_history):

    chat_history_str = str(chat_history)

    classification_instruction_prompt = """
    ### Task
    You are a message classifier. Given a user message and some chat history, classify whether the message 
    user sent is a message/query to elaborate on previous messages or a completely new query seeking new information.

    ### Guidelines:
    - Analyze the lastest message and the chat history provided to response approriately for the task.
    - If the message is a query seeking completely new information, return "new_task".
    - If the message is a giving more detailed instruction for the a query/task previously answered by the system, return "new_task"
    - If the message is asking to redo the previously defined task, return "redo_task".
    - If the message is giving more details for task/query that was asked in previous messages return "task_clarification"
    - If the message is a message/query that seeks to elaborate on previous answers to the task sent by the system and if previous messages seem related to the new message and have
    data/information that could respond to the latest message, return "elaboration".
    - If message is just a related question to previously asked tasks/queries, treat this as "new_task" not "elaboration"

    ### Input Format:
    Latest User Message: <message text>
    Chat History: [<json array consisting of previous messages>]

    ### Output Format (JSON):
    {
        "task_class": <"elaboration" or "new_task" or "redo_task" or "task_clarification">
    }

    ### Input for your task:
    """

    classification_instruction_prompt = classification_instruction_prompt + f"\nLatest User Message: {user_message}\nChat History: {chat_history_str}"

    return classification_instruction_prompt

def get_elaboration_prompt(query, chat_history):

    chat_history_str = str(chat_history)

    elaboration_instruction_prompt = """
    ### Task:
    You are a helpful assistant that elaborates on your responses. Given a user query, asking to
    elaborate on one of the previous messages and chat history, identify which message is reffered to
    in the chat history and elaborate on that message. Explain in detail the message, clarify every
    aspect of it including technical and non-technical jargons mentioned in the message.

    ### Input Format:
    Query: <query text>
    Chat History: [<json array consisting of chat message history>]

    ### Output Format (JSON):
    {
        "answer": <elaborate on one of the previous messages>
    }

    ###Input for your task:
    """

    elaboration_instruction_prompt = elaboration_instruction_prompt + f"\nQuery: {query}\nChat History: {chat_history_str}"

    return elaboration_instruction_prompt

def get_task_clarification_prompt(user_message, context_messages):
    context_str = str(context_messages)

    clarification_instruction_prompt = """
    ### Task
    You are a helpful assistant that summarizes a query/instruction given by a user.
    You are given a user message, list of past message exchanges elaborating on the user task and the following
    data extractors we have access to (it is given below). Analyze the current message, past message exchanges and determine
    if the task described by the user is clear and if there is enough information to determine
    which data extractors to use to execute the user task. If there is ambiguity in user task 
    or a detail missing, ask for clarification on the detail. If the task is clear, gives enough
    information to determine the next step, return "TASK_CLEAR".
    If extraction of trajectory data is needed, ask the user the source to be used.

    ### Data Extractors:
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
        "extract_trajectory_with_gps": {
            "purpose": "Extracts trajectory data (lon, lat, alt, time) using GPS_RAW_INT as the source.",
            "returns": "Dictionary with source as key and values including startAltitude, trajectory (list), and timeTrajectory (dict)."
        },
        "extract_trajectory_with_globalposition": {
            "purpose": "Extracts trajectory data (lon, lat, alt, time) using GLOBAL_POSITION_INT as the source.",
            "returns": "Dictionary with source as key and values including startAltitude, trajectory (list), and timeTrajectory (dict)."
        },
        "extract_trajectory_with_ahrs2": {
            "purpose": "Extracts trajectory data (lon, lat, alt, time) using AHRS2 as the source.",
            "returns": "Dictionary with source as key and values including startAltitude, trajectory (list), and timeTrajectory (dict)."
        },
        "extract_trajectory_with_ahrs3": {
            "purpose": "Extracts trajectory data (lon, lat, alt, time) using AHRS3 as the source.",
            "returns": "Dictionary with source as key and values including startAltitude, trajectory (list), and timeTrajectory (dict)."
        },
        "extract_named_value_float_names": {
            "purpose": "Returns unique parameter names from NAMED_VALUE_FLOAT in messages.",
            "returns": "List of string parameter names."
        }
    }

    ### Input Format:
    Latest User Message: <user message possibly a query or task instruction>
    Past Message Exchanges: [<list of messages about task clarification details>]
    
    ### Output Format (JSON):
    {
        "task_info": <description of which information needed or return "TASK_CLEAR">
    }

    ### Input for your task:
    """

    clarification_instruction_prompt = clarification_instruction_prompt + f"\nLatest User Message: {user_message}\nPast Message Exchanges: {context_str}"

    return clarification_instruction_prompt


def get_telemetry_summarization_prompt(telemetry_data, data_info, user_message):
    telemetry_data_str = str(telemetry_data)

    telemetry_summarization_prompt = """
    ### Task:
    You are a telemetry data summarizer.
    Given telemetry data, instruction by user and some metadata about the data, summarize the changes
    in the telemetry data. Clearly describe the change that happens and what it implies.
    Also list any unusual changes and what they imply.
    
    ### Guidelines:
    - Use the user message as primary guideline to look for specific changes, asked for in the user message.
    - describe change event that are related to the change events, user asked for in the message.
    - List the change event in a JSON object format. Add "description", "implications", "changes_observed", "timestamp" (if available in the telemetry data) as keys.
    - "description" and "implication" are text descriptions and "changes_observed" can be a JSON object of
    some arbitrary structure of your choosing, to explain the changes clearly.
    - Leave "timestamp" field as blank if the data is not available in the original telemetry data.
    - Send only as many events as you can send while adhering to the output token limits of 8192.

    ### Input Format:
    Telemetry Data: <a json array consisting of telemetry data>
    User Instruction: <a text describing what the change might look like in the data>
    Data Info: <a description of structure of the data point in the json array and what they signify>

    ### Output Format (JSON):
    {"data_summary": [<list of every change observed in the data, description of the change and what it implies>]}

    ### Example Output (JSON):
    {"data_summary": [{ "timestamp": 2156200, "changes_observed": { "previous_altitude_m": 120.5, "current_altitude_m": 85.3, "delta_altitude_m": -35.2 }, "description": "The UAV experienced a rapid descent of over 35 meters within a 5-second interval.", "implication": "This may indicate an emergency descent, possible loss of lift, or a commanded rapid landing. Further checks on attitude and control inputs are recommended to determine if the maneuver was planned or anomalous." }]}

    ### Input for your task:
    """

    telemetry_summarization_prompt = telemetry_summarization_prompt + f"\nTelemetry Data: {telemetry_data_str}\nUser Instruction: {user_message}\nData Info: {data_info}"

    return telemetry_summarization_prompt
