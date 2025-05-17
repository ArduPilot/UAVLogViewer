from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from chat.memory_manager import EnhancedMemoryManager
from telemetry.analyzer import TelemetryAnalyzer
import os
from dotenv import load_dotenv
import json
import pandas as pd

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
            openai_api_key=os.getenv("OPENAI_API_KEY")
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
                "Use this data in your analysis."
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template("{input}"),
        ])

    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message with enhanced ReAct framework."""
        try:
            print(f"Starting to process message: {message}")
            
            # Get comprehensive context using memory manager
            print("Fetching context from memory manager...")
            context = await self.memory_manager.get_context(message)
            print("Context retrieved successfully")
            
            # Perform detailed flight data analysis based on query reasoning
            query_reasoning = context.get("query_reasoning", "No specific reasoning available.")
            print(f"Query reasoning: {query_reasoning[:100]}...")
            
            print("Performing flight analysis...")
            flight_analysis = await self._perform_flight_analysis(message, query_reasoning)
            print("Flight analysis completed")
            
            # Prepare analysis_data for the API JSON response
            analysis_data_for_api = {
                "type": "Flight Analysis", # Static type for now
                "metrics": {},
                "anomalies": "No anomaly data processed" # Default
            }

            # Populate metrics for API response
            # If query was general, _filter_relevant_metrics returns an "overview"
            # If specific, it returns specific metrics.
            # For the API, if it was general, let's provide ALL metrics.
            # Otherwise, provide the query-filtered metrics.
            filtered_metrics = flight_analysis.get("metrics", {})
            if "overview" in filtered_metrics: # Indicates a general query by current _filter_relevant_metrics logic
                all_calculated_metrics = self.analyzer.cache.get("metrics")
                analysis_data_for_api["metrics"] = all_calculated_metrics if all_calculated_metrics else {"info": "No metrics calculated or available in cache."}
            else: # Specific query, so use the filtered metrics
                analysis_data_for_api["metrics"] = filtered_metrics if filtered_metrics else {"info": "No specific metrics found for the query."}

            # Populate anomalies for API response - always use the full detection list
            all_detected_anomalies = self.analyzer.cache.get("anomalies")
            if isinstance(all_detected_anomalies, list):
                if all_detected_anomalies:
                    analysis_data_for_api["anomalies"] = f"Detected {len(all_detected_anomalies)} anomalies."
                    # Optionally, could include a few examples or a summary of types
                    # For now, count is consistent with LLM prompt's anomaly info.
                else:
                    analysis_data_for_api["anomalies"] = "No anomalies detected in the flight log."
            else:
                analysis_data_for_api["anomalies"] = "Anomaly detection data not available or not processed."
            
            # Process memory recall from both entity memory and semantic context
            print("Processing memory recall...")
            memory_recall = self._process_memory_recall(context)
            print("Memory recall processed")
            
            # Format chat history from the summary buffer memory
            chat_history = context.get("chat_history", [])
            print(f"Retrieved {len(chat_history)} chat history items")
            
            # Generate response using ReAct framework
            print("Generating response using chat model...")
            try:
                # Build flight data summary for the prompt
                flight_metrics = self.analyzer._calculate_flight_metrics()
                flight_data_for_prompt = {
                    "duration": "N/A",
                    "time_range": "N/A",
                    "key_metrics": "No specific metrics available from the log.",
                    "anomalies": "Anomaly detection data not available or no anomalies found."
                }

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

                # Populate key_metrics for the prompt string
                if flight_metrics:
                    temp_metrics_parts = []
                    if "altitude" in flight_metrics and isinstance(flight_metrics["altitude"], dict):
                        max_alt = flight_metrics["altitude"].get('max')
                        mean_alt = flight_metrics["altitude"].get('mean')
                        if max_alt is not None: temp_metrics_parts.append(f"Max Altitude: {max_alt:.1f} m")
                        if mean_alt is not None: temp_metrics_parts.append(f"Avg Altitude: {mean_alt:.1f} m")
                    
                    if "velocity" in flight_metrics and isinstance(flight_metrics["velocity"], dict):
                        max_vel = flight_metrics["velocity"].get('max')
                        mean_vel = flight_metrics["velocity"].get('mean')
                        if max_vel is not None: temp_metrics_parts.append(f"Max Speed: {max_vel:.1f} m/s")
                        if mean_vel is not None: temp_metrics_parts.append(f"Avg Speed: {mean_vel:.1f} m/s")

                    if "battery" in flight_metrics and isinstance(flight_metrics["battery"], dict):
                        initial_bat = flight_metrics["battery"].get('initial')
                        final_bat = flight_metrics["battery"].get('final')
                        drain_rate = flight_metrics["battery"].get('drain_rate')
                        if initial_bat is not None: temp_metrics_parts.append(f"Initial Battery: {initial_bat:.0f}%")
                        if final_bat is not None: temp_metrics_parts.append(f"Final Battery: {final_bat:.0f}%")
                        # Drain rate might be too detailed for a summary, consider if needed for LLM

                    if temp_metrics_parts:
                        flight_data_for_prompt["key_metrics"] = "; ".join(temp_metrics_parts)
                    else:
                        # This case means flight_metrics was not empty, but no relevant parts were extracted
                        flight_data_for_prompt["key_metrics"] = "General metrics calculated but not itemized here."
                
                # Populate anomalies for the prompt string
                anomalies_list = self.analyzer._detect_anomalies()
                if anomalies_list:
                    flight_data_for_prompt["anomalies"] = f"Detected {len(anomalies_list)} anomalies. Example: {anomalies_list[0]['type']} at {anomalies_list[0]['timestamp']}"
                else:
                    flight_data_for_prompt["anomalies"] = "No anomalies detected during the flight."

                messages = self.prompt.format_messages(
                    input=message,
                    flight_duration=flight_data_for_prompt["duration"],
                    time_range=flight_data_for_prompt["time_range"],
                    key_metrics=flight_data_for_prompt["key_metrics"],
                    anomalies=flight_data_for_prompt["anomalies"],
                    chat_history=chat_history
                )
                print(f"Formatted {len(messages)} messages for the prompt")
                
                print("Invoking chat model...")
                response = self.chat.invoke(messages)
                print("Response generated successfully")
            except Exception as prompt_error:
                print(f"Error formatting prompt or invoking chat model: {str(prompt_error)}")
                import traceback
                print(f"PROMPT ERROR TRACEBACK: {traceback.format_exc()}")
                
                # Fallback to a simpler prompt if the rich prompt fails
                fallback_prompt = ChatPromptTemplate.from_messages([
                    SystemMessagePromptTemplate.from_template("You are a UAV flight data analyst. Provide a brief analysis based on the available information."),
                    HumanMessagePromptTemplate.from_template("Analyze this flight data query: {input}")
                ])
                
                fallback_messages = fallback_prompt.format_messages(input=message)
                response = self.chat.invoke(fallback_messages)
                print("Used fallback prompt successfully")
            
            # Extract metadata from reasoning for storage
            metadata = self._extract_metadata_from_reasoning(query_reasoning)
            
            # Save interaction to memory with enhanced metadata
            print("Saving user message to memory...")
            await self.memory_manager.add_message(
                role="user",
                content=message,
                metadata=metadata
            )
            
            print("Saving assistant response to memory...")
            await self.memory_manager.add_message(
                role="assistant",
                content=response.content,
                metadata={
                    **metadata,
                    "analysis_performed": True,
                    "flight_data_analyzed": flight_analysis is not None
                }
            )
            
            return {
                "answer": response.content,
                "analysis": analysis_data_for_api, # Use the new comprehensive dict
                "reasoning": query_reasoning
            }
            
        except Exception as e:
            # Enhanced error handling
            error_msg = f"Error processing message: {str(e)}"
            print(f"ERROR IN PROCESS_MESSAGE: {error_msg}")
            import traceback
            print(f"TRACEBACK: {traceback.format_exc()}")
            
            try:
                await self.memory_manager.add_message(
                    role="system",
                    content=error_msg,
                    metadata={
                        "error": True,
                        "error_type": type(e).__name__,
                        "query": message
                    }
                )
            except Exception as mem_error:
                print(f"Additional error saving error to memory: {str(mem_error)}")
            
            # Always return a valid response even if an error occurs
            return {
                "answer": "I apologize, but I encountered an error while processing your request. Please try again with a different question about the flight data.",
                "analysis": None,
                "error": str(e)
            }
    
    async def _perform_flight_analysis(self, query: str, reasoning: str) -> Dict[str, Any]:
        """Perform targeted flight data analysis based on query and reasoning."""
        try:
            # Use reasoning to determine what to analyze
            analyzer_result = self.analyzer.analyze_for_query(query)
            
            # Format analysis result as a structured dictionary
            result = {
                "metrics": analyzer_result.get("metrics", {}),
                "anomalies": analyzer_result.get("anomalies", []),
                "kpis": analyzer_result.get("kpis", {})
            }
            
            # Add specific analysis based on query content
            if "altitude" in query.lower() or "altitude" in reasoning.lower():
                altitude_analysis = analyzer_result.get("altitude_analysis", {})
                if altitude_analysis and "statistics" in altitude_analysis:
                    result["metrics"]["altitude"] = altitude_analysis["statistics"]
                elif "altitude" in result["metrics"]:
                    # Ensure altitude data is available if already in metrics
                    result["metrics"]["altitude"] = result["metrics"]["altitude"]
            
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
                "metrics": {"error": "Could not analyze flight data."},
                "anomalies": [],
                "kpis": {}
            }
    
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