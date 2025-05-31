from langgraph.graph import StateGraph
from typing import TypedDict, List, Dict, Any, Literal
from langchain_core.messages import HumanMessage
from langchain_core.language_models import BaseLanguageModel


# custom imports
from utils.extractors import (
    extract_flight_modes,
    extract_events,
    extract_mission,
    extract_vehicle_type,
    extract_attitude,
    extract_trajectory_with_gps,
    extract_trajectory_with_ahrs3,
    extract_trajectory_with_ahrs2,
    extract_trajectory_with_globalposition,
    extract_trajectory_sources,
    extract_text_messages,
    extract_named_value_float_names
)
from prompts.answer_query import get_final_answer_prompt
from prompts.agentic_router import get_routing_prompt
from utils.string_utils import extract_json_text_by_key, extract_array_from_response
from telemetry_summarizer import TelemetrySummarizer

ALL_STEPS = ["get_flight_modes", "get_events", "get_mission", "get_vehicle_type", "get_trajectory_sources", "get_trajectory_with_gps", "get_trajectory_with_globalposition", "get_trajectory_with_ahrs2", "get_trajectory_with_ahrs3", "get_attitudes", "get_text_messages"]

TRAJECTORY_DATA_DESC = """
{
    "description": "List of relative UAV positions over time for path reconstruction.",
    "structure": [
      "longitude (float): Longitude in degrees",
      "latitude (float): Latitude in degrees",
      "relative_altitude (float): Altitude relative to starting altitude, in meters",
      "time_boot_ms (int): Timestamp in milliseconds since system boot"
    ]
}
"""

EVENT_DATA_DESC = """
{
    "description": "List of UAV arming state transitions over time.",
    "structure": [
        "time_boot_ms (int): Timestamp in milliseconds since system boot",
        "event_state (str): Either 'Armed' or 'Disarmed' depending on the base_mode flag"
    ]
}
"""

TEXT_MSG_DATA_DESC = """
{
    "description": "List of status text messages emitted by the UAV system.",
    "structure": [
      "time_boot_ms (int): Timestamp in milliseconds since system boot",
      "severity (int): Numerical code representing importance/severity (typically 0 = emergency, 6 = info)",
      "text (str): Human-readable system message"
    ],
}
"""

ATTITUDES_DATA_DESC = """
{
    "description": "Dictionary of UAV attitude readings over time, keyed by timestamp.",
    "structure": {
        "timestamp (int)": "[roll (float), pitch (float), yaw (float)] — Attitude angles in radians recorded at the given timestamp. Each value represents rotation around a principal axis:"
    },
    "value_details": [
        "roll: Rotation around the X-axis (positive = right wing down)",
        "pitch: Rotation around the Y-axis (positive = nose up)",
        "yaw: Rotation around the Z-axis (positive = clockwise from North)"
    ]
}
"""

class UAVState(TypedDict):
    raw_messages: Dict[str, Any]
    query: str
    flight_modes: List[List[Any]]
    events: List[List[Any]]
    mission: List[List[float]]
    trajectory_sources: List[str]
    text_messages: List[List[Any]]
    trajectory: Dict[str, Any]
    attitudes: Dict[str, Any]
    vehicle_type: str
    completed_get_flight_modes: bool
    completed_get_events: bool
    completed_get_mission: bool
    completed_get_vehicle_type: bool
    completed_get_trajectory_sources: bool
    completed_get_trajectory_with_gps: bool
    completed_get_trajectory_with_globalposition: bool
    completed_get_trajectory_with_ahrs2: bool
    completed_get_trajectory_with_ahrs3: bool
    completed_get_text_messages: bool
    completed_get_attitudes: bool
    completed_summarize_answer: bool
    output: str
    llm: BaseLanguageModel
    plan: List[str]

def get_flight_modes(state: UAVState) -> UAVState:
    return { "flight_modes": extract_flight_modes(state["raw_messages"]), "completed_get_flight_modes": True }

def get_events(state: UAVState) -> UAVState:
    return { "events": extract_events(state["raw_messages"]), "completed_get_events": True }

def get_mission(state: UAVState) -> UAVState:
    return { "mission": extract_mission(state["raw_messages"]), "completed_get_mission": True }

def get_vehicle_type(state: UAVState) -> UAVState:
    return { "vehicle_type": extract_vehicle_type(state["raw_messages"]), "completed_get_vehicle_type": True }

def get_trajectory_sources(state: UAVState) -> UAVState:
    return { "trajectory_sources": extract_trajectory_sources(state["raw_messages"]), "completed_get_trajectory_sources": True}

def get_attitudes(state: UAVState) -> UAVState:
    return { "attitudes": extract_attitude(state["raw_messages"]), "completed_get_attitudes": True }

def get_trajectory_with_gps(state: UAVState) -> UAVState:
    res = extract_trajectory_with_gps(state["raw_messages"])
    print('trajectory response: ', len(res["GPS_RAW_INT"]["trajectory"]))
    return { "trajectory": res['GPS_RAW_INT'], "completed_get_trajectory_with_gps": True }

def get_trajectory_with_globalposition(state: UAVState) -> UAVState:
    res = extract_trajectory_with_globalposition(state["raw_messages"])
    print('trajectory response: ', len(res["GLOBAL_POSITION_INT"]["trajectory"]))
    return { "trajectory": res['GLOBAL_POSITION_INT'], "completed_get_trajectory_with_globalposition": True }

def get_trajectory_with_ahrs2(state: UAVState) -> UAVState:
    res = extract_trajectory_with_ahrs2(state["raw_messages"])
    print('trajectory response: ', len(res["AHRS2"]["trajectory"]))
    return { "trajectory": res['AHRS2'], "completed_get_trajectory_with_ahrs2": True }

def get_trajectory_with_ahrs3(state: UAVState) -> UAVState:
    res = extract_trajectory_with_ahrs3(state["raw_messages"])
    print('trajectory response: ', len(res["AHRS3"]["trajectory"]))
    return { "trajectory": res['AHRS3'], "completed_get_trajectory_with_ahrs3": True }

def get_text_messages(state: UAVState) -> UAVState:
    return { "text_messages": extract_text_messages(state["raw_messages"]), "completed_get_text_messages": True }

def summarize_data(telemetry_data, data_info, user_message) -> Dict[str, Any]:
    telmetry_summarizer = TelemetrySummarizer()
    res = telmetry_summarizer.summarize_telemetry(telemetry_data=telemetry_data, data_info=data_info, user_message = user_message)
    print('data summary: ', res)
    return res

def get_necessary_context(state: UAVState) -> Dict[str, Any]:
    context_data = {}
    plan = state.get("plan", [])
    for step in plan:
        if step == "get_flight_modes":
            context_data = context_data | { "flight_modes": state.get("flight_modes", []) }
        elif step == "get_events":
            events = state.get("events", [])
            if events!= []:
                events_summary = summarize_data(telemetry_data=events, data_info = EVENT_DATA_DESC, user_message = state["query"])
                context_data = context_data | { "events": events_summary }
            else:
                context_data = context_data | { "events": state.get("events", []) }
        elif step == "get_mission":
            context_data = context_data | { "mission": state.get("mission", [])[:20] }
        elif step == "get_vehicle_type":
            context_data = context_data | { "vehicle_type": state.get("vehicle_type", "") }
        elif step == "get_trajectory_sources":
            context_data = context_data | { "trajectory_sources": state.get("trajectory_sources", []) }
        elif step == "get_trajectory_with_gps":
            trajectory = state.get("trajectory", {})
            if trajectory != {}:
                trajectory_summary = summarize_data(telemetry_data=trajectory['trajectory'], data_info = TRAJECTORY_DATA_DESC, user_message=state["query"])
                context_data = context_data | { "trajectory": trajectory_summary }
            else:
                context_data = context_data | { "trajectory": trajectory }
        elif step == "get_trajectory_with_globalposition":
            trajectory = state.get("trajectory", {})
            if trajectory != {}:
                trajectory_summary = summarize_data(telemetry_data=trajectory['trajectory'], data_info = TRAJECTORY_DATA_DESC, user_message=state["query"])
                context_data = context_data | { "trajectory": trajectory_summary }
            else:
                context_data = context_data | { "trajectory": trajectory }
        elif step == "get_trajectory_with_ahrs2":
            trajectory = state.get("trajectory", {})
            if trajectory != {}:
                trajectory_summary = summarize_data(telemetry_data=trajectory['trajectory'], data_info = TRAJECTORY_DATA_DESC, user_message=state["query"])
                #print('trajectory summary: ', trajectory_summary)
                context_data = context_data | { "trajectory": trajectory_summary }
            else:
                context_data = context_data | { "trajectory": trajectory }
        elif step == "get_trajectory_with_ahrs3":
            trajectory = state.get("trajectory", {})
            if trajectory != {}:
                trajectory_summary = summarize_data(telemetry_data=trajectory['trajectory'], data_info = TRAJECTORY_DATA_DESC, user_message=state["query"])
                #print('trajectory summary: ', trajectory_summary)
                context_data = context_data | { "trajectory": trajectory_summary }
            else:
                context_data = context_data | { "trajectory": trajectory }
        elif step == "get_attitudes":
            attitudes = state.get("attitudes", {})
            if attitudes != {}:
                attitudes_summary = summarize_data(telemetry_data=attitudes, data_info = ATTITUDES_DATA_DESC, user_message=state["query"])
                context_data = context_data | { "attitudes": attitudes_summary }
            else:
                context_data = context_data | { "attitudes": state.get("attitudes", {}) }
        elif step == "get_text_messages":
            text_messages = state.get("text_messages", [])
            if text_messages != []:
                text_messages_summary = summarize_data(telemetry_data=text_messages, data_info = TEXT_MSG_DATA_DESC, user_message=state["query"])
                context_data = context_data | { "text_messages": text_messages_summary }
            else:
                context_data = context_data | { "text_messages": state.get("text_messages", []) }
    
    return context_data

def answer_summarizer(state: UAVState) -> UAVState:

    context_data = get_necessary_context(state)
    prompt = get_final_answer_prompt(context_data, state['query'])
    input = HumanMessage(content = prompt)
    res = state["llm"].invoke([input])
    response_obj = extract_json_text_by_key(res.content, "answer")
    print("\nFINAL ANSWER: ", response_obj)
    if (response_obj == None) or (response_obj != None and "answer" in response_obj and response_obj['answer'] == 'INSUFFICIENT DATA'):
        return { "output": "Sorry, I have insufficient or no data to answer this query." }
    return { "output": response_obj['answer'] }

def get_plan(state: UAVState) -> UAVState:
    router_prompt = get_routing_prompt(query = state["query"])
    input = HumanMessage(content = router_prompt)
    res = state["llm"].invoke([input])
    print('res obj', res.content)
    res_arr = extract_array_from_response(response_str = res.content, target_key = "extractors")
    print('extracted res obj', res_arr, type(res_arr))
    if res_arr != None and len(res_arr) > 0:
        if "no_data" in res_arr:
            return { "plan": [] }
        if "get_all" in res_arr:
            return { "plan": ALL_STEPS }
        return { "plan": res_arr }
    return { "plan": ALL_STEPS }

def step_selector(state: UAVState) -> str:
    plan = state.get("plan", [])
    if len(plan) > 0:
        all_steps_completed = True
        for step in plan:
            ckey = f"completed_{step}"
            print('state keys', state.keys())
            all_steps_completed = all_steps_completed and state.get(ckey, False)
            if not(state.get(ckey, False)):
                return step
        if all_steps_completed:
            return "summarize_answer"
    return "no_plan"

class UAVGraph:

    def __init__(self, chat_agent):
        self.chat_agent = chat_agent
        self.llm = chat_agent.get_llm()
        self.graph = self.build()

    def build(self):
        graph_builder = StateGraph(UAVState)

        # add all extractors as nodes
        graph_builder.add_node("get_plan", get_plan)
        #graph_builder.add_node("route_step", agentic_router)
        #graph_builder.add_node("step_selector", step_selector)
        graph_builder.add_node("get_flight_modes", get_flight_modes)
        graph_builder.add_node("get_events", get_events)
        graph_builder.add_node("get_mission", get_mission)
        graph_builder.add_node("get_vehicle_type", get_vehicle_type)
        graph_builder.add_node("get_attitudes", get_attitudes)
        graph_builder.add_node("get_trajectory_sources", get_trajectory_sources)
        graph_builder.add_node("get_trajectory_with_gps", get_trajectory_with_gps)
        graph_builder.add_node("get_trajectory_with_globalposition", get_trajectory_with_globalposition)
        graph_builder.add_node("get_trajectory_with_ahrs2", get_trajectory_with_ahrs2)
        graph_builder.add_node("get_trajectory_with_ahrs3", get_trajectory_with_ahrs3)
        graph_builder.add_node("get_text_messages", get_text_messages)

        graph_builder.add_node("summarize_answer", answer_summarizer)

        graph_builder.set_entry_point("get_plan")
        graph_builder.add_conditional_edges("get_plan", step_selector, {
            "get_flight_modes": "get_flight_modes",
            "get_events": "get_events",
            "get_mission": "get_mission",
            "get_vehicle_type": "get_vehicle_type",
            "get_attitudes": "get_attitudes",
            "get_trajectory_sources": "get_trajectory_sources",
            "get_trajectory_with_gps": "get_trajectory_with_gps",
            "get_trajectory_with_globalposition": "get_trajectory_with_globalposition",
            "get_trajectory_with_ahrs2": "get_trajectory_with_ahrs2",
            "get_trajectory_with_ahrs3": "get_trajectory_with_ahrs3",
            "get_text_messages": "get_text_messages",
            "summarize_answer": "summarize_answer",
            "no_plan": "summarize_answer"
        })


        # connect all extractor nodes to the plan selection node (get_plan)
        graph_builder.add_conditional_edges("get_flight_modes", step_selector)
        graph_builder.add_conditional_edges("get_events", step_selector)
        graph_builder.add_conditional_edges("get_mission", step_selector)
        graph_builder.add_conditional_edges("get_vehicle_type", step_selector)
        graph_builder.add_conditional_edges("get_attitudes", step_selector)
        graph_builder.add_conditional_edges("get_trajectory_sources", step_selector)
        graph_builder.add_conditional_edges("get_trajectory_with_gps", step_selector)
        graph_builder.add_conditional_edges("get_trajectory_with_globalposition", step_selector)
        graph_builder.add_conditional_edges("get_trajectory_with_ahrs2", step_selector)
        graph_builder.add_conditional_edges("get_trajectory_with_ahrs3", step_selector)
        graph_builder.add_conditional_edges("get_text_messages", step_selector)
        graph_builder.set_finish_point("summarize_answer")

        return graph_builder.compile()
    
    def invoke(self, query: str, raw_messages: Dict[str, Any]) -> str:
        return self.graph.invoke({
            "raw_messages": raw_messages,
            "query": query,
            "llm": self.llm
        })["output"]