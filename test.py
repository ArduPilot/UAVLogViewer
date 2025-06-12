from langgraph.prebuilt import create_react_agent
from langchain_core.tools import Tool
from langchain_experimental.utilities import PythonREPL
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

import dotenv
import os

dotenv.load_dotenv(".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")

def analyze_telemetry_data(instructions: str, hint: str) -> str:  
    """This tool extracts insights such as maximum or minimum altitude, speed, GPS coordinates, attitude (pitch, roll, yaw), flight anomalies, sensor readings, and onboard system status. 
    The tool takes a natural language instruction describing what to analyze, along with an optional hint indicating which ArduPilot Onboard Message Log Message types (e.g., GPS, ATT, IMU, ERR, MODE, CMD, NKF*) are relevant to the query. The output is a specific value or summary derived from the telemetry data. 
    This tool should be used only when the question requires analyzing data from the telemetry logs."""

    python_prompt = """
    You are given access to flight telemetry data stored in 'parsed_telemetry.json'.
    write python code to analyze the data as per the instructions given. do not use json.JSONDecodeError, instead use a generic Exception handler.
    Use only libraries that are available in the Python REPL environment. The code should return the final answer to the user's query.
    You are also given a hint about what all Onboard Message Log Messages onboard ArduPilot vehicles may help you answer the user's query.
    which is:
    {hint}
    Only return the python code which will be executed to get the answer. Make sure it also mentions the correct unit of the answer.
    An snippet of how the data is:
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
    prompt = ChatPromptTemplate.from_messages([
    ("system", python_prompt),
    ("user", "{input}"),
    ])
    model = ChatGoogleGenerativeAI(model=GEMINI_MODEL_NAME, google_api_key=GEMINI_API_KEY)
    python_code_generator = prompt | model | StrOutputParser()
    reply = python_code_generator.invoke(
        {"input": instructions, "hint": hint},
    )
    reply = reply.replace("```python", "")
    reply = reply.replace("```", "")
  
    with open("python_code.py", "w") as f:
        f.write(reply)
    python_repl = PythonREPL()
    ans = python_repl.run(reply)
    print("--"* 20)
    print(ans)
    print("--"* 20)
    return ans
    


system_prompt = """
You are an expert UAV flight analyst. Your role is to answer user questions related to UAV flight telemetry data.
You have all the data about flight logs that are in the MavLink protocol format, parsed and stored in a file named `parsed_telemetry.json`.
You have access to a tool called `analyze_telemetry_data` that can analyze these telemetry logs.
You need to determine what specific data or logs you should analyze.

If the question is **general** or **not related to telemetry data**, answer directly without calling the tool.

### How to Use the Tool:
When calling `analyze_telemetry_data`, include the following:
1. A clear instruction about what the tool should do (e.g., “Find the maximum altitude in the flight data”).
2. A hint about which **Onboard Message Log Messages** from ArduPilot vehicles may help answer the question.

Reason out how you determine user's query in a MAVLink protocol data parsed from flight logs and provide it as a hint.

Example:
> Q: What is the maximum altitude of the flight?
> A: [Call `analyze_telemetry_data` with instructions: “Find the maximum altitude in the telemetry data.” Hint: This requires the `GPS` message type. Look for the `alt` field, which represents altitude above mean sea level (AMSL).]

### Additional Guidelines:
* If the question is unclear or lacks necessary context, **ask the user for clarification**.
* Do **not** make up data or answers.

If the tool gives impossible answers like "inf" or "nan". You should try calling the tool again with a more specific instruction or hint.
Stay precise, structured, and focused on the data.Take the feedback from the tool and answer the question accordingly.
"""

model = ChatGoogleGenerativeAI(model=GEMINI_MODEL_NAME, google_api_key=GEMINI_API_KEY)

checkpointer = InMemorySaver()
config = {"configurable": {"thread_id": "1"}}
agent = create_react_agent(
    model=model,  
    tools=[analyze_telemetry_data],  
    prompt=system_prompt,
    checkpointer=checkpointer,
)

my_response = agent.invoke(
    {"messages": [{"role": "user", "content": "Can you spot any issues in the GPS data? Analyze any and all GPS issues"}]},
    config
)

print(my_response)

