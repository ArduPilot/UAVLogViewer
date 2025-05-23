from __future__ import annotations

import inspect
import re, json
import logging
import textwrap
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


_JSON_RE = re.compile(r"\{.*?\}", re.S)

def _extract_json(block: str) -> Dict[str, Any]:
    """
    Return the first valid JSON object found inside *block*.
    Raises ValueError if none can be parsed.
    """
    m = _JSON_RE.search(block.strip())
    if not m:
        raise ValueError("no-json")
    return json.loads(m.group(0))

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
         "tools": [<tool1>, <tool2>, ...]
       }

       *The tools list may be empty.*

    ## AVAILABLE TOOLS
      • metrics              → get_metrics_for_query
      • anomalies            → detect_anomalies
      • altitude_details     → detailed_altitude_analysis
      • battery_details      → detailed_battery_analysis
      • speed_details        → detailed_speed_analysis
      • gps_details          → detailed_gps_analysis
      • rc_signal_details    → detailed_rc_signal_analysis
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

    --- EX2b -----------------------------------------------
    User → “But what do you think about the no voltage drop or energy consumption in the battery aspect of the flight?”

    THINK  
    • The user asserts there was no battery voltage drop or energy use.
    • I need to verify that claim against the telemetry data.
    • I should retrieve detailed battery metrics—voltage over time, current draw, total energy consumed, and state-of-charge—to confirm or correct the user.

    PLAN  
    Call **battery_details** to fetch:
    - Voltage curve and drop percentages
    - Current draw statistics
    - Total energy consumed (Wh)
    - Remaining battery percentage and any anomalies

    EXECUTE
    {"clarification_needed":"NO","follow_up":null,"tools":["battery_details"]}
    --------------------------------------------------------

    --- EX3 ------------------------------------------------
    User → “Give me a full flight summary.”

    THINK  Requires holistic statistics + overall KPIs.  
    PLAN   Call **flight_statistics** (covers everything: duration, distance, etc.).  
    EXECUTE

    Assistant →  
    {"clarification_needed":"NO","follow_up":null,"tools":["flight_statistics"]}
    --------------------------------------------------------

    --- EX4 ------------------------------------------------
    User → “How bad was the GPS drift?”

    THINK  Need GPS-specific statistics (fix/no-fix %, transitions, distance).  
    PLAN   Call **gps_details** only. 
    EXECUTE

    Assistant →  
    {"clarification_needed":"NO","follow_up":null,"tools":["gps_details"]}
    --------------------------------------------------------

    --- EX5 ------------------------------------------------
    User → “Were there any RC signal dropouts?”

    THINK  User wants RC-link loss details.  
    PLAN   Call **rc_signal_details** to get loss count, first drop time, durations, and transitions.  
    EXECUTE

    Assistant →
    {"clarification_needed":"NO","follow_up":null,"tools":["rc_signal_details"]}
    --------------------------------------------------------

    --- EX6 ------------------------------------------------
    User → “Is there anything wrong?”

    THINK  Too vague – cannot know which subsystem to inspect.  
    PLAN   Ask a clarifying question, no tools yet.  
    EXECUTE

    Assistant →  
    {"clarification_needed":"YES",
     "follow_up":"Could you specify which aspect of the flight you’d like me to examine – battery, altitude stability, GPS accuracy, or something else?",
     "tools":[]}
    --------------------------------------------------------

    --- EX7 ------------------------------------------------
    User → “What was the peak speed?”

    THINK  Need speed-specific statistics.  
    PLAN   Call **speed_details** only.  
    EXECUTE

    Assistant →
    {"clarification_needed":"NO","follow_up":null,"tools":["speed_details"]}
    --------------------------------------------------------

    --- EX8 ------------------------------------------------
    User → “Tell me about the flight”

    THINK  Need comprehensive flight statistics.  
    PLAN   Call **flight_statistics** only.  
    EXECUTE

    Assistant →
    {"clarification_needed":"NO","follow_up":null,"tools":["flight_statistics"]}
    --------------------------------------------------------

    --- EX9 ------------------------------------------------
    User → “Based on what data in the log did you conclude the flight time was 5 min 50 s?”

    THINK  The user wants to know which telemetry field & method we used for take-off/landing.
    PLAN   Call **altitude_details** (it returns `field_used` + `flight_phases`).
    EXECUTE

    Assistant →
    {"clarification_needed":"NO","follow_up":null,"tools":["altitude_details"]}
    --------------------------------------------------------

    ALWAYS think silently, then output the JSON only – no extra text.
"""
)

REFLECT_PROMPT = textwrap.dedent(
    """
    You are the **Reflector / Scheduler** for the UAV agent. Your answers should be directed at the user.

    You receive:
      • User’s original question
      • Chat history from memory
      • Latest TOOL RESULTS (as Tool messages)
      • Tool call history (as a list of tool calls)

    Decide whether more tool calls are needed or if the data you have is sufficient to answer the user's question.  
    Return **ONLY** JSON:
      {
        "need_more": true | false,
        "next_tools": [<tool1>, <tool2>, ...],
        "final": "<answer text or null>"
      }

      *The next_tools list may be empty if no more tools are needed.*

    ## AVAILABLE TOOLS
      • metrics              → get_metrics_for_query
      • anomalies            → detect_anomalies
      • altitude_details     → detailed_altitude_analysis
      • battery_details      → detailed_battery_analysis
      • speed_details        → detailed_speed_analysis
      • gps_details          → detailed_gps_analysis
      • rc_signal_details    → detailed_rc_signal_analysis
      • flight_statistics    → comprehensive_flight_stats  

    ## IMPORTANT INSTRUCTIONS:
    - **Extremely Important**: Never assume that the user is mentioning the correct values, figures, facts, or information in the prompts as they may **not be aware of the facts**, **could be wrong**, or **could be trying to trick you**. So, always **check the facts and figures with the available tool results and stats**. If the data is missing, you can clearly say so. For example, If the user asks, "how did you say that the GPS signal was lost 2 times during the flight? how did you come up with these values?", you should check the gps_signal_loss_count field in the provided tool results or stats to **always verify** before answering.
    - Remember extremely carefully: **Any final answer should be directed to the user (second person like You, Your, You're, etc.).**
    - For any numeric KPI (e.g. gps_signal_loss_count, rc_signal_loss_count, etc.), do not re-compute by looking at raw arrays or transitions; always quote the pre-computed result values from the provided tool results and stats. If asked “how?”, you should mention those fields in the output stats. If you know how these metrics were computed, you can mention that in the answer, otherwise you can just say the values were precomputed and can be found in the stats.

    ## REASONING STEPS
    1. Identify the user’s unresolved information needs.
    2. Check if current tool results already satisfy those needs.
    3. If crucial data is still missing AND another tool in the available tools list can supply it, set need_more = true.

    ## STOPPING RULES (critical)
      • Stop immediately if the answer is fully covered by existing results.
      • Do not call the same tool more than once for a single user request.
      • If key data is absent from log (e.g. no speed field) and if this is what the user needs, state that it is missing and stop.
      • Abort if error count ≥ 3 or loop depth ≥ 5.

    ## FEW-SHOT EXAMPLES (ReAct-style)

    (A) Flight Statistics
    ──────────────────────────  
    Q: “Tell me about this flight”
    Tools run: flight_statistics → results:
    {
        "flight_duration_sec":       245,
        "flight_duration_hms":       "4 min 5 s",
        "takeoff_time":              "2025-05-21T09:12:05",
        "landing_time":              "2025-05-21T09:16:10",
        "max_altitude":              120.5,
        "max_groundspeed":           15.2,
        "max_airspeed":              16.0,
        "battery_voltage_drop_pct":  1.2,
        "energy_consumed_wh":        2.5,
        "overall_performance_score": 0.92,
        "anomaly_count":             3,
        "distance_traveled_km":      1.25,
        "start_location":            {"lat":37.7749,"lon":-122.4194},
        "end_location":              {"lat":37.7790,"lon":-122.4180},
        "gps_good_fix_percentage":   98.4,
        "gps_no_fix_percentage":      1.6,
        "gps_signal_loss_count":      1,
        "gps_signal_first_loss":     "2025-05-21T09:12:10",
        "gps_fix_transitions": [
            {"time":"2025-05-21T09:12:10","from":3,"to":0},
            {"time":"2025-05-21T09:12:12","from":0,"to":3}
        ],
        "rc_signal_loss_count":      1,
        "rc_signal_dropouts_total":  1,
        "rc_signal_first_loss":     "2025-05-21T09:12:07",
        "rc_signal_longest_loss_s":  0.5,
        "rc_signal_transitions": [
            {"time":"2025-05-21T09:12:07","from":1,"to":0},
            {"time":"2025-05-21T09:12:07.500","from":0,"to":1}
        ]
    }

    THINK
    - Duration: 245 s (4 min 5 s).
    - Lift-off/landing: 09:12:05 → 09:16:10 on May 21 2025 (I should mention the dates **clearly in english** whenever possible).
    - Peaks: 120.5 m altitude; 15.2/16.0 m/s ground/air speeds.
    - Battery: –1.2 %, 2.5 Wh → score 0.92.
    - 3 anomalies over 1.25 km from (37.7749, –122.4194) to (37.7790, –122.4180).
    - **GPS**:
        - Count: quote gps_signal_loss_count (1) to report GPS signal loss count.
        - First loss: quote gps_signal_first_loss (“2025-05-21T09:12:10”) to report the first instance of GPS signal loss.
        - Do not recount gps_fix_transitions or re-compute gps_signal_loss_count.
    - **RC**:
        - Count: quote rc_signal_loss_count (1) to report RC signal loss count.
        - First loss: quote rc_signal_first_loss (“2025-05-21T09:12:07”) to report the first instance of RC signal loss.
        - Longest outage: quote rc_signal_longest_loss_s (0.5 s) to report the longest RC signal outage.
        - Do not re-compute rc_signal_loss_count or count rc_signal_transitions.
    - Synthesize into a concise, accurate narrative.

    Output (strictly JSON format):
    {
        "need_more": false,
        "next_tools": [],
        "final": "The flight lasted 4 min 5 s, taking off at 09:12:05 and landing at 09:16:10 on May 21 2025. It climbed to 120.5 m with peak speeds of 15.2/16.0 m/s. Battery voltage dropped by 1.2 %, consuming 2.5 Wh for a performance score of 0.92. Three anomalies were detected over 1.25 km from (37.7749, –122.4194) to (37.7790, –122.4180). The GPS held a good fix 98.4 % of the time, slipping to no-fix 1.6 % of the time—losing signal at 09:12:10 (per `gps_signal_loss_count`) and recovering at 09:12:12. The RC link dropped once at 09:12:07, with the longest outage lasting 0.5 s."
    }

    (B) Top speed
    ──────────────────────────  
    Q: “What was the peak speed?”
    Tools run: speed_details → results: {"groundspeed":{"max":27.8}}
    THINK  We already have max speed; no more tools needed.
    Output: {"need_more":false,"next_tools":[],"final":"The maximum ground-speed recorded was 27.8 m/s."}

    (C) Altitude
    ─────────────────────────────────────────────  
    Q: “Max altitude?”
    Tools run: altitude_details → results: {"statistics":{"max":85.7}}
    THINK  Answer present already – so stop.
    Output: {"need_more":false,"next_tools":[],"final":"The aircraft climbed to 85.7 m above launch point."}

    (D) No repeating tool calls – give up with no data found
    ─────────────────────────────────────────────────  
    Q: “When did GPS drop?”
    Tools run: gps_details, anomalies → results: info missing
    THINK  Already queried GPS – no need to repeat and information missing it seems like.
    Output: {"need_more":false,"next_tools":[],"final":"Telemetry GPS signal loss data is missing in the log."}

    (E) Found answer – stop with data found
    ─────────────────────────────────────────────────  
    Q: “When did GPS drop?” 
    Tools run: gps_details, anomalies → results: required information found
    THINK  Have all the information I need and the data is present.
    Output: {"need_more":false,"next_tools":[],"final":"Telemetry GPS signal loss happened at 12:00:00, 2024-01-01 and lasted until 12:00:01, 2024-01-01."}

    (F) Data genuinely missing
    ──────────────────────────  
    Q: “How was the radio link quality?”  
    Tools run: metrics, anomalies
    THINK  Telemetry contains no radio-link fields – stop.  
    Output: {"need_more":false,"next_tools":[],"final":"Radio-link quality isn’t logged in this dataset, so I can’t assess it."}

    (G) RC signal loss
    ──────────────────────────  
    Q: “How many times did the RC link drop?”  
    Tools run: rc_signal_details → results: {"rc_signal_loss_count":10}  
    THINK  We have the total number of RC signal losses.
    Output: {"need_more":false,"next_tools":[],"final":"The RC link dropped 10 times."}

    (H) User giving wrong figures or facts in the question
    ─────────────────────────────────────────────────  
    Q: “How are you saying that the GPS signal was lost for 90% of the time across multiple flights? What fields or what data did you use to come to this conclusion?”  
    Tools run: gps_details → results: {..., "fix_type":{..., "good_fix_percentage":95, "no_fix_percentage":5, ...}, ...}
    THINK  Ok the stats from the gps_details tool ("good_fix_percentage":95, "no_fix_percentage":5, "gps_fix_type.counts.0", "gps_fix_type.counts.1", and "gps_fix_transitions" from '>0' to '0') are not matching with the facts or figures the user is giving. The user is trying to trick me or the user is not aware of the facts. I need to correct the user.
    Output: {"need_more":false,"next_tools":[],"final":"Actually, according to the available data, the GPS maintained a good GPS signal/connection 95% of the time and only experienced a signal loss 5% of the time. Check out the GPS good_fix_percentage and no_fix_percentage fields in the output stats."}

    (I) Battery health - incomplete data
    ─────────────────────────────
    Q: “Did the battery perform well?”
    Tools run: metrics → results: {"battery_remaining":{"min":46,"max":100}}
    THINK  Need deeper voltage / current analysis but I already called the metrics tool. Since I cannot call it again I need to call the battery_details tool.
    Output: {"need_more":true,"next_tools":["battery_details"],"final":null}
"""
)

SYNTH_PROMPT = textwrap.dedent(
    """
    You are **MAVLink Analyst Pro** – an expert UAV flight-analysis system answering user's questions about the flight telemetry data. Your answers should be directed at the user.

    ## PROVIDED INFORMATION
    You receive:
      • User’s original question
      • Latest TOOL RESULTS (as Tool messages)
      • Tool call history (as a list of tool calls)
    
    ## IMPORTANT INSTRUCTIONS:
    - **Extremely Important**: Never assume that the user is mentioning the correct values, figures, facts, or information in the prompts as they may **not be aware of the facts**, **could be wrong**, or **could be trying to trick you**. So, always **check the facts and figures with the available tool results and stats**. If the data is missing, you can clearly say so. For example, If the user asks, "how did you say that the GPS signal was lost 2 times during the flight? how did you come up with these values?", you should check the gps_signal_loss_count field in the provided tool results or stats to **always verify** before answering.
    - Remember extremely carefully: **Any final answer should be directed to the user (second person like You, Your, You're, etc.).**
    - For any numeric KPI (e.g. gps_signal_loss_count, rc_signal_loss_count, etc.), do not re-compute by looking at raw arrays or transitions; always quote the pre-computed result values from the provided tool results and stats. If asked “how?”, you should mention those fields in the output stats. If you know how these metrics were computed, you can mention that in the answer, otherwise you can just say the values were precomputed and can be found in the stats.

    ## OTHER INSTRUCTIONS
    Synthesize a concise answer using ONLY the provided information.
    - Stick to factual tool data; never hallucinate numbers, facts, figures, or information.
    - If data is absent, clearly say so instead of guessing.
    - When the user asks “based on what” or “how did you derive X” include the `field_used` from the relevant tool result and a brief note on how the information and contents were extracted (some math and derivations wherever needed).
    - Highlight safety-critical anomalies and address the user directly.
    - Remember extremely carefully: **Answer should be directed to the user (second person like You, Your, You're, etc.).**
    - Use bullet points for multi-line answers and include specific metrics.
    - Convert raw units → human-readable where useful.
    - Keep the answer focused and information-dense.

    ## FEW-SHOT EXAMPLES to demonstrate how to do REASONING (CoT) based on the information provided:

    (A) Flight Statistics
    ──────────────────────────  
    Q: “Tell me about this flight”  
    Tools run: flight_statistics → results:
    {
        "flight_duration_sec":       245,
        "flight_duration_hms":       "4 min 5 s",
        "takeoff_time":              "2025-05-21T09:12:05",
        "landing_time":              "2025-05-21T09:16:10",
        "max_altitude":              120.5,
        "max_groundspeed":           15.2,
        "max_airspeed":              16.0,
        "battery_voltage_drop_pct":  1.2,
        "energy_consumed_wh":        2.5,
        "overall_performance_score": 0.92,
        "anomaly_count":             3,
        "distance_traveled_km":      1.25,
        "start_location":            {"lat":37.7749,"lon":-122.4194},
        "end_location":              {"lat":37.7790,"lon":-122.4180},
        "gps_good_fix_percentage":   98.4,
        "gps_no_fix_percentage":      1.6,
        "gps_signal_loss_count":      1,
        "gps_signal_first_loss":     "2025-05-21T09:12:10",
        "gps_fix_transitions": [
            {"time":"2025-05-21T09:12:10","from":3,"to":0},
            {"time":"2025-05-21T09:12:12","from":0,"to":3}
        ],
        "rc_signal_loss_count":      1,
        "rc_signal_dropouts_total":  1,
        "rc_signal_first_loss":     "2025-05-21T09:12:07",
        "rc_signal_longest_loss_s":  0.5,
        "rc_signal_transitions": [
            {"time":"2025-05-21T09:12:07","from":1,"to":0},
            {"time":"2025-05-21T09:12:07.500","from":0,"to":1}
        ]
    }
    THINK
    - Duration: 245 s (4 min 5 s).
    - Lift-off/landing: 09:12:05 → 09:16:10 on May 21 2025 (I should mention the dates **clearly in english** whenever possible).
    - Peaks: 120.5 m altitude; 15.2/16.0 m/s ground/air speeds.
    - Battery: –1.2 %, 2.5 Wh → score 0.92.
    - 3 anomalies over 1.25 km from (37.7749, –122.4194) to (37.7790, –122.4180).
    - **GPS**:
        - Count: quote gps_signal_loss_count (1) to report GPS signal loss count.
        - First loss: quote gps_signal_first_loss (“2025-05-21T09:12:10”) to report the first instance of GPS signal loss.
        - Do not recount gps_fix_transitions or re-compute gps_signal_loss_count.
    - **RC**:
        - Count: quote rc_signal_loss_count (1) to report RC signal loss count.
        - First loss: quote rc_signal_first_loss (“2025-05-21T09:12:07”) to report the first instance of RC signal loss.
        - Longest outage: quote rc_signal_longest_loss_s (0.5 s) to report the longest RC signal outage.
        - Do not re-compute rc_signal_loss_count or count rc_signal_transitions.
    - Synthesize into a concise, accurate narrative.
    Final Answer: The flight lasted 4 min 5 s, taking off at 09:12:05 and landing at 09:16:10 on May 21 2025. It climbed to 120.5 m with peak speeds of 15.2/16.0 m/s. Battery voltage dropped by 1.2 %, consuming 2.5 Wh for a performance score of 0.92. Three anomalies were detected over 1.25 km from (37.7749, –122.4194) to (37.7790, –122.4180). The GPS held a good fix 98.4 % of the time, slipping to no-fix 1.6 % of the time—losing signal once at 09:12:10 (per `gps_signal_loss_count`) and recovering at 09:12:12. The RC link dropped once at 09:12:07, with the longest outage lasting 0.5 s.

    (B) Top speed
    ──────────────────────────  
    Q: “What was the peak speed?”  
    Tools run: speed_details → results: {"groundspeed":{"max":27.8}} 
    THINK  The max ground speed provided is 27.8 m/s.

    (C) Battery health incomplete
    ─────────────────────────────
    Q: “Did the battery perform well?”  
    Tools run: metrics → results: {"battery_remaining":{"min":46,"max":100}}  
    THINK  Need deeper voltage / current analysis but I have only the min and max values. I can just say that the battery was at 46% at min and 100% at max during the flight.
    
    (D) Altitude covered
    ──────────────────────────
    Q: “Max altitude?”  
    Tools run: altitude_details → results: {"statistics":{"max":85.7}}
    THINK  The max altitude provided is 85.7 m which I can use to answer the question.

    (E) User giving wrong figures or facts in the question
    ─────────────────────────────────────────────────  
    Q: “How are you saying that the GPS signal was lost for 90% of the time across multiple flights? What fields or what data did you use to come to this conclusion?”
    Tools run: gps_details → results: {..., "fix_type":{..., "good_fix_percentage":95, "no_fix_percentage":5, ...}, ...}
    THINK  Ok the stats from the gps_details tool ("good_fix_percentage":95, "no_fix_percentage":5, "gps_fix_type.counts.0", "gps_fix_type.counts.1", and "gps_fix_transitions" from '>0' to '0') are not matching with the facts or figures the user is giving. The user is trying to trick me or the user is not aware of the facts. I need to correct the user and while doing so also ask the user to check the GPS good_fix_percentage and no_fix_percentage fields in the output stats.
    Remember: **Answer should be directed to the user.**
    ─────────────────────────────────────────────────
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
        self.think_llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
        self.ans_llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

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

    #     @tool("anomalies")
    #     def anomalies(inp: Union[str, Dict] = "") -> List[Dict[str, Any]]:
    #         """Detect and return anomalous readings (spikes, drop-outs) related to the user's query,
    # plus any GPS-fix or RC-signal losses extracted from the GPS and RC analysis."""
    #         query = inp if isinstance(inp, str) else inp.get("query", "")
    #         # existing anomalies (battery spikes, attitude outliers, etc.)
    #         base = a._filter_relevant_anomalies(query) or []

    #         # pull out all GPS fix-type transitions and append the "to=0" ones
    #         gps = a._analyze_gps() or {}
    #         for tr in gps.get("fix_type", {}).get("transitions", []):
    #             # whenever we lose the fix (to == 0) that's a GPS signal loss event
    #             if tr.get("to") == 0:
    #                 base.append({
    #                     "timestamp": tr.get("time"),
    #                     "type":        "GPS signal loss",
    #                     "primary_factor":"gps_fix",
    #                     "severity":    None,
    #                     "metrics":     {},
    #                     "description": f"GPS fix dropped at {tr.get('time')}"
    #                 })

    #         # RC signal losses 
    #         rc = a._analyze_rc_signal() or {}
    #         # one item per lost-transition
    #         for tr in rc.get("transitions", []):
    #             if tr.get("to") == 0:
    #                 base.append({
    #                     "timestamp":      tr["time"],
    #                     "type":           "RC signal loss",
    #                     "primary_factor": "rc_signal",
    #                     "severity":       None,
    #                     "metrics":        {},
    #                     "description":    f"RC link dropped at {tr['time']}"
    #                 })

    #         # A single summary anomaly with your three fields
    #         total = rc.get("dropout_total", rc.get("loss_count", 0))
    #         first = rc.get("first_loss_time")
    #         longest = rc.get("longest_loss_duration_sec")
    #         if total:
    #             base.append({
    #                 "timestamp":      first,
    #                 "type":           "RC signal loss summary",
    #                 "primary_factor": "rc_signal",
    #                 "severity":       None,
    #                 "metrics": {
    #                     "dropout_total":             total,
    #                     "longest_loss_duration_sec": longest
    #                 },
    #                 "description": (
    #                     f"RC link dropped {total} times; "
    #                     f"first at {first}, "
    #                     f"longest outage {longest} s"
    #                 )
    #             })

    #         return ensure_serializable(base)

        @tool("anomalies")
        def anomalies(inp: Union[str, Dict] = "") -> List[Dict[str, Any]]:
            """
            Return all anomalies that are relevant to *query* **plus**
            derived GPS-fix-loss and RC-signal-loss summary.

            Returns a dict with:
            • gps: {
                signal_loss_count: int,
                good_fix_percentage: float?,
                no_fix_percentage: float?,
                fix_transitions: [ … ],
                first_loss_time: str?,
                longest_loss_duration_sec: float?
                }
            • rc: {
                signal_loss_count: int,
                first_loss_time: str?,
                longest_loss_duration_sec: float?,
                transitions: [ … ]
                }
            • anomaly_count: int
            • anomalies: [ … ]  # your base anomalies
            """
            query = inp if isinstance(inp, str) else inp.get("query", "")
            base_anoms: List[Dict[str, Any]] = list(a._filter_relevant_anomalies(query) or [])

            # GPS
            gps = a._analyze_gps() or {}
            gps_info = {
                "signal_loss_count"          : gps.get("dropout_total"),
                "first_loss_time"            : gps.get("first_loss_time"),
                "longest_loss_duration_sec"  : gps.get("longest_loss_duration_sec"),
                "good_fix_percentage"        : gps.get("fix_type", {}).get("good_fix_percentage"),
                "no_fix_percentage"          : gps.get("fix_type", {}).get("no_fix_percentage"),
                "fix_transitions"            : gps.get("fix_type", {}).get("transitions", []),
            }

            # RC
            rc = a._analyze_rc_signal() or {}
            rc_trans = rc.get("transitions", [])
            rc_loss_count = sum(1 for tr in rc_trans if tr.get("to") == 0)
            rc_info = {
                "signal_loss_count":          rc_loss_count,
                "rc_signal_loss_samples":     rc.get("loss_count"),
                "first_loss_time":            rc.get("first_loss_time"),
                "longest_loss_duration_sec":  rc.get("longest_loss_duration_sec"),
                "transitions":                rc_trans
            }

            # Assemble and return
            result = {
                "gps":       gps_info,
                "rc":        rc_info,
                "anomaly_count": len(base_anoms),
                "anomalies": base_anoms,
            }
            return ensure_serializable(result)


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
            travel distance, start/end coordinates, plus explicit loss count."""
            res = a._analyze_gps() or {}
            res["gps_signal_loss_count"]        = res.get("dropout_total")
            res["gps_signal_first_loss"]        = res.get("first_loss_time")
            res["gps_signal_longest_loss_sec"]  = res.get("longest_loss_duration_sec")
            return ensure_serializable(res)
        
        @tool("rc_signal_details")
        def rc_signal_details() -> Dict[str, Any]:
            """RC-link quality & signal-loss analysis:
                • RSSI statistics (if available)
                • loss/recovery transitions
                • total dropout count (recomputed from transitions)"""
            # fetch raw RC analysis
            rc = a._analyze_rc_signal() or {}
            # count only those where we go from connected (1) → lost (0)
            loss_events = [tr for tr in rc.get("transitions", []) if tr.get("to") == 0]
            # overwrite loss_count/dropout_total with the true number of drop events
            rc["rc_signal_loss_samples"]= rc.get("loss_count")
            rc["rc_signal_loss_count"]  = len(loss_events)
            # leave other fields untouched
            return ensure_serializable(rc)

        # @tool("performance_details")
        # def performance_details() -> Dict[str, Any]:
        #     """Calculated KPIs such as altitude stability, attitude stability,
        # battery efficiency, overall performance score."""
        #     return a._calculate_kpis()

        @tool("flight_statistics")
        def flight_statistics() -> Dict[str, Any]:
            """
            One-shot summary that stitches together altitude, GPS, speed, battery and
            performance data.  It guarantees:
            • takeoff_time & landing_time are always ISO-8601 strings (or None)
            • flight_duration is given both in seconds and as a “H M S” label
            • every numeric is JSON-serialisable out of the box
            """
            stats: Dict[str, Any] = {}

            # -------- raw analyses --------------------------------------------------
            alt  = a._analyze_altitude()   or {}
            gps  = a._analyze_gps()        or {}
            rc   = a._analyze_rc_signal()  or {}
            spd  = a._analyze_speed()      or {}
            bat  = a._analyze_battery()    or {}
            perf = a._calculate_kpis()     or {}

            # -------- altitude-driven flight phases --------------------------------
            phases = alt.get("flight_phases", {}) or {}
            # normalise timestamps → ISO text
            for key in ("takeoff_time", "landing_time"):
                ts = phases.get(key)
                if isinstance(ts, (pd.Timestamp, datetime)):
                    phases[key] = ts.isoformat()

            # ensure we always have duration in seconds
            flight_dur_sec: Optional[float] = phases.get("flight_duration")
            if flight_dur_sec is None and phases.get("takeoff_time") and phases.get("landing_time"):
                try:
                    t0 = pd.to_datetime(phases["takeoff_time"])
                    t1 = pd.to_datetime(phases["landing_time"])
                    flight_dur_sec = (t1 - t0).total_seconds()
                except Exception:
                    flight_dur_sec = None

            # pretty “H M S” label (used by the LLM, avoids rounding errors)
            def _sec_to_hms(sec: Optional[float]) -> Optional[str]:
                if sec is None:
                    return None
                sec = int(round(sec))
                h, m = divmod(sec, 3600)
                m, s = divmod(m, 60)
                if h:
                    return f"{h} h {m} min {s} s"
                if m:
                    return f"{m} min {s} s"
                return f"{s} s"

            # -------- flight altitude/takeoff/landing --------------------------------
            stats.update(
                {
                    "flight_duration_sec" : flight_dur_sec,
                    "flight_duration_hms" : _sec_to_hms(flight_dur_sec),
                    "takeoff_time"        : phases.get("takeoff_time"),
                    "landing_time"        : phases.get("landing_time"),
                    "max_altitude"        : alt.get("statistics", {}).get("max"),
                }
            )

            # -------- speed, battery, KPIs ---------------------------------------
            stats.update({
                "max_groundspeed":            spd.get("groundspeed", {}).get("max"),
                "max_airspeed":               spd.get("airspeed",    {}).get("max"),
                "battery_voltage_drop_pct":   bat.get("voltage", {}).get("drop_percent"),
                "energy_consumed_wh":         bat.get("power",   {}).get("total_energy_wh"),
                "overall_performance_score":  perf.get("overall_performance"),
                "anomaly_count":              len(a._detect_anomalies()),
            })

            # -------- GPS summary ------------------------------------------------
            pos = gps.get("position", {}) or {}
            stats.update({
                "distance_traveled_km":       pos.get("distance_traveled_km"),
                "start_location":             {"lat": pos.get("start_lat"), "lon": pos.get("start_lon")},
                "end_location":               {"lat": pos.get("end_lat"),   "lon": pos.get("end_lon")},
                "gps_no_fix_percentage"      : gps.get("fix_type", {}).get("no_fix_percentage"),
                "gps_good_fix_percentage"    : gps.get("fix_type", {}).get("good_fix_percentage"),
                "gps_signal_loss_count"      : gps.get("dropout_total"),
                "gps_signal_first_loss"      : gps.get("first_loss_time"),
                "gps_signal_longest_loss_sec": gps.get("longest_loss_duration_sec"),
                "gps_fix_transitions"        : gps.get("fix_type", {}).get("transitions", []),
            })

            # ── RC-link summary ─────────────────────────────────────────────────
            loss_events = [tr for tr in rc.get("transitions", []) if tr.get("to") == 0]
            stats.update({
                "rc_signal_loss_count"        : len(loss_events),
                "rc_signal_dropouts_total"    : len(loss_events),
                "rc_signal_loss_samples"      : rc.get("loss_count"),
                "rc_signal_first_loss"        : rc.get("first_loss_time"),
                "rc_signal_longest_loss_s"    : rc.get("longest_loss_duration_sec"),
                "rc_signal_transitions"       : rc.get("transitions"),
            })

            return ensure_serializable(stats)


        return [
            metrics,
            anomalies,
            altitude_details,
            battery_details,
            speed_details,
            gps_details,
            rc_signal_details,
            # performance_details,
            flight_statistics,
        ]


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

        raw = self.think_llm.invoke([SystemMessage(content=INT_ROUTE_PROMPT), HumanMessage(content=query)]).content
        errors = st.get("errors", [])
        try:
            cfg = _extract_json(raw)
        except Exception as e:
            errors.append(f"route-json-error:{e}")
            cfg = {"clarification_needed": "YES", "follow_up": "Sorry, could you rephrase?", "tools": []}

        tools = list(cfg.get("tools", []))
        # if flight_statistics is in the plan, drop every other tool
        if "flight_statistics" in tools:
            tools = ["flight_statistics"]

        scratch = {
            "route_raw": raw,
            "clarify": cfg.get("clarification_needed") == "YES",
            "follow_up": cfg.get("follow_up"),
            "pending_tools": tools,
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
        pending = scratch.get("pending_tools", []) or []
        tool_results = list(scratch.get("tool_results", [])) or []
        tool_history = list(scratch.get("tool_history", [])) or []
        executed: List[str] = []
        errors = st.get("errors", [])

        if not pending:
            # keep loop counter + never store `None` for errors
            out = {"scratch": scratch, "current_step": st.get("current_step", 0)}
            if errors:
                out["errors"] = errors
            return out

        calls = []
        for name in pending:
            if name not in tool_history:
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
                    executed.append(name)
                    res = fut.result()
                    tool_results.append({name: res})
                    await self.memory_manager.add_message(
                        role="tool",
                        content=json.dumps(res, default=str)[:4000],
                        metadata={"tool": name, "session_id": st["session_id"]},
                    )
                except Exception as e:
                    errors.append(f"tool_fail:{name}:{e}")

        scratch["pending_tools"] = []
        scratch["tool_history"] = tool_history + executed
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
        tool_history = scratch.get("tool_history", [])

        msgs = [SystemMessage(content=REFLECT_PROMPT), HumanMessage(content=st["input"])]
        if scratch.get("tool_results"):
            optimised = self._optimise_results(scratch['tool_results'])
            logger.info(f"Optimised tool results: {optimised}")
            msgs.append(AIMessage(content=f"Tool results:\n{optimised}"))

        if tool_history:
            logger.info(f"Tool history: {tool_history}")
            msgs.append(AIMessage(content=f"Tool history:\n{tool_history}"))

        raw = self.think_llm.invoke(msgs).content
        errors = st.get("errors", [])
        try:
            cfg = _extract_json(raw)
        except Exception as e:
            errors.append(f"reflect-json-error:{e}")
            # cfg = {"need_more": False, "next_tools": [], "final": "Unable to proceed due to parse error."}
            return {
                "scratch": scratch,
                "current_step": current_step,
                "answer": raw,
                "errors": errors,
            }

        # If the model claims it still needs work but failed to supply
        # at least one tool, flip the switch off – otherwise we’ll spin
        # forever with empty workloads.
        need_more  = bool(cfg.get("need_more", False))
        next_tools = list(cfg.get("next_tools", []))

        # prune tools we’ve already run
        history_flat = tool_history
        pruned       = []
        for t in next_tools:
            if t in history_flat:
                self._log_loop_guard(f"Skipping '{t}' – already called once")
            else:
                pruned.append(t)

        # If nothing meaningful is left, stop looping
        if need_more and not pruned:
            need_more = False
            self._log_loop_guard("Disabled `need_more` because no viable tools left")

        scratch.update({"need_more": need_more, "pending_tools": pruned})
        out: AgentState = {"scratch": scratch, "current_step": current_step}
        if not need_more:
            out["answer"] = cfg.get("final")
            # or "Information missing in the log due to which I could not derive an answer."
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

        if scratch.get("tool_history"):
            msgs.append(
                SystemMessage(
                    content=f"Tool history:\n{json.dumps(scratch['tool_history'])[:2000]}"
                )
            )

        answer = self.ans_llm.invoke(msgs).content
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
    # def _optimise_results(self, results: List[Dict[str, Any]]) -> str:
    #     """
    #     Build a compact but information-rich summary string from tool outputs.

    #     Design goals
    #     ------------
    #     • Capture every scalar KPI needed to answer follow-up questions
    #     (battery, altitude, GPS, RC/GPS signal-loss, flight times, etc.).
    #     • Avoid duplicates when multiple tools expose the same value.
    #     • Keep token count low by skipping large arrays / raw logs.
    #     • Emit ISO-8601 timestamps so downstream LLMs can compare them.
    #     """
    #     parts:      List[str] = []
    #     seen_parts: set[str] = set()          # de-duplication helper

    #     def _add(fragment: str) -> None:
    #         """Append unique key=value fragments."""
    #         if fragment and fragment not in seen_parts:
    #             parts.append(fragment)
    #             seen_parts.add(fragment)

    #     # ------------------------------------------------------------------ #
    #     # iterate through every tool result
    #     # ------------------------------------------------------------------ #
    #     for item in results:
    #         for tool_name, payload in item.items():
    #             if not payload:
    #                 continue

    #             # ───────────────── FLIGHT STATISTICS ────────────────────────
    #             if tool_name == "flight_statistics" and isinstance(payload, dict):
    #                 # loop over every scalar key without hand-coding each one
    #                 for key, val in payload.items():
    #                     if val is None:
    #                         continue
    #                     if isinstance(val, (int, float)):
    #                         _add(f"{key}={val:.3f}" if isinstance(val, float) else f"{key}={val}")
    #                     else:
    #                         _add(f'{key}="{val}"')

    #             # ───────────────── ALTITUDE DETAILS ─────────────────────────
    #             elif tool_name == "altitude_details" and isinstance(payload, dict):
    #                 stats  = payload.get("statistics", {})
    #                 phases = payload.get("flight_phases", {})
    #                 for k, v in stats.items():
    #                     if v is not None:
    #                         _add(f"altitude_{k}={v:.2f}")
    #                 for k, v in phases.items():
    #                     if v is None:
    #                         continue
    #                     if isinstance(v, (int, float)):
    #                         _add(f"{k}={v:.2f}")
    #                     else:
    #                         _add(f'{k}="{v}"')

    #             # ───────────────── BATTERY DETAILS ─────────────────────────
    #             elif tool_name == "battery_details" and isinstance(payload, dict):
    #                 for section in ("voltage", "current", "remaining", "power", "temperature"):
    #                     sub = payload.get(section, {})
    #                     for k, v in sub.items():
    #                         if v is not None:
    #                             label = f"{section}_{k}"
    #                             fmt   = f"{label}={v:.2f}" if isinstance(v, float) else f"{label}={v}"
    #                             _add(fmt)

    #             # ───────────────── SPEED DETAILS ───────────────────────────
    #             elif tool_name == "speed_details" and isinstance(payload, dict):
    #                 for speed_type, stats in payload.items():
    #                     if not isinstance(stats, dict):
    #                         continue
    #                     for k, v in stats.items():
    #                         if v is not None:
    #                             _add(f"{speed_type}_{k}={v:.2f}")

    #             # ───────────────── GPS DETAILS ─────────────────────────────
    #             elif tool_name == "gps_details" and isinstance(payload, dict):
    #                 for section in ("fix_type", "satellites", "position", "dops"):
    #                     sub = payload.get(section, {})
    #                     for k, v in sub.items():
    #                         if v is not None:
    #                             label = f"gps_{section}_{k}"
    #                             _add(f"{label}={v:.3f}" if isinstance(v, float) else f"{label}={v}")

    #             # ───────────────── ANOMALIES LIST ──────────────────────────
    #             elif tool_name == "anomalies" and isinstance(payload, dict):
    #                # anomalies
    #                 anoms = payload.get("anomalies", [])
    #                 _add(f"anomaly_count={len(anoms)}")

    #                 # GPS losses
    #                 gps_info = payload.get("gps", {})
    #                 gps_count = gps_info.get("signal_loss_count")
    #                 _add(f"gps_loss_total={gps_count}")
    #                 # record first GPS‐loss timestamp if you like:
    #                 if gps_count and gps_info.get("fix_transitions"):
    #                     first = min(gps_info["fix_transitions"], key=lambda tr: tr["time"])
    #                     _add(f'gps_loss_first="{first["time"]}"')

    #                 # RC losses
    #                 rc_info = payload.get("rc", {})
    #                 rc_count = rc_info.get("signal_loss_count")
    #                 _add(f"rc_signal_loss_count={rc_count}")
    #                 if rc_count and rc_info.get("transitions"):
    #                     first = min(rc_info["transitions"], key=lambda tr: tr["time"])
    #                     _add(f'rc_signal_loss_first="{first["time"]}"')

    #             # ───────────────── PERFORMANCE KPIs ────────────────────────
    #             # elif tool_name == "performance_details" and isinstance(payload, dict):
    #             #     for k, v in payload.items():
    #             #         if v is not None:
    #             #             _add(f"{k}={v:.3f}")

    #             # ───────────────── RC / SIGNAL TOOLS ───────────────────────
    #             elif (tool_name.startswith(("rc_", "signal_")) and isinstance(payload, dict)):
    #                 _add(f"{tool_name}={json.dumps(payload, separators=(',',':'))}")

    #             # ───────────────── GENERIC SCALAR FALLBACK ─────────────────
    #             elif isinstance(payload, dict):
    #                 # If a new tool arrives with simple scalars, capture them automatically.
    #                 for k, v in payload.items():
    #                     if isinstance(v, (int, float, str)) and len(str(v)) < 64:
    #                         _add(f"{tool_name}_{k}={v}")

    #     # Final compact string (pipe-delimited so reflection is easy to parse)
    #     return " | ".join(parts)


    def _optimise_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Build a compact but information-rich summary string from tool outputs.

        Captures every scalar KPI or timestamp needed to answer follow-ups:
        • flight_statistics
        • altitude_details
        • battery_details
        • speed_details
        • gps_details
        • rc_signal_details
        • anomalies (including gps+rc loss summary)
        """
        parts:      List[str] = []
        seen: set[str]   = set()

        def _add(fragment: str):
            if fragment and fragment not in seen:
                parts.append(fragment)
                seen.add(fragment)

        for item in results:
            for tool, payload in item.items():
                if not isinstance(payload, dict):
                    continue

                # 1) flight_statistics: flatten everything
                if tool == "flight_statistics":
                    for k, v in payload.items():
                        if v is None:
                            continue
                        if isinstance(v, (int, float)):
                            _add(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}")
                        else:
                            _add(f'{k}="{v}"')

                # 2) altitude_details
                elif tool == "altitude_details":
                    stats  = payload.get("statistics", {})
                    phases = payload.get("flight_phases", {})
                    for k, v in stats.items():
                        if v is not None:
                            _add(f"altitude_{k}={v:.2f}")
                    for k, v in phases.items():
                        if v is None:
                            continue
                        if isinstance(v, (int, float)):
                            _add(f"{k}={v:.2f}")
                        else:
                            _add(f'{k}="{v}"')

                # 3) battery_details
                elif tool == "battery_details":
                    for section in ("voltage", "current", "remaining", "power", "temperature"):
                        sub = payload.get(section, {})
                        for k, v in sub.items():
                            if v is not None:
                                label = f"{section}_{k}"
                                if isinstance(v, float):
                                    _add(f"{label}={v:.2f}")
                                else:
                                    _add(f"{label}={v}")

                # 4) speed_details
                elif tool == "speed_details":
                    for speed_type, stats in payload.items():
                        if not isinstance(stats, dict):
                            continue
                        for k, v in stats.items():
                            if v is not None:
                                _add(f"{speed_type}_{k}={v:.2f}")

                # 5) gps_details
                elif tool == "gps_details":
                    # flat fields that _gps_details_ injects at top level
                    for key in (
                        "gps_signal_loss_count",
                        "gps_signal_first_loss",
                        "gps_signal_longest_loss_sec",
                    ):
                        if key in payload and payload[key] is not None:
                            val = payload[key]
                            if isinstance(val, (int, float)):
                                _add(f"{key}={val}")
                            else:
                                _add(f'{key}="{val}"')
                    # nested fix_type, satellites, position
                    for section in ("fix_type", "satellites", "position"):
                        sub = payload.get(section, {}) or {}
                        for k, v in sub.items():
                            if v is None:
                                continue
                            label = f"gps_{section}_{k}"
                            if isinstance(v, float):
                                _add(f"{label}={v:.3f}")
                            else:
                                _add(f"{label}={v}")

                # 6) rc_signal_details
                elif tool == "rc_signal_details":
                    for key in (
                        "rc_signal_loss_samples",
                        "rc_signal_loss_count",
                        "rc_signal_first_loss",
                        "rc_signal_longest_loss_s",
                    ):
                        if key in payload and payload[key] is not None:
                            val = payload[key]
                            if isinstance(val, (int, float)):
                                _add(f"{key}={val}")
                            else:
                                _add(f'{key}="{val}"')

                # 7) anomalies
                elif tool == "anomalies":
                    # top-level anomaly count
                    total = payload.get("anomaly_count")
                    if total is not None:
                        _add(f"anomaly_count={total}")
                    # gps summary
                    gps = payload.get("gps", {})
                    if gps:
                        if gps.get("signal_loss_count") is not None:
                            _add(f"gps_signal_loss_count={gps['signal_loss_count']}")
                        if gps.get("first_loss_time"):
                            _add(f'gps_signal_first_loss="{gps["first_loss_time"]}"')
                        if gps.get("longest_loss_duration_sec") is not None:
                            _add(f"gps_signal_longest_loss_sec={gps['longest_loss_duration_sec']:.3f}")
                    # rc summary
                    rc = payload.get("rc", {})
                    if rc:
                        if rc.get("signal_loss_count") is not None:
                            _add(f"rc_signal_loss_count={rc['signal_loss_count']}")
                        if rc.get("first_loss_time"):
                            _add(f'rc_signal_first_loss="{rc["first_loss_time"]}"')
                        if rc.get("longest_loss_duration_sec") is not None:
                            _add(f"rc_signal_longest_loss_s={rc['longest_loss_duration_sec']:.3f}")

                # 8) generic fallback: pick any remaining simple scalars
                else:
                    for k, v in payload.items():
                        if isinstance(v, (int, float, str)) and len(str(v)) < 64:
                            _add(f"{tool}_{k}={v}")

        return " | ".join(parts)


    
    # def _optimise_results(self, results: List[Dict[str, Any]]) -> str:
    #     """
    #     Build a concise, token-efficient summary of our tool outputs by
    #     extracting every key scalar (flight duration, altitudes, GPS stats,
    #     battery voltages/current/power, RC losses, signal drops, anomalies, KPIs)
    #     and skipping raw time series or arrays.
    #     """
    #     parts: List[str] = []

    #     for item in results:
    #         for tool_name, payload in item.items():
    #             if not payload:
    #                 continue

    #             # ── FLIGHT STATISTICS ─────────────────────────────────────────
    #             if tool_name == "flight_statistics" and isinstance(payload, dict):
    #                 if payload.get("flight_duration_sec") is not None:
    #                     parts.append(f"flight_duration_sec={payload['flight_duration_sec']:.1f}")
    #                 if payload.get("flight_duration_hms"):
    #                     parts.append(f"flight_duration_hms=\"{payload['flight_duration_hms']}\"")
    #                 for key in ("takeoff_time", "landing_time"):
    #                     if payload.get(key):
    #                         parts.append(f"{key}=\"{payload[key]}\"")
    #                 for key in ("max_altitude", "distance_traveled_km",
    #                             "max_groundspeed", "max_airspeed",
    #                             "battery_voltage_drop_pct", "energy_consumed_wh",
    #                             "overall_performance_score", "anomaly_count"):
    #                     if payload.get(key) is not None:
    #                         val = payload[key]
    #                         # format floats
    #                         if isinstance(val, float):
    #                             parts.append(f"{key}={val:.2f}")
    #                         else:
    #                             parts.append(f"{key}={val}")

    #             # ── ALTITUDE DETAILS ─────────────────────────────────────────
    #             elif tool_name == "altitude_details" and isinstance(payload, dict):
    #                 stats = payload.get("statistics", {})
    #                 for field in ("max", "min"):
    #                     if stats.get(field) is not None:
    #                         parts.append(f"altitude_{field}={stats[field]:.2f}")
    #                 phases = payload.get("flight_phases", {})
    #                 for key in ("takeoff_time", "landing_time"):
    #                     if phases.get(key):
    #                         parts.append(f"{key}=\"{phases[key]}\"")
    #                 for key in ("max_climb_rate", "max_descent_rate"):
    #                     if phases.get(key) is not None:
    #                         parts.append(f"{key}={phases[key]:.2f}")

    #             # ── BATTERY DETAILS ──────────────────────────────────────────
    #             elif tool_name == "battery_details" and isinstance(payload, dict):
    #                 vol = payload.get("voltage", {})
    #                 if vol.get("initial") is not None and vol.get("final") is not None:
    #                     parts.append(f"initial_voltage={vol['initial']:.2f}")
    #                     parts.append(f"final_voltage={vol['final']:.2f}")
    #                     parts.append(f"voltage_drop_percent={vol['drop_percent']:.1f}")
    #                 curr = payload.get("current", {})
    #                 if curr.get("min") is not None and curr.get("max") is not None:
    #                     parts.append(f"current_min={curr['min']:.2f}")
    #                     parts.append(f"current_max={curr['max']:.2f}")
    #                 rem = payload.get("remaining", {})
    #                 if rem.get("initial") is not None and rem.get("final") is not None:
    #                     parts.append(f"remaining_initial={rem['initial']:.1f}")
    #                     parts.append(f"remaining_final={rem['final']:.1f}")
    #                 power = payload.get("power", {})
    #                 if power.get("total_energy_wh") is not None:
    #                     parts.append(f"total_energy_wh={power['total_energy_wh']:.2f}")

    #             # ── SPEED DETAILS ───────────────────────────────────────────
    #             elif tool_name == "speed_details" and isinstance(payload, dict):
    #                 for speed_field in ("groundspeed", "airspeed", "velocity_3d"):
    #                     sp = payload.get(speed_field, {})
    #                     if sp.get("max") is not None:
    #                         parts.append(f"{speed_field}_max={sp['max']:.2f}")
    #                     if sp.get("mean") is not None:
    #                         parts.append(f"{speed_field}_mean={sp['mean']:.2f}")

    #             # ── GPS DETAILS ─────────────────────────────────────────────
    #             elif tool_name == "gps_details" and isinstance(payload, dict):
    #                 fix = payload.get("fix_type", {})
    #                 if fix.get("good_fix_percentage") is not None:
    #                     parts.append(f"fix_good_percentage={fix['good_fix_percentage']:.1f}")
    #                 if fix.get("no_fix_percentage") is not None:
    #                     parts.append(f"fix_no_percentage={fix['no_fix_percentage']:.1f}")
    #                 sats = payload.get("satellites", {})
    #                 if sats.get("min") is not None and sats.get("max") is not None:
    #                     parts.append(f"satellites_min={sats['min']}")
    #                     parts.append(f"satellites_max={sats['max']}")
    #                 pos = payload.get("position", {})
    #                 for key in ("distance_traveled_km", "return_distance_km"):
    #                     if pos.get(key) is not None:
    #                         parts.append(f"{key}={pos[key]:.3f}")

    #             # ── ANOMALIES ───────────────────────────────────────────────
    #             elif tool_name == "anomalies" and isinstance(payload, list):
    #                 # total anomaly count
    #                 parts.append(f"anomaly_count={len(payload)}")
    #                 # find RC/signal-loss anomalies
    #                 rc_events = [
    #                     ann for ann in payload
    #                     if "rc" in ann.get("type", "").lower()
    #                     or "signal loss" in ann.get("type", "").lower()
    #                     or "rc" in ann.get("description", "").lower()
    #                 ]
    #                 parts.append(f"rc_signal_loss_count={len(rc_events)}")
    #                 if rc_events:
    #                     first = rc_events[0]
    #                     parts.append(f"first_rc_signal_loss_timestamp=\"{first['timestamp']}\"")

    #             # ── PERFORMANCE DETAILS ─────────────────────────────────────
    #             elif tool_name == "performance_details" and isinstance(payload, dict):
    #                 for key in ("altitude_stability", "battery_efficiency",
    #                             "attitude_stability", "overall_performance"):
    #                     if payload.get(key) is not None:
    #                         parts.append(f"{key}={payload[key]:.3f}")

    #             # ── DEDICATED RC / SIGNAL TOOL ─────────────────────────────
    #             elif (tool_name.startswith("rc_") or tool_name.startswith("signal_")) \
    #                 and isinstance(payload, dict):
    #                 # if you later add a tool like rc_signal_details, pass its raw JSON
    #                 parts.append(f"{tool_name}={json.dumps(payload)}")

    #             # ── EVERYTHING ELSE: skip raw arrays, servo channels, debug streams
    #             else:
    #                 continue

    #     # join with pipes so the reflector LLM sees one tidy summary line
    #     return " | ".join(parts)


    
    # def _optimise_results(self, results: List[Dict[str, Any]]) -> str:
    #     """
    #     Build a concise, token‐efficient summary of our tool outputs by
    #     extracting every key scalar (flight duration, altitudes, GPS stats,
    #     battery voltages/current/power, RC losses, signal drops, anomalies, KPIs)
    #     and skipping raw time series or arrays.
    #     """
    #     parts: List[str] = []

    #     for item in results:
    #         for tool_name, payload in item.items():
    #             if not payload:
    #                 continue

    #             # ── FLIGHT STATISTICS ─────────────────────────────────────────
    #             if tool_name == "flight_statistics" and isinstance(payload, dict):
    #                 if payload.get("flight_duration_sec") is not None:
    #                     parts.append(f"flight_duration_sec={payload['flight_duration_sec']:.1f}")
    #                 if payload.get("flight_duration_hms"):
    #                     parts.append(f"flight_duration_hms=\"{payload['flight_duration_hms']}\"")
    #                 if payload.get("takeoff_time"):
    #                     parts.append(f"takeoff_time=\"{payload['takeoff_time']}\"")
    #                 if payload.get("landing_time"):
    #                     parts.append(f"landing_time=\"{payload['landing_time']}\"")
    #                 if payload.get("max_altitude") is not None:
    #                     parts.append(f"max_altitude={payload['max_altitude']:.1f}")
    #                 if payload.get("distance_traveled_km") is not None:
    #                     parts.append(f"distance_traveled_km={payload['distance_traveled_km']:.3f}")
    #                 if payload.get("max_groundspeed") is not None:
    #                     parts.append(f"max_groundspeed={payload['max_groundspeed']:.2f}")
    #                 if payload.get("max_airspeed") is not None:
    #                     parts.append(f"max_airspeed={payload['max_airspeed']:.2f}")
    #                 if payload.get("battery_voltage_drop_pct") is not None:
    #                     parts.append(f"battery_voltage_drop_pct={payload['battery_voltage_drop_pct']:.1f}")
    #                 if payload.get("energy_consumed_wh") is not None:
    #                     parts.append(f"energy_consumed_wh={payload['energy_consumed_wh']:.2f}")
    #                 if payload.get("overall_performance_score") is not None:
    #                     parts.append(f"overall_performance_score={payload['overall_performance_score']:.2f}")
    #                 if payload.get("anomaly_count") is not None:
    #                     parts.append(f"anomaly_count={payload['anomaly_count']}")

    #             # ── ALTITUDE DETAILS ─────────────────────────────────────────
    #             elif tool_name == "altitude_details" and isinstance(payload, dict):
    #                 stats = payload.get("statistics", {})
    #                 if stats.get("max") is not None:
    #                     parts.append(f"altitude_max={stats['max']:.1f}")
    #                 if stats.get("min") is not None:
    #                     parts.append(f"altitude_min={stats['min']:.1f}")
    #                 phases = payload.get("flight_phases", {})
    #                 if phases.get("takeoff_time"):
    #                     parts.append(f"takeoff_time=\"{phases['takeoff_time']}\"")
    #                 if phases.get("landing_time"):
    #                     parts.append(f"landing_time=\"{phases['landing_time']}\"")
    #                 if phases.get("max_climb_rate") is not None:
    #                     parts.append(f"max_climb_rate={phases['max_climb_rate']:.2f}")
    #                 if phases.get("max_descent_rate") is not None:
    #                     parts.append(f"max_descent_rate={phases['max_descent_rate']:.2f}")

    #             # ── BATTERY DETAILS ──────────────────────────────────────────
    #             elif tool_name == "battery_details" and isinstance(payload, dict):
    #                 vol = payload.get("voltage", {})
    #                 if vol.get("initial") is not None and vol.get("final") is not None:
    #                     parts.append(f"initial_voltage={vol['initial']:.2f}")
    #                     parts.append(f"final_voltage={vol['final']:.2f}")
    #                     parts.append(f"voltage_drop_percent={vol['drop_percent']:.1f}")
    #                 curr = payload.get("current", {})
    #                 if curr.get("min") is not None and curr.get("max") is not None:
    #                     parts.append(f"current_min={curr['min']:.2f}")
    #                     parts.append(f"current_max={curr['max']:.2f}")
    #                 rem = payload.get("remaining", {})
    #                 if rem.get("initial") is not None and rem.get("final") is not None:
    #                     parts.append(f"remaining_initial={rem['initial']:.1f}")
    #                     parts.append(f"remaining_final={rem['final']:.1f}")
    #                 power = payload.get("power", {})
    #                 if power.get("total_energy_wh") is not None:
    #                     parts.append(f"total_energy_wh={power['total_energy_wh']:.2f}")

    #             # ── SPEED DETAILS ───────────────────────────────────────────
    #             elif tool_name == "speed_details" and isinstance(payload, dict):
    #                 gs = payload.get("groundspeed", {})
    #                 if gs.get("max") is not None:
    #                     parts.append(f"groundspeed_max={gs['max']:.2f}")
    #                 if gs.get("mean") is not None:
    #                     parts.append(f"groundspeed_mean={gs['mean']:.2f}")
    #                 ap = payload.get("airspeed", {})
    #                 if ap.get("max") is not None:
    #                     parts.append(f"airspeed_max={ap['max']:.2f}")
    #                 vel3 = payload.get("velocity_3d", {})
    #                 if vel3.get("max") is not None:
    #                     parts.append(f"velocity_3d_max={vel3['max']:.2f}")

    #             # ── GPS DETAILS ─────────────────────────────────────────────
    #             elif tool_name == "gps_details" and isinstance(payload, dict):
    #                 fix = payload.get("fix_type", {})
    #                 if fix.get("good_fix_percentage") is not None:
    #                     parts.append(f"fix_good_percentage={fix['good_fix_percentage']:.1f}")
    #                 if fix.get("no_fix_percentage") is not None:
    #                     parts.append(f"fix_no_percentage={fix['no_fix_percentage']:.1f}")
    #                 sats = payload.get("satellites", {})
    #                 if sats.get("min") is not None and sats.get("max") is not None:
    #                     parts.append(f"satellites_min={sats['min']}")
    #                     parts.append(f"satellites_max={sats['max']}")
    #                 pos = payload.get("position", {})
    #                 if pos.get("distance_traveled_km") is not None:
    #                     parts.append(f"distance_traveled_km={pos['distance_traveled_km']:.3f}")
    #                 if pos.get("return_distance_km") is not None:
    #                     parts.append(f"return_distance_km={pos['return_distance_km']:.3f}")

    #             # ── ANOMALIES ───────────────────────────────────────────────
    #             elif tool_name == "anomalies" and isinstance(payload, list):
    #                 parts.append(f"anomaly_count={len(payload)}")
    #                 # look for first RC or signal loss anomaly
    #                 for ann in payload:
    #                     ann_type = ann.get("type", "").lower()
    #                     if "rc" in ann_type or "signal" in ann_type:
    #                         parts.append(f"first_rc_signal_loss=\"{ann.get('timestamp')}\"")
    #                         break

    #             # ── PERFORMANCE DETAILS ─────────────────────────────────────
    #             elif tool_name == "performance_details" and isinstance(payload, dict):
    #                 for key in ("altitude_stability", "battery_efficiency", "attitude_stability", "overall_performance"):
    #                     if payload.get(key) is not None:
    #                         parts.append(f"{key}={payload[key]:.3f}")

    #             # ── RC / SIGNAL EVENTS (if you eventually add a dedicated tool) ─
    #             elif (tool_name.startswith("rc_") or tool_name.startswith("signal_")) and isinstance(payload, dict):
    #                 # pass through entire dict so LLM can inspect details
    #                 parts.append(f"{tool_name}={json.dumps(payload)}")

    #             # ── EVERYTHING ELSE: skip raw arrays, servo channels, debug streams
    #             else:
    #                 continue

    #     # join with pipes so the reflector LLM sees a single tidy summary line
    #     return " | ".join(parts)


    # def _optimise_results(self, results: List[Dict[str, Any]]) -> str:
    #     """Very small summary of tool outputs to save tokens during reflection."""
    #     parts = []
    #     for item in results:
    #         for tool_name, payload in item.items():
    #             if tool_name == "battery_details" and isinstance(payload, dict):
    #                 vol = payload.get("voltage", {})
    #                 if vol:
    #                     parts.append(
    #                         f"Battery: Vstart={vol.get('initial')}V, Vend={vol.get('final')}V, drop={vol.get('drop_percent')}%"
    #                     )
    #                 curr = payload.get("current", {})
    #                 if curr:
    #                     parts.append(
    #                         f"Current: min={curr.get('min')}A, max={curr.get('max')}A"
    #                     )
    #                 rem = payload.get("remaining", {})
    #                 if rem:
    #                     parts.append(
    #                         f"Remaining: {rem.get('initial')}%→{rem.get('final')}%"
    #                     )
    #                 power = payload.get("power", {})
    #                 if power:
    #                     parts.append(
    #                         f"Energy: {power.get('total_energy_wh')}Wh"
    #                     )

    #             # ── ALTITUDE ──────────────────────────────────────────────
    #             elif tool_name == "altitude_details" and isinstance(payload, dict):
    #                 stats = payload.get("statistics", {})
    #                 parts.append(
    #                     f"Altitude: max={stats.get('max')}m, min={stats.get('min')}m"
    #                 )
    #                 phases = payload.get("flight_phases", {}) or {}
    #                 td = phases.get("flight_duration")
    #                 parts.append(f"Flight time={td:.1f}s" if td is not None else "Flight time=N/A")
    #                 tof = phases.get("takeoff_time")
    #                 lnd = phases.get("landing_time")
    #                 parts.append(f"Takeoff={tof}, Landing={lnd}")
    #                 parts.append(
    #                     f"Climb max={phases.get('max_climb_rate')}m/s, Descent min={phases.get('max_descent_rate')}m/s"
    #                 )

    #             # ── SPEED ─────────────────────────────────────────────────
    #             elif tool_name == "speed_details" and isinstance(payload, dict):
    #                 gs = payload.get("groundspeed", {})
    #                 if gs:
    #                     parts.append(
    #                         f"Ground spd: max={gs.get('max')}m/s, mean={gs.get('mean')}m/s"
    #                     )
    #                 ap = payload.get("airspeed", {})
    #                 if ap:
    #                     parts.append(
    #                         f"Air spd: max={ap.get('max')}m/s, mean={ap.get('mean')}m/s"
    #                     )
    #                 vel3 = payload.get("velocity_3d", {})
    #                 if vel3:
    #                     parts.append(f"3D spd max={vel3.get('max')}m/s")

    #             # ── GPS ───────────────────────────────────────────────────
    #             elif tool_name == "gps_details" and isinstance(payload, dict):
    #                 fix = payload.get("fix_type", {})
    #                 if fix:
    #                     parts.append(
    #                         f"GPS fix: good {fix.get('good_fix_percentage')}%, no-fix {fix.get('no_fix_percentage')}%"
    #                     )
    #                 sats = payload.get("satellites", {})
    #                 if sats:
    #                     parts.append(
    #                         f"Sats: min={sats.get('min')}, max={sats.get('max')}"
    #                     )
    #                 pos = payload.get("position", {})
    #                 if pos:
    #                     parts.append(
    #                         f"Dist={pos.get('distance_traveled_km')}km, Return={pos.get('return_distance_km')}km"
    #                     )
    #                     parts.append(
    #                         f"From ({pos.get('start_lat')},{pos.get('start_lon')}) → ({pos.get('end_lat')},{pos.get('end_lon')})"
    #                     )

    #             # ── ANOMALIES ─────────────────────────────────────────────
    #             elif tool_name == "anomalies" and isinstance(payload, list):
    #                 count = len(payload)
    #                 parts.append(f"Anomalies: {count}")
    #                 if count:
    #                     top = payload[0]
    #                     parts.append(
    #                         f"Top anomaly: {top.get('type')} @ {top.get('timestamp')}"
    #                     )

    #             # ── PERFORMANCE KPIs ──────────────────────────────────────
    #             elif tool_name == "performance_details" and isinstance(payload, dict):
    #                 if "altitude_stability" in payload:
    #                     parts.append(f"Alt_stability={payload.get('altitude_stability'):.2f}")
    #                 if "battery_efficiency" in payload:
    #                     parts.append(f"Bat_eff={payload.get('battery_efficiency'):.2f}")
    #                 if "attitude_stability" in payload:
    #                     parts.append(f"Att_stability={payload.get('attitude_stability'):.2f}")
    #                 if "overall_performance" in payload:
    #                     parts.append(f"Overall_perf={payload.get('overall_performance'):.2f}")

    #             # ── FULL FLIGHT SUMMARY ───────────────────────────────────
    #             elif tool_name == "flight_statistics" and isinstance(payload, dict):
    #                 dur = payload.get("flight_duration_hms")
    #                 if dur:
    #                     parts.append(f"Total flight time={dur}")
    #                 parts.append(f"Dist={payload.get('distance_traveled_km')}km")
    #                 parts.append(f"Max_alt={payload.get('max_altitude')}m")
    #                 parts.append(f"Vdrop={payload.get('battery_voltage_drop_pct')}%")
    #                 parts.append(f"Econs={payload.get('energy_consumed_wh')}Wh")
    #                 parts.append(f"Anomalies={payload.get('anomaly_count')}")
    #                 parts.append(f"Perf_score={payload.get('overall_performance_score'):.2f}")

    #             # ── RC / SIGNAL EVENTS ────────────────────────────────────
    #             elif tool_name.startswith("rc_") or tool_name.startswith("signal_"):
    #                 parts.append(f"{tool_name}: {json.dumps(payload)}")

    #             # ── FALLBACK ──────────────────────────────────────────────
    #             else:
    #                 # drop raw arrays, servo channels, debug fields, etc.
    #                 continue

    #     return " | ".join(parts)

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
