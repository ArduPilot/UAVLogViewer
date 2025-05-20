from __future__ import annotations
import traceback
import json, uuid, inspect, textwrap
from typing import Dict, Any, List, Optional, TypedDict, Literal
from dataclasses import field
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool, BaseTool
from langgraph.graph import StateGraph, END

from telemetry.analyzer import TelemetryAnalyzer
from telemetry.parser import TelemetryParser
from chat.memory_manager import EnhancedMemoryManager

# Configure logging
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────
# Graph state TypedDict (NEW)
# ──────────────────────────────────────────────────────────
class AgentState(TypedDict, total=False):
    """State maintained throughout the graph execution."""
    # immutable inputs
    input: str
    session_id: str

    # working memory
    scratch: Dict[str, Any]
    current_step: int
    errors: List[str]

    # final output
    answer: Optional[str]

# ──────────────────────────────────────────────────────────
# prompts
# ──────────────────────────────────────────────────────────
INT_ROUTE_PROMPT = textwrap.dedent("""
    You are the **Routing / Planner** module for an agentic UAV-telemetry assistant.

    ## TASK
    1. Read the *User Query*.
    2. THINK ➔ PLAN ➔ EXECUTE in your private scratch-pad.
    3. Output **ONLY** valid JSON with these keys:
       {
         "clarification_needed": "YES" | "NO",
         "follow_up": "<question or null>",
         "tools": ["metrics","anomalies","altitude_details","battery_details","speed_details","gps_details","performance_details","flight_statistics"]   // may be empty
       }

    ## AVAILABLE TOOLS
      • metrics            → get_metrics_for_query (extract relevant metrics for the query)
      • anomalies          → detect_anomalies (find unusual patterns in flight data)
      • altitude_details   → detailed_altitude_analysis (comprehensive altitude analysis)
      • battery_details    → detailed_battery_analysis (battery performance analysis)
      • speed_details      → detailed_speed_analysis (velocity and speed analysis)
      • gps_details        → detailed_gps_analysis (GPS and position analysis)
      • performance_details → detailed_performance_analysis (overall flight KPIs)
      • flight_statistics  → comprehensive_flight_stats (complete flight overview)

    ## FEW-SHOT EXAMPLES (ReAct-style)

    --- EX1 ------------------------------------------------
    User: "What was the maximum altitude reached during this flight?"

    THINK: The user wants the highest altitude value. Need detailed altitude analysis.
    PLAN: Call altitude_details tool for comprehensive altitude metrics.
    EXECUTE: produce JSON.

    Assistant:
    {"clarification_needed":"NO","follow_up":null,"tools":["altitude_details"]}
    --------------------------------------------------------

    --- EX2 ------------------------------------------------
    User: "Can you spot any issues in the GPS data?"

    THINK: Need anomalies in GPS plus supporting metrics for full analysis.
    PLAN: Use anomalies for initial detection + specific GPS details for deeper analysis.
    EXECUTE.

    Assistant:
    {"clarification_needed":"NO","follow_up":null,"tools":["anomalies","gps_details"]}
    --------------------------------------------------------

    --- EX3 ------------------------------------------------
    User: "How was the overall flight performance?"

    THINK: This requires comprehensive flight analysis across multiple domains.
    PLAN: Gather performance metrics, flight statistics and potential anomalies.
    EXECUTE.

    Assistant:
    {"clarification_needed":"NO","follow_up":null,"tools":["performance_details","flight_statistics","anomalies"]}
    --------------------------------------------------------

    --- EX4 ------------------------------------------------
    User: "Are there any problems?"

    THINK: Too vague – must clarify which aspect of flight to analyze.
    PLAN: Ask follow-up, no tools yet.
    EXECUTE.

    Assistant:
    {"clarification_needed":"YES",
     "follow_up":"Which aspect of the flight would you like me to check for problems - altitude stability, GPS signal quality, battery performance, or something else?",
     "tools":[]}
    --------------------------------------------------------

    ALWAYS think silently, then output the JSON only.
""")

REFLECT_PROMPT = textwrap.dedent("""
    You are the **Reflector / Scheduler** for the UAV agent.

    You receive:
      • User's original question
      • Entire memory context with chat history
      • Latest TOOL RESULTS (as Tool messages)

    Your job is to carefully analyze the available data and determine if more tool calls are needed for a complete answer.

    Return **ONLY** JSON:
    {
      "need_more": true | false,
      "next_tools": ["metrics","anomalies","altitude_details","battery_details","speed_details","gps_details","performance_details","flight_statistics"],
      "final": "<answer text or null>"
    }

    ### REASONING FRAMEWORK
    1. Identify the user's core questions and information needs
    2. Evaluate which aspects have been covered by current tool results
    3. Determine if data quality and completeness are sufficient
    4. Consider data dependencies between tools
    5. Decide if more tools would meaningfully improve the answer
    
    ### STOPPING CRITERIA
      • Stop if answer is confidently complete with high-quality data
      • Stop if error count ≥ 3 or loop depth ≥ 6
      • Stop if key data is provably missing from logs (state this clearly)
      • Continue if critical information gaps can be filled by additional tools

    ### FEW-SHOT EXAMPLES

    (A) Maximum altitude already obtained:
      Question: "What was the maximum altitude reached?"
      Tools run: altitude_details → {"statistics": {"max": 63.3, "min": 1.2, "mean": 27.8}}
      THINK: We have the maximum altitude (63.3m) from a reliable source. The data looks complete and answers the core question. No other tools needed.
      Output:
      {"need_more":false,"next_tools":[],"final":"The maximum altitude reached during the flight was 63.3 meters."}

    (B) Battery query, incomplete data:
      Question: "Did the battery perform well during the flight?"
      Tools run: metrics → {"battery_remaining": {"min": 45, "max": 98}}
      THINK: We have basic battery metrics but need detailed battery analysis for voltage drops, current draws and consumption patterns to properly evaluate performance.
      Output:
      {"need_more":true,"next_tools":["battery_details"],"final":null}

    (C) Complex flight analysis, insufficient data:
      Question: "Was this a good flight?"
      Tools run: metrics → {"alt": {...}}, performance_details → {"altitude_stability": 0.82}
      THINK: Need more comprehensive data across key flight systems. We should check battery, speed, and potential anomalies to form a complete picture.
      Output:
      {"need_more":true,"next_tools":["battery_details","speed_details","anomalies"],"final":null}

    (D) Data provably missing:
      Question: "How was the communication with the ground station?"
      Tools run: metrics → {...}, anomalies → [...]
      THINK: After examining all metrics and anomalies, there's no telemetry data related to communication with the ground station. This information is simply not available in the log.
      Output:
      {"need_more":false,"next_tools":[],"final":"I don't see any telemetry data related to ground station communications in this log file. The available data covers flight performance, GPS, battery, and altitude, but doesn't include radio link quality or ground station telemetry."}

    (E) Data quality issues:
      Question: "What was the top speed during the flight?"
      Tools run: metrics → {...}, speed_details → {"error": "No valid speed data found in telemetry"}
      THINK: We've tried the appropriate tools but the log doesn't contain usable speed data. Further tool calls won't help.
      Output:
      {"need_more":false,"next_tools":[],"final":"I cannot determine the top speed from this flight log as it doesn't contain valid speed or velocity data. The telemetry appears to be missing or corrupted for speed-related parameters."}
""")

SYNTH_PROMPT = textwrap.dedent("""
    You are **MAVLink Analyst Pro** - an expert UAV flight analysis system.

    ## INSTRUCTIONS
    Synthesize a concise answer to the user's question using ONLY the verified tool outputs provided.
    
    ### GUIDELINES
    • Stay strictly within the facts from the tool outputs - NO speculation
    • If data is missing or incomplete, clearly acknowledge this
    • Highlight any critical safety issues or anomalies
    • Use bullet points for multi-part analyses
    • Include specific metrics and values to support your conclusions
    • Convert units and values to human-readable formats
    • Explain technical terms briefly when relevant
    • Provide context for unusual values or patterns
    
    ### RESPONSE FORMAT
    • Start with a direct answer to the question
    • Organize information in order of importance
    • Use precise technical language appropriate for UAV operators
    • Keep your answer focused and information-dense

    Return only the final answer text.
""")

# ──────────────────────────────────────────────────────────
# Main Agent implementation
# ──────────────────────────────────────────────────────────
class UavAgent:
    """
    Advanced UAV telemetry analysis agent with graph-based execution flow.
    
    This agent uses a graph-based approach to:
    1. Interpret user queries
    2. Plan appropriate tool usage
    3. Execute telemetry analysis tools in parallel
    4. Reflect on results to determine if more tools are needed
    5. Synthesize a final response
    
    Features:
    - Session-based memory isolation
    - Parallel tool execution for improved performance
    - Advanced CoT reasoning for complex queries
    - Robust error handling and logging
    """
    
    MAX_LOOPS = 6
    MAX_ERRORS = 3
    PARALLEL_WORKERS = 4  # Maximum number of parallel tool executions

    def __init__(self, session_id: str, telemetry_data: Optional[Dict] = None, analyzer: Optional[TelemetryAnalyzer] = None, log_path: Optional[str] = None):
        """
        Initialize the UAV agent with session ID and telemetry data.
        
        Args:
            session_id: Unique session identifier for memory isolation
            telemetry_data: Optional pre-parsed telemetry data
            analyzer: Optional pre-configured analyzer instance
            log_path: Optional path to telemetry log file
        """
        self.session_id = session_id
        logger.info(f"Initializing UAV agent with session ID: {session_id}")
        
        # Initialize telemetry components
        self.analyzer = None
        
        # Option 1: Use provided analyzer
        if analyzer is not None:
            self.analyzer = analyzer
            logger.info("Using provided analyzer instance")
            
        # Option 2: Use provided telemetry data
        elif telemetry_data is not None:
            self.analyzer = TelemetryAnalyzer(telemetry_data)
            logger.info("Initialized analyzer with provided telemetry data")
            
        # Option 3: Parse from log path
        elif log_path is not None:
            logger.info(f"Parsing telemetry log: {log_path}")
            try:
                telemetry_data = TelemetryParser(log_path).parse()
                self.analyzer = TelemetryAnalyzer(telemetry_data)
                logger.info("Successfully initialized telemetry analyzer from log file")
            except Exception as e:
                logger.error(f"Failed to initialize telemetry analyzer: {str(e)}")
                # Let the error propagate as this indicates a fundamental issue
                raise
        else:
            logger.error("No telemetry source provided (analyzer, data, or log path)")
            raise ValueError("Must provide telemetry analyzer, data, or log path")
        
        # Initialize LLMs for different agent components
        self.fast_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.0)
        self.smart_llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        
        # Initialize memory manager with session ID for isolation
        self.memory_manager = EnhancedMemoryManager(session_id=session_id)
        
        # Initialize tools
        self.tools = self._create_tools()
        self.tool_map = {t.name: t for t in self.tools}
        
        # Initialize LangGraph
        self.graph = self._build_graph()
        logger.info("Agent graph successfully built")

    def _create_tools(self) -> List[BaseTool]:
        """Create tool wrappers for telemetry analysis functions."""
        analyzer = self.analyzer  # Store reference to avoid repeated lookups
        
        # List of tools with proper docstrings for LLM clarity
        @tool
        def get_metrics_for_query(query: str) -> Dict[str, Any]:
            """
            Extract metrics from telemetry data relevant to a specific query.
            Use this to get basic statistics on flight parameters related to the query.
            
            Args:
                query: The query string describing which metrics to extract
                
            Returns:
                Dictionary of metric fields with min/max/mean/std statistics
            """
            return analyzer._filter_relevant_metrics(query)

        @tool
        def detect_anomalies(query: str = "") -> List[Dict[str, Any]]:
            """
            Detect anomalies in the telemetry data, optionally filtered by query terms.
            Use this to find unusual patterns or potential issues in the flight data.
            
            Args:
                query: Optional query string to filter anomalies (e.g., "battery", "altitude")
                
            Returns:
                List of anomaly objects with timestamp, type, description and severity
            """
            return analyzer._filter_relevant_anomalies(query)

        @tool
        def detailed_altitude_analysis() -> Dict[str, Any]:
            """
            Perform comprehensive analysis of altitude data from the flight.
            Use this for detailed altitude statistics, flight phases, climb/descent rates.
            
            Returns:
                Dictionary with altitude statistics, flight phases, and rates
            """
            return analyzer._analyze_altitude()

        @tool
        def detailed_battery_analysis() -> Dict[str, Any]:
            """
            Perform comprehensive analysis of battery performance during the flight.
            Use this for voltage, current, remaining capacity, and power consumption analysis.
            
            Returns:
                Dictionary with battery statistics and performance metrics
            """
            return analyzer._analyze_battery()

        @tool
        def detailed_speed_analysis() -> Dict[str, Any]:
            """
            Perform comprehensive analysis of speed and velocity during the flight.
            Use this for groundspeed, airspeed, and 3D velocity vector analysis.
            
            Returns:
                Dictionary with speed statistics and velocity metrics
            """
            return analyzer._analyze_speed()

        @tool
        def detailed_gps_analysis() -> Dict[str, Any]:
            """
            Perform comprehensive analysis of GPS performance during the flight.
            Use this for GPS fix quality, satellite count, position accuracy.
            
            Returns:
                Dictionary with GPS statistics and quality metrics
            """
            return analyzer._analyze_gps()

        @tool
        def detailed_performance_analysis() -> Dict[str, Any]:
            """
            Evaluate overall flight performance with key performance indicators.
            Use this for stability metrics, efficiency scores, and overall flight quality.
            
            Returns:
                Dictionary with performance scores and quality metrics
            """
            return analyzer._calculate_kpis()
            
        @tool
        def comprehensive_flight_stats() -> Dict[str, Any]:
            """
            Get comprehensive flight statistics across all major systems.
            Use this for a holistic view of the entire flight including distance, duration, altitude.
            
            Returns:
                Dictionary with comprehensive flight statistics 
            """
            # Combine data from multiple analysis functions for a complete picture
            stats = {}
            
            # Get altitude data
            alt_data = analyzer._analyze_altitude()
            if alt_data and "flight_phases" in alt_data:
                stats["flight_duration"] = alt_data["flight_phases"].get("flight_duration")
                stats["takeoff_time"] = alt_data["flight_phases"].get("takeoff_time")
                stats["landing_time"] = alt_data["flight_phases"].get("landing_time")
                stats["max_altitude"] = alt_data.get("statistics", {}).get("max")
            
            # Get GPS/position data
            gps_data = analyzer._analyze_gps()
            if gps_data and "position" in gps_data:
                stats["distance_traveled"] = gps_data["position"].get("distance_traveled_km")
                stats["start_location"] = {
                    "lat": gps_data["position"].get("start_lat"),
                    "lon": gps_data["position"].get("start_lon")
                }
                stats["end_location"] = {
                    "lat": gps_data["position"].get("end_lat"),
                    "lon": gps_data["position"].get("end_lon")
                }
            
            # Get speed data
            speed_data = analyzer._analyze_speed()
            if speed_data:
                if "groundspeed" in speed_data:
                    stats["max_groundspeed"] = speed_data["groundspeed"].get("max")
                if "airspeed" in speed_data:
                    stats["max_airspeed"] = speed_data["airspeed"].get("max")
            
            # Get battery data
            battery_data = analyzer._analyze_battery()
            if battery_data:
                if "voltage" in battery_data:
                    stats["battery_voltage_drop"] = battery_data["voltage"].get("drop_percent")
                if "power" in battery_data:
                    stats["energy_consumed_wh"] = battery_data["power"].get("total_energy_wh")
            
            # Get overall performance metrics
            performance = analyzer._calculate_kpis()
            if performance:
                stats["overall_performance_score"] = performance.get("overall_performance")
            
            # Add anomaly count
            anomalies = analyzer._detect_anomalies()
            stats["anomaly_count"] = len(anomalies)
            
            return stats

        # Return all tools
        return [
            get_metrics_for_query,
            detect_anomalies,
            detailed_altitude_analysis,
            detailed_battery_analysis,
            detailed_speed_analysis,
            detailed_gps_analysis,
            detailed_performance_analysis,
            comprehensive_flight_stats
        ]

    def _build_graph(self) -> StateGraph:
        """Build the graph for agent execution flow."""
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("interpret", self._interpret)
        graph.add_node("ask_clarification", self._ask_clarification)
        graph.add_node("run_tools", self._run_tools)
        graph.add_node("reflect", self._reflect)
        graph.add_node("synthesize", self._synthesize)

        # Set entry point
        graph.set_entry_point("interpret")

        # Add edges
        graph.add_conditional_edges(
            "interpret",
            self._branch_after_interpret,
            {
                "ask_clarification": "ask_clarification",
                "run_tools": "run_tools"
            }
        )
        graph.add_edge("ask_clarification", END)
        graph.add_edge("run_tools", "reflect")
        graph.add_conditional_edges(
            "reflect",
            self._branch_after_reflect,
            {
                "synthesize": "synthesize",
                "run_tools": "run_tools"
            }
        )
        graph.add_edge("synthesize", END)

        return graph.compile()

    def _branch_after_interpret(self, state: AgentState) -> str:
        """Determine next step after interpretation."""
        scratch = state.get("scratch", {})
        return "ask_clarification" if scratch.get("clarify") else "run_tools"

    def _branch_after_reflect(self, state: AgentState) -> str:
        """Determine next step after reflection."""
        scratch = state.get("scratch", {})
        current_step = state.get("current_step", 0)
        errors = state.get("errors", [])
        stop = (
            not scratch.get("need_more") or
            current_step >= self.MAX_LOOPS or
            len(errors) >= self.MAX_ERRORS
        )
        return "synthesize" if stop else "run_tools"

    async def _interpret(self, state: AgentState) -> AgentState:
        """Interpret user query and determine needed tools."""
        input_text = state["input"]
        logger.info(f"Interpreting query: {input_text}")
        
        # Add user message to memory with session-specific metadata
        await self.memory_manager.add_message(
            role="user",
            content=input_text,
            metadata={"is_query": True, "session_id": state["session_id"]}
        )
        
        # Invoke interpret LLM
        raw = self.fast_llm.invoke([
            SystemMessage(content=INT_ROUTE_PROMPT),
            HumanMessage(content=input_text)
        ]).content
        
        current_errors = state.get("errors", [])
        try:
            cfg = json.loads(raw)
        except Exception as e:
            logger.error(f"Error parsing interpretation JSON: {str(e)}")
            cfg = {"clarification_needed": "YES", "follow_up": "Could you rephrase your question?", "tools": []}
            current_errors.append(f"route-json-error:{str(e)}")

        # Return only the keys that changed
        updated_scratch = {
            "route_raw": raw,
            "clarify": cfg["clarification_needed"] == "YES",
            "follow_up": cfg.get("follow_up"),
            "pending_tools": cfg.get("tools", []),
        }
        
        logger.info(f"Interpretation result: clarify={updated_scratch['clarify']}, tools={updated_scratch['pending_tools']}")
        
        return_state: AgentState = {"scratch": updated_scratch}
        if current_errors:
            return_state["errors"] = current_errors
        return return_state

    async def _ask_clarification(self, state: AgentState) -> AgentState:
        """Ask for clarification when query is ambiguous."""
        scratch = state.get("scratch", {})
        follow_up = scratch.get("follow_up") or "Could you clarify what you'd like to know about the flight data?"
        logger.info(f"Asking for clarification: {follow_up}")
        
        # Add clarification request to memory with session-specific metadata
        await self.memory_manager.add_message(
            role="assistant",
            content=follow_up,
            metadata={"is_clarification": True, "session_id": state["session_id"]}
        )
        
        return {"answer": follow_up}

    async def _run_tools(self, state: AgentState) -> AgentState:
        """Run selected tools in parallel for efficiency."""
        scratch = state.get("scratch", {})
        pending_tools = scratch.get("pending_tools", [])
        input_text = state["input"]
        current_errors = state.get("errors", [])
        
        logger.info(f"Running tools: {pending_tools}")
        
        tool_results = scratch.get("tool_results", [])
        
        tool_calls = []

        # Prepare tool calls
        for tool_name in pending_tools:
            tool_instance = self.tool_map.get(tool_name)
            if not tool_instance:
                error_msg = f"Unknown tool: {tool_name}"
                logger.error(error_msg)
                current_errors.append(f"unknown_tool: {tool_name}")
                continue
                
            # Determine if tool needs query parameter
            sig = inspect.signature(tool_instance.run)
            kwargs = {"query": input_text} if "query" in sig.parameters else {}
            tool_calls.append({"tool_instance": tool_instance, "kwargs": kwargs, "name": tool_name})

        # Execute tools in parallel
        with ThreadPoolExecutor(max_workers=self.PARALLEL_WORKERS) as executor:
            futures = {
                executor.submit(self._execute_tool, call["tool_instance"], call["kwargs"]): call["name"]
                for call in tool_calls
            }
            
            for future in as_completed(futures):
                tool_name = futures[future]
                try:
                    result = future.result()
                    tool_results.append({tool_name: result})
                    
                    tool_content = json.dumps(result, default=str)
                    logger.debug(f"Tool {tool_name} result: {tool_content[:200]}...")
                    
                    await self.memory_manager.add_message(
                        role="tool",
                        content=tool_content,
                        metadata={
                            "tool": tool_name, 
                            "has_metrics": True, 
                            "session_id": state["session_id"]
                        }
                    )
                    
                except Exception as e:
                    error_msg = f"Tool execution failed: {tool_name} - {str(e)}"
                    logger.error(error_msg)
                    current_errors.append(f"tool_fail: {tool_name}: {str(e)}")

        logger.info(f"Completed running {len(tool_calls)} tools with {len(current_errors) - len(state.get('errors', []))} new errors")
        
        return_state: AgentState = {"scratch": {**scratch, "tool_results": tool_results}}
        if current_errors:
            return_state["errors"] = current_errors
        return return_state
    
    def _execute_tool(self, tool_to_exec: BaseTool, kwargs: Dict[str, Any]) -> Any:
        """Execute a single tool with error handling."""
        try:
            if hasattr(tool_to_exec, 'invoke') and callable(tool_to_exec.invoke):
                 return tool_to_exec.invoke(kwargs) if kwargs else tool_to_exec.invoke()
            elif hasattr(tool_to_exec, 'run') and callable(tool_to_exec.run):
                 return tool_to_exec.run(kwargs) if kwargs else tool_to_exec.run()
            else:
                raise NotImplementedError(f"Tool {tool_to_exec.name} does not have a callable 'invoke' or 'run' method.")

        except Exception as e:
            logger.error(f"Error executing tool {tool_to_exec.name}: {str(e)}")
            raise

    async def _reflect(self, state: AgentState) -> AgentState:
        """Reflect on tool results and determine if more tools are needed."""
        current_step = state.get("current_step", 0)
        input_text = state["input"]
        scratch = state.get("scratch", {})
        current_errors = state.get("errors", [])
        
        logger.info(f"Reflecting on results after step {current_step}")
        
        update_dict: AgentState = {"current_step": current_step + 1}

        try:
            context = await self.memory_manager.get_context(input_text)
            
            messages = [
                SystemMessage(content=REFLECT_PROMPT),
                HumanMessage(content=input_text)
            ]
            
            if context:
                relevant_history = self._extract_relevant_messages(
                    context.get("chat_history", []), 
                    input_text,
                    max_count=3
                )
                if relevant_history: messages.extend(relevant_history)
                
                if context.get("semantic_context"):
                    relevant_context = [
                        item for item in context.get("semantic_context", [])
                        if item.get("metadata", {}).get("session_id") == state["session_id"]
                    ]
                    if relevant_context:
                        relevant_context.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
                        top_context = relevant_context[:3]
                        context_summary = "\n".join([f"- {item.get('role', 'system')}: {item.get('content', '')[:150]}..." for item in top_context])
                        messages.append(SystemMessage(content=f"Relevant context:\n{context_summary}"))
                
                if context.get("query_analysis"):
                    analysis = context.get("query_analysis")
                    if isinstance(analysis, dict):
                        info_types = analysis.get("information_type", [])
                        fields = analysis.get("telemetry_fields", [])
                        if info_types or fields:
                            info_message = "Query analysis: "
                            if info_types: info_message += f"Information needed: {', '.join(info_types)}. "
                            if fields: info_message += f"Relevant telemetry fields: {', '.join(fields)}."
                            messages.append(SystemMessage(content=info_message))
            
            tool_results = scratch.get("tool_results", [])
            if tool_results:
                tool_summary = self._optimize_tool_results(tool_results)
                messages.append(AIMessage(content=f"Tool results:\n{tool_summary}"))
                
            raw = self.fast_llm.invoke(messages).content
            logger.debug(f"Reflection raw output: {raw}")
            
            try:
                info = json.loads(raw)
            except Exception as e:
                logger.error(f"Error parsing reflection JSON: {str(e)}")
                info = {"need_more": False, "next_tools": [], "final": "Unable to process further due to internal error."}
                current_errors.append(f"reflect-json-error:{str(e)}")

            # Update scratch with reflection results
            updated_scratch = {
                **scratch,
                "need_more": info.get("need_more", False),
                "pending_tools": info.get("next_tools", [])
            }
            update_dict["scratch"] = updated_scratch
            
            if not info.get("need_more"):
                update_dict["answer"] = info.get("final")
                
            logger.info(f"Reflection result: need_more={updated_scratch['need_more']}, next_tools={updated_scratch['pending_tools']}")
            
        except Exception as e:
            logger.error(f"Error in reflection step: {str(e)}")
            logger.error(traceback.format_exc())
            
            update_dict["scratch"] = {**scratch, "need_more": False}
            update_dict["answer"] = "I'm unable to process your query due to an internal error. Please try a different question."
            current_errors.append(f"reflect-error:{str(e)}")

        if current_errors:
             update_dict["errors"] = current_errors
        return update_dict

    async def _synthesize(self, state: AgentState) -> AgentState:
        """Synthesize final answer from all tool results."""
        if state.get("answer"):
            logger.info("Using answer from reflection, no synthesis needed.")
            return {}
            
        logger.info("Synthesizing final answer")
        input_text = state["input"]
        scratch = state.get("scratch", {})
        current_errors = state.get("errors", [])
        
        update_dict: AgentState = {}

        try:
            context = await self.memory_manager.get_context(input_text)
            
            messages = [
                SystemMessage(content=SYNTH_PROMPT),
                HumanMessage(content=input_text)
            ]
            
            tool_results = scratch.get("tool_results", [])
            if tool_results:
                tool_json = self._optimize_tool_results(tool_results, include_full_details=True)
                messages.append(SystemMessage(content=f"Tool results:\n{tool_json}"))
            
            if context:
                relevant_history = self._extract_relevant_messages(
                    context.get("chat_history", []),
                    input_text,
                    max_count=3,
                    filter_system=True
                )
                if relevant_history: messages.extend(relevant_history)
                
                if context.get("entity_memory"):
                    entity_data = context.get("entity_memory", {})
                    relevant_entities = []
                    query_terms = input_text.lower().split()
                    for entity, info in entity_data.items():
                        if entity.lower() in input_text.lower() or any(term in entity.lower() for term in query_terms):
                            relevant_entities.append((entity, info))
                    if relevant_entities:
                        entity_summary = "\n".join([f"- {entity}: {info}" for entity, info in relevant_entities[:5]])
                        messages.append(SystemMessage(content=f"Relevant entities:\n{entity_summary}"))
                
                if context.get("semantic_context"):
                    semantic_items = [
                        item for item in context.get("semantic_context", [])
                        if item.get("metadata", {}).get("session_id") == state["session_id"]
                        and item.get("role") in ["assistant", "user", "tool"]
                    ]
                    if semantic_items:
                        semantic_items.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
                        top_items = semantic_items[:2]
                        if top_items:
                            semantic_summary = "\n".join([f"- {item.get('role').title()}: {item.get('content', '')[:100]}..." for item in top_items])
                            messages.append(SystemMessage(content=f"Relevant context:\n{semantic_summary}"))
            
            final_answer = self.smart_llm.invoke(messages).content
            logger.debug(f"Synthesis raw output: {final_answer[:200]}...")
            
            update_dict["answer"] = final_answer
            
            await self.memory_manager.add_message(
                role="assistant",
                content=final_answer,
                metadata={
                    "is_final_answer": True, 
                    "session_id": state["session_id"],
                    "query": input_text,
                    "tool_count": len(tool_results)
                }
            )
            logger.info("Successfully synthesized final answer")
            
        except Exception as e:
            logger.error(f"Error in synthesis step: {str(e)}")
            logger.error(traceback.format_exc())
            update_dict["answer"] = "I'm unable to provide a complete answer due to an internal error. Please try a different question."
            current_errors.append(f"synth-error:{str(e)}")

        if current_errors:
            update_dict["errors"] = current_errors
        return update_dict

    # Add new helper methods for memory optimization

    def _extract_relevant_messages(self, messages: List[Any], query: str, max_count: int = 3, filter_system: bool = False) -> List[Any]:
        """
        Extract the most relevant messages from the provided list based on the query.
        
        Args:
            messages: List of messages to filter
            query: The user query to check relevance against
            max_count: Maximum number of messages to return
            filter_system: Whether to filter out system messages
            
        Returns:
            List of most relevant messages
        """
        if not messages:
            return []
        
        # Filter out system messages if requested
        if filter_system:
            messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]
        
        # Extract query terms for simple relevance matching
        query_terms = set(query.lower().split())
        
        # Assign relevance scores to messages
        scored_messages = []
        for i, msg in enumerate(messages):
            score = 0
            
            # Recent messages get higher base score
            recency_score = (i + 1) / len(messages)
            score += recency_score
            
            # Check content overlap with query terms
            if hasattr(msg, 'content'):
                content = msg.content.lower()
                # Count term overlap
                shared_terms = sum(1 for term in query_terms if term in content)
                score += shared_terms * 0.5
                
                # Boost score for tool messages that might contain relevant data
                if "tool" in content or any(tool_name in content for tool_name in self.tool_map.keys()):
                    score += 1.0
            
            scored_messages.append((msg, score))
        
        # Sort by score (descending) and take top messages
        scored_messages.sort(key=lambda x: x[1], reverse=True)
        
        # Return top messages respecting max_count
        return [msg for msg, _ in scored_messages[:max_count]]

    def _optimize_tool_results(self, tool_results: List[Dict[str, Any]], include_full_details: bool = False) -> str:
        """
        Optimize tool results for token efficiency.
        
        Args:
            tool_results: List of tool result dictionaries
            include_full_details: Whether to include all details (True) or 
                                 create a summary (False)
            
        Returns:
            Optimized JSON string or summary of tool results
        """
        if not tool_results:
            return "No tool results available."
        
        if include_full_details:
            # For full details, just format as JSON with default values
            return json.dumps(tool_results, default=str, indent=2)
        
        # For optimized summary, extract only the most important info
        summaries = []
        
        for result in tool_results:
            for tool_name, tool_output in result.items():
                # Handle common tool outputs differently
                if tool_name == "altitude_details":
                    if isinstance(tool_output, dict) and "statistics" in tool_output:
                        stats = tool_output["statistics"]
                        summary = f"{tool_name}: max={stats.get('max')}m, min={stats.get('min')}m, mean={stats.get('mean')}m"
                        summaries.append(summary)
                    else:
                        summaries.append(f"{tool_name}: {str(tool_output)[:100]}...")
                
                elif tool_name == "battery_details":
                    if isinstance(tool_output, dict):
                        voltage = tool_output.get("voltage", {})
                        summary = f"{tool_name}: initial={voltage.get('initial')}V, final={voltage.get('final')}V"
                        summaries.append(summary)
                    else:
                        summaries.append(f"{tool_name}: {str(tool_output)[:100]}...")
                
                elif tool_name == "metrics":
                    # For metrics, just count how many there are
                    if isinstance(tool_output, dict):
                        metric_count = len(tool_output)
                        top_metrics = list(tool_output.keys())[:3]
                        summary = f"{tool_name}: {metric_count} metrics including {', '.join(top_metrics)}"
                        summaries.append(summary)
                    else:
                        summaries.append(f"{tool_name}: {str(tool_output)[:100]}...")
                
                elif tool_name == "anomalies":
                    # For anomalies, count them
                    if isinstance(tool_output, list):
                        anomaly_count = len(tool_output)
                        summary = f"{tool_name}: {anomaly_count} anomalies detected"
                        summaries.append(summary)
                    else:
                        summaries.append(f"{tool_name}: {str(tool_output)[:100]}...")
                
                else:
                    # For other tools, provide a brief summary
                    summary = f"{tool_name}: {str(tool_output)[:150]}..."
                    summaries.append(summary)
        
        return "\n".join(summaries)

    async def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process a message asynchronously and return detailed results.
        
        Args:
            message: The user's message/query
            
        Returns:
            Dictionary with answer and analysis data
        """
        logger.info(f"Processing message asynchronously: {message[:50]}...")
        
        try:
            # Create initial state as a dict, following the AgentState TypedDict structure
            initial_state: AgentState = {
                "input": message, 
                "session_id": self.session_id,
                "scratch": {},       # Initialize scratch as an empty dict
                "current_step": 0,
                "errors": [],        # Initialize errors as an empty list
                "answer": None       # Initialize answer as None
            }
            
            # Invoke the graph with the dictionary state
            # The graph.compile() should handle the rest if nodes are set up for dicts
            final_graph_state: AgentState = await self.graph.ainvoke(initial_state) # final_graph_state will be a dict
            
            answer = final_graph_state.get("answer", "I don't have enough data to answer that question based on the available telemetry.")
            
            # Extract any analysis results from tool execution
            analysis = {}
            final_scratch = final_graph_state.get("scratch", {})
            tool_results = final_scratch.get("tool_results", [])

            for tool_result_item in tool_results: # Renamed to avoid conflict
                if "altitude_details" in tool_result_item:
                    analysis["altitude_analysis"] = tool_result_item["altitude_details"]
                elif "battery_details" in tool_result_item:
                    analysis["battery_analysis"] = tool_result_item["battery_details"]
                elif "speed_details" in tool_result_item:
                    analysis["speed_analysis"] = tool_result_item["speed_details"]
                elif "gps_details" in tool_result_item:
                    analysis["gps_analysis"] = tool_result_item["gps_details"]
                elif "metrics" in tool_result_item:
                    analysis["metrics"] = tool_result_item["metrics"]
                elif "anomalies" in tool_result_item:
                    analysis["anomalies"] = tool_result_item["anomalies"]
                elif "performance_details" in tool_result_item:
                    analysis["performance"] = tool_result_item["performance_details"]
                elif "flight_statistics" in tool_result_item:
                    analysis["flight_stats"] = tool_result_item["flight_statistics"]
            
            # Return combined result
            return {
                "answer": answer,
                "analysis": analysis,
                "session_id": self.session_id
            }
        except Exception as e:
            logger.error(f"Error in process_message: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "error": str(e),
                "answer": "Sorry, I encountered an error while processing your request.",
                "session_id": self.session_id
            }
            
    def clear_memory(self):
        """Clear the agent's memory."""
        logger.info(f"Clearing memory for session {self.session_id}")
        self.memory_manager.clear()
