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
        """Process raw telemetry data (Dict[str, pd.DataFrame]) into analyzable time series."""
        self.time_series = {
            "timestamp": [], "altitude": [], "velocity": [], "battery": [],
            "motor_temps": [], "control_inputs": []
        }

        if not self.telemetry_data:
            print("TelemetryAnalyzer: No telemetry data provided to process.")
            return

        combined_df_list = []

        # Altitude
        if 'GLOBAL_POSITION_INT' in self.telemetry_data:
            gpi_df = self.telemetry_data['GLOBAL_POSITION_INT']
            if not gpi_df.empty and 'relative_alt' in gpi_df.columns and 'timestamp' in gpi_df.columns:
                df = gpi_df[['timestamp', 'relative_alt']].copy()
                df.rename(columns={'relative_alt': 'altitude'}, inplace=True)
                df['altitude'] = df['altitude'] / 1000.0 # mm to m
                df.set_index('timestamp', inplace=True)
                combined_df_list.append(df)

        # Velocity
        if 'VFR_HUD' in self.telemetry_data:
            vfr_df = self.telemetry_data['VFR_HUD']
            if not vfr_df.empty and 'groundspeed' in vfr_df.columns and 'timestamp' in vfr_df.columns:
                df = vfr_df[['timestamp', 'groundspeed']].copy()
                df.rename(columns={'groundspeed': 'velocity'}, inplace=True)
                df.set_index('timestamp', inplace=True)
                combined_df_list.append(df)
        
        # Battery
        if 'BATTERY_STATUS' in self.telemetry_data:
            bat_df = self.telemetry_data['BATTERY_STATUS']
            if not bat_df.empty and 'battery_remaining' in bat_df.columns and 'timestamp' in bat_df.columns:
                df = bat_df[['timestamp', 'battery_remaining']].copy()
                df.rename(columns={'battery_remaining': 'battery'}, inplace=True)
                df.set_index('timestamp', inplace=True)
                combined_df_list.append(df)
        
        # --- Placeholder for actual motor_temps and control_inputs parsing ---
        # Example: if motor_temps were in a 'MOTOR_STATUS' message type
        # if 'MOTOR_STATUS' in self.telemetry_data:
        #     motor_df = self.telemetry_data['MOTOR_STATUS']
        #     if not motor_df.empty and 'temp1' in motor_df.columns and 'timestamp' in motor_df.columns:
        #         # Assuming 'temp1' is one of the motor temperatures
        #         df = motor_df[['timestamp', 'temp1']].copy() 
        #         df.rename(columns={'temp1': 'motor_temp_example'}, inplace=True)
        #         df.set_index('timestamp', inplace=True)
        #         combined_df_list.append(df)
        # --- End Placeholder ---

        if not combined_df_list:
            print("TelemetryAnalyzer: No suitable DataFrames found to combine for time series processing.")
            # Populate with empty lists of correct type to avoid downstream errors if some metrics can still be calculated
            # Or handle more gracefully depending on requirements
            for key in self.time_series: self.time_series[key] = []
            return

        final_df = pd.concat(combined_df_list, axis=1, join='outer').sort_index()
        final_df.ffill(inplace=True)
        final_df.bfill(inplace=True)
        # Instead of global fillna(0), handle per expected column type or leave as NaN for stats
        
        num_timestamps = len(final_df.index)
        self.time_series["timestamp"] = final_df.index.tolist()

        for key in ["altitude", "velocity", "battery", "motor_temps", "control_inputs"]:
            if key in final_df.columns:
                # Ensure data is numeric, replace non-numeric with NaN then fill
                self.time_series[key] = pd.to_numeric(final_df[key], errors='coerce').fillna(0).tolist()
            else:
                # If column doesn't exist after concat, fill with zeros of correct length
                self.time_series[key] = [0.0] * num_timestamps 
                print(f"TelemetryAnalyzer: Column '{key}' not found in combined DataFrame. Filled with zeros.")


        if self.time_series["timestamp"]:
            print(f"TelemetryAnalyzer: Processed {len(self.time_series['timestamp'])} time series entries.")
            for key in ["altitude", "velocity", "battery"]: # Only print example for core data
                if self.time_series[key] and len(self.time_series[key]) > 0: # Check if list is not empty
                     print(f"TelemetryAnalyzer: {key} data example (first 5): {self.time_series[key][:5]}")
        else:
            print("TelemetryAnalyzer: Time series processing resulted in no timestamp data.")
    
    def analyze_for_query(self, query: str) -> Dict[str, Any]:
        """Analyze telemetry data specifically for a query."""
        try:
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
        except Exception as e:
            print(f"Error in analyze_for_query: {str(e)}")
            import traceback
            print(f"TRACEBACK: {traceback.format_exc()}")
            
            # Return a minimal set of data to prevent further errors
            return {
                "metrics": {"info": "Error analyzing flight data"},
                "error": str(e)
            }
    
    def _update_analysis_cache(self):
        """Update cached analysis results."""
        self.cache["metrics"] = self._calculate_flight_metrics()
        self.cache["kpis"] = self._calculate_performance_indicators()
        self.cache["anomalies"] = self._detect_anomalies()
        self.cache["last_update"] = datetime.now(timezone.utc)
    
    def _calculate_flight_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive flight metrics."""
        metrics = {}
        ts = self.time_series

        def get_stats(data_list, list_name="data"):
            if not isinstance(data_list, list) or not data_list: # Check if it's a list and not empty
                print(f"TelemetryAnalyzer: No data or invalid data type in {list_name} list for stats calculation.")
                return None
            valid_data = [x for x in data_list if pd.notnull(x) and isinstance(x, (int, float))]
            if not valid_data:
                print(f"TelemetryAnalyzer: No valid numeric data in {list_name} list after filtering.")
                return None
            return {
                "max": float(np.max(valid_data)), "min": float(np.min(valid_data)),
                "mean": float(np.mean(valid_data)), "std": float(np.std(valid_data))
            }

        alt_stats = get_stats(ts.get("altitude"), "altitude")
        if alt_stats: metrics["altitude"] = alt_stats

        vel_list = ts.get("velocity")
        if isinstance(vel_list, list) and vel_list:
            valid_vel = [x for x in vel_list if pd.notnull(x) and isinstance(x, (int, float))]
            if valid_vel:
                mean_vel = float(np.mean(valid_vel))
                metrics["velocity"] = {
                    "max": float(np.max(valid_vel)), "mean": mean_vel,
                    "stability": float(np.std(valid_vel)) / mean_vel if mean_vel != 0 else 0.0
                }
            else:
                print("TelemetryAnalyzer: No valid numeric data in velocity list.")
        else:
            print("TelemetryAnalyzer: No velocity data list or invalid type.")

        bat_list = ts.get("battery")
        if isinstance(bat_list, list) and bat_list:
            valid_bat = [x for x in bat_list if pd.notnull(x) and isinstance(x, (int, float))]
            if len(valid_bat) > 1:
                metrics["battery"] = {
                    "initial": float(valid_bat[0]), "final": float(valid_bat[-1]),
                    "drain_rate": (float(valid_bat[0]) - float(valid_bat[-1])) / len(valid_bat) if len(valid_bat) > 0 else 0.0
                }
            elif valid_bat: # Only one entry
                 metrics["battery"] = {"initial": float(valid_bat[0]), "final": float(valid_bat[0]), "drain_rate": 0.0}
            else:
                print("TelemetryAnalyzer: No valid numeric data in battery list or not enough data points.")
        else:
            print("TelemetryAnalyzer: No battery data list or invalid type.")
        
        # Example for motor_health, if motor_temps were processed
        motor_temps_list = ts.get("motor_temps")
        if isinstance(motor_temps_list, list) and motor_temps_list:
             valid_motor_temps = [x for x in motor_temps_list if pd.notnull(x) and isinstance(x, (int, float))]
             if valid_motor_temps:
                  metrics["motor_health"] = {
                       "max_temp": float(np.max(valid_motor_temps)),
                       "temp_stability": float(np.std(valid_motor_temps))
                  }
             else:
                  print("TelemetryAnalyzer: No valid numeric data in motor_temps list.")
        else:
            print("TelemetryAnalyzer: No motor_temps data list or invalid type.")

        print(f"TelemetryAnalyzer: Calculated metrics: {metrics}")
        return metrics
    
    def _calculate_performance_indicators(self) -> Dict[str, Any]:
        """Calculate key performance indicators."""
        # metrics = self.cache["metrics"] # This was the old way
        # Get fresh metrics or ensure cache is up-to-date.
        # For simplicity, let's assume _update_analysis_cache ensures metrics are fresh.
        metrics = self.cache.get("metrics")
        if not metrics: # Check if metrics is None or empty
            print("TelemetryAnalyzer: KPIs calculation skipped, metrics not available in cache.")
            return { # Return default structure for KPIs
                "flight_efficiency": 0.0, "stability_score": 0.0,
                "power_efficiency": 0.0, "control_quality": 0.0,
                "overall_performance": 0.0
            }
        
        kpis = {
            "flight_efficiency": self._calculate_efficiency_score(metrics),
            "stability_score": self._calculate_stability_score(metrics),
            "power_efficiency": self._calculate_power_efficiency(metrics),
            "control_quality": self._calculate_control_quality(metrics), # control_quality depends on control metrics
            "overall_performance": 0.0
        }
        
        weights = {
            "flight_efficiency": 0.3, "stability_score": 0.3,
            "power_efficiency": 0.2, "control_quality": 0.2
        }
        
        # Calculate overall performance score carefully
        overall_score = 0.0
        active_kpis = 0
        for key, weight in weights.items():
            if kpis.get(key) is not None: # Check if KPI was successfully calculated
                 # Ensure kpis[key] is float, if it's None or other, handle it
                kpi_value = kpis[key]
                if isinstance(kpi_value, (int, float)):
                    overall_score += kpi_value * weight
                    active_kpis +=1
        kpis["overall_performance"] = overall_score if active_kpis > 0 else 0.0 # Avoid division by zero if no KPIs
        
        print(f"TelemetryAnalyzer: Calculated KPIs: {kpis}")
        return kpis
    
    def _detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalies in flight data."""
        ts = self.time_series
        required_min_length = 2 # For IsolationForest or meaningful stats

        # Ensure all feature lists are present and have sufficient, consistent length
        feature_keys = ["altitude", "velocity", "battery", "motor_temps"] # "control_inputs"
        
        valid_features_data = []
        base_length = 0

        if ts.get("timestamp") and len(ts["timestamp"]) >= required_min_length:
            base_length = len(ts["timestamp"])
        else:
            print("TelemetryAnalyzer: Not enough timestamp data for anomaly detection.")
            return []

        for key in feature_keys:
            data_list = ts.get(key)
            if isinstance(data_list, list) and len(data_list) == base_length:
                # Convert to numpy array of floats, coercing errors to NaN, then filling NaN
                # This ensures all arrays are numeric and of the same type for stacking
                processed_list = pd.to_numeric(pd.Series(data_list), errors='coerce').fillna(0).to_numpy()
                valid_features_data.append(processed_list)
            else:
                print(f"TelemetryAnalyzer: Feature '{key}' is missing, not a list, or has inconsistent length ({len(data_list) if isinstance(data_list, list) else 'N/A'} vs base {base_length}) for anomaly detection. Using zeros.")
                valid_features_data.append(np.zeros(base_length))
        
        if not valid_features_data or len(valid_features_data) != len(feature_keys):
             print("TelemetryAnalyzer: Not enough valid feature sets to stack for anomaly detection.")
             return []

        try:
            features_stacked = np.column_stack(valid_features_data)
        except ValueError as e:
            print(f"TelemetryAnalyzer: Error during np.column_stack for anomaly detection: {e}. Check feature dimensions.")
            # print(f"Lengths: {[len(f) for f in valid_features_data]}")
            return []


        # Scale features
        scaled_features = self.scaler.fit_transform(features_stacked)
        
        # Detect anomalies
        anomaly_labels = self.anomaly_detector.fit_predict(scaled_features)
        
        anomalies = []
        for i, label in enumerate(anomaly_labels):
            if label == -1:  # Anomaly detected
                anomaly_metrics = {}
                for idx, key in enumerate(feature_keys):
                    anomaly_metrics[key] = features_stacked[i, idx]
                
                anomalies.append({
                    "timestamp": ts["timestamp"][i], # Assuming timestamp is pd.Timestamp or similar
                    "type": self._classify_anomaly(features_stacked[i], feature_keys), # Pass feature_keys for context
                    "severity": self._calculate_anomaly_severity(features_stacked[i]),
                    "metrics": anomaly_metrics
                })
        print(f"TelemetryAnalyzer: Detected {len(anomalies)} anomalies.")
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
        if not metrics: return 0.0
        
        # Default values if specific metrics are missing
        altitude_stability = 0.0
        velocity_efficiency = 0.0
        battery_efficiency = 0.0
        
        if "altitude" in metrics and isinstance(metrics["altitude"], dict) and "std" in metrics["altitude"] and metrics["altitude"]["std"] is not None:
            altitude_stability = 1.0 / (1.0 + metrics["altitude"]["std"])
        
        if "velocity" in metrics and isinstance(metrics["velocity"], dict) and "stability" in metrics["velocity"] and metrics["velocity"]["stability"] is not None:
            velocity_efficiency = 1.0 / (1.0 + metrics["velocity"]["stability"])
            
        if "battery" in metrics and isinstance(metrics["battery"], dict) and "drain_rate" in metrics["battery"] and metrics["battery"]["drain_rate"] is not None:
            battery_efficiency = 1.0 / (1.0 + abs(metrics["battery"]["drain_rate"]))
        
        # If no factors were calculated, return 0. Otherwise, mean of calculated factors.
        calculated_factors = [f for f in [altitude_stability, velocity_efficiency, battery_efficiency] if f is not None] # f might be 0.0
        return np.mean(calculated_factors) if calculated_factors else 0.0
    
    def _calculate_stability_score(self, metrics: Dict) -> float:
        """Calculate overall flight stability score."""
        if not metrics: return 0.0
        
        factors = []
        if "altitude" in metrics and isinstance(metrics["altitude"], dict) and "std" in metrics["altitude"] and metrics["altitude"]["std"] is not None:
            factors.append(1.0 / (1.0 + metrics["altitude"]["std"]))
        
        if "velocity" in metrics and isinstance(metrics["velocity"], dict) and "stability" in metrics["velocity"] and metrics["velocity"]["stability"] is not None:
            factors.append(1.0 / (1.0 + metrics["velocity"]["stability"]))
            
        # control_smoothness depends on control metrics which might be missing
        if "control" in metrics and isinstance(metrics["control"], dict) and "smoothness" in metrics["control"] and metrics["control"]["smoothness"] is not None:
            factors.append(metrics["control"]["smoothness"])
        else: # Add a default if control smoothness is critical but missing
            # factors.append(0.5) # Or handle as per requirement
            pass

        return np.mean(factors) if factors else 0.0
    
    def _calculate_power_efficiency(self, metrics: Dict) -> float:
        """Calculate power usage efficiency."""
        if not metrics: return 0.0
        
        battery_factor = 0.0
        temp_factor = 0.0 # Assuming motor_health might be missing
        
        if "battery" in metrics and isinstance(metrics["battery"], dict) and "drain_rate" in metrics["battery"] and metrics["battery"]["drain_rate"] is not None:
            battery_factor = 1.0 / (1.0 + abs(metrics["battery"]["drain_rate"]))
            
        if "motor_health" in metrics and isinstance(metrics["motor_health"], dict) and "temp_stability" in metrics["motor_health"] and metrics["motor_health"]["temp_stability"] is not None:
            temp_factor = 1.0 / (1.0 + metrics["motor_health"]["temp_stability"])
        
        calculated_factors = [f for f in [battery_factor, temp_factor] if f is not None]
        return np.mean(calculated_factors) if calculated_factors else 0.0

    def _calculate_control_quality(self, metrics: Dict) -> float:
        """Calculate overall control quality score."""
        if not metrics or "control" not in metrics or not isinstance(metrics["control"], dict):
            return 0.0
        
        control_metrics = metrics["control"]
        responsiveness = control_metrics.get("responsiveness")
        smoothness = control_metrics.get("smoothness")
        
        factors = []
        if responsiveness is not None: factors.append(responsiveness)
        if smoothness is not None: factors.append(smoothness)
        
        return np.mean(factors) if factors else 0.0
    
    def _classify_anomaly(self, features_row: np.ndarray, feature_keys: List[str]) -> str:
        """Classify type of anomaly based on feature values and their keys."""
        # Example: Find which feature contributed most to the anomaly by deviation
        # This is a placeholder; real classification would be more complex.
        # For simplicity, let's check thresholds if we have specific knowledge.
        
        # Find indices for specific features if they exist
        altitude_idx = feature_keys.index("altitude") if "altitude" in feature_keys else -1
        velocity_idx = feature_keys.index("velocity") if "velocity" in feature_keys else -1
        battery_idx = feature_keys.index("battery") if "battery" in feature_keys else -1
        # motor_temps_idx = feature_keys.index("motor_temps") if "motor_temps" in feature_keys else -1

        # Simplified classification logic based on which features are present and their values
        if altitude_idx != -1 and features_row[altitude_idx] > np.mean(self.time_series["altitude"] or [0]) * 1.5: # Check if altitude has data
            return "altitude_spike"
        if velocity_idx != -1 and features_row[velocity_idx] > np.mean(self.time_series["velocity"] or [0]) * 1.5:
            return "velocity_spike"
        if battery_idx != -1 and features_row[battery_idx] < np.mean(self.time_series["battery"] or [100]) * 0.5: # Assuming battery is %
            return "battery_low_anomaly"
        # if motor_temps_idx != -1 and features_row[motor_temps_idx] > np.mean(self.time_series.get("motor_temps") or [0]) * 1.2 :
        # return "temperature_anomaly" # If motor_temps data was reliable

        # Fallback based on max deviation if specific rules don't apply
        # This requires z-scores or similar normalized values to be meaningful
        # For now, a generic fallback
        return "general_flight_parameter_anomaly"
    
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