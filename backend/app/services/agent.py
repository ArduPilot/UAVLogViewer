from __future__ import annotations

from typing import AsyncGenerator, Dict, Any, List, Optional

from langgraph.graph import START, StateGraph
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from ..config import get_settings
from ..services.telemetry_tools import telemetry_query, anomaly_scan
from ..services.docs import docs_lookup


def build_graph():
    # Simple single-node graph that decides which tool to call based on the user text.
    def router(state: Dict[str, Any]) -> Dict[str, Any]:
        text = state["input"].lower()
        tool = None
        if any(k in text for k in ["max altitude", "highest altitude", "altitude"]):
            tool = ("telemetry_query", {"metrics": ["max_altitude"]})
        elif any(k in text for k in ["gps", "hdop", "signal loss", "lost"]):
            tool = ("telemetry_query", {"metrics": ["gps_first_loss"]})
        elif any(k in text for k in ["anomal", "issue", "problem"]):
            tool = ("anomaly_scan", {})
        return {"tool": tool}

    workflow = StateGraph(dict)
    workflow.add_node("router", router)
    workflow.add_edge(START, "router")
    graph = workflow.compile()
    return graph


async def run_agent_stream(session_id: str, message: str) -> AsyncGenerator[Dict[str, Any], None]:
    settings = get_settings()

    if settings.openai_api_key:
        # Define tools bound to this session_id
        @tool("telemetry_query", return_direct=False)
        def telemetry_query_tool(metrics: List[str], from_t: Optional[float] = None, to_t: Optional[float] = None) -> Dict[str, Any]:
            """Return precise metrics/timestamps from cached flight summary.
            metrics: array of metric names, e.g. ["max_altitude","gps_first_loss","flight_time","battery_min_voltage","battery_max_temp","rc_first_loss","critical_errors","mode_changes"].
            from_t: optional start time (seconds). to_t: optional end time (seconds).
            """
            return telemetry_query(session_id, metrics=metrics, from_t=from_t, to_t=to_t)

        @tool("anomaly_scan", return_direct=False)
        def anomaly_scan_tool(signals: Optional[List[str]] = None, window_s: int = 10, sensitivity: str = "normal") -> Dict[str, Any]:
            """Detect potential anomalies using simple statistical checks over cached series.
            signals: subset like ["ALT","VOLT","HDOP"]. window_s: window size. sensitivity: low|normal|high.
            """
            return anomaly_scan(session_id, signals=signals, window_s=window_s, sensitivity=sensitivity)

        @tool("docs_lookup", return_direct=False)
        def docs_lookup_tool(query: str) -> Dict[str, Any]:
            """Lookup ArduPilot log message docs and return small snippets with a URL."""
            return docs_lookup(query=query)

        llm = ChatOpenAI(api_key=settings.openai_api_key, model=settings.openai_model, temperature=0)
        llm_with_tools = llm.bind_tools([telemetry_query_tool, anomaly_scan_tool, docs_lookup_tool])

        # First turn: ask the model what to do
        ai: AIMessage = llm_with_tools.invoke([HumanMessage(content=message)])
        if getattr(ai, "tool_calls", None):
            for tc in ai.tool_calls:
                name = tc["name"] if isinstance(tc, dict) else getattr(tc, "name", "")
                args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
                if name == "telemetry_query":
                    out = telemetry_query_tool.invoke(args)
                    yield {"type": "tool_result", "name": name, "result": out}
                elif name == "anomaly_scan":
                    out = anomaly_scan_tool.invoke(args)
                    yield {"type": "tool_result", "name": name, "result": out}
                elif name == "docs_lookup":
                    out = docs_lookup_tool.invoke(args)
                    yield {"type": "tool_result", "name": name, "result": out}
            # Optionally, provide a compact textual summary
            yield {"type": "message", "content": "Executed requested tools. See results above."}
            return

        # No tool calls — return the model's text
        if ai.content:
            yield {"type": "message", "content": str(ai.content)}
            return

        # Fallback message
        yield {"type": "message", "content": "I can report max altitude, GPS loss, anomalies, and look up docs."}
        return

    # No API key available: fallback to simple router
    graph = build_graph()
    result = graph.invoke({"input": message})
    tool_sel = result.get("tool")
    if tool_sel is None:
        yield {"type": "message", "content": "I can report max altitude, GPS loss, and basic anomalies. Ask me about those!"}
        return
    name, args = tool_sel
    if name == "telemetry_query":
        out = telemetry_query(session_id, **args)
        yield {"type": "tool_result", "name": name, "result": out}
        yield {"type": "message", "content": str(out)}
    elif name == "anomaly_scan":
        out = anomaly_scan(session_id, **args)
        yield {"type": "tool_result", "name": name, "result": out}
        yield {"type": "message", "content": str(out)}
    elif name == "docs_lookup":
        out = docs_lookup(**args)
        yield {"type": "tool_result", "name": name, "result": out}
        yield {"type": "message", "content": str(out)}
    else:
        yield {"type": "message", "content": "Unknown tool."}


