
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
    - If the message is a message/query that seeks to elaborate on previous messages and if previous messages seem related to the new message, return "elaboration"
    - If the message is a query seeking completely new information, return "new_task"
    - If the message is just a simple message, acknowledging that the previous responses are satisfactory
    or if it's neither a new query nor elaboration on old messages, return "task_end"


    ### Input Format:
    Latest User Message: <message text>
    Chat History: [<json array consisting of previous messages>]

    ### Output Format (JSON):
    {
        "task_class": <"elaboration" or "new_task" or "task_end">
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
    information to determine the next step, return "TASK_CLEAR"

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
