from agent_tools.python_tool import analyze_telemetry_data
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
import dotenv
import os

dotenv.load_dotenv(".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")

class Agent:
    def __init__(self):
        self.system_prompt = """
        You are an expert UAV flight analyst. Your role is to answer user questions related to UAV flight telemetry data.
        You have all the data about flight logs that are in the MavLink protocol format, parsed and stored in a file named `parsed_telemetry.json`.
        You have access to a tool called `analyze_telemetry_data` that can analyze these telemetry logs.
        You need to determine what specific data or logs you should analyze.

        If the question is **general** or **not related to telemetry data**, answer directly without calling the tool.

        ### How to Use the Tool:
        When calling `analyze_telemetry_data`, include the following:
        1. A clear instruction about what the tool should do (e.g., “Find the maximum altitude in the flight data”).
        2. A hint about which **Onboard Message Log Messages** from ArduPilot vehicles may help answer the question.

        The hint should specify how you determine user's query in a MAVLink protocol data parsed from flight logs.

        Example:
        > Q: What is the maximum altitude of the flight?
        > A: [Call `analyze_telemetry_data` with instructions: “Find the maximum altitude in the telemetry data.” Hint: This requires the `GPS` message type. Look for the `Alt` field, which represents altitude above mean sea level (AMSL).]

        > Q: Are there any anomalies or issues in this flight?
        > A: [Call `analyze_telemetry_data` with instructions: “Find the anomalies/issues in the telemetry data.” Hint: Analyze the following Altitude - Sudden drop/climb (possible crash, wind); GPS - Loss of signal or jump in position; Battery voltage - sudden drop, battery temperature being too low or high (power failure, bad cell); Roll/Pitch/Yaw - Sudden spikes (loss of control, turbulence; EKF status - Bad estimation, sensor mismatch; IMU vibration - Excessive vibration (loose frame)

        ### Additional Guidelines:
        * If the question is unclear or lacks necessary context, **ask the user for clarification**.
        * Do **not** make up data or answers.

        If the tool gives impossible answers like "inf" or "nan" or gives an error. You should try calling the tool again with a more specific instruction or hint to fix the error.
        For example, if the tool replies as NameError, pandas not defined. You should call the tool with the hint and ask it not use pandas library.
        Stay precise, structured, and focused on the data. Take the feedback from the tool and answer the question accordingly.
        """

        self.model = ChatGoogleGenerativeAI(model=MODEL_NAME, google_api_key=GEMINI_API_KEY, max_retries=3)

        self.checkpointer = InMemorySaver()
        self.config = {"configurable": {"thread_id": "1"}}
        self.agent = create_react_agent(
            model=self.model,  
            tools=[analyze_telemetry_data],  
            prompt=self.system_prompt,
            checkpointer=self.checkpointer)

    # def __repr__(self):
    #     return f"Agent(name={self.name}, description={self.description})"

    def chat(self, user_request: str):
        response = self.agent.invoke(
            {"messages": [{"role": "user", "content": user_request}]},
            config=self.config )  
        try: 
            return response.get("messages", [])[-1].content
            # return response
        except:
            return "An error occurred while processing your request. Please try again."
        