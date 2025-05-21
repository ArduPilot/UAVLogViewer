from __future__ import annotations

import inspect
import json
import logging
import textwrap
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict, Union

import pandas as pd
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from chat.memory_manager import EnhancedMemoryManager
from telemetry.analyzer import TelemetryAnalyzer
from telemetry.parser import TelemetryParser

# ──────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────
# JSON helpers
# ──────────────────────────────────────────────────────────
class CustomJSONEncoder(json.JSONEncoder):
    """Encode pandas / numpy / datetime objects for JSON."""

    def default(self, obj):  # noqa: D401 – required by JSONEncoder
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "dtype") and hasattr(obj, "item"):  # numpy scalar
            return obj.item()
        return super().default(obj)


def ensure_serializable(obj: Any) -> Any:
    """Recursively convert *obj* into plain-Python JSON-serialisable types."""
    if isinstance(obj, dict):
        return {k: ensure_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [ensure_serializable(v) for v in obj]
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if hasattr(obj, "dtype") and hasattr(obj, "item"):  # numpy scalar
        return obj.item()
    if hasattr(obj, "__dict__"):
        return ensure_serializable(obj.__dict__)
    return obj


# ──────────────────────────────────────────────────────────
# LangGraph state definition
# ──────────────────────────────────────────────────────────
class AgentState(TypedDict, total=False):
    input: str
    session_id: str
    scratch: Dict[str, Any]
    current_step: int
    errors: List[str]
    answer: Optional[str]


# ──────────────────────────────────────────────────────────
# Prompts
# ──────────────────────────────────────────────────────────
INT_ROUTE_PROMPT = textwrap.dedent(
    """
    You are the **Routing / Planner** module for an agentic UAV-telemetry assistant.

    ## TASK
    1. Read the *User Query*.
    2. THINK ➔ PLAN ➔ EXECUTE silently (ReAct style) in your private scratch-pad.
    3. Output **ONLY** valid JSON with the following keys:

       {
         "clarification_needed": "YES" | "NO",
         "follow_up": "<question or null>",
         "tools": ["metrics","anomalies","altitude_details","battery_details",
                   "speed_details","gps_details","performance_details","flight_statistics"]
       }

       *The tools list may be empty.*

    ## AVAILABLE TOOLS
      • metrics              → get_metrics_for_query
      • anomalies            → detect_anomalies
      • altitude_details     → detailed_altitude_analysis
      • battery_details      → detailed_battery_analysis
      • speed_details        → detailed_speed_analysis
      • gps_details          → detailed_gps_analysis
      • performance_details  → detailed_performance_analysis
      • flight_statistics    → comprehensive_flight_stats

    ## FEW-SHOT EXAMPLES (ReAct)

    --- EX1 ------------------------------------------------
    User → “What was the highest ground-speed reached?”

    THINK  The question is about top speed.  
    PLAN   Call **speed_details** which returns max / mean / p95 speeds.  
    EXECUTE

    Assistant →  
    {"clarification_needed":"NO","follow_up":null,"tools":["speed_details"]}
    --------------------------------------------------------

    --- EX2 ------------------------------------------------
    User → “Any battery anomalies?”

    THINK  Need anomaly detection & detailed battery context.  
    PLAN   Use **anomalies** for spikes + **battery_details** for voltage/current curves.  
    EXECUTE

    Assistant →  
    {"clarification_needed":"NO","follow_up":null,"tools":["anomalies","battery_details"]}
    --------------------------------------------------------

    --- EX3 ------------------------------------------------
    User → “Give me a full flight summary.”

    THINK  Requires holistic statistics + overall KPIs.  
    PLAN   Combine **flight_statistics** (duration, distance, etc.) with **performance_details**.  
    EXECUTE

    Assistant →  
    {"clarification_needed":"NO","follow_up":null,"tools":["flight_statistics","performance_details"]}
    --------------------------------------------------------

    --- EX4 ------------------------------------------------
    User → “How bad was the GPS drift?”

    THINK  Need GPS metrics + anomalies tied to GPS.  
    PLAN   Call **gps_details** and **anomalies**.  
    EXECUTE

    Assistant →  
    {"clarification_needed":"NO","follow_up":null,"tools":["gps_details","anomalies"]}
    --------------------------------------------------------

    --- EX5 ------------------------------------------------
    User → “Is there anything wrong?”

    THINK  Too vague – cannot know which subsystem to inspect.  
    PLAN   Ask a clarifying question, no tools yet.  
    EXECUTE

    Assistant →  
    {"clarification_needed":"YES",
     "follow_up":"Could you specify which aspect of the flight you’d like me to examine – battery, altitude stability, GPS accuracy, or something else?",
     "tools":[]}
    --------------------------------------------------------

    ALWAYS think silently, then output the JSON only – no extra text.
"""
)

REFLECT_PROMPT = textwrap.dedent(
    """
    You are the **Reflector / Scheduler** for the UAV agent.

    You receive:
      • User’s original question
      • Chat history from memory
      • Latest TOOL RESULTS (as Tool messages)
      • Tool call history

    Decide whether more tool calls are needed.  
    Return **ONLY** JSON:

      {
        "need_more": true | false,
        "next_tools": ["metrics","anomalies","altitude_details","battery_details",
                       "speed_details","gps_details","performance_details","flight_statistics"],
        "final": "<answer text or null>"
      }

    ## REASONING STEPS
    1. Identify the user’s unresolved information needs.
    2. Check if current tool results already satisfy those needs.
    3. If crucial data is still missing AND another tool can supply it, set need_more = true.
    4. Respect data-quality / repetition limits (see below).

    ## STOPPING RULES (critical)
      • Stop immediately if the answer is fully covered by existing results.
      • Do not call the same tool more than twice for a single user request.
      • If key data is absent from log (e.g. no speed field), state that and stop.
      • Abort if error count ≥ 3 or loop depth ≥ 5.

    ## FEW-SHOT EXAMPLES

    (A) Top speed already known  
    ──────────────────────────  
    Q: “What was the peak speed?”  
    Tools run: speed_details → {"groundspeed":{"max":27.8}}  
    THINK  We already have max speed; no more tools.  
    Output:  
    {"need_more":false,"next_tools":[],"final":"The maximum ground-speed recorded was 27.8 m/s."}

    (B) Battery health incomplete  
    ─────────────────────────────  
    Q: “Did the battery perform well?”  
    Tools: metrics → {"battery_remaining":{"min":46,"max":100}}  
    THINK  Need deeper voltage / current analysis.  
    Output:  
    {"need_more":true,"next_tools":["battery_details"],"final":null}

    (C) Altitude covered – stop  
    ───────────────────────────  
    Q: “Max altitude?”  
    Tools: altitude_details → {"statistics":{"max":63.3}}  
    THINK  Answer present – stop.  
    Output:  
    {"need_more":false,"next_tools":[],"final":"The aircraft climbed to 63.3 m above launch point."}

    (D) Repeated tool calls – give up  
    ─────────────────────────────────  
    Q: “When did GPS drop?”  
    Tools: gps_details, anomalies, gps_details (again)  
    THINK  Already queried GPS twice – no dropout.  
    Output:  
    {"need_more":false,"next_tools":[],"final":"Telemetry shows no significant GPS signal loss during the flight."}

    (E) Data genuinely missing  
    ──────────────────────────  
    Q: “How was the radio link quality?”  
    Tools: metrics, anomalies  
    THINK  Telemetry contains no radio-link fields – stop.  
    Output:  
    {"need_more":false,"next_tools":[],"final":"Radio-link quality isn’t logged in this dataset, so I can’t assess it."}

    (F) Corrupted speed values  
    ──────────────────────────  
    Q: “Top speed?”  
    Tools: speed_details → {"error":"No valid speed data"}  
    THINK  Data corrupted – further calls futile.  
    Output:  
    {"need_more":false,"next_tools":[],"final":"Speed data is missing or corrupted; peak speed can’t be determined."}
"""
)

SYNTH_PROMPT = textwrap.dedent(
    """
    You are **MAVLink Analyst Pro** – an expert UAV flight-analysis system.

    ## INSTRUCTIONS
    Synthesize a concise answer using ONLY verified tool outputs.

    • Stick to factual tool data; never hallucinate numbers.  
    • If data is absent, clearly say so instead of guessing.  
    • Highlight safety-critical anomalies.  
    • Use bullet points for multi-part answers and include specific metrics.  
    • Convert raw units → human-readable where useful.  
    • Keep the answer focused and information-dense.

    Return only the final answer text.
"""
)

# ──────────────────────────────────────────────────────────
# Main agent
# ──────────────────────────────────────────────────────────
class UavAgent:
    """LLM-driven UAV-telemetry analysis agent using LangGraph."""

    MAX_LOOPS = 5
    MAX_ERRORS = 3
    PARALLEL_WORKERS = 4

    # -----------------------------------------------------
    # Construction
    # -----------------------------------------------------
    def __init__(
        self,
        session_id: str,
        *,
        telemetry_data: Optional[Dict] = None,
        analyzer: Optional[TelemetryAnalyzer] = None,
        log_path: Optional[str] = None,
    ) -> None:
        self.session_id = session_id
        logger.info("Creating agent for session %s", session_id)

        # Telemetry source
        if analyzer is not None:
            self.analyzer = analyzer
        elif telemetry_data is not None:
            self.analyzer = TelemetryAnalyzer(telemetry_data)
        elif log_path is not None:
            self.analyzer = TelemetryAnalyzer(TelemetryParser(log_path).parse())
        else:
            raise ValueError("One of analyzer, telemetry_data or log_path must be supplied")

        # LLMs
        self.fast_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.0)
        self.smart_llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

        # Memory
        self.memory_manager = EnhancedMemoryManager(session_id=session_id)

        # Tools
        self.tools: List[BaseTool] = self._create_tools()
        self.tool_map = {t.name: t for t in self.tools}

        # LangGraph
        self.graph = self._build_graph()
        logger.info("LangGraph compiled for session %s", session_id)

    # -----------------------------------------------------
    # Tool wrappers
    # -----------------------------------------------------
    def _create_tools(self) -> List[BaseTool]:
        a = self.analyzer  # local alias

        @tool("metrics")
        def metrics(inp: Union[str, Dict] = "") -> Dict[str, Any]:
            """Return telemetry metrics that match the user's text query
        (e.g. altitude statistics, battery_remaining, etc.)."""
            query = inp if isinstance(inp, str) else inp.get("query", "")
            return a._filter_relevant_metrics(query)

        @tool("anomalies")
        def anomalies(inp: Union[str, Dict] = "") -> List[Dict[str, Any]]:
            """Detect and return anomalous readings (spikes, drop-outs) related to
        the user's query."""
            query = inp if isinstance(inp, str) else inp.get("query", "")
            return a._filter_relevant_anomalies(query)

        @tool("altitude_details")
        def altitude_details() -> Dict[str, Any]:
            """Detailed altitude analysis (min/max/mean, climb/descent rates,
        take-off & landing times, flight phases)."""
            res = a._analyze_altitude()
            if "flight_phases" in res:
                for k in ("takeoff_time", "landing_time"):
                    v = res["flight_phases"].get(k)
                    if isinstance(v, (pd.Timestamp, datetime)):
                        res["flight_phases"][k] = v.isoformat()
            return res

        @tool("battery_details")
        def battery_details() -> Dict[str, Any]:
            """Comprehensive battery analysis: voltage curve, current draw,
        energy consumed, remaining %, anomalies."""
            return a._analyze_battery()

        @tool("speed_details")
        def speed_details() -> Dict[str, Any]:
            """Ground-speed / air-speed statistics (max, mean, 95th percentile)."""
            return a._analyze_speed()

        @tool("gps_details")
        def gps_details() -> Dict[str, Any]:
            """GPS quality & position analysis: fix-type transitions, satellites,
        travel distance, start/end coordinates."""
            return a._analyze_gps()

        @tool("performance_details")
        def performance_details() -> Dict[str, Any]:
            """Calculated KPIs such as altitude stability, attitude stability,
        battery efficiency, overall performance score."""
            return a._calculate_kpis()

        @tool("flight_statistics")
        def flight_statistics() -> Dict[str, Any]:
            """One-shot summary combining altitude, GPS, speed, battery and
        performance into a single dictionary."""
            stats: Dict[str, Any] = {}
            alt, gps, spd, bat, perf = (
                a._analyze_altitude(),
                a._analyze_gps(),
                a._analyze_speed(),
                a._analyze_battery(),
                a._calculate_kpis(),
            )
            if alt:
                phases = alt.get("flight_phases", {})
                for k in ("takeoff_time", "landing_time"):
                    v = phases.get(k)
                    if isinstance(v, (pd.Timestamp, datetime)):
                        phases[k] = v.isoformat()
                stats.update(
                    {
                        "flight_duration": phases.get("flight_duration"),
                        "takeoff_time": phases.get("takeoff_time"),
                        "landing_time": phases.get("landing_time"),
                        "max_altitude": alt.get("statistics", {}).get("max"),
                    }
                )
            if gps:
                pos = gps.get("position", {})
                stats.update(
                    {
                        "distance_traveled": pos.get("distance_traveled_km"),
                        "start_location": {"lat": pos.get("start_lat"), "lon": pos.get("start_lon")},
                        "end_location": {"lat": pos.get("end_lat"), "lon": pos.get("end_lon")},
                    }
                )
            if spd:
                stats.update(
                    {
                        "max_groundspeed": spd.get("groundspeed", {}).get("max"),
                        "max_airspeed": spd.get("airspeed", {}).get("max"),
                    }
                )
            if bat:
                stats.update(
                    {
                        "battery_voltage_drop": bat.get("voltage", {}).get("drop_percent"),
                        "energy_consumed_wh": bat.get("power", {}).get("total_energy_wh"),
                    }
                )
            if perf:
                stats["overall_performance_score"] = perf.get("overall_performance")
            stats["anomaly_count"] = len(a._detect_anomalies())
            return ensure_serializable(stats)

        return [
            metrics,
            anomalies,
            altitude_details,
            battery_details,
            speed_details,
            gps_details,
            performance_details,
            flight_statistics,
        ]

    # -----------------------------------------------------
    # LangGraph wiring
    # -----------------------------------------------------
    def _build_graph(self):
        g = StateGraph(AgentState)

        g.add_node("interpret", self._interpret)
        g.add_node("ask_clarification", self._ask_clarification)
        g.add_node("run_tools", self._run_tools)
        g.add_node("reflect", self._reflect)
        g.add_node("synthesize", self._synthesize)

        g.set_entry_point("interpret")

        g.add_conditional_edges(
            "interpret",
            self._branch_after_interpret,
            {"ask_clarification": "ask_clarification", "run_tools": "run_tools"},
        )
        g.add_edge("ask_clarification", END)
        g.add_edge("run_tools", "reflect")
        g.add_conditional_edges(
            "reflect",
            self._branch_after_reflect,
            {"synthesize": "synthesize", "run_tools": "run_tools"},
        )
        g.add_edge("synthesize", END)
        return g.compile()

    # -----------------------------------------------------
    # Branching helpers
    # -----------------------------------------------------
    def _branch_after_interpret(self, st: AgentState) -> str:
        return "ask_clarification" if st.get("scratch", {}).get("clarify") else "run_tools"

    def _branch_after_reflect(self, st: AgentState) -> str:
        scratch = st.get("scratch", {})
        loops = st.get("current_step", 0)
        errors = len(st.get("errors", []))
        if not scratch.get("need_more", False) or loops >= self.MAX_LOOPS or errors >= self.MAX_ERRORS:
            return "synthesize"
        return "run_tools"

    # -----------------------------------------------------
    # Node implementations
    # -----------------------------------------------------
    async def _interpret(self, st: AgentState) -> AgentState:
        query = st["input"]
        await self.memory_manager.add_message(role="user", content=query, metadata={"session_id": st["session_id"]})

        raw = self.fast_llm.invoke([SystemMessage(content=INT_ROUTE_PROMPT), HumanMessage(content=query)]).content
        errors = st.get("errors", [])
        try:
            cfg = json.loads(raw)
        except Exception as e:
            errors.append(f"route-json-error:{e}")
            cfg = {"clarification_needed": "YES", "follow_up": "Sorry, could you rephrase?", "tools": []}

        scratch = {
            "route_raw": raw,
            "clarify": cfg.get("clarification_needed") == "YES",
            "follow_up": cfg.get("follow_up"),
            "pending_tools": cfg.get("tools", []),
            "tool_history": st.get("scratch", {}).get("tool_history", []),
            "tool_results": [],
        }
        return {"scratch": scratch, "errors": errors} if errors else {"scratch": scratch}

    async def _ask_clarification(self, st: AgentState) -> AgentState:
        follow_up = st.get("scratch", {}).get("follow_up") or "Could you clarify what you need?"
        await self.memory_manager.add_message(role="assistant", content=follow_up, metadata={"session_id": st["session_id"]})
        return {"answer": follow_up}

    async def _run_tools(self, st: AgentState) -> AgentState:
        scratch = st.get("scratch", {})
        pending = scratch.get("pending_tools", [])
        tool_results = scratch.get("tool_results", [])
        errors = st.get("errors", [])

        if not pending:
            # keep loop counter + never store `None` for errors
            out = {"scratch": scratch, "current_step": st.get("current_step", 0)}
            if errors:
                out["errors"] = errors
            return out

        calls = []
        for name in pending:
            obj = self.tool_map.get(name)
            if obj is None:
                errors.append(f"unknown_tool:{name}")
                continue
            sig = inspect.signature(obj.run)
            kwargs: Dict[str, Any] = {}
            if sig.parameters and "query" in sig.parameters:
                kwargs = {"query": st["input"]}
            calls.append((name, obj, kwargs))

        if not calls:
            return {"scratch": scratch, "errors": errors}

        with ThreadPoolExecutor(max_workers=self.PARALLEL_WORKERS) as exe:
            futures = {exe.submit(self._exec_tool, obj, kw): nm for nm, obj, kw in calls}
            for fut in as_completed(futures):
                name = futures[fut]
                try:
                    res = fut.result()
                    tool_results.append({name: res})
                    await self.memory_manager.add_message(
                        role="tool",
                        content=json.dumps(res, default=str)[:4000],
                        metadata={"tool": name, "session_id": st["session_id"]},
                    )
                except Exception as e:
                    errors.append(f"tool_fail:{name}:{e}")

        scratch["tool_results"] = tool_results
        out = {"scratch": scratch, "current_step": st.get("current_step", 0)}
        if errors:
            out["errors"] = errors
        return out

    def _exec_tool(self, obj: BaseTool, kwargs: Dict[str, Any]):
        return ensure_serializable(obj.run({} if not kwargs else kwargs))


    # -----------------------------------------------------
    # Loop-guard helper (called from _reflect)
    # -----------------------------------------------------
    def _log_loop_guard(self, msg: str) -> None:
        """
        Emit a warning whenever we automatically short-circuit a runaway loop.
        Keeps one central place so we don’t litter the code with logger calls.
        """
        logger.warning("Loop-guard: %s  [session=%s]", msg, self.session_id)


    async def _reflect(self, st: AgentState) -> AgentState:
        scratch = st.get("scratch", {})
        current_step = st.get("current_step", 0) + 1
        tool_history = scratch.get("tool_history", []) + [scratch.get("pending_tools", [])]
        scratch["tool_history"] = tool_history

        msgs = [SystemMessage(content=REFLECT_PROMPT), HumanMessage(content=st["input"])]
        if scratch.get("tool_results"):
            msgs.append(AIMessage(content=f"Tool results:\n{self._optimise_results(scratch['tool_results'])}"))

        raw = self.fast_llm.invoke(msgs).content
        errors = st.get("errors", [])
        try:
            cfg = json.loads(raw)
        except Exception as e:
            errors.append(f"reflect-json-error:{e}")
            cfg = {"need_more": False, "next_tools": [], "final": "Unable to proceed due to parse error."}

        # If the model claims it still needs work but failed to supply
        # at least one tool, flip the switch off – otherwise we’ll spin
        # forever with empty workloads.
        need_more  = bool(cfg.get("need_more", False))
        next_tools = list(cfg.get("next_tools", []))   # make a copy

        # ---------- prune tools we’ve already run twice ----------
        history_flat = [t for sub in scratch["tool_history"] for t in sub]
        pruned       = []
        for t in next_tools:
            if history_flat.count(t) >= 2:
                self._log_loop_guard(f"Skipping '{t}' – already called twice")
            else:
                pruned.append(t)

        # If nothing meaningful is left, stop looping
        if need_more and not pruned:
            need_more = False
            self._log_loop_guard("Disabled `need_more` because no viable tools left")

        next_tools = pruned
        scratch.update({"need_more": need_more, "pending_tools": next_tools})
        out: AgentState = {"scratch": scratch, "current_step": current_step}
        if not cfg.get("need_more"):
            out["answer"] = cfg.get("final")
        if errors:
            out["errors"] = errors
        return out

    async def _synthesize(self, st: AgentState) -> AgentState:
        if st.get("answer"):
            return {}  # already have it

        scratch = st.get("scratch", {})
        msgs = [SystemMessage(content=SYNTH_PROMPT), HumanMessage(content=st["input"])]
        if scratch.get("tool_results"):
            msgs.append(
                SystemMessage(
                    content=f"Tool results:\n{json.dumps(scratch['tool_results'], cls=CustomJSONEncoder)[:6000]}"
                )
            )

        answer = self.smart_llm.invoke(msgs).content
        await self.memory_manager.add_message(
            role="assistant", content=answer, metadata={"session_id": st["session_id"], "final": True}
        )
        return {"answer": answer}

    # -----------------------------------------------------
    # Public API
    # -----------------------------------------------------
    async def process_message(self, message: str) -> Dict[str, Any]:
        init_state: AgentState = {
            "input": message,
            "session_id": self.session_id,
            "scratch": {"tool_history": []},
            "current_step": 0,
            "errors": [],
        }
        final_state: AgentState = await self.graph.ainvoke(init_state)
        return ensure_serializable(
            {
                "answer": final_state.get("answer", "I couldn't derive an answer."),
                "analysis": self._format_analysis(final_state),
                "session_id": self.session_id,
            }
        )

    # -----------------------------------------------------
    # Helpers
    # -----------------------------------------------------
    def _optimise_results(self, results: List[Dict[str, Any]]) -> str:
        """Very small summary of tool outputs to save tokens during reflection."""
        parts = []
        for item in results:
            for name, payload in item.items():
                if name == "battery_details" and isinstance(payload, dict):
                    v = payload.get("voltage", {})
                    parts.append(f"battery Vstart={v.get('initial')} Vend={v.get('final')}")
                elif name == "altitude_details" and isinstance(payload, dict):
                    s = payload.get("statistics", {})
                    parts.append(f"altitude max={s.get('max')} min={s.get('min')}")
                elif name == "anomalies":
                    parts.append(f"{len(payload)} anomalies")
                else:
                    parts.append(name)
        return " | ".join(parts)

    def _format_analysis(self, st: AgentState) -> Dict[str, Any]:
        analysis: Dict[str, Any] = {"type": "Flight Analysis"}
        scratch = st.get("scratch", {})
        for res in scratch.get("tool_results", []):
            analysis.update(res)
        if st.get("errors"):
            analysis["errors"] = st["errors"]
        return ensure_serializable(analysis)

    # -----------------------------------------------------
    # Maintenance
    # -----------------------------------------------------
    def clear_memory(self):
        self.memory_manager.clear()
