from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from chat.memory_manager import EnhancedMemoryManager
from telemetry.analyzer import TelemetryAnalyzer
import os
from dotenv import load_dotenv
import json
import pandas as pd
import asyncio
import numpy as np

# Load environment variables
load_dotenv()

class FlightAgent:
    """Agent for analyzing flight data using ReAct reasoning framework."""
    
    def __init__(
        self,
        session_id: str,
        telemetry_data: Dict,
        analyzer: TelemetryAnalyzer,
        db_session=None,  # Kept for backward compatibility but not used
        memory_window_size: int = 10
    ):
        self.session_id = session_id
        self.telemetry_data = telemetry_data
        self.analyzer = analyzer
        
        # Initialize memory manager with configurable window size
        self.memory_manager = EnhancedMemoryManager(
            session_id=session_id,
            db_session=db_session,
            window_size=memory_window_size
        )
        
        # Initialize chat model with GPT-4o
        self.chat = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            max_retries=2,
            request_timeout=30  # 30 seconds timeout to avoid hanging
        )
        
        # Advanced ReAct system prompt with examples
        self.system_prompt = SystemMessagePromptTemplate.from_template("""
You are **MAVLink Analyst**, an agentic UAV-flight-data assistant.

# CAPABILITIES
- Analyze flight telemetry data (altitude, position, battery, motor temperatures, etc.)
- Detect and explain anomalies in flight behavior
- Calculate flight metrics and statistics
- Recall past conversations and previous analysis

# AVAILABLE TOOLS
- get_flight_metrics: Retrieve specific flight metrics
- detect_anomalies: Find anomalies in specific parameters
- analyze_time_range: Analyze data within specific time periods

# REASONING FRAMEWORK
For each query, follow this ReAct (Reasoning + Action) framework:

1. THOUGHT: Reason step-by-step about the query. What is the user asking? What information is needed?
2. ACTION: Select an appropriate tool to gather needed information. Only use tools when necessary.
3. OBSERVATION: Review and analyze the results from the tool.
4. THOUGHT: Process the observations and determine if additional actions are needed.
5. ANSWER: Provide a detailed response based on all gathered information.

---

## EXAMPLES

### Example 1: Highest altitude
Question: What was the highest altitude reached during the flight?

THOUGHT: The user wants to know the maximum altitude reached during the flight. I need to retrieve altitude metrics from the telemetry data.

ACTION: get_flight_metrics {"metric":"max_altitude","detailed":true}

OBSERVATION: Maximum altitude: 127.5 meters, reached at timestamp 1234.56

THOUGHT: I now have the maximum altitude value and when it was reached. This fully answers the query.

ANSWER: The highest altitude reached during this flight was 127.5 meters, which occurred at timestamp 1234.56.

### Example 2: GPS Signal Loss
Question: When did the GPS signal first get lost?

THOUGHT: The user wants to know about the first instance of GPS signal loss. This would be classified as a GPS anomaly in the telemetry data.

ACTION: detect_anomalies {"parameter":"gps"}

OBSERVATION: Detected 2 anomalies for 'gps':
1. Type: gps_anomaly, Severity: 2.4, Timestamp: 857.42
   Metrics: {"duration": 1.8, "altitude": 78.3, "velocity": 15.6}
2. Type: gps_anomaly, Severity: 1.9, Timestamp: 1730.18
   Metrics: {"duration": 1.2, "altitude": 92.1, "velocity": 12.3}

THOUGHT: The observation shows two GPS anomalies. The first one occurred at timestamp 857.42 with a duration of 1.8 seconds.

ANSWER: The GPS signal was first lost at timestamp 857.42 for approximately 1.8 seconds during flight. This was classified as a high-severity anomaly (2.4/3.0) and occurred while the drone was at 78.3 meters altitude.

### Example 3: Flight Duration
Question: How long was the total flight time?

THOUGHT: The user wants to know the total duration of the flight. This is a basic flight metric that can be directly retrieved.

ACTION: get_flight_metrics {"metric":"flight_time"}

OBSERVATION: Flight time: 11 min 32 s

THOUGHT: The observation provides the total flight time of 11 minutes and 32 seconds. This straightforward metric fully answers the query.

ANSWER: The total flight time was 11 minutes and 32 seconds from takeoff to landing.

### Example 4: Critical Errors
Question: List all critical errors that happened mid-flight.

THOUGHT: The user wants to know about critical errors during the flight, particularly in the middle section. I should run a comprehensive anomaly scan and identify all critical issues.

ACTION: detect_anomalies {"parameter":"all"}

OBSERVATION: Detected 5 anomalies for 'all':
1. Type: gps_anomaly, Severity: 2.4, Timestamp: 612.3
   Metrics: {"duration": 3.2, "altitude": 82.1}
2. Type: rc_signal_loss, Severity: 2.8, Timestamp: 895.7
   Metrics: {"duration": 0.8, "altitude": 95.2}
3. Type: ekf_error, Severity: 2.6, Timestamp: 1421.3
   Metrics: {"error_type": "EKF_YAW_ERR", "altitude": 105.8}
4. Type: battery_anomaly, Severity: 2.2, Timestamp: 2345.6
   Metrics: {"voltage_drop": 0.8, "altitude": 62.4}
5. Type: gps_anomaly, Severity: 1.9, Timestamp: 2687.2
   Metrics: {"duration": 1.1, "altitude": 43.2}

THOUGHT: I need to filter these anomalies to identify the ones that occurred mid-flight. Since there were 5 anomalies in total, I can consider the ones between roughly 25% and 75% of the flight time as "mid-flight". Based on the timestamps, anomalies 1, 2, and 3 appear to be in the mid-flight range.

ANSWER: Three critical errors occurred during the mid-flight phase:
1. GPS failure at timestamp 612.3 (severity 2.4/3.0) lasting 3.2 seconds
2. RC signal loss at timestamp 895.7 (severity 2.8/3.0) lasting 0.8 seconds
3. EKF yaw error at timestamp 1421.3 (severity 2.6/3.0)

These represent significant control and navigation issues that occurred during the main operational phase of the flight.

### Example 5: GPS Investigation
Question: Can you spot any issues in the GPS data?

THOUGHT: The user wants a detailed analysis of potential GPS issues. I should first check for GPS-specific anomalies.

ACTION: detect_anomalies {"parameter":"gps"}

OBSERVATION: Detected 2 anomalies for 'gps':
1. Type: gps_anomaly, Severity: 2.4, Timestamp: 857.42
   Metrics: {"duration": 1.8, "altitude": 78.3, "velocity": 15.6, "bank_angle": 22.5}
2. Type: gps_anomaly, Severity: 1.9, Timestamp: 1730.18
   Metrics: {"duration": 1.2, "altitude": 92.1, "velocity": 12.3, "bank_angle": 18.7}

THOUGHT: I've found two GPS anomalies. To understand if there's a pattern, I should also look at the vehicle's movement during these times.

ACTION: analyze_time_range {"start_time":"857","end_time":"859","parameter":"velocity"}

OBSERVATION: Velocity analysis from 857.0 to 859.0:
- Maximum: 17.2 m/s at timestamp 857.8
- Minimum: 13.4 m/s at timestamp 858.5
- Average: 15.3 m/s
- Total change: -0.6 m/s

THOUGHT: The GPS issues appear to correlate with high velocity and significant bank angles. The first GPS anomaly occurred when the drone was banking at 22.5 degrees with a velocity of around 15.6 m/s. This pattern suggests the GPS issues might be related to the drone's orientation during turns.

ANSWER: I've identified two significant GPS issues in the flight data:

1. First GPS anomaly at timestamp 857.42:
   - Signal loss duration: 1.8 seconds
   - Occurred during high-speed maneuver (15.6 m/s)
   - Bank angle was steep (22.5°)

2. Second GPS anomaly at timestamp 1730.18:
   - Signal loss duration: 1.2 seconds 
   - Also during moderate banking (18.7°)

The pattern suggests these GPS issues are likely caused by antenna shadowing during banking maneuvers, where the drone's body blocks satellite signals. This is a common phenomenon during aggressive turns at high speed.

# IMPORTANT GUIDELINES

1. Always think carefully about what tools are needed. Don't use tools when the query can be answered from conversation context.
2. Be specific with numbers, timestamps, and technical details.
3. When analyzing anomalies, explain their potential causes and implications.
4. For complex queries, break down your analysis into clear sections.
5. When analyzing performance, consider correlations between different parameters.
6. Proactively surface risky anomalies even if unasked.
""")
        
        # Enhanced ReAct human prompt template for structured reasoning
        self.human_prompt = HumanMessagePromptTemplate.from_template("""
USER QUERY: {input}

THOUGHT: 
{query_reasoning}

ACTION: 
Let me analyze the flight data based on this query.

OBSERVATION: 
[Flight Analysis]
{flight_analysis}

[Memory Context]
{memory_recall}

THOUGHT: 
Based on my analysis of the flight data and context from memory, I can now provide a detailed answer.

ANSWER: 
""")
        
        # Combine templates into the full prompt
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(
                "You are a specialized AI assistant for UAV flight data analysis. "
                "Your goal is to provide accurate, concise insights about flight performance, "
                "anomalies, and metrics. Use all available data and reasoning to give the best analysis. "
                "Structure responses as:\n"
                "- **Flight Analysis**: [Key observations about the flight]\n"
                "- **Performance Metrics**: [Relevant metrics with values]\n"
                "- **Insights**: [Deeper analysis and recommendations]\n"
                "Current flight data summary:\n"
                "- Duration: {flight_duration}\n"
                "- Time range: {time_range}\n"
                "- Key metrics: {key_metrics}\n"
                "- Anomalies: {anomalies}\n"
                "IMPORTANT: Always include ALL available altitude metrics (max, min, mean) in your response.\n"
                "Use this data in your analysis."
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template("{input}"),
        ])

    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message with enhanced ReAct framework."""
        try:
            print(f"Starting to process message: {message}")
            
            # Set a timeout for the whole process to prevent hanging
            async def process_with_timeout():
                # Get comprehensive context using memory manager
                print("Fetching context from memory manager...")
                try:
                    context = await asyncio.wait_for(
                        self.memory_manager.get_context(message),
                        timeout=10.0  # 10 seconds timeout for context retrieval
                    )
                    print("Context retrieved successfully")
                except asyncio.TimeoutError:
                    print("ERROR: Context retrieval timed out")
                    # If we can't get context, we should fail explicitly rather than continuing with a poor experience
                    raise
                except Exception as ctx_err:
                    print(f"ERROR retrieving context: {str(ctx_err)}")
                    import traceback
                    print(f"CONTEXT ERROR TRACEBACK: {traceback.format_exc()}")
                    # If context retrieval fails for any reason, we should propagate the error
                    raise
                
                # Extract query reasoning
                query_reasoning = context.get("query_reasoning", "No specific reasoning available.")
                print(f"Query reasoning: {query_reasoning[:100]}...")
                
                # Perform flight analysis with timeout protection
                print("Performing flight analysis...")
                try:
                    flight_analysis = await asyncio.wait_for(
                        self._perform_flight_analysis(message, query_reasoning),
                        timeout=15.0  # 15 seconds timeout for flight analysis
                    )
                    print("Flight analysis completed")
                except asyncio.TimeoutError:
                    print("ERROR: Flight analysis timed out")
                    # If analysis times out, propagate the error
                    raise
                except Exception as analysis_err:
                    print(f"ERROR in flight analysis: {str(analysis_err)}")
                    import traceback
                    print(f"FLIGHT ANALYSIS ERROR TRACEBACK: {traceback.format_exc()}")
                    # If analysis fails for any reason, propagate the error
                    raise
                
                # Prepare analysis_data for the API JSON response
                analysis_data_for_api = {
                    "type": "Flight Analysis",
                    "metrics": {},
                    "anomalies": "No anomaly data processed"
                }

                # Populate metrics and anomalies only if we have valid data
                if flight_analysis and isinstance(flight_analysis, dict):
                    filtered_metrics = flight_analysis.get("metrics", {})
                    if "overview" in filtered_metrics:
                        all_calculated_metrics = self.analyzer.cache.get("metrics")
                        analysis_data_for_api["metrics"] = all_calculated_metrics if all_calculated_metrics else {"info": "No metrics calculated or available in cache."}
                    else:
                        analysis_data_for_api["metrics"] = filtered_metrics if filtered_metrics else {"info": "No specific metrics found for the query."}

                    # Populate anomalies for API response
                    all_detected_anomalies = self.analyzer.cache.get("anomalies")
                    if isinstance(all_detected_anomalies, list):
                        if all_detected_anomalies:
                            analysis_data_for_api["anomalies"] = f"Detected {len(all_detected_anomalies)} anomalies."
                        else:
                            analysis_data_for_api["anomalies"] = "No anomalies detected in the flight log."
                    else:
                        analysis_data_for_api["anomalies"] = "Anomaly detection data not available or not processed."
                
                # Process memory recall with proper error handling
                print("Processing memory recall...")
                memory_recall = ""
                try:
                    memory_recall = self._process_memory_recall(context)
                    print("Memory recall processed")
                except Exception as mem_err:
                    print(f"ERROR processing memory recall: {str(mem_err)}")
                    import traceback
                    print(f"MEMORY RECALL ERROR TRACEBACK: {traceback.format_exc()}")
                    # If memory recall fails, continue with empty recall
                    memory_recall = ""
                
                # Format chat history from the summary buffer memory
                chat_history = context.get("chat_history", [])
                print(f"Retrieved {len(chat_history)} chat history items")
                
                # Generate response using ChatOpenAI with timeout protection
                print("Generating response using chat model...")
                
                # Build flight data summary for the prompt
                flight_data_for_prompt = self._build_flight_data_summary()
            
                # Format messages for the model
                messages = self.prompt.format_messages(
                    input=message,
                    flight_duration=flight_data_for_prompt["duration"],
                    time_range=flight_data_for_prompt["time_range"],
                    key_metrics=flight_data_for_prompt["key_metrics"],
                    anomalies=flight_data_for_prompt["anomalies"],
                    chat_history=chat_history
                )
                
                print(f"Formatted {len(messages)} messages for the prompt")
                
                # Call the model with timeout and error handling
                print("Invoking chat model...")
                try:
                    response = await asyncio.wait_for(
                        self._async_chat_invoke(messages),
                        timeout=30.0  # 30 seconds timeout
                    )
                    response_content = response.content
                    print("Response generated successfully")
                except (asyncio.TimeoutError, Exception) as model_err:
                    print(f"ERROR in chat model: {str(model_err)}")
                    import traceback
                    print(f"CHAT MODEL ERROR TRACEBACK: {traceback.format_exc()}")
                    # Attempt a simpler fallback only if the primary model call fails
                    try:
                        print("Attempting fallback with simpler prompt...")
                        fallback_prompt = ChatPromptTemplate.from_messages([
                            SystemMessagePromptTemplate.from_template("You are a UAV flight data analyst. Answer the query concisely based on available data."),
                            HumanMessagePromptTemplate.from_template("{input}")
                        ])
                        
                        fallback_messages = fallback_prompt.format_messages(input=message)
                        fallback_response = await asyncio.wait_for(
                            self._async_chat_invoke(fallback_messages),
                            timeout=15.0
                        )
                        response_content = fallback_response.content
                        print("Fallback prompt succeeded")
                    except Exception as fallback_err:
                        print(f"ERROR in fallback prompt: {str(fallback_err)}")
                        import traceback
                        print(f"FALLBACK ERROR TRACEBACK: {traceback.format_exc()}")
                        # If even the fallback fails, propagate the error
                        raise
                
                # Store messages in memory - this is optional so we can use fire-and-forget
                metadata = self._extract_metadata_from_reasoning(query_reasoning)
                
                # Store user message asynchronously
                try:
                    asyncio.create_task(self.memory_manager.add_message(
                        role="user",
                        content=message,
                        metadata=metadata
                    ))
                except Exception as msg_err:
                    # Just log errors in message storage, don't fail the request
                    print(f"ERROR storing user message: {str(msg_err)}")
                
                # Store assistant response asynchronously
                try:
                    asyncio.create_task(self.memory_manager.add_message(
                        role="assistant",
                        content=response_content,
                        metadata={
                            **metadata,
                            "analysis_performed": True,
                            "flight_data_analyzed": flight_analysis is not None
                        }
                    ))
                except Exception as resp_err:
                    # Just log errors in response storage, don't fail the request
                    print(f"ERROR storing assistant response: {str(resp_err)}")
                
                return {
                    "answer": response_content,
                    "analysis": analysis_data_for_api,
                    "reasoning": query_reasoning
                }
            
            # Execute the process with overall timeout
            return await asyncio.wait_for(process_with_timeout(), timeout=60.0)  # 60 seconds total timeout
            
        except asyncio.TimeoutError:
            error_msg = "The operation timed out. Please try again with a simpler query."
            print(f"ERROR: Process message timed out after 60 seconds")
            # Return a proper error response that will be handled by the API endpoint
            return {
                "answer": "I apologize, but your query timed out. Please try again with a more specific question.",
                "analysis": {"metrics": {"error": "Analysis timed out."}, "anomalies": "Analysis timed out."},
                "error": error_msg
            }
        except Exception as e:
            # Enhanced error handling with detailed logs
            error_msg = f"Error processing message: {str(e)}"
            print(f"ERROR IN PROCESS_MESSAGE: {error_msg}")
            import traceback
            print(f"PROCESS MESSAGE ERROR TRACEBACK: {traceback.format_exc()}")
            
            # Return a proper error response that will be handled by the API endpoint
            return {
                "answer": "I encountered an error while analyzing the flight data. Please try again with a different question.",
                "analysis": {"metrics": {"error": str(e)}, "anomalies": "Error during analysis."},
                "error": error_msg
            }
    
    async def _async_chat_invoke(self, messages):
        """Async wrapper for chat model invocation."""
        return self.chat.invoke(messages)
    
    def _build_flight_data_summary(self) -> Dict[str, str]:
        """Build a flight data summary for the prompt with error handling."""
        flight_data_for_prompt = {
            "duration": "N/A",
            "time_range": "N/A",
            "key_metrics": "No specific metrics available from the log.",
            "anomalies": "Anomaly detection data not available or no anomalies found."
        }

        try:
            # Estimate duration and time_range from timestamps if available
            if hasattr(self.analyzer, 'time_series') and self.analyzer.time_series.get("timestamp"):
                timestamps = self.analyzer.time_series["timestamp"]
                if len(timestamps) > 1:
                    ts_start = pd.to_datetime(timestamps[0])
                    ts_end = pd.to_datetime(timestamps[-1])
                    duration_seconds = (ts_end - ts_start).total_seconds()
                    flight_data_for_prompt["duration"] = f"{duration_seconds/60:.1f} minutes"
                    flight_data_for_prompt["time_range"] = f"From {ts_start.strftime('%Y-%m-%d %H:%M:%S')} to {ts_end.strftime('%Y-%m-%d %H:%M:%S')}"
                elif len(timestamps) == 1:
                    flight_data_for_prompt["duration"] = "Single data point, duration not applicable."
                    flight_data_for_prompt["time_range"] = f"At {pd.to_datetime(timestamps[0]).strftime('%Y-%m-%d %H:%M:%S')}"

            # Build metrics summary with accurate altitude data
            try:
                temp_metrics_parts = []
                
                # CRITICAL FIX: Get altitude data directly from reliable _analyze_altitude method
                alt_analysis = self.analyzer._analyze_altitude()
                if alt_analysis and "statistics" in alt_analysis:
                    max_alt = alt_analysis["statistics"].get("max")
                    min_alt = alt_analysis["statistics"].get("min")
                    mean_alt = alt_analysis["statistics"].get("mean")
                    field_used = alt_analysis.get("field_used", "unknown")
                    
                    # Ensure reasonable values only
                    if max_alt is not None and isinstance(max_alt, (int, float)) and max_alt < 100000:
                        # Convert to meters if in millimeters (common in some MAVLink messages)
                        if max_alt > 10000 and "relative_alt" in field_used:
                            max_alt = max_alt / 1000.0  # Convert mm to meters
                        temp_metrics_parts.append(f"Max Altitude: {max_alt:.1f} m")
                    
                    if min_alt is not None and isinstance(min_alt, (int, float)) and abs(min_alt) < 100000:
                        # Convert to meters if in millimeters
                        if abs(min_alt) > 10000 and "relative_alt" in field_used:
                            min_alt = min_alt / 1000.0  # Convert mm to meters
                        temp_metrics_parts.append(f"Min Altitude: {min_alt:.1f} m")
                    
                    if mean_alt is not None and isinstance(mean_alt, (int, float)) and mean_alt < 100000:
                        # Convert to meters if in millimeters
                        if mean_alt > 10000 and "relative_alt" in field_used:
                            mean_alt = mean_alt / 1000.0  # Convert mm to meters
                        temp_metrics_parts.append(f"Avg Altitude: {mean_alt:.1f} m")
                
                # Process other important metrics
                # Look for velocity-related fields
                flight_metrics = self.analyzer.cache.get("metrics", {})
                
                # Find velocity data
                vfr_hud_speed = None
                for field_name in flight_metrics:
                    if "groundspeed" in field_name.lower():
                        if isinstance(flight_metrics[field_name], dict):
                            speed_data = flight_metrics[field_name]
                            max_vel = speed_data.get('max')
                            mean_vel = speed_data.get('mean')
                            if max_vel is not None: temp_metrics_parts.append(f"Max Speed: {max_vel:.1f} m/s")
                            if mean_vel is not None: temp_metrics_parts.append(f"Avg Speed: {mean_vel:.1f} m/s")
                            vfr_hud_speed = True
                            break
                
                # Find battery-related fields if not already found
                battery_field = None
                for field_name in flight_metrics:
                    if any(kw in field_name.lower() for kw in ["battery_remaining", "voltage_battery", "bat_volt"]):
                        battery_field = field_name
                        if isinstance(flight_metrics[battery_field], dict):
                            bat_data = flight_metrics[battery_field]
                            if 'max' in bat_data: temp_metrics_parts.append(f"Battery Level: {bat_data['max']:.0f}%")
                            break
                            
                if temp_metrics_parts:
                    flight_data_for_prompt["key_metrics"] = "; ".join(temp_metrics_parts)
                else:
                    flight_data_for_prompt["key_metrics"] = "General metrics calculated but not itemized here."
                
            except Exception as metrics_err:
                print(f"Error getting metrics summary: {str(metrics_err)}")
                import traceback
                print(f"METRICS SUMMARY ERROR: {traceback.format_exc()}")
                flight_data_for_prompt["key_metrics"] = "Error retrieving metrics."
            
            # Try to add anomaly info if available
            try:
                anomalies_list = self.analyzer.cache.get("anomalies")
                if not anomalies_list:
                    anomalies_list = self.analyzer._detect_anomalies()
                    
                if anomalies_list:
                    flight_data_for_prompt["anomalies"] = f"Detected {len(anomalies_list)} anomalies. Example: {anomalies_list[0]['type']} at {anomalies_list[0]['timestamp']}"
                else:
                    flight_data_for_prompt["anomalies"] = "No anomalies detected during the flight."
            except Exception as anomaly_err:
                print(f"Error getting anomaly summary: {str(anomaly_err)}")
                flight_data_for_prompt["anomalies"] = "Error retrieving anomalies."
                
        except Exception as e:
            print(f"Error building flight data summary: {str(e)}")
            import traceback
            print(f"FLIGHT DATA SUMMARY ERROR: {traceback.format_exc()}")
            # Return default values if error
            
        return flight_data_for_prompt
    
    async def _perform_flight_analysis(self, query: str, reasoning: str) -> Dict[str, Any]:
        """Perform targeted flight data analysis based on query and reasoning."""
        try:
            # Set up a task with timeout to prevent hanging
            analyze_task = asyncio.create_task(self._async_analyze_for_query(query))
            
            try:
                # Use a strict timeout to ensure we don't hang
                analyzer_result = await asyncio.wait_for(analyze_task, timeout=10.0)
            except asyncio.TimeoutError:
                print("TelemetryAnalyzer: Analysis for query timed out, using limited analysis")
                # Perform limited analysis with fewer fields
                analyzer_result = self._limited_analyze_for_query(query)
            
            # Format analysis result as a structured dictionary
            result = {
                "metrics": analyzer_result.get("metrics", {}),
                "anomalies": analyzer_result.get("anomalies", []),
                "kpis": analyzer_result.get("kpis", {})
            }
            
            # Add specific analysis based on query content
            if "altitude" in query.lower() or "altitude" in reasoning.lower():
                # For altitude queries, ensure we're using proper altitude fields
                altitude_analysis = analyzer_result.get("altitude_analysis", {})
                if altitude_analysis and "statistics" in altitude_analysis:
                    result["metrics"]["altitude"] = altitude_analysis["statistics"]
                    
                    # Add field used information if available
                    if "field_used" in altitude_analysis:
                        result["metrics"]["altitude"]["field_used"] = altitude_analysis["field_used"]
                    
                    # Remove any potentially unreasonable altitude values
                    for key in ["max", "min", "mean"]:
                        if key in result["metrics"]["altitude"] and result["metrics"]["altitude"][key] > 1000000:
                            print(f"TelemetryAnalyzer: Removing unreasonable {key} altitude value: {result['metrics']['altitude'][key]}")
                            result["metrics"]["altitude"][key] = "N/A (unreasonable value)"
            
            if "battery" in query.lower() or "battery" in reasoning.lower():
                battery_analysis = analyzer_result.get("battery_analysis", {})
                if battery_analysis:
                    result["metrics"]["battery"] = battery_analysis
            
            if "performance" in query.lower() or "performance" in reasoning.lower():
                performance_analysis = analyzer_result.get("performance_analysis", {})
                if performance_analysis:
                    result["metrics"]["performance"] = performance_analysis
            
            return result
        
        except Exception as e:
            print(f"Error in _perform_flight_analysis: {str(e)}")
            import traceback
            print(f"TRACEBACK: {traceback.format_exc()}")
            
            # Return a minimal result that won't cause formatting issues
            return {
                "metrics": {"error": f"Could not analyze flight data: {str(e)}"},
                "anomalies": [],
                "kpis": {}
            }
    
    async def _async_analyze_for_query(self, query: str) -> Dict[str, Any]:
        """Async wrapper for analyzer's analyze_for_query to allow timeout management."""
        # The new analyzer may not have analyze_for_query method, so implement it here
        try:
            # Update cache if needed - safely check for existence using .get()
            if not self.analyzer.cache.get("metrics"):
                metrics = self._calculate_basic_metrics()
                self.analyzer.cache["metrics"] = metrics
            
            if not self.analyzer.cache.get("anomalies"):
                anomalies = self.analyzer._detect_anomalies()
                self.analyzer.cache["anomalies"] = anomalies
            
            # Extract relevant data for the query
            relevant_data = {
                "metrics": self._filter_relevant_metrics(query),
                "anomalies": self._filter_relevant_anomalies(query),
                "kpis": self.analyzer.cache.get("kpis", {})  # Safely access KPIs with default
            }
            
            # Add query-specific analysis
            if "altitude" in query.lower() or "height" in query.lower():
                alt_analysis = self.analyzer._analyze_altitude()
                if alt_analysis:
                    relevant_data["altitude_analysis"] = alt_analysis
            
            if "battery" in query.lower() or "power" in query.lower():
                bat_analysis = self._analyze_battery(query)
                if bat_analysis:
                    relevant_data["battery_analysis"] = bat_analysis
            
            # Add other analyses if implemented in TelemetryAnalyzer
            try:
                # Try accessing additional analysis methods if they exist
                if hasattr(self.analyzer, '_analyze_speed') and 'speed' in query.lower():
                    speed_analysis = self.analyzer._analyze_speed()
                    if speed_analysis:
                        relevant_data["speed_analysis"] = speed_analysis
                    
                if hasattr(self.analyzer, '_analyze_gps') and any(term in query.lower() for term in ['gps', 'satellite']):
                    gps_analysis = self.analyzer._analyze_gps()
                    if gps_analysis:
                        relevant_data["gps_analysis"] = gps_analysis
            except Exception as additional_err:
                print(f"Note: Additional analysis methods failed: {str(additional_err)}")
                # Non-critical, continue with what we have
            
            return relevant_data
        except Exception as e:
            print(f"Error in _async_analyze_for_query: {str(e)}")
            import traceback
            print(f"ANALYZE QUERY ERROR: {traceback.format_exc()}")
            return {
                "error": f"Error analyzing flight data: {str(e)}",
                "metrics": {"info": "Analysis incomplete due to error."},
                "anomalies": []
            }

    def _calculate_basic_metrics(self) -> Dict[str, Any]:
        """Calculate basic flight metrics from time series data."""
        metrics = {}
        
        try:
            ts = self.analyzer.time_series
            if not ts or "timestamp" not in ts or not ts["timestamp"]:
                print("WARNING: Empty time series or missing timestamp field")
                return metrics
            
            # Get all non-timestamp keys
            potential_fields = [k for k in ts.keys() if k != 'timestamp']
            if not potential_fields:
                print("WARNING: No data fields found in time series")
                return metrics
            
            print(f"Calculating metrics for {len(potential_fields)} potential fields")
            
            for field_name in potential_fields:
                data_list = ts.get(field_name)
                if not isinstance(data_list, list) or not data_list:
                    continue
                
                # Convert to numpy array for faster calculations and filter valid values
                try:
                    valid_data = np.array([x for x in data_list if pd.notnull(x) and isinstance(x, (int, float))])
                    if valid_data.size == 0:
                        continue
                    
                    # Calculate basic statistics
                    metrics[field_name] = {
                        "mean": float(np.mean(valid_data)),
                        "min": float(np.min(valid_data)),
                        "max": float(np.max(valid_data)),
                        "std": float(np.std(valid_data)),
                        "count": len(valid_data),
                        "variance": float(np.var(valid_data))
                    }
                except Exception as field_err:
                    print(f"Error calculating metrics for field {field_name}: {str(field_err)}")
                    continue
            
            # Calculate altitude metrics separately for fields that match altitude patterns
            alt_fields = []
            for field_name in metrics:
                if any(pattern in field_name.lower() for pattern in ["alt", "height", "terrain"]):
                    alt_fields.append(field_name)
                    
            if alt_fields:
                # Create a dedicated altitude field in metrics if it doesn't exist yet
                if "altitude" not in metrics:
                    # Find the best altitude field based on known reliable fields
                    best_alt_field = None
                    for priority_field in ["GLOBAL_POSITION_INT_relative_alt", "VFR_HUD_alt", "TERRAIN_REPORT_current_height"]:
                        if priority_field in alt_fields:
                            best_alt_field = priority_field
                            break
                    
                    # If no priority field found, use the first one
                    if not best_alt_field and alt_fields:
                        best_alt_field = alt_fields[0]
                    
                    if best_alt_field:
                        alt_values = np.array(ts[best_alt_field])
                        # Convert from mm to m if it's a relative_alt field
                        if "relative_alt" in best_alt_field and np.max(alt_values) > 1000:
                            alt_values = alt_values / 1000.0
                            
                        metrics["altitude"] = {
                            "mean": float(np.mean(alt_values)),
                            "min": float(np.min(alt_values)),
                            "max": float(np.max(alt_values)),
                            "std": float(np.std(alt_values)),
                            "count": len(alt_values),
                            "field_used": best_alt_field
                        }
            
            print(f"FlightAgent: Calculated metrics for {len(metrics)} fields")
            return metrics
        except Exception as e:
            print(f"Error in _calculate_basic_metrics: {str(e)}")
            import traceback
            print(f"METRICS CALCULATION ERROR: {traceback.format_exc()}")
            return metrics  # Return empty dict

    def _filter_relevant_metrics(self, query: str) -> Dict[str, Any]:
        """Filter metrics relevant to the query from the analyzer's cache."""
        metrics = self.analyzer.cache.get("metrics", {})
        if not metrics:
            return {}
        
        query_lower = query.lower()
        relevant_metrics = {}
        
        # First, check for specific keywords in query
        important_keywords = ["altitude", "height", "speed", "velocity", "battery", 
                             "voltage", "current", "gps", "position", "attitude",
                             "roll", "pitch", "yaw"]
        
        for keyword in important_keywords:
            if keyword in query_lower:
                for field_name, stats in metrics.items():
                    if keyword in field_name.lower():
                        relevant_metrics[field_name] = stats
        
        # If no specific matches, provide a subset of common metrics
        if not relevant_metrics:
            # Find common field types (altitude, speed, battery)
            for field_type in ["alt", "speed", "groundspeed", "battery", "voltage"]:
                for field_name, stats in metrics.items():
                    if field_type in field_name.lower() and field_name not in relevant_metrics:
                        relevant_metrics[field_name] = stats
                        # Limit to 1 field per type to avoid overwhelming
                        break
        
        return relevant_metrics

    def _filter_relevant_anomalies(self, query: str) -> List[Dict[str, Any]]:
        """Filter anomalies relevant to the query from the analyzer's cache."""
        anomalies = self.analyzer.cache.get("anomalies", [])
        if not anomalies:
            return []
        
        query_lower = query.lower()
        
        # If query is about anomalies or issues generally, return all (up to a limit)
        if any(term in query_lower for term in ["anomaly", "issue", "problem", "error"]):
            # Limit to 20 anomalies to avoid overwhelming
            return sorted(anomalies[:20], key=lambda x: x.get("severity", 0), reverse=True)
        
        # Otherwise filter by relevance to query
        filtered_anomalies = []
        for anomaly in anomalies:
            # Check if any of the metrics in the anomaly match keywords in the query
            metrics = anomaly.get("metrics", {})
            for metric_name in metrics.keys():
                if any(part in metric_name.lower() for part in query_lower.split()):
                    filtered_anomalies.append(anomaly)
                    break
        
        # Limit results and sort by severity
        return sorted(filtered_anomalies[:10], key=lambda x: x.get("severity", 0), reverse=True)

    def _analyze_battery(self, query: str) -> Dict[str, Any]:
        """Analyze battery data for a specific query."""
        ts = self.analyzer.time_series
        
        # Look for battery-related fields
        bat_fields = ["battery_remaining", "voltage_battery", "current_battery", "bat_volt"]
        bat_field = None
        
        for field in bat_fields:
            for key in ts.keys():
                if field in key.lower():
                    bat_field = key
                    break
            if bat_field:
                break
        
        if not bat_field or bat_field not in ts:
            return {"info": "No battery data found"}
        
        battery_data = [x for x in ts[bat_field] if isinstance(x, (int, float))]
        if len(battery_data) < 2:
            return {"info": "Insufficient battery data for analysis"}
        
        # Basic battery analysis
        return {
            "field_used": bat_field,
            "levels": {
                "initial": float(battery_data[0]),
                "final": float(battery_data[-1]),
                "mean": float(np.mean(battery_data)),
                "min": float(np.min(battery_data)),
                "max": float(np.max(battery_data))
            },
            "change": float(battery_data[-1] - battery_data[0])
        }

    def _limited_analyze_for_query(self, query: str) -> Dict[str, Any]:
        """Perform a limited analysis with fewer fields when full analysis times out."""
        try:
            # Get only relevant fields for the query to limit processing time
            query_lower = query.lower()
            
            # Basic metrics dictionary with error handling
            metrics = {}
            
            # If altitude in query, try to get altitude metrics directly
            if "altitude" in query_lower or "height" in query_lower:
                alt_analysis = self.analyzer._analyze_altitude()
                if alt_analysis:
                    metrics["altitude"] = alt_analysis.get("statistics", {})
                    if "field_used" in alt_analysis:
                        metrics["altitude"]["field_used"] = alt_analysis["field_used"]
            
            # If battery in query, get battery metrics
            if "battery" in query_lower or "power" in query_lower:
                bat_analysis = self.analyzer._analyze_battery()
                if bat_analysis:
                    metrics["battery"] = bat_analysis
            
            return {
                "metrics": metrics,
                "anomalies": [],  # Skip anomaly detection in limited analysis
                "kpis": {}  # Skip KPIs in limited analysis
            }
        except Exception as e:
            print(f"Error in _limited_analyze_for_query: {str(e)}")
            return {"metrics": {"error": "Limited analysis failed"}, "anomalies": [], "kpis": {}}
    
    def _process_memory_recall(self, context: Dict) -> str:
        """Process memory recall from entity memory and semantic context."""
        # Extract entity memory
        entity_memories = context.get("entity_memory", {})
        entity_str = ""
        
        if entity_memories:
            entity_str += "Prior knowledge from memory:\n"
            for entity, info in entity_memories.items():
                entity_str += f"- {entity}: {info}\n"
        
        # Extract semantic context
        semantic_results = context.get("semantic_context", [])
        semantic_str = ""
        
        if semantic_results:
            semantic_str += "Relevant context from previous interactions:\n"
            for i, result in enumerate(semantic_results[:3]):  # Limit to top 3
                content = result.get("content", "")
                if len(content) > 150:
                    content = content[:147] + "..."
                semantic_str += f"- {content}\n"
        
        return entity_str + semantic_str
    
    def _extract_metadata_from_reasoning(self, reasoning: str) -> Dict[str, Any]:
        """Extract structured metadata from reasoning output."""
        metadata = {
            "query_type": "general",
            "has_analysis": True
        }
        
        # Extract query type from reasoning if available
        if "Query type:" in reasoning:
            query_type_line = reasoning.split("Query type:")[1].split("\n")[0].strip()
            metadata["query_type"] = query_type_line
        
        # Extract relevant parameters if available
        if "Relevant flight parameters:" in reasoning:
            params_line = reasoning.split("Relevant flight parameters:")[1].split("\n")[0].strip()
            metadata["relevant_parameters"] = params_line
        
        # Extract temporal focus if available
        if "Temporal focus:" in reasoning:
            temporal_line = reasoning.split("Temporal focus:")[1].split("\n")[0].strip()
            metadata["temporal_focus"] = temporal_line
        
        return metadata

    def clear_memory(self) -> None:
        """Clear all memory components."""
        self.memory_manager.clear() 