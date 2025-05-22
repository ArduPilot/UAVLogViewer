import google.generativeai as genai
from config import settings
from chatbot.core.data_loader import TelemetryDataLoader
from chatbot.core.data_tools import DataTools

class LLMAnalyst:
    def __init__(self, log_path: str = "logs/flight_logs"):
        try:
            genai.configure(api_key=settings.chatbot.LLM.API_KEY)
            self.model = genai.GenerativeModel(settings.chatbot.LLM.MODEL)
            print(f"Gemini model initialized: {self.model is not None}")
        except Exception as e:
            print(f"Gemini API initialization error: {e}")
            self.model = None
        try:
            self.telemetry_data = TelemetryDataLoader(log_path)
            print(f"Telemetry data loaded: {self.telemetry_data.data is not None}")
        except ValueError as e:
            print(f"TelemetryDataLoader error: {e}")
            self.telemetry_data = None
        self.data_tools = DataTools(self.telemetry_data) if self.telemetry_data else None
        self.anomaly_metrics = self.telemetry_data.get_anomaly_metrics() if self.telemetry_data else {}
        self.system_prompt = f"""
        You're a MAVLink flight data analyst specializing in anomaly detection. Use these tools and data to answer questions:
        - get_max_value(field): Returns the maximum value of a field (e.g., altitude, battery_temp)
        - find_events(field, condition): Returns events where the field matches the condition (e.g., GPS_status == lost, errors == RC_LOSS)
        - calculate_duration(start, end): Returns the duration between two timestamps in seconds
        Supported fields: {', '.join(settings.uav.SUPPORTED_FIELDS)}

        **Anomaly Detection Data**:
        - Altitude rates of change (m/s): {self.anomaly_metrics.get('altitude_rates', [])[:10]}... (first 10 values)
        - Battery temperature rates of change (°C/s): {self.anomaly_metrics.get('battery_temp_rates', [])[:10]}... (first 10 values)
        - GPS status transitions: {self.anomaly_metrics.get('gps_transitions', [])[:5]}... (first 5 transitions)
        - GPS statuses (0 = No Fix, 2 = 2D, 3 = 3D): {self.anomaly_metrics.get('gps_statuses', [])[:10]}... (first 10 values)
        - Error summary: {self.anomaly_metrics.get('error_summary', {})}
        - Flight duration: {self.anomaly_metrics.get('flight_duration', 0.0)} seconds

        **Anomaly Detection Guidelines**:
        - Look for sudden changes in altitude (e.g., rapid drops or spikes in altitude_rate).
        - Check for GPS instability (e.g., frequent transitions between fix types, prolonged periods of no fix).
        - Identify unusual battery temperature changes (e.g., rapid increases in battery_temp_rate).
        - Highlight frequent or critical errors (e.g., multiple RC_LOSS or GYRO_ERROR events).
        - Consider the flight context (e.g., duration, expected behavior) when assessing anomalies.
        - Reason dynamically and avoid rigid thresholds unless explicitly supported by data patterns.

        Always answer using metric units. Be concise but technical. Ask clarifying questions if needed.
        """

    async def generate_response(self, history: list, tools: dict) -> str:
        if not self.model:
            return "Gemini API is not available. Check API key configuration."
        prompt = self.system_prompt + "\nUser: " + history[0]["content"]
        try:
            response = self.model.generate_content(prompt)
            return response.text if response.text else "No response generated"
        except Exception as e:
            print(f"Generate response error: {e}")
            return f"Error generating response: {e}"

    def _tool_schema(self, tools):
        return {"type": "function", "function": {"name": "example_tool", "description": "Example tool"}}

    async def process_message(self, message: dict) -> dict:
        user_message = message.get("message", "")
        history = [{"role": "user", "content": user_message}]

        if not self.data_tools:
            return {"message": "No flight data available. Please load a valid flight log.", "type": "error"}

        tools = {
            "get_max_value": lambda field: self.data_tools.execute_query(
                "max_altitude" if field == "altitude" else "max_battery_temp"
            ),
            "find_events": lambda field, condition: self.data_tools.execute_query(
                "gps_loss_events" if field == "GPS_status" and condition == "lost"
                else "rc_loss_events" if field == "errors" and condition == "RC_LOSS"
                else "critical_errors"
            ),
            "calculate_duration": lambda start, end: self.data_tools.execute_query("flight_time")
        }

        if "highest altitude" in user_message.lower():
            max_altitude = tools["get_max_value"]("altitude")
            response_content = f"The highest altitude reached was {max_altitude} meters."
        elif "gps signal first get lost" in user_message.lower():
            gps_events = tools["find_events"]("GPS_status", "lost")
            if gps_events:
                first_event = gps_events[0]
                response_content = f"The GPS signal was first lost at timestamp {first_event['timestamp']}."
            else:
                response_content = "No GPS signal loss events were recorded."
        elif "maximum battery temperature" in user_message.lower():
            max_temp = tools["get_max_value"]("battery_temp")
            response_content = f"The maximum battery temperature was {max_temp}°C."
        elif "total flight time" in user_message.lower():
            duration = tools["calculate_duration"](None, None)
            response_content = f"The total flight time was {duration} seconds."
        elif "critical errors" in user_message.lower():
            errors = tools["find_events"]("errors", "critical")
            if errors:
                error_list = [f"{err['event']} at timestamp {err['timestamp']}" for err in errors]
                response_content = "Critical errors mid-flight:\n" + "\n".join(error_list)
            else:
                response_content = "No critical errors were recorded mid-flight."
        elif "first instance of rc signal loss" in user_message.lower():
            rc_events = tools["find_events"]("errors", "RC_LOSS")
            if rc_events:
                first_event = rc_events[0]
                response_content = f"The first instance of RC signal loss occurred at timestamp {first_event['timestamp']}."
            else:
                response_content = "No RC signal loss events were recorded."
        elif "anomalies in this flight" in user_message.lower():
            response_content = await self.generate_response(history, tools)
        elif "issues in the gps data" in user_message.lower():
            response_content = await self.generate_response(history, tools)
        else:
            response_content = await self.generate_response(history, tools)

        return {"message": response_content, "type": "ai_response"}