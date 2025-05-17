import pandas as pd
import numpy as np
from typing import Dict, List, Any
from dataclasses import dataclass
from scipy import stats
from datetime import datetime, timezone
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

@dataclass
class AnomalyDetection:
    type: str
    timestamp: pd.Timestamp
    description: str
    severity: str
    data: Dict[str, Any]

class TelemetryAnalyzer:
    """Advanced telemetry analysis system for UAV flight data."""
    
    def __init__(self, telemetry_data: Dict[str, Any]):
        self.telemetry_data = telemetry_data
        self.scaler = StandardScaler()
        self.anomaly_detector = IsolationForest(
            contamination=0.1,
            random_state=42
        )
        
        # Initialize analysis cache
        self.cache = {
            "metrics": None,
            "kpis": None,
            "anomalies": None,
            "last_update": None
        }
        
        # Process initial data
        self._process_telemetry_data()
    
    def _process_telemetry_data(self):
        """Process raw telemetry data into analyzable format."""
        if not self.telemetry_data:
            return
        
        # Extract time series data
        self.time_series = {
            "timestamp": [],
            "altitude": [],
            "velocity": [],
            "battery": [],
            "motor_temps": [],
            "control_inputs": []
        }
        
        for entry in self.telemetry_data.get("entries", []):
            self.time_series["timestamp"].append(entry.get("timestamp"))
            self.time_series["altitude"].append(entry.get("altitude", 0))
            self.time_series["velocity"].append(entry.get("velocity", 0))
            self.time_series["battery"].append(entry.get("battery_level", 0))
            self.time_series["motor_temps"].append(entry.get("motor_temperatures", [0]))
            self.time_series["control_inputs"].append(entry.get("control_inputs", [0, 0, 0, 0]))
    
    def analyze_for_query(self, query: str) -> Dict[str, Any]:
        """Analyze telemetry data specifically for a query."""
        # Update cache if needed
        current_time = datetime.now(timezone.utc)
        if (not self.cache["last_update"] or 
            (current_time - self.cache["last_update"]).seconds > 60):
            self._update_analysis_cache()
        
        # Extract relevant metrics based on query
        relevant_data = {
            "metrics": self._filter_relevant_metrics(query),
            "anomalies": self._filter_relevant_anomalies(query),
            "kpis": self._filter_relevant_kpis(query)
        }
        
        # Add query-specific analysis
        if "altitude" in query.lower():
            relevant_data["altitude_analysis"] = self._analyze_altitude()
        if "battery" in query.lower():
            relevant_data["battery_analysis"] = self._analyze_battery()
        if "performance" in query.lower():
            relevant_data["performance_analysis"] = self._analyze_performance()
        
        return relevant_data
    
    def _update_analysis_cache(self):
        """Update cached analysis results."""
        self.cache["metrics"] = self._calculate_flight_metrics()
        self.cache["kpis"] = self._calculate_performance_indicators()
        self.cache["anomalies"] = self._detect_anomalies()
        self.cache["last_update"] = datetime.now(timezone.utc)
    
    def _calculate_flight_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive flight metrics."""
        if not self.time_series["altitude"]:
            return {}
        
        metrics = {
            "altitude": {
                "max": np.max(self.time_series["altitude"]),
                "min": np.min(self.time_series["altitude"]),
                "mean": np.mean(self.time_series["altitude"]),
                "std": np.std(self.time_series["altitude"])
            },
            "velocity": {
                "max": np.max(self.time_series["velocity"]),
                "mean": np.mean(self.time_series["velocity"]),
                "stability": np.std(self.time_series["velocity"]) / np.mean(self.time_series["velocity"])
            },
            "battery": {
                "initial": self.time_series["battery"][0],
                "final": self.time_series["battery"][-1],
                "drain_rate": (self.time_series["battery"][0] - self.time_series["battery"][-1]) / len(self.time_series["battery"])
            },
            "motor_health": {
                "max_temp": np.max(self.time_series["motor_temps"]),
                "temp_stability": np.std(self.time_series["motor_temps"])
            },
            "control": {
                "responsiveness": self._calculate_control_responsiveness(),
                "smoothness": self._calculate_control_smoothness()
            }
        }
        
        return metrics
    
    def _calculate_performance_indicators(self) -> Dict[str, Any]:
        """Calculate key performance indicators."""
        if not self.cache["metrics"]:
            return {}
        
        metrics = self.cache["metrics"]
        
        kpis = {
            "flight_efficiency": self._calculate_efficiency_score(metrics),
            "stability_score": self._calculate_stability_score(metrics),
            "power_efficiency": self._calculate_power_efficiency(metrics),
            "control_quality": self._calculate_control_quality(metrics),
            "overall_performance": None  # Will be calculated below
        }
        
        # Calculate overall performance score
        weights = {
            "flight_efficiency": 0.3,
            "stability_score": 0.3,
            "power_efficiency": 0.2,
            "control_quality": 0.2
        }
        
        kpis["overall_performance"] = sum(
            kpis[key] * weight 
            for key, weight in weights.items()
        )
        
        return kpis
    
    def _detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalies in flight data."""
        if not self.time_series["altitude"]:
            return []
        
        # Prepare data for anomaly detection
        features = np.column_stack([
            self.time_series["altitude"],
            self.time_series["velocity"],
            self.time_series["battery"],
            self.time_series["motor_temps"]
        ])
        
        # Scale features
        scaled_features = self.scaler.fit_transform(features)
        
        # Detect anomalies
        anomaly_labels = self.anomaly_detector.fit_predict(scaled_features)
        
        # Collect anomalies
        anomalies = []
        for i, label in enumerate(anomaly_labels):
            if label == -1:  # Anomaly detected
                anomalies.append({
                    "timestamp": self.time_series["timestamp"][i],
                    "type": self._classify_anomaly(features[i]),
                    "severity": self._calculate_anomaly_severity(features[i]),
                    "metrics": {
                        "altitude": features[i][0],
                        "velocity": features[i][1],
                        "battery": features[i][2],
                        "motor_temp": features[i][3]
                    }
                })
        
        return anomalies
    
    def _calculate_control_responsiveness(self) -> float:
        """Calculate control input responsiveness."""
        if not self.time_series["control_inputs"]:
            return 0.0
        
        # Calculate lag between control inputs and state changes
        # Simplified implementation - could be enhanced with cross-correlation
        return np.mean([abs(x[0]) for x in self.time_series["control_inputs"]])
    
    def _calculate_control_smoothness(self) -> float:
        """Calculate smoothness of control inputs."""
        if not self.time_series["control_inputs"]:
            return 0.0
        
        # Calculate the rate of change of control inputs
        control_changes = np.diff([x[0] for x in self.time_series["control_inputs"]])
        return 1.0 / (1.0 + np.std(control_changes))
    
    def _calculate_efficiency_score(self, metrics: Dict) -> float:
        """Calculate flight efficiency score."""
        if not metrics:
            return 0.0
        
        # Consider multiple factors for efficiency
        altitude_stability = 1.0 / (1.0 + metrics["altitude"]["std"])
        velocity_efficiency = 1.0 / (1.0 + metrics["velocity"]["stability"])
        battery_efficiency = 1.0 / (1.0 + abs(metrics["battery"]["drain_rate"]))
        
        return np.mean([altitude_stability, velocity_efficiency, battery_efficiency])
    
    def _calculate_stability_score(self, metrics: Dict) -> float:
        """Calculate overall flight stability score."""
        if not metrics:
            return 0.0
        
        factors = [
            1.0 / (1.0 + metrics["altitude"]["std"]),
            1.0 / (1.0 + metrics["velocity"]["stability"]),
            metrics["control"]["smoothness"]
        ]
        
        return np.mean(factors)
    
    def _calculate_power_efficiency(self, metrics: Dict) -> float:
        """Calculate power usage efficiency."""
        if not metrics:
            return 0.0
        
        # Consider battery drain rate and motor temperatures
        battery_factor = 1.0 / (1.0 + abs(metrics["battery"]["drain_rate"]))
        temp_factor = 1.0 / (1.0 + metrics["motor_health"]["temp_stability"])
        
        return np.mean([battery_factor, temp_factor])
    
    def _calculate_control_quality(self, metrics: Dict) -> float:
        """Calculate overall control quality score."""
        if not metrics:
            return 0.0
        
        return np.mean([
            metrics["control"]["responsiveness"],
            metrics["control"]["smoothness"]
        ])
    
    def _classify_anomaly(self, features: np.ndarray) -> str:
        """Classify type of anomaly based on feature values."""
        # Simplified classification logic
        if features[0] > np.mean(self.time_series["altitude"]) * 1.5:
            return "altitude_anomaly"
        if features[1] > np.mean(self.time_series["velocity"]) * 1.5:
            return "velocity_anomaly"
        if features[2] < np.mean(self.time_series["battery"]) * 0.5:
            return "battery_anomaly"
        if features[3] > np.mean(self.time_series["motor_temps"]) * 1.2:
            return "temperature_anomaly"
        return "unknown_anomaly"
    
    def _calculate_anomaly_severity(self, features: np.ndarray) -> float:
        """Calculate severity score for an anomaly."""
        # Calculate z-scores for each feature
        z_scores = stats.zscore(features)
        return float(np.max(np.abs(z_scores)))
    
    def _filter_relevant_metrics(self, query: str) -> Dict[str, Any]:
        """Filter metrics relevant to the query."""
        if not self.cache["metrics"]:
            return {}
        
        query = query.lower()
        metrics = {}
        
        if "altitude" in query:
            metrics["altitude"] = self.cache["metrics"]["altitude"]
        if "speed" in query or "velocity" in query:
            metrics["velocity"] = self.cache["metrics"]["velocity"]
        if "battery" in query or "power" in query:
            metrics["battery"] = self.cache["metrics"]["battery"]
        if "motor" in query or "temperature" in query:
            metrics["motor_health"] = self.cache["metrics"]["motor_health"]
        if "control" in query:
            metrics["control"] = self.cache["metrics"]["control"]
        
        # If no specific metrics mentioned, return overview
        if not metrics:
            metrics = {
                "overview": {
                    "mean_altitude": self.cache["metrics"]["altitude"]["mean"],
                    "mean_velocity": self.cache["metrics"]["velocity"]["mean"],
                    "battery_drain": self.cache["metrics"]["battery"]["drain_rate"]
                }
            }
        
        return metrics
    
    def _filter_relevant_anomalies(self, query: str) -> List[Dict[str, Any]]:
        """Filter anomalies relevant to the query."""
        if not self.cache["anomalies"]:
            return []
        
        query = query.lower()
        
        # If specific type mentioned, filter by type
        if "altitude" in query:
            return [a for a in self.cache["anomalies"] if a["type"] == "altitude_anomaly"]
        if "speed" in query or "velocity" in query:
            return [a for a in self.cache["anomalies"] if a["type"] == "velocity_anomaly"]
        if "battery" in query or "power" in query:
            return [a for a in self.cache["anomalies"] if a["type"] == "battery_anomaly"]
        if "motor" in query or "temperature" in query:
            return [a for a in self.cache["anomalies"] if a["type"] == "temperature_anomaly"]
        
        # If no specific type mentioned, return all anomalies sorted by severity
        return sorted(
            self.cache["anomalies"],
            key=lambda x: x["severity"],
            reverse=True
        )
    
    def _filter_relevant_kpis(self, query: str) -> Dict[str, Any]:
        """Filter KPIs relevant to the query."""
        if not self.cache["kpis"]:
            return {}
        
        query = query.lower()
        kpis = {}
        
        if "efficiency" in query:
            kpis["flight_efficiency"] = self.cache["kpis"]["flight_efficiency"]
            kpis["power_efficiency"] = self.cache["kpis"]["power_efficiency"]
        if "stability" in query:
            kpis["stability_score"] = self.cache["kpis"]["stability_score"]
        if "control" in query:
            kpis["control_quality"] = self.cache["kpis"]["control_quality"]
        if "performance" in query:
            kpis["overall_performance"] = self.cache["kpis"]["overall_performance"]
        
        # If no specific KPIs mentioned, return overall performance
        if not kpis:
            kpis = {
                "overall_performance": self.cache["kpis"]["overall_performance"]
            }
        
        return kpis
    
    def _analyze_altitude(self) -> Dict[str, Any]:
        """Perform detailed altitude analysis."""
        if not self.time_series["altitude"]:
            return {}
        
        altitude_data = np.array(self.time_series["altitude"])
        
        return {
            "statistics": {
                "max": np.max(altitude_data),
                "min": np.min(altitude_data),
                "mean": np.mean(altitude_data),
                "std": np.std(altitude_data),
                "variance": np.var(altitude_data)
            },
            "stability": {
                "coefficient_of_variation": np.std(altitude_data) / np.mean(altitude_data),
                "range_ratio": (np.max(altitude_data) - np.min(altitude_data)) / np.mean(altitude_data)
            },
            "trends": {
                "overall_trend": np.polyfit(range(len(altitude_data)), altitude_data, 1)[0],
                "stability_score": 1.0 / (1.0 + np.std(altitude_data))
            }
        }
    
    def _analyze_battery(self) -> Dict[str, Any]:
        """Perform detailed battery analysis."""
        if not self.time_series["battery"]:
            return {}
        
        battery_data = np.array(self.time_series["battery"])
        
        return {
            "levels": {
                "initial": battery_data[0],
                "final": battery_data[-1],
                "mean": np.mean(battery_data)
            },
            "consumption": {
                "total_drain": battery_data[0] - battery_data[-1],
                "drain_rate": (battery_data[0] - battery_data[-1]) / len(battery_data),
                "efficiency_score": 1.0 / (1.0 + abs((battery_data[0] - battery_data[-1]) / len(battery_data)))
            },
            "health": {
                "voltage_stability": 1.0 / (1.0 + np.std(battery_data)),
                "estimated_remaining_time": self._estimate_remaining_time(battery_data)
            }
        }
    
    def _analyze_performance(self) -> Dict[str, Any]:
        """Perform comprehensive performance analysis."""
        if not self.cache["metrics"] or not self.cache["kpis"]:
            return {}
        
        return {
            "overall_score": self.cache["kpis"]["overall_performance"],
            "efficiency": {
                "flight": self.cache["kpis"]["flight_efficiency"],
                "power": self.cache["kpis"]["power_efficiency"]
            },
            "stability": {
                "score": self.cache["kpis"]["stability_score"],
                "altitude": 1.0 / (1.0 + self.cache["metrics"]["altitude"]["std"]),
                "velocity": 1.0 / (1.0 + self.cache["metrics"]["velocity"]["stability"])
            },
            "control": {
                "quality": self.cache["kpis"]["control_quality"],
                "responsiveness": self.cache["metrics"]["control"]["responsiveness"],
                "smoothness": self.cache["metrics"]["control"]["smoothness"]
            }
        }
    
    def _estimate_remaining_time(self, battery_data: np.ndarray) -> float:
        """Estimate remaining flight time based on battery trend."""
        if len(battery_data) < 2:
            return 0.0
        
        # Calculate drain rate
        drain_rate = (battery_data[0] - battery_data[-1]) / len(battery_data)
        
        if drain_rate <= 0:
            return float('inf')
        
        # Estimate remaining time
        remaining_battery = battery_data[-1]  # Current battery level
        return remaining_battery / drain_rate  # Time until battery reaches 0 