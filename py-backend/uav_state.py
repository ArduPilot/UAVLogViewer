from langgraph.graph import StateGraph
from typing import TypedDict, List, Dict, Any, Literal
from typing_extensions import Annotated
from langchain_core.messages import HumanMessage
from langchain_core.language_models import BaseLanguageModel


# custom imports
from utils.extractors import (
    extract_flight_modes,
    extract_events,
    extract_mission,
    extract_vehicle_type
)
from prompts.answer_query import get_final_answer_prompt
from prompts.agentic_router import get_routing_prompt
from utils.string_utils import extract_json_text_by_key, extract_array_from_response

class UAVState(TypedDict):
    raw_messages: Dict[str, Any]
    query: str
    flight_modes: List[List[Any]]
    events: List[List[Any]]
    mission: List[List[float]]
    vehicle_type: str
    completed_get_flight_modes: bool
    completed_get_events: bool
    completed_get_mission: bool
    completed_get_vehicle_type: bool
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

def answer_summarizer(state: UAVState) -> UAVState:

    context_data = {
        'flight_modes': state.get('flight_modes', None),
        'events': state.get('events', None),
        'waypoints (first 10)': state.get('mission', [])[:10],
        'vehicle_type': state.get('vehicle_type', None)
    }
    prompt = get_final_answer_prompt(context_data, state['query'])
    input = HumanMessage(content = prompt)
    print(input)
    res = state["llm"].invoke([input])
    response_obj = extract_json_text_by_key(res.content, "answer")
    print("\nFINAL ANSWER: ", response_obj)
    if response_obj['answer'] == 'INSUFFICIENT DATA':
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
            return { "plan": ["get_flight_modes", "get_events", "get_mission", "get_vehicle_type"] }
        return { "plan": res_arr }
    return { "plan": ["get_flight_modes", "get_events", "get_mission", "get_vehicle_type"] }

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

    def __init__(self, llm):
        self.llm = llm
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
        graph_builder.add_node("summarize_answer", answer_summarizer)

        graph_builder.set_entry_point("get_plan")
        graph_builder.add_conditional_edges("get_plan", step_selector, {
            "get_flight_modes": "get_flight_modes",
            "get_events": "get_events",
            "get_mission": "get_mission",
            "get_vehicle_type": "get_vehicle_type",
            "summarize_answer": "summarize_answer",
            "no_plan": "summarize_answer"
        })


        # connect all extractor nodes to the plan selection node (get_plan)
        graph_builder.add_conditional_edges("get_flight_modes", step_selector)

        graph_builder.add_conditional_edges("get_events", step_selector)

        graph_builder.add_conditional_edges("get_mission", step_selector)

        graph_builder.add_conditional_edges("get_vehicle_type", step_selector)

        graph_builder.set_finish_point("summarize_answer")

        return graph_builder.compile()
    
    def invoke(self, query: str, raw_messages: Dict[str, Any]) -> str:
        return self.graph.invoke({
            "raw_messages": raw_messages,
            "query": query,
            "llm": self.llm
        })["output"]