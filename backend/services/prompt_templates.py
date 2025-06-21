"""
Prompt template system for flight-aware chatbot interactions.
Provides structured prompts with flight context injection.
"""

import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def build_flight_aware_prompt(
    user_message: str,
    flight_metrics: Dict[str, Any],
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    DEPRECATED: Build a comprehensive prompt for flight-aware conversations.

    This function is kept for backward compatibility but is no longer used
    in the main chat flow. The new Responses API uses _get_flight_aware_instructions()
    and _format_flight_metrics_for_developer_message() instead.

    Build a comprehensive prompt for flight-aware conversations.

    Parameters
    ----------
    user_message : str
        Current user question/message
    flight_metrics : Dict[str, Any]
        Structured flight metrics from flight context service
    conversation_history : Optional[List[Dict[str, Any]]]
        Previous conversation messages for context

    Returns
    -------
    str
        Complete LLM prompt with system instructions, flight data, and user query
    """

    # System instructions for flight analysis
    system_prompt = _get_system_instructions()

    # Format flight data for LLM consumption
    flight_context = _format_flight_context(flight_metrics)

    # Include conversation history if available
    history_context = _format_conversation_history(conversation_history)

    # Build complete prompt
    prompt_parts = [
        system_prompt,
        flight_context,
        history_context,
        f"User Question: {user_message}",
        _get_response_guidelines(),
    ]

    # Join with clear separators
    return "\n\n" + "\n\n---\n\n".join(filter(None, prompt_parts)) + "\n\n"


def _get_system_instructions() -> str:
    """Get core system instructions for the flight analysis assistant."""
    return """You are UAVGPT, an expert UAV flight data analyst and assistant. 
    
Your role is to help users understand their flight data by answering questions about flight performance, navigation, system health, and operational characteristics. You have access to pre-computed flight metrics from MAVLink telemetry logs.

Core Capabilities:
- Analyze flight performance metrics (altitude, speed, distance, duration)
- Interpret navigation data (GPS fix quality, coordinate accuracy)
- Assess system health (error/warning counts, message availability)  
- Explain vehicle configuration and flight modes
- Provide technical insights about ArduPilot/PX4 flight behaviors

Analysis Approach:
- Base all answers on the available flight data provided
- When data is insufficient, clearly state limitations
- Provide specific numeric values when available
- Explain technical terms in accessible language
- Suggest follow-up analysis when relevant

Documentation Support:
- You may consult the official ArduPilot documentation via the `search_ardu_doc` tool whenever relevant
- Use this tool to look up meanings of log messages, troubleshooting guidance, or technical explanations
- Note: Documentation coverage is limited to selected ArduPilot pages; not every topic is available"""


def _format_flight_context(flight_metrics: Dict[str, Any]) -> str:
    """Format flight metrics into structured context for LLM."""

    if not flight_metrics or "error" in flight_metrics:
        return "Flight Data Status: No flight metrics available for analysis."

    context_lines = ["Available Flight Data:"]

    # Format each section of metrics
    for section_name, section_data in flight_metrics.items():
        if not section_data:
            continue

        # Convert section name to readable format
        section_title = section_name.replace("_", " ").title()
        context_lines.append(f"\n{section_title}:")

        # Format section data based on type
        if isinstance(section_data, dict):
            for key, value in section_data.items():
                formatted_key = key.replace("_", " ").title()
                context_lines.append(f"  • {formatted_key}: {value}")
        elif isinstance(section_data, list):
            if section_data:  # Only show if list has items
                context_lines.append(f"  • Items: {', '.join(map(str, section_data))}")
        else:
            context_lines.append(f"  • Value: {section_data}")

    return "\n".join(context_lines)


def _format_conversation_history(
    conversation_history: Optional[List[Dict[str, Any]]],
) -> str:
    """Format conversation history for context continuity."""

    if not conversation_history:
        return ""

    # Limit history to prevent context overflow (last 6 messages)
    recent_history = (
        conversation_history[-6:]
        if len(conversation_history) > 6
        else conversation_history
    )

    history_lines = ["Recent Conversation Context:"]

    for msg in recent_history:
        message_type = msg.get("message_type", "unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")

        # Truncate very long messages
        if len(content) > 200:
            content = content[:197] + "..."

        prefix = "User" if message_type == "user" else "Assistant"
        history_lines.append(f"  {prefix}: {content}")

    return "\n".join(history_lines)


def _get_response_guidelines() -> str:
    """Get response formatting guidelines for the LLM."""
    return """Response Guidelines:
- Answer based strictly on the available flight data
- When data is missing or insufficient, say "I don't have that data" or "This information is not available in the current flight log"
- Provide specific numeric values when available
- Use clear, technical but accessible language
- For technical terms, provide brief explanations
- Keep responses concise but informative
- If the question requires data not in the metrics, explain what additional data would be needed"""


def build_no_session_prompt(user_message: str) -> str:
    """
    DEPRECATED: Build a prompt for when no flight session is available.

    This function is kept for backward compatibility but is no longer used
    in the main chat flow. The new Responses API uses _get_no_session_instructions() instead.

    Build a prompt for when no flight session is available.

    Parameters
    ----------
    user_message : str
        User's message

    Returns
    -------
    str
        Prompt explaining limitations without flight data
    """

    return f"""You are UAVGPT, a UAV flight data analysis assistant.

Current Status: No flight session data is available for analysis.

User Message: {user_message}

You should respond by:
1. Acknowledging that no flight data is currently loaded
2. Explaining that you can help analyze UAV flight logs once a .bin file is uploaded
3. Briefly describing what types of questions you can answer about flight data
4. If the user is asking a general UAV question (not requiring specific flight data), provide a helpful general response

Keep your response helpful and encouraging while being clear about current limitations."""


def validate_prompt_inputs(
    user_message: str, flight_metrics: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """
    Validate inputs for prompt generation.

    Parameters
    ----------
    user_message : str
        User's message to validate
    flight_metrics : Dict[str, Any]
        Flight metrics to validate

    Returns
    -------
    tuple[bool, Optional[str]]
        (is_valid, error_message)
    """

    # Check user message
    if not user_message or not user_message.strip():
        return False, "User message cannot be empty"

    if len(user_message.strip()) > 5000:
        return False, "User message too long (max 5000 characters)"

    # Check flight metrics structure
    if not isinstance(flight_metrics, dict):
        return False, "Flight metrics must be a dictionary"

    return True, None


def estimate_prompt_tokens(prompt: str) -> int:
    """
    Rough estimation of prompt tokens for LLM context management.

    Parameters
    ----------
    prompt : str
        The generated prompt

    Returns
    -------
    int
        Estimated token count (rough approximation)
    """

    # Rough approximation: 1 token ≈ 4 characters for English text
    return len(prompt) // 4


def truncate_for_context_limit(prompt: str, max_tokens: int = 3000) -> str:
    """
    DEPRECATED: Truncate prompt to fit within context limits.

    This function is no longer needed with the Responses API as OpenAI handles
    context management automatically. Kept for backward compatibility.

    Truncate prompt to fit within context limits.

    Parameters
    ----------
    prompt : str
        The prompt to potentially truncate
    max_tokens : int
        Maximum allowed tokens (default: 3000)

    Returns
    -------
    str
        Truncated prompt if necessary
    """
    estimated_tokens = estimate_prompt_tokens(prompt)

    if estimated_tokens <= max_tokens:
        return prompt

    # Calculate target character count (rough approximation)
    target_chars = int(len(prompt) * (max_tokens / estimated_tokens))

    # Truncate and add notice
    truncated = prompt[:target_chars]
    truncated += "\n\n[Note: Context truncated due to length limits]"

    logger.warning(f"Prompt truncated from {estimated_tokens} to ~{max_tokens} tokens")

    return truncated


def _get_flight_aware_instructions() -> str:
    """Get system instructions for flight-aware conversations using Responses API."""
    return """You are UAVGPT, an expert UAV flight data analyst and assistant.

Your role is to help users understand their flight data by answering questions about flight performance, navigation, system health, and operational characteristics. You have access to pre-computed flight metrics from MAVLink telemetry logs.

Core Capabilities:
- Analyze flight performance metrics (altitude, speed, distance, duration)
- Interpret navigation data (GPS fix quality, coordinate accuracy)  
- Assess system health (error/warning counts, message availability)
- Explain vehicle configuration and flight modes
- Provide technical insights about ArduPilot/PX4 flight behaviors

Analysis Approach:
- Base all answers on the available flight data provided in developer messages
- When data is insufficient, clearly state limitations
- Provide specific numeric values when available
- Explain technical terms in accessible language
- Suggest follow-up analysis when relevant
- Keep responses concise but informative

Response Guidelines:
- Answer based strictly on the available flight data
- When data is missing, say "I don't have that data" or "This information is not available"
- Use clear, technical but accessible language
- For technical terms, provide brief explanations
- If needed, ask the user to provide more information

Documentation Support:
- You may consult the official ArduPilot documentation via the `search_ardu_doc` tool whenever relevant
- Use this tool to look up meanings of log messages, troubleshooting guidance, or technical explanations
- Note: Documentation coverage is limited to selected ArduPilot pages; not every topic is available"""


def _get_no_session_instructions() -> str:
    """Get system instructions when no flight session is available."""
    return """You are UAVGPT, a UAV flight data analysis assistant.

Current Status: No flight session data is available for analysis.

You should respond by:
1. Acknowledging that no flight data is currently loaded
2. Explaining that you can help analyze UAV flight logs once a .bin file is uploaded
3. Briefly describing what types of questions you can answer about flight data
4. If the user is asking a general UAV question (not requiring specific flight data), provide a helpful general response

Keep your response helpful and encouraging while being clear about current limitations."""


def _format_flight_metrics_for_developer_message(flight_metrics: Dict[str, Any]) -> str:
    """Format flight metrics as a developer message for the Responses API."""
    if not flight_metrics or "error" in flight_metrics:
        return "Developer: No flight metrics available for analysis."

    lines = ["Developer: Available flight data for this session:"]

    # Format each section of metrics
    for section_name, section_data in flight_metrics.items():
        if not section_data:
            continue

        # Convert section name to readable format
        section_title = section_name.replace("_", " ").title()
        lines.append(f"\n{section_title}:")

        # Format section data based on type
        if isinstance(section_data, dict):
            for key, value in section_data.items():
                formatted_key = key.replace("_", " ").title()
                lines.append(f"  • {formatted_key}: {value}")
        elif isinstance(section_data, list):
            if section_data:  # Only show if list has items
                lines.append(f"  • Items: {', '.join(map(str, section_data))}")
        else:
            lines.append(f"  • Value: {section_data}")

    lines.append("\nPlease answer the user's question based on this flight data.")
    return "\n".join(lines)


def _get_usage_instructions() -> str:
    """Get usage instructions for the LLM."""
    # Deterministic concept→table/tool mapping for the LLM
    data_index = {
        # Raw telemetry tables with their columns
        "gps_telemetry": {
            "table": "gps_telemetry",
            "columns": [
                "time_boot_ms",
                "timestamp_utc",
                "lat",
                "lon",
                "alt",
                "relative_alt",
                "vx",
                "vy",
                "vz",
                "hdg",
                "eph",
                "epv",
                "vel",
                "cog",
                "fix_type",
                "satellites_visible",
                "dgps_numch",
                "dgps_age",
            ],
        },
        "attitude_telemetry": {
            "table": "attitude_telemetry",
            "columns": [
                "time_boot_ms",
                "timestamp_utc",
                "roll",
                "pitch",
                "yaw",
                "rollspeed",
                "pitchspeed",
                "yawspeed",
            ],
        },
        "sensor_telemetry": {
            "table": "sensor_telemetry",
            "columns": [
                "time_boot_ms",
                "timestamp_utc",
                "xacc",
                "yacc",
                "zacc",
                "xgyro",
                "ygyro",
                "zgyro",
                "xmag",
                "ymag",
                "zmag",
            ],
        },
        "flight_events": {
            "table": "flight_events",
            "columns": [
                "time_boot_ms",
                "timestamp_utc",
                "event_type",
                "event_description",
                "severity",
                "parameters",
            ],
        },
        "system_status": {
            "table": "system_status",
            "columns": [
                "time_boot_ms",
                "timestamp_utc",
                "battery_voltage",
                "battery_current",
                "battery_remaining",
                "battery_temperature",
                "radio_rssi",
                "radio_remrssi",
                "radio_noise",
                "radio_remnoise",
                "mode",
                "armed",
            ],
        },
        # High-level statistics tool
        "statistics": {
            "tool": "get_flight_summary",
            "fields": [
                "max_altitude_m",
                "max_speed_ms",
                "error_count",
                "warning_count",
                "total_distance_km",
                "flight_duration_seconds",
            ],
        },
    }

    mapping_json = json.dumps(data_index, indent=4)

    return f"""
        **Usage Instructions (per turn)**

        1. ALWAYS consult the **data_index** mapping below before you construct ANY tool call. If the user's request matches a concept in the mapping, you MUST use the specified table/tool and columns—do NOT guess.

        ```json
        {mapping_json}
        ```

        2. General troubleshooting when data are missing:
            • If a selected table is empty, double-check with `check_data_availability`, then try an alternative table if appropriate.
            • Use `list_table_columns` to confirm column names before querying.

        3. If you follow the mapping and still cannot find the requested data, clearly state that the information is unavailable.

        4. For log message meanings or troubleshooting guidance, use **search_ardu_doc(query, k=3)** to search the embedded ArduPilot documentation. This covers log messages, vibration analysis, and troubleshooting guides with semantic search.

        5. If the embedded documentation doesn't have relevant information, you can fall back to **fetch_url_content(offset,max_chars,as_text?)** to retrieve parts of the broader ArduPilot documentation. Search within the returned text for the relevant keyword. Paginate by increasing `offset` until `has_more` becomes false.
    """
