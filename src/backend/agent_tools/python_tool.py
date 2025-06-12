
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os
import dotenv

dotenv.load_dotenv(".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")

#Added the JSONDecodeError exception handling part because i was getting errors with the REPL tool
python_prompt = """
    You are given access to flight telemetry data stored in 'parsed_telemetry.json'.
    write python code to analyze the data as per the instructions given. use libraries that are available in the Python REPL environment.
    The code should store the final result in a variable called 'result'.
    do not use json.JSONDecodeError, instead use a generic Exception handler.
    You are also given a hint about what all Onboard Message Log Messages onboard ArduPilot vehicles may help you answer the user's query.
    Make sure the result you generate is concise and it should be formatted as a small value or a summary that can be easily interpreted.
    ### HINT ###
    {hint}
    Only return the python code which will be executed to get the answer. 
    Make sure it also mentions the correct unit of the answer.
    ### EXAMPLE DATA SNIPPET ###
    [
    {{
        "type": "RAW_IMU",
        "data": {{
        "mavpackettype": "RAW_IMU",
        "time_usec": 608582234,
        "xacc": 33,
        "yacc": -10,
        "zacc": -999,
        "xgyro": -9,
        "ygyro": 3,
        "zgyro": -231,
        "xmag": -146,
        "ymag": -160,
        "zmag": -541,
        "timestamp": 1533737161.905
        }}
    }},
    {{
        "type": "SCALED_IMU2",
        "data": {{
        "mavpackettype": "SCALED_IMU2",
        "time_boot_ms": 608582,
        "xacc": 33,
        "yacc": -10,
        "zacc": -999,
        "xgyro": -8,
        "ygyro": 4,
        "zgyro": -231,
        "xmag": -146,
        "ymag": -160,
        "zmag": -541,
        "timestamp": 1533737161.905
        }}
    }},
    {{
        "type": "SCALED_PRESSURE",
        "data": {{
        "mavpackettype": "SCALED_PRESSURE",
        "time_boot_ms": 608582,
        "press_abs": 944.5953979492188,
        "press_diff": 2.441406195430318e-06,
        "temperature": 3500,
        "timestamp": 1533737161.905
        }}
    }},
    {{
        "type": "SYS_STATUS",
        "data": {{
        "mavpackettype": "SYS_STATUS",
        "onboard_control_sensors_present": 56753215,
        "onboard_control_sensors_enabled": 23170111,
        "onboard_control_sensors_health": 22150206,
        "load": 0,
        "voltage_battery": 0,
        "current_battery": -1,
        "battery_remaining": -1,
        "drop_rate_comm": 0,
        "errors_comm": 0,
        "errors_count1": 0,
        "errors_count2": 0,
        "errors_count3": 0,
        "errors_count4": 0,
        "timestamp": 1533737161.905
        }}
    }}
    ]
    """

def analyze_telemetry_data(instructions: str, hint: str) -> str:  
    """This tool extracts insights such as maximum or minimum altitude, speed, GPS coordinates, attitude (pitch, roll, yaw), flight anomalies, sensor readings, and onboard system status. 
    The tool takes a natural language instruction describing what to analyze, along with an optional hint indicating which ArduPilot Onboard Message Log Message types (e.g., GPS, ATT, IMU, ERR, MODE, CMD, NKF*) are relevant to the query. The output is a specific value or summary derived from the telemetry data. 
    This tool should be used only when the question requires analyzing data from the telemetry logs."""

    prompt = ChatPromptTemplate.from_messages([
    ("system", python_prompt),
    ("user", "{input}")
    ])

    model = ChatGoogleGenerativeAI(model=MODEL_NAME, google_api_key=GEMINI_API_KEY)
    python_code_generator = prompt | model | StrOutputParser()

    reply = python_code_generator.invoke({"input": instructions, "hint": hint})

    #Removing the code block markers from the reply
    reply = reply.replace("```python", "")
    reply = reply.replace("```", "")

    #Writing the generated code to a file for debugging. Can be removed later.
    with open("python_code.py", "w") as f:
        f.write(reply)
        
    namespace = {}
    exec(reply, namespace)
    output = namespace.get("result")
    print("Returned:", output)
    return output