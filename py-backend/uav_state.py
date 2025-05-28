from langgraph.graph import StateGraph
from typing import TypedDict, List, Dict, Any
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
from utils.string_utils import extract_json_text_by_key

class UAVState(TypedDict):
    raw_messages: Dict[str, Any]
    query: str
    flight_modes: List[List[Any]]
    events: List[List[Any]]
    mission: List[List[float]]
    vehicle_type: str
    output: str
    llm: BaseLanguageModel

def get_flight_modes(state: UAVState) -> UAVState:
    return { "flight_modes": extract_flight_modes(state["raw_messages"]) }

def get_events(state: UAVState) -> UAVState:
    return { "events": extract_events(state["raw_messages"]) }

def get_mission(state: UAVState) -> UAVState:
    return { "mission": extract_mission(state["raw_messages"]) }

def get_vehicle_type(state: UAVState) -> UAVState:
    return { "vehicle_type": extract_vehicle_type(state["raw_messages"]) }

def answer_summarizer(state: UAVState) -> UAVState:

    context_data = {
        'flight_modes': state['flight_modes'],
        'events': state['events'],
        'waypoints (first 10)': state['mission'][:10],
        'vehicle_type': state['vehicle_type']
    }
    prompt = get_final_answer_prompt(context_data, state['query'])
    input = HumanMessage(content = prompt)
    print(input)
    res = state["llm"].invoke([input])
    response_obj = extract_json_text_by_key(res.content, "answer")

    return { "output": response_obj['answer'] }


class UAVGraph:

    def __init__(self, llm):
        self.llm = llm
        self.graph = self.build()

    def build(self):
        graph_builder = StateGraph(UAVState)

        graph_builder.add_node("get_flight_modes", get_flight_modes)
        graph_builder.add_node("get_events", get_events)
        graph_builder.add_node("get_mission", get_mission)
        graph_builder.add_node("get_vehicle_type", get_vehicle_type)
        graph_builder.add_node("summarize_answer", answer_summarizer)

        graph_builder.set_entry_point("get_flight_modes")
        graph_builder.add_edge("get_flight_modes", "get_events")
        graph_builder.add_edge("get_events", "get_mission")
        graph_builder.add_edge("get_mission", "get_vehicle_type")
        graph_builder.add_edge("get_vehicle_type", "summarize_answer")
        graph_builder.set_finish_point("summarize_answer")

        return graph_builder.compile()
    
    def invoke(self, query: str, raw_messages: Dict[str, Any]) -> str:
        return self.graph.invoke({
            "raw_messages": raw_messages,
            "query": query,
            "llm": self.llm
        })["output"]