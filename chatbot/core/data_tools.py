class DataTools:
    def __init__(self, telemetry_data):
        self.telemetry_data = telemetry_data

    def execute_query(self, metric: str):
        """Execute a query on telemetry data based on the metric."""
        query_handlers = {
            "max_altitude": lambda: self.telemetry_data.get_max_value("altitude"),
            "max_battery_temp": lambda: self.telemetry_data.get_max_value("battery_temp"),
            "gps_loss_events": lambda: self.telemetry_data.find_events("GPS_status", "lost"),
            "rc_loss_events": lambda: self.telemetry_data.find_events("errors", "RC_LOSS"),
            "critical_errors": lambda: self.telemetry_data.find_events("errors", "critical"),
            "flight_time": lambda: self.telemetry_data.calculate_flight_duration(),
        }
        return query_handlers.get(metric, lambda: None)()