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

    The tools list **may be empty**.

    ## AVAILABLE TOOLS
      • metrics              → get_metrics_for_query
      • anomalies            → detect_anomalies
      • altitude_details     → detailed_altitude_analysis
      • battery_details      → detailed_battery_analysis
      • speed_details        → detailed_speed_analysis
      • gps_details          → detailed_gps_analysis
      • rc_signal_details    → detailed_rc_signal_analysis
      • flight_statistics    → comprehensive_flight_stats

    ## FEW-SHOT EXAMPLES

    Example 1:
    User → What was the highest ground-speed reached?

    THINK  The question is about top speed.  
    PLAN   Call **speed_details** which returns max / mean / p95 speeds.  
    EXECUTE

    Assistant →  
    {"clarification_needed":"NO","follow_up":null,"tools":["speed_details"]}
    -----------------------------------------

    Example 2:
    User → Any battery anomalies?

    THINK  Need anomaly detection & detailed battery context.  
    PLAN   Use **anomalies** for spikes + **battery_details** for voltage/current curves.  
    EXECUTE

    Assistant →  
    {"clarification_needed":"NO","follow_up":null,"tools":["anomalies","battery_details"]}
    -----------------------------------------

    Example 3:
    User → But what do you think about the no voltage drop or energy consumption in the battery aspect of the flight?

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
    -------------------------------------

    Example 4:
    User → Give me a full flight summary.

    THINK  Requires holistic statistics + overall KPIs.  
    PLAN   Call **flight_statistics** (covers everything: altitude, duration, distance, battery, gps, rc, etc.).
    EXECUTE

    Assistant →  
    {"clarification_needed":"NO","follow_up":null,"tools":["flight_statistics"]}
    ---------------------------------------

    Example 5:
    User → How bad was the GPS drift?

    THINK  Need GPS-specific statistics (gps fix/no-fix %, gps fix transitions, distance).  
    PLAN   Call **gps_details** only.
    EXECUTE

    Assistant →
    {"clarification_needed":"NO","follow_up":null,"tools":["gps_details"]}
    -------------------------------------

    Example 6:
    User → Were there any RC signal dropouts?

    THINK  User wants RC-link loss details.
    PLAN   Call **rc_signal_details** to get rc signal loss count, first drop time, durations, and rc signal transitions.
    EXECUTE

    Assistant →
    {"clarification_needed":"NO","follow_up":null,"tools":["rc_signal_details"]}
    ------------------------------------

    Example 7:
    User → Is there anything wrong?

    THINK  Too vague – cannot know which subsystem to inspect.
    PLAN   Ask a clarifying question, no tools yet.
    EXECUTE

    Assistant →
    {"clarification_needed":"YES","follow_up":"Could you specify which aspect of the flight you’d like me to examine – battery, altitude stability, GPS accuracy, or something else?","tools":[]}
    ---------------------------------------

    Example 8:
    User → What was the peak speed?

    THINK  Need speed-specific statistics to report the peak speed.
    PLAN   Call **speed_details** only to get the UAV speed details.
    EXECUTE

    Assistant →
    {"clarification_needed":"NO","follow_up":null,"tools":["speed_details"]}
    --------------------------------------

    Example 9:
    User → Tell me about the flight

    THINK  Need comprehensive flight statistics and `flight_statistics` tool provides all the information about the flight including GPS, RC, battery, altitude, and anomaly count. Nothing else is needed for this question.
    PLAN   Call **flight_statistics** only to cover all the overall flight stats.
    EXECUTE

    Assistant →
    {"clarification_needed":"NO","follow_up":null,"tools":["flight_statistics"]}
    -------------------------------------

    Example 10:
    User → Based on what data in the log did you conclude the flight time was 5 min 50 s?

    THINK  The user wants to know which telemetry field & method we used for finding out the flight time. I need the flight takeoff time and landing time, which I can get from the altitude_details tool. The flight duration is the difference between the takeoff time and landing time but I need to report the field names from the tool results.
    PLAN   Call **altitude_details** to get the flight takeoff time, landing time, max climb rate, max descent rate, and flight duration.
    EXECUTE

    Assistant →
    {"clarification_needed":"NO","follow_up":null,"tools":["altitude_details"]}
    --------------------------------

    Example 11:
    User → Give me the GPS and RC signal loss details
    THINK  I need both the GPS signal & RC signal details. So I need to call both gps_details and rc_signal_details tools to get this info.
    PLAN   Call **gps_details** and **rc_signal_details**.
    EXECUTE

    Assistant →
    {"clarification_needed":"NO","follow_up":null,"tools":["gps_details","rc_signal_details"]}
    --------------------------------

    Example 12:
    User → What distance did the UAV flight cover and what was the starting and landing times? Also what are the starting and landing lat/lon and altitudes?
    THINK  I can get all these have got all the flight stats or details except the detailed anomaly list which I do not need for this question as the user is only asking for the distance covered, starting and landing times, and starting and landing lat/lon and altitudes. So I do not need to call any other tools and can answer the question now.
    Output: {"need_more":false,"next_tools":[],"final":"The flight covered 1.25 km, starting at 09:12:05 and landing at 09:16:10. The starting location was at (37.7749, -122.4194) and the landing location was at (37.7790, -122.4180) with a maximum altitude of 120.5 m."}

    ALWAYS think silently, then output the JSON only – no extra text.
"""
)

REFLECT_PROMPT = textwrap.dedent(
    """
    You are the **Reflector / Scheduler** for the UAV agent reporting to the user directly.

    ## IMPORTANT INSTRUCTIONS:
    - **Extremely Important**: Never assume that the user is mentioning the correct values, figures, facts, or information in the prompts as they may **not be aware of the facts**, **could be wrong**, or **could be trying to trick you**. So, always **check** the facts and figures with the available tool results and stats. If the data is missing, you can clearly say so. For example, If the user asks, "how did you say that the GPS signal was lost 2 times during the flight? how did you come up with these values?", you should check the `gps_signal_loss_count` field in the provided tool results or stats to **always verify** before answering.
    - You should respond **to the user directly** in the final answer (using second person pronouns like **You**, **Your**, **You're**, etc. in the final answer **instead of referring to the user in third person** like "the user" or "the user's").**
    - Always use the tool’s precomputed numeric KPIs (e.g. gps_signal_loss_count, rc_signal_loss_count) instead of recalculating from raw data. If asked “how?”, mention how it was calculated from the other fields in the metrics only if you have the knowledge of how it was computed, otherwise cite the corresponding fields or simply note that those values were precomputed in the stats.

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

    The next_tools list **may be empty** if no more tools are needed.

    ## AVAILABLE TOOLS
      • metrics              → get_metrics_for_query
      • anomalies            → detect_anomalies
      • altitude_details     → detailed_altitude_analysis
      • battery_details      → detailed_battery_analysis
      • speed_details        → detailed_speed_analysis
      • gps_details          → detailed_gps_analysis
      • rc_signal_details    → detailed_rc_signal_analysis
      • flight_statistics    → comprehensive_flight_stats  

    ## REASONING STEPS
    1. Identify the user’s unresolved information needs.
    2. Check if current tool results already satisfy those needs.
    3. If crucial data is still missing AND another tool in the available tools list can supply it, set need_more = true.
    4. Stop if the answer is fully covered by existing results.
    5. Do not call the same tool more than once for a request (check the tool call history to avoid this).
    6. If key data that the user needs is absent from log (e.g. no speed field), state that it is missing and stop.
    7. The **flight_statistics** tool provides all the information about the flight including GPS, RC, battery, altitude, and anomaly count. If this tool is called, no other tools are needed unless detailed information about anomalies or other details is needed. This does not provide a detailed list of anomalies.

    ## FEW-SHOT EXAMPLES

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
        "gps_signal_first_loss_time":     "2025-05-21T09:12:10",
        "gps_signal_longest_loss_duration_sec":  <...>,
        "gps_fix_transitions": [
            {"time":"2025-05-21T09:12:10","from":3,"to":0},
            {"time":"2025-05-21T09:12:12","from":0,"to":3}
        ],
        "rc_signal_loss_count":      1,
        "rc_signal_dropouts":        1,
        "rc_signal_first_loss_time":     "2025-05-21T09:12:07",
        "rc_signal_longest_loss_duration_sec":  0.5,
        "rc_signal_transitions": [
            {"time":"2025-05-21T09:12:07","from":1,"to":0},
            {"time":"2025-05-21T09:12:07.500","from":0,"to":1}
        ]
    }

    THINK
    - Duration: 245 s (4 min 5 s).
    - Lift-off/landing: 09:12:05 → 09:16:10 on May 21 2025 (should mention the dates **clearly in english** whenever possible).
    - Peaks: 120.5 m altitude; 15.2/16.0 m/s ground/air speeds.
    - Battery: –1.2 %, 2.5 Wh → score 0.92.
    - 3 anomalies over 1.25 km from (37.7749, –122.4194) to (37.7790, –122.4180).
    - **GPS**:
        - Count: quote gps_signal_loss_count (1) to report GPS signal loss count.
        - First loss: quote gps_signal_first_loss_time (“2025-05-21T09:12:10”) to report the first instance of GPS signal loss.
        - Do not recount gps_fix_transitions or re-compute gps_signal_loss_count.
    - **RC**:
        - Count: quote rc_signal_loss_count (1) to report RC signal loss count.
        - First loss: quote rc_signal_first_loss_time (“2025-05-21T09:12:07”) to report the first instance of RC signal loss.
        - Longest outage: quote rc_signal_longest_loss_duration_sec (0.5 s) to report the longest RC signal outage.
        - Do not re-compute rc_signal_loss_count or count rc_signal_transitions.
    - The GPS or RC transitions is not a full list but consists of max 10 samples.
    - The **flight_statistics** tool provides all the information about the flight including GPS, RC, battery, altitude, and anomaly count. If this tool is called, no other tools are needed.
    - Synthesize into a concise and accurate narrative.

    Output (strict JSON format):
    {
        "need_more": false,
        "next_tools": [],
        "final": "The flight lasted 4 min 5 s, taking off at 09:12:05 and landing at 09:16:10 on May 21 2025. It climbed to 120.5 m with peak speeds of 15.2/16.0 m/s. Battery voltage dropped by 1.2 %, consuming 2.5 Wh for a performance score of 0.92. Three anomalies were detected over 1.25 km from (37.7749, –122.4194) to (37.7790, –122.4180). The GPS held a good fix 98.4 % of the time, slipping to no-fix 1.6 % of the time—losing signal at 09:12:10 (per `gps_signal_loss_count`) and recovering at 09:12:12. The RC link dropped once at 09:12:07, with the longest outage lasting 0.5 s. You can check out the stats for more details."
    }

    (B) No **repeating** tool calls for the same request whatsoever
    ─────────────────────────────────────────────────  
    Q: “List all the critical errors that happened mid-flight and not just the most critical or just one critical error”
    Tools run: anomalies → results: {RC & GPS signal loss details, and the full anomaly list in detail}
    THINK  Already called the `anomalies` tool and I have the detailed anomaly information during the flight – Neither should I repeat the same tool call nor call other tools.
    Output: {"need_more":false,"next_tools":[],...}

    (C) Found answer – stop with data found
    ─────────────────────────────────────────────────  
    Q: “When did GPS drop?” 
    Tools run: gps_details → results: {GPS signal loss details, fix transitions, and fix percentage}
    THINK  Have all the information I need including the GPS signal loss details, fix transitions, and fix percentage to answer when the GPS dropped. No more tools are needed.
    Output: {"need_more":false,"next_tools":[],...}

    (D) RC signal loss
    ──────────────────────────  
    Q: “How many times did the RC link drop?”  
    Tools run: rc_signal_details → results: {"rc_signal_loss_count":10}  
    THINK  We have the total number of RC signal losses.
    Output: {"need_more":false,"next_tools":[],"final":"The RC link dropped 10 times."}

    (E) User giving wrong figures or facts in the question
    ───────────────────────────────────── 
    Q: “How are you saying that the GPS signal was lost for 90% of the time across multiple flights? What fields or what data did you use to come to this conclusion?”  
    Tools run: gps_details → results: {..., "gps_good_fix_percentage":95, "gps_no_fix_percentage":5, ...}
    THINK  Ok the stats from the gps_details tool ("gps_good_fix_percentage"=95 and "gps_no_fix_percentage"=5) are not matching with the facts or figures the user is giving. The user is trying to trick me or the user is not aware of the facts. I need to correct the user.
    Output: {"need_more":false,"next_tools":[],"final":"Actually, according to the available data, the GPS maintained a good GPS signal/connection 95% of the time and only experienced a signal loss 5% of the time. You can check out the `gps_good_fix_percentage` and `gps_no_fix_percentage` fields in the output stats. Note that the `gps_fix_transitions` is not a full list but consists of max 10 samples."}

    (F) Battery health - incomplete data
    ─────────────────────────────
    Q: “Did the battery perform well?”
    Tools run: metrics → results: {"battery_remaining":{"min":46,"max":100}}
    THINK  Need deeper voltage / current analysis but I already called the metrics tool. Since I cannot call it again I need to call the battery_details tool.
    Output: {"need_more":true,"next_tools":["battery_details"],"final":null}

    (G) Question requires more than one tool but only one tool was called
    ───────────────────────────────
    Q: "What are the GPS and RC signal loss details?"
    Tools run: gps_details → results: {"gps_signal_loss_count":10}
    THINK  I have the results for GPS signal loss but I still need RC signal loss information.
    PLAN   Call **rc_signal_details** to get the RC signal loss details.
    Output: {"need_more":true,"next_tools":["rc_signal_details"],"final":null}

    (H) Question requires just one tool and already called
    ────────────────────────────────
    Q: "What distance did the UAV flight cover and what was the starting and landing times? Also what are the starting and landing lat/lon and altitudes?"
    Tools run: flight_statistics → results: {...all flight stats, RC, battery, altitude, and anomaly count}
    THINK  I have got all the flight stats or details except the detailed anomaly list which I do not need for this question as the user is only asking for the distance covered, starting and landing times, and starting and landing lat/lon and altitudes. So I do not need to call any other tools and can answer the question now.
    Output: {"need_more":false,"next_tools":[],"final":"The flight covered 1.25 km, starting at 09:12:05 and landing at 09:16:10. The starting location was at (37.7749, -122.4194) and the landing location was at (37.7790, -122.4180) with a maximum altitude of 120.5 m."}

    (I) User mentioning a lot of details in the question but every single detail needs to be verified for authenticity first before answering
    ─────────────────────────────────────────
    Q: "You say the count of RC signal being lost 47 times is derived from the transitions where the signal changed from '1' (signal present) to '0' (signal lost) and the tool results indicate a total of 47 such transitions, which accounts for the RC signal loss count, but I only see a total of 12 such transitions from '1' to '0' in the results. What is up?"
    Tools run: rc_signal_details → results: {
        "rc_signal_loss_count": 12,
        "rc_signal_transitions": [
            {
                "time": "2018-08-08 14:06:01.910000+00:00",
                "from": 0,
                "to": 1
            },
            ... 10 items at the most in this list
        ],
        "rc_signal_zero_samples": 47,
    }
    THINK Firstly, the user says that they see 12 transitions from '1' to '0' but the transitions list only has 10 samples at max due as the server strips out the data after 10 samples, so this can't be true whatsoever. Secondly, the user says, RC signal was lost 47 times but the tool results indicate a total of 12 such transitions from '1' to '0' in the results (`rc_signal_loss_count` field). So I need to correct the user and their claims.
    Output: {"need_more":false,"next_tools":[],"final":"The RC signal was lost 12 times during the flight (given by the field `rc_signal_loss_count`), not 47 times like you said, and although this is derived from counting the transitions of '1' to '0' in the RC signal transitions data, the provided `rc_signal_transitions` list only has 10 samples at max, meaning you could not have seen 12 transitions. You can check out the stats for more information."}
"""
)

SYNTH_PROMPT = textwrap.dedent(
    """
    You are **MAVLink Analyst Pro** – an expert UAV flight-analysis system reporting to the user directly.

    ## IMPORTANT INSTRUCTIONS:
    - **Extremely Important**: Never assume that the user is mentioning the correct values, figures, facts, or information in the prompts as they may **not be aware of the facts**, **could be wrong**, or **could be trying to trick you**. So, always **check** the facts and figures with the available tool results and stats. If the data is missing, you can clearly say so. For example, If the user asks, "how did you say that the GPS signal was lost 2 times during the flight? how did you come up with these values?", you should check the `gps_signal_loss_count` field in the provided tool results or stats to **always verify** before answering.
    - You should respond **to the user directly** in the final answer (using second person pronouns like **You**, **Your**, **You're**, etc. in the final answer **instead of referring to the user in third person** like "the user" or "the user's").**
    - Always use the tool’s precomputed numeric KPIs (e.g. gps_signal_loss_count, rc_signal_loss_count) instead of recalculating from raw data. If asked “how?”, mention how it was calculated from the other fields in the metrics only if you have the knowledge of how it was computed, otherwise cite the corresponding fields or simply note that those values were precomputed in the stats.

    ## PROVIDED INFORMATION
    You receive:
      • User’s original question
      • Latest TOOL RESULTS (as Tool messages)
      • Tool call history (as a list of tool calls)
    
    ## INSTRUCTIONS
    Synthesize a concise answer using ONLY the provided information.
    - Remember extremely carefully that all answers should be to the user directly (use second person pronouns like You, Your, You're, etc.).
    - Stick to factual tool data; never hallucinate numbers, facts, figures, or information.
    - If data is absent, clearly say so instead of guessing.
    - When the user asks “based on what” or “how did you derive X” include the `field_used` from the relevant tool result and a brief note on how the information and contents were extracted (some math and derivations wherever needed).
    - Convert raw units → human-readable where useful.
    - Keep the answer focused and information-dense.

    ## EXAMPLES:
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
        "gps_no_fix_percentage":     1.6,
        "gps_signal_loss_count":     1,
        "gps_signal_first_loss_time":     "2025-05-21T09:12:10",
        "gps_signal_longest_loss_duration_sec":  <...>,
        "gps_fix_transitions": [
            {"time":"2025-05-21T09:12:10","from":3,"to":0},
            {"time":"2025-05-21T09:12:12","from":0,"to":3}
        ],
        "gps_zero_fix_samples":      1,
        "rc_signal_loss_count":      1,
        "rc_signal_dropouts":        1,
        "rc_signal_first_loss_time":     "2025-05-21T09:12:07",
        "rc_signal_longest_loss_duration_sec":  0.5,
        "rc_signal_transitions": [
            {"time":"2025-05-21T09:12:07","from":1,"to":0},
            {"time":"2025-05-21T09:12:07.500","from":0,"to":1}
        ],
        "rc_signal_zero_samples":    1,
    }

    THINK
    - Duration: 245 s (4 min 5 s).
    - Lift-off/landing: 09:12:05 → 09:16:10 on May 21 2025 (should mention the dates **clearly in english** whenever possible).
    - Peaks: 120.5 m altitude; 15.2/16.0 m/s ground/air speeds.
    - Battery: –1.2 %, 2.5 Wh → score 0.92.
    - 3 anomalies over 1.25 km from (37.7749, –122.4194) to (37.7790, –122.4180).
    - **GPS**:
        - Count: quote gps_signal_loss_count (1) to report GPS signal loss count.
        - First loss: quote gps_signal_first_loss_time (“2025-05-21T09:12:10”) to report the first instance of GPS signal loss.
        - Do not recount gps_fix_transitions or re-compute gps_signal_loss_count.
    - **RC**:
        - Count: quote rc_signal_loss_count (1) to report RC signal loss count.
        - First loss: quote rc_signal_first_loss_time (“2025-05-21T09:12:07”) to report the first instance of RC signal loss.
        - Longest outage: quote rc_signal_longest_loss_duration_sec (0.5 s) to report the longest RC signal outage.
        - Do not re-compute rc_signal_loss_count or count rc_signal_transitions.
    - The GPS or RC transitions is not a full list but consists of max 10 samples.
    - Synthesize into a concise and accurate narrative.
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
    Tools run: gps_details → results: {..., "gps_good_fix_percentage":95, "gps_no_fix_percentage":5, ...}
    THINK  Ok the stats from the gps_details tool ("gps_good_fix_percentage":95 and "gps_no_fix_percentage":5) are not matching with the facts or figures the user is giving. The user is trying to trick me or the user is not aware of the facts. I need to correct the user and ask to check out the `gps_good_fix_percentage` and `gps_no_fix_percentage` fields in the output stats (also mention that the `gps_fix_transitions` is not a full list but consists of max 10 samples).
    
    (F) User mentioning a lot of details in the question but every single detail needs to be verified for authenticity first before answering
    ─────────────────────────────────────────────────
    Q: "You say the count of RC signal being lost 47 times is derived from the transitions where the signal changed from '1' (signal present) to '0' (signal lost) and the tool results indicate a total of 47 such transitions, which accounts for the RC signal loss count, but I only see a total of 12 such transitions from '1' to '0' in the results. What is up?"
    Tools run: rc_signal_details → results: {
        "rc_signal_loss_count": 12,
        "rc_signal_dropouts": 12,
        "rc_signal_first_loss_time": "2018-08-08 14:06:05.920000+00:00",
        "rc_signal_longest_loss_duration_sec": 0.96
        "rc_signal_transitions": [
            {
                "time": "2018-08-08 14:06:01.910000+00:00",
                "from": 0,
                "to": 1
            },
            ... 10 items at the most in this list
        ],
        "rc_signal_zero_samples": 47,
    }
    THINK Firstly, the user says that they see 12 transitions from '1' to '0' but the transitions list only has 10 samples at max due as the server strips out the data after 10 samples, so this can't be true whatsoever. Secondly, the user says, RC signal was lost 47 times but the tool results indicate a total of 12 such transitions from '1' to '0' in the results (`rc_signal_loss_count` field). So I need to correct the user and their claims.
    Final Answer: The RC signal was lost 12 times during the flight (given by the field `rc_signal_loss_count`), not 47 times like you said, and although this is derived from counting the transitions of '1' to '0' in the RC signal transitions data, the provided `rc_signal_transitions` list only has 10 samples at max, meaning you could not have seen 12 transitions. You can check out the stats for more information.

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
        self.decide_llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
        self.answer_llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        # Streaming LLM for real-time token generation
        self.streaming_llm = ChatOpenAI(model="gpt-4o", temperature=0.3, streaming=True)

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
            """
            Return all anomalies that are relevant to *query* **plus**
            derived GPS-fix-loss and RC-signal-loss summary.

            Returns a dict with:
            • gps: {
                distance_traveled_km: float?,
                start_location: {lat: float, lon: float},
                end_location: {lat: float, lon: float},
                gps_no_fix_percentage: float?,
                gps_good_fix_percentage: float?,
                gps_signal_loss_count: int,
                gps_signal_first_loss_time: str?,
                gps_signal_longest_loss_duration_sec: float?,
                gps_fix_transitions: [ … ],
                gps_zero_fix_samples: int,
            }
            • rc: {
                rc_signal_loss_count: int,
                rc_signal_dropouts: int,
                rc_signal_first_loss_time: str?,
                rc_signal_longest_loss_duration_sec: float?,
                rc_signal_transitions: [ … ],
                rc_signal_zero_samples: int,
            }
            • anomaly_count: int
            • anomalies: [ … ]  # your base anomalies
            """
            query = inp if isinstance(inp, str) else inp.get("query", "")
            base_anoms: List[Dict[str, Any]] = list(a._filter_relevant_anomalies(query) or [])

            # GPS
            gps = a._analyze_gps() or {}
            pos = gps.get("position", {}) or {}
            gps_info = {
                "distance_traveled_km":       pos.get("distance_traveled_km"),
                "start_location":             {"lat": pos.get("start_lat"), "lon": pos.get("start_lon")},
                "end_location":               {"lat": pos.get("end_lat"),   "lon": pos.get("end_lon")},
                "gps_no_fix_percentage"      : gps.get("gps_no_fix_percentage"),
                "gps_good_fix_percentage"    : gps.get("gps_good_fix_percentage"),
                "gps_signal_loss_count"      : gps.get("gps_signal_loss_count"),
                "gps_signal_first_loss_time"      : gps.get("gps_signal_first_loss_time"),
                "gps_signal_longest_loss_duration_sec": gps.get("gps_signal_longest_loss_duration_sec"),
                "gps_fix_transitions"        : gps.get("gps_fix_transitions", []),
                "gps_zero_fix_samples"  : gps.get("gps_zero_fix_samples"),
            }

            # RC
            rc = a._analyze_rc_signal() or {}
            rc_info = {
                "rc_signal_loss_count"        : rc.get("rc_signal_loss_count"),
                "rc_signal_dropouts"    : rc.get("rc_signal_dropouts"),
                "rc_signal_first_loss_time"        : rc.get("rc_signal_first_loss_time"),
                "rc_signal_longest_loss_duration_sec"  : rc.get("rc_signal_longest_loss_duration_sec"),
                "rc_signal_transitions"       : rc.get("rc_signal_transitions", []),
                "rc_signal_zero_samples" : rc.get("rc_signal_zero_samples"),
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
            """GPS quality & position analysis: gps fix percentage, gps fix transitions, satellites,
            travel distance, start/end coordinates, plus explicit loss count."""
            res = a._analyze_gps() or {}
            return ensure_serializable(res)
        
        @tool("rc_signal_details")
        def rc_signal_details() -> Dict[str, Any]:
            """RC-link quality & signal-loss analysis:
                • RSSI statistics (if available)
                • rc signal loss/recovery transitions
                • total dropout count"""
            # fetch raw RC analysis
            rc = a._analyze_rc_signal() or {}
            return ensure_serializable(rc)
        

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
                "gps_no_fix_percentage"      : gps.get("gps_no_fix_percentage"),
                "gps_good_fix_percentage"    : gps.get("gps_good_fix_percentage"),
                "gps_signal_loss_count"      : gps.get("gps_signal_loss_count"),
                "gps_signal_first_loss_time" : gps.get("gps_signal_first_loss_time"),
                "gps_signal_longest_loss_duration_sec": gps.get("gps_signal_longest_loss_duration_sec"),
                "gps_fix_transitions"        : gps.get("gps_fix_transitions", []),
                "gps_zero_fix_samples"       : gps.get("gps_zero_fix_samples"),
            })

            # ── RC-link summary ─────────────────────────────────────────────────
            stats.update({
                "rc_signal_loss_count"        : rc.get("rc_signal_loss_count"),
                "rc_signal_dropouts"    : rc.get("rc_signal_dropouts"),
                "rc_signal_first_loss_time"        : rc.get("rc_signal_first_loss_time"),
                "rc_signal_longest_loss_duration_sec"  : rc.get("rc_signal_longest_loss_duration_sec"),
                "rc_signal_transitions"       : rc.get("rc_signal_transitions", []),
                "rc_signal_zero_samples" : rc.get("rc_signal_zero_samples"),
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
        # await self.memory_manager.add_message(role="user", content=query, metadata={"session_id": st["session_id"]})
        # raw = self.think_llm.invoke([SystemMessage(content=INT_ROUTE_PROMPT), HumanMessage(content=query)]).content
        
        await self.memory_manager.add_message(role="user", content=query, metadata={"session_id": st["session_id"]})
        # pull relevant history and pass it to the planner LLM
        ctx = await self.memory_manager.get_context(query)
        hist_txt = self._history_to_text(ctx.get("relevant_history", []))
        
        msgs = [SystemMessage(content=INT_ROUTE_PROMPT)]
        if hist_txt:
            msgs.append(SystemMessage(content=f"Relevant chat so far:\n{hist_txt}"))
        
        msgs.append(HumanMessage(content=query))
        raw = self.decide_llm.invoke(msgs).content
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
        # return {"scratch": scratch, "errors": errors} if errors else {"scratch": scratch}
        out: AgentState = {"input": query, "scratch": scratch, "session_id": st.get("session_id", self.session_id)}
        if errors:
            out["errors"] = errors
        return out

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
            out = {"input": st["input"], "scratch": scratch, "current_step": st.get("current_step", 0), "session_id": st.get("session_id", self.session_id)}
            if errors:
                out["errors"] = errors
            return out

        calls = []
        # for name in pending:
        #     if name in tool_history:
        #         continue

        #     obj = self.tool_map.get(name)
        #     if obj is None:
        #         errors.append(f"unknown_tool:{name}")
        #         continue

        #     # If the wrapped LangChain tool takes **any** parameter, we’ll
        #     # feed the user’s question positionally; else call with no args.
        #     takes_arg = bool(inspect.signature(obj.run).parameters)
        #     calls.append((name, obj, st["input"] if takes_arg else None))

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
                    # errors.append(f"tool_fail:{name}:{e}")
                    errors.append(f"tool_fail:{name}:{type(e).__name__}:{e}")

        scratch["pending_tools"] = []
        scratch["tool_history"] = tool_history + executed
        scratch["tool_results"] = tool_results
        out: AgentState = {
            "input": st["input"],
            "scratch": scratch,
            "current_step": st.get("current_step", 0),
            "session_id": st.get("session_id", self.session_id)
        }
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
        # bring in memory context
        mem_ctx = await self.memory_manager.get_context(st["input"])
        hist_txt = self._history_to_text(mem_ctx.get("relevant_history", []))

        current_step = st.get("current_step", 0) + 1
        tool_history = scratch.get("tool_history", [])

        msgs = [SystemMessage(content=REFLECT_PROMPT)]
        if hist_txt:
            msgs.append(SystemMessage(content=f"Relevant chat so far:\n{hist_txt}"))
        
        msgs.append(HumanMessage(content=st["input"]))

        if scratch.get("tool_results"):
            optimised = self._optimise_results(scratch['tool_results'])
            logger.info(f"Optimised tool results: {optimised}")
            msgs.append(AIMessage(content=f"Tool results:\n{optimised}"))

        if tool_history:
            logger.info(f"Tool history: {tool_history}")
            msgs.append(AIMessage(content=f"Tool history:\n{tool_history}"))

        # CRITICAL: Add error information to the LLM so it knows when tools failed
        errors = st.get("errors", [])
        if errors:
            error_summary = "\n".join(errors)
            msgs.append(SystemMessage(content=f"TOOL ERRORS ENCOUNTERED:\n{error_summary}\n\nNote: When tools fail, you MUST inform the user that the requested data is unavailable due to errors. DO NOT hallucinate or make up numbers."))

        raw = self.decide_llm.invoke(msgs).content
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
        out: AgentState = {
            "input": st["input"],
            "scratch": scratch,
            "current_step": current_step,
            "session_id": st.get("session_id", self.session_id)
        }
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
        mem_ctx = await self.memory_manager.get_context(st["input"])
        hist_txt = self._history_to_text(mem_ctx.get("relevant_history", []))

        msgs = [SystemMessage(content=SYNTH_PROMPT)]
        if hist_txt:
            msgs.append(SystemMessage(content=f"Relevant chat so far:\n{hist_txt}"))
        
        msgs.append(HumanMessage(content=st["input"]))

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

        # CRITICAL: Add error information to the LLM so it knows when tools failed
        errors = st.get("errors", [])
        if errors:
            error_summary = "\n".join(errors)
            msgs.append(SystemMessage(content=f"TOOL ERRORS ENCOUNTERED:\n{error_summary}\n\nNote: When tools fail, you MUST inform the user that the requested data is unavailable due to errors. DO NOT hallucinate or make up numbers."))

        answer = self.answer_llm.invoke(msgs).content
        await self.memory_manager.add_message(
            role="assistant", content=answer, metadata={"session_id": st["session_id"], "final": True}
        )
        return {"answer": answer}

    async def _synthesize_streaming(self, st: AgentState):
        """
        Streaming version of _synthesize that yields tokens as they are generated.
        """
        if st.get("answer"):
            # Already have answer, just return it
            yield {
                "type": "complete",
                "content": st["answer"],
                "analysis": self._format_analysis(st),
                "session_id": st.get("session_id", self.session_id)
            }
            return

        scratch = st.get("scratch", {})
        user_input = st.get("input", "")
        session_id = st.get("session_id", self.session_id)
        
        # Get memory context if we have user input
        hist_txt = ""
        if user_input:
            mem_ctx = await self.memory_manager.get_context(user_input)
            hist_txt = self._history_to_text(mem_ctx.get("relevant_history", []))

        msgs = [SystemMessage(content=SYNTH_PROMPT)]
        if hist_txt:
            msgs.append(SystemMessage(content=f"Relevant chat so far:\n{hist_txt}"))
        
        if user_input:
            msgs.append(HumanMessage(content=user_input))

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

        # CRITICAL: Add error information to the LLM so it knows when tools failed
        errors = st.get("errors", [])
        if errors:
            error_summary = "\n".join(errors)
            msgs.append(SystemMessage(content=f"TOOL ERRORS ENCOUNTERED:\n{error_summary}\n\nNote: When tools fail, you MUST inform the user that the requested data is unavailable due to errors. DO NOT hallucinate or make up numbers."))

        # Stream the response
        full_content = ""
        async for chunk in self.streaming_llm.astream(msgs):
            # if chunk.content:
            #     full_content += chunk.content
            # LangChain v0.1 and v0.2 emit different chunk shapes
            token_text = getattr(chunk, "content", None)
            if token_text is None and hasattr(chunk, "message"):
                token_text = getattr(chunk.message, "content", None)
            
            if token_text:
                full_content += token_text
                yield {
                    "type": "token",
                    # "content": chunk.content,
                    "content": token_text,
                    "full_content": full_content
                }

        # Save to memory and send completion
        await self.memory_manager.add_message(
            role="assistant", content=full_content, metadata={"session_id": session_id, "final": True}
        )
        
        yield {
            "type": "complete",
            "content": full_content,
            "analysis": self._format_analysis(st),
            "session_id": session_id
        }

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

    async def process_message_streaming(self, message: str):
        """
        Process a message with streaming token generation.
        Yields tokens as they are generated from the LLM.
        """
        init_state: AgentState = {
            "input": message,
            "session_id": self.session_id,
            "scratch": {"tool_history": []},
            "current_step": 0,
            "errors": [],
        }
        
        # Process through the graph until we reach synthesis
        # We need to run all steps except the final synthesis
        current_state = init_state
        
        # Run interpret step
        current_state = await self._interpret(current_state)
        
        # Check if we need clarification
        if self._branch_after_interpret(current_state) == "ask_clarification":
            current_state = await self._ask_clarification(current_state)
            # For clarification, we don't stream - just return the question
            yield {
                "type": "complete",
                "content": current_state.get("answer", "I need clarification."),
                "analysis": self._format_analysis(current_state),
                "session_id": self.session_id
            }
            return
        
        # Run tools if needed
        if self._branch_after_interpret(current_state) == "run_tools":
            current_state = await self._run_tools(current_state)
            
            # Run reflection loop until we're ready to synthesize
            while self._branch_after_reflect(current_state) == "run_tools":
                current_state = await self._reflect(current_state)
                if current_state.get("scratch", {}).get("need_more", False):
                    current_state = await self._run_tools(current_state)
                else:
                    break
        
        # Now do streaming synthesis
        async for token_data in self._synthesize_streaming(current_state):
            yield token_data
    

    # ──────────────────────────────────────────────────────────
    # Helper – turn LC messages / dicts into Chat-style lines
    # ──────────────────────────────────────────────────────────
    @staticmethod
    def _history_to_text(history: List[Any], limit: int = 40) -> str:
        """
        Convert a list coming from EnhancedMemoryManager into plain text
        the LLM can digest.  Keeps the newest `limit` messages.
        """
        out: List[str] = []
        for msg in history[-limit:]:
            # Two possible shapes: a langchain Message or a dict
            if hasattr(msg, "type"):                        # Message object
                role = msg.type
                content = msg.content
            else:                                          # dict from FAISS
                role = msg.get("metadata", {}).get("role", "unknown")
                content = msg.get("content", "")
            out.append(f"{role.capitalize()}: {content}")
        return "\n".join(out)


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
                        if isinstance(v, float):
                            _add(f"{k}={v:.3f}")
                        else:
                            _add(f'{k}="{v}"')

                # 2) altitude_details
                elif tool == "altitude_details":
                    stats  = payload.get("statistics", {})
                    phases = payload.get("flight_phases", {})
                    for k, v in stats.items():
                        if v is not None:
                            if isinstance(v, float):
                                _add(f"altitude_{k}={v:.3f}")
                            else:
                                _add(f'altitude_{k}="{v}"')

                    for k, v in phases.items():
                        if v is None:
                            continue

                        if isinstance(v, float):
                            _add(f"{k}={v:.3f}")
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
                                    _add(f"{label}={v:.3f}")
                                else:
                                    _add(f"{label}={v}")

                # 4) speed_details
                elif tool == "speed_details":
                    for speed_type, stats in payload.items():
                        if not isinstance(stats, dict):
                            continue

                        for k, v in stats.items():
                            if v is not None:
                                if isinstance(v, float):
                                    _add(f"{speed_type}_{k}={v:.3f}")
                                else:
                                    _add(f'{speed_type}_{k}="{v}"')

                # 5) gps_details
                elif tool == "gps_details":
                    # flat fields that gps_details tool injects at top level
                    for key in (
                        "gps_signal_loss_count",
                        "gps_signal_dropouts",
                        "gps_signal_first_loss_time",
                        "gps_signal_longest_loss_duration_sec",
                        "gps_no_fix_percentage",
                        "gps_good_fix_percentage",
                        "gps_fix_transitions",
                        "gps_zero_fix_samples",
                    ):
                        if key in payload and payload[key] is not None:
                            val = payload[key]
                            if isinstance(val, float):
                                _add(f"{key}={val:.3f}")
                            else:
                                _add(f'{key}="{val}"')

                    # nested gps_fix_type_counts, satellites, position
                    for section in ("gps_fix_type_counts", "satellites", "position"):
                        sub = payload.get(section, {}) or {}
                        for k, v in sub.items():
                            if v is None:
                                continue

                            label = f"{section}_{k}"
                            if isinstance(v, float):
                                _add(f"{label}={v:.3f}")
                            else:
                                _add(f"{label}={v}")

                # 6) rc_signal_details
                elif tool == "rc_signal_details":
                    for key in (
                        "rc_signal_loss_count",
                        "rc_signal_dropouts",
                        "rc_signal_first_loss_time",
                        "rc_signal_longest_loss_duration_sec",
                        "rc_signal_transitions",
                        "rc_signal_zero_samples"
                    ):
                        if key in payload and payload[key] is not None:
                            val = payload[key]
                            if isinstance(val, float):
                                _add(f"{key}={val:.3f}")
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
                        if gps.get("gps_signal_loss_count") is not None:
                            _add(f"gps_signal_loss_count={gps['gps_signal_loss_count']}")
                        if gps.get("gps_signal_first_loss_time"):
                            _add(f'gps_signal_first_loss_time="{gps["gps_signal_first_loss_time"]}"')
                        if gps.get("gps_signal_longest_loss_duration_sec") is not None:
                            _add(f"gps_signal_longest_loss_duration_sec={gps['gps_signal_longest_loss_duration_sec']:.3f}")
                        if gps.get("gps_no_fix_percentage") is not None:
                            _add(f"gps_no_fix_percentage={gps['gps_no_fix_percentage']:.3f}")
                        if gps.get("gps_good_fix_percentage") is not None:
                            _add(f"gps_good_fix_percentage={gps['gps_good_fix_percentage']:.3f}")
                    # rc summary
                    rc = payload.get("rc", {})
                    if rc:
                        if rc.get("rc_signal_loss_count") is not None:
                            _add(f"rc_signal_loss_count={rc['rc_signal_loss_count']}")
                        if rc.get("rc_signal_first_loss_time"):
                            _add(f'rc_signal_first_loss_time="{rc["rc_signal_first_loss_time"]}"')
                        if rc.get("rc_signal_longest_loss_duration_sec") is not None:
                            _add(f"rc_signal_longest_loss_duration_sec={rc['rc_signal_longest_loss_duration_sec']:.3f}")
                        if rc.get("rc_signal_dropouts") is not None:
                            _add(f"rc_signal_dropouts={rc['rc_signal_dropouts']}")
                        if rc.get("rc_signal_zero_samples") is not None:
                            _add(f"rc_signal_zero_samples={rc['rc_signal_zero_samples']}")

                # 8) generic fallback: pick any remaining simple scalars
                else:
                    for k, v in payload.items():
                        if isinstance(v, (int, float, str)) and len(str(v)) < 64:
                            _add(f"{tool}_{k}={v}")

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
