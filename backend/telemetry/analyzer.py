# telemetry/analyzer.py
# Focused, robust, duplicate-proof time-series builder + KPI/anomaly helpers.
from __future__ import annotations
from dataclasses import dataclass
from datetime   import datetime, timezone
from typing     import Dict, List, Any, Optional, Tuple, Set, Union

import numpy  as np
import pandas as pd
import logging
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble      import IsolationForest
import re
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
@dataclass
class AnomalyDetection:
    type: str
    timestamp: pd.Timestamp
    description: str
    severity: str
    data: Dict[str, Any]


# -----------------------------------------------------------------------------
class TelemetryAnalyzer:
    """Advanced analytics on telemetry data from multiple UAV platforms."""

    # Unit metadata extracted from MAVLink specifications
    TELEMETRY_UNITS = {
        # Position and altitude units
        "lat": {"unit": "deg", "scale": 1e-7, "for_fields": ["lat", "latitude", "lng", "lon", "longitude"]},
        "lon": {"unit": "deg", "scale": 1e-7, "for_fields": ["lon", "lng", "longitude"]},
        "alt": {"unit": "m", "scale": 1.0, "for_fields": ["alt", "altitude", "height", "terrain_height"]},
        "relative_alt": {"unit": "m", "scale": 1e-3, "for_fields": ["relative_alt", "relative_altitude"]},
        "climb": {"unit": "m/s", "scale": 1.0, "for_fields": ["climb", "climb_rate", "vspeed"]},
        
        # Velocity units
        "vx": {"unit": "m/s", "scale": 0.01, "for_fields": ["vx", "velocity_x", "vel_x"]},
        "vy": {"unit": "m/s", "scale": 0.01, "for_fields": ["vy", "velocity_y", "vel_y"]},
        "vz": {"unit": "m/s", "scale": 0.01, "for_fields": ["vz", "velocity_z", "vel_z"]},
        "groundspeed": {"unit": "m/s", "scale": 1.0, "for_fields": ["groundspeed", "ground_speed", "gspeed"]},
        "airspeed": {"unit": "m/s", "scale": 1.0, "for_fields": ["airspeed", "air_speed", "aspeed"]},
        
        # Battery and power units
        "voltage": {"unit": "V", "scale": 1e-3, "for_fields": ["voltage", "volt", "voltage_battery", "voltages"]},
        "current": {"unit": "A", "scale": 0.01, "for_fields": ["current", "current_battery", "curr"]},
        "remaining": {"unit": "%", "scale": 1.0, "for_fields": ["battery_remaining", "remaining", "capacity"]},
        
        # Attitude units
        "roll": {"unit": "rad", "scale": 1.0, "for_fields": ["roll", "roll_angle"]},
        "pitch": {"unit": "rad", "scale": 1.0, "for_fields": ["pitch", "pitch_angle"]},
        "yaw": {"unit": "rad", "scale": 1.0, "for_fields": ["yaw", "yaw_angle", "heading"]},
        
        # GPS units
        "eph": {"unit": "m", "scale": 1.0, "for_fields": ["eph", "h_accuracy", "hdop"]},
        "epv": {"unit": "m", "scale": 1.0, "for_fields": ["epv", "v_accuracy", "vdop"]},
        "satellites_visible": {"unit": "count", "scale": 1.0, "for_fields": ["satellites_visible", "satellites", "sats"]}
    }
    
    # Build reverse lookup for unit identification
    FIELD_TO_UNIT_MAP = {}
    for unit_key, unit_info in TELEMETRY_UNITS.items():
        for field in unit_info["for_fields"]:
            FIELD_TO_UNIT_MAP[field] = {
                "base_field": unit_key,
                "unit": unit_info["unit"],
                "scale": unit_info["scale"]
            }

    # -------------------------------------------------------------------------
    def __init__(self, telemetry: Dict[str, pd.DataFrame]) -> None:
        self.telemetry = telemetry
        self.cache: Dict[str, Any] = {}
        self.time_series: Dict[str, List[float]] = {}
        self.unit_info: Dict[str, Dict[str, Any]] = {}
        
        # Process the telemetry data
        logger.info("Processing telemetry data into time series")
        self._process_telemetry_data()
        
        # Verify we have valid data
        if not self.time_series.get("timestamp", []):
            logger.warning("No valid time series data produced after processing")
        else:
            logger.info(f"Successfully processed {len(self.time_series) - 1} data fields")

    # -------------------------------------------------------------------------
    # TIME-SERIES PREP
    # -------------------------------------------------------------------------
    IMPORTANT_PATTERNS = [
        "alt", "height",
        "lat", "lon",
        "speed", "vel", "groundspeed", "airspeed",
        "roll", "pitch", "yaw",
        "volt", "current", "battery", "remaining", "temperature",
        "fix_type", "satellites",
        "rc", "chan", "servo"
    ]

    def _process_telemetry_data(self) -> None:
        """Process telemetry DataFrames into a unified time series dictionary."""
        if not self.telemetry:
            logger.warning("No telemetry data provided")
            self.time_series = {"timestamp": []}
            return

        # Extract the message types we care about most for flight analysis
        key_message_types = [
            'GLOBAL_POSITION_INT',  # Position and altitude data
            'LOCAL_POSITION_NED',   # Local position data
            'VFR_HUD',              # Speed and altitude data
            'ATTITUDE',             # Roll, pitch, yaw
            'BATTERY_STATUS',       # Battery voltage, current, remaining
            'SYS_STATUS',           # System status including battery
            'GPS_RAW_INT',          # GPS data
            'GPS2_RAW',             # Secondary GPS
            'ALTITUDE',             # Altitude data (various types)
            'TERRAIN_REPORT',       # Terrain data and relative height
            'RC_CHANNELS',          # RC receiver channel pulses      
        ]
        
        # Additional message types that might contain useful data
        fallback_types = [
            'AHRS',                 # Attitude and position estimates
            'AHRS2',                # Alternative AHRS data
            'AHRS3',                # 3rd AHRS system data
            'RC_CHANNELS',          # RC channel data
            'SERVO_OUTPUT_RAW',     # Servo outputs
            'HEARTBEAT',            # System status
            'STATUSTEXT',           # Status messages
        ]
        
        # Combine all available message types
        available_types = [mt for mt in key_message_types if mt in self.telemetry]
        if len(available_types) < 3:  # If we don't have enough key message types
            # Add fallback types that are available
            available_types.extend([mt for mt in fallback_types if mt in self.telemetry])
        
        if not available_types:
            logger.warning("No usable message types found in telemetry data")
            self.time_series = {"timestamp": []}
            return
        
        logger.info(f"Found {len(available_types)} usable message types: {', '.join(available_types)}")
        
        # -------------------------------------------------------------------- #
        # First pass: collect timestamps from all frames to create master index
        # -------------------------------------------------------------------- #
        timestamps = []
        for msg_type in available_types:
            df = self.telemetry.get(msg_type)
            if df is not None and not df.empty:
                # If timestamp is the index, reset it to a column for processing
                if df.index.name == "timestamp":
                    timestamps.extend(df.index.tolist())
                elif "timestamp" in df.columns:
                    timestamps.extend(df["timestamp"].tolist())
        
        if not timestamps:
            logger.warning("No timestamps found in telemetry data")
            self.time_series = {"timestamp": []}
            return
            
        # Create a sorted, unique timestamp index
        self.master_index = sorted(set(timestamps))
        logger.info(f"Created master index with {len(self.master_index)} unique timestamps")
        
        # -------------------------------------------------------------------- #
        # Second pass: collect and align all numeric fields with master index
        # -------------------------------------------------------------------- #
        numeric_data = {}
        field_origins = {}
        
        for msg_type in available_types:
            df = self.telemetry.get(msg_type)
            if df is None or df.empty:
                continue
            
            # Ensure DataFrame has timestamp as index
            if df.index.name != "timestamp" and "timestamp" in df.columns:
                df = df.set_index("timestamp")
            
            # Process each column in the DataFrame
            for col in df.columns:
                # Only process numeric columns
                try:
                    # Try to convert to numeric
                    series = pd.to_numeric(df[col], errors="coerce").dropna()
                    if series.empty:
                        continue
                    
                    # Skip timestamp column if it was included
                    lc = col.lower()
                    if lc == "timestamp":
                        continue
                    
                    # Focus on important patterns
                    if not any(pat in lc for pat in self.IMPORTANT_PATTERNS):
                        continue
                    
                    # Create field name with message type prefix for clarity
                    field_name = f"{msg_type}_{col}"
                    numeric_data[field_name] = series
                    field_origins[field_name] = msg_type
                    
                    # Store unit information based on field name
                    self._extract_unit_info(field_name, col)
                    
                except Exception as e:
                    # If conversion fails, skip this column
                    logger.debug(f"Skipping non-numeric column {msg_type}_{col}: {str(e)}")
                    continue
        
        if not numeric_data:
            logger.warning("No numeric data extracted from telemetry")
            self.time_series = {"timestamp": []}
            return
        
        # -------------------------------------------------------------------- #
        # Build final time series dictionary with timestamps and numeric fields
        # -------------------------------------------------------------------- #
        try:
            # Create a unified DataFrame with all numeric series
            wide = pd.concat(numeric_data, axis=1, join="outer")
            
            # Ensure index is unique
            if not wide.index.is_unique:
                logger.info(f"Resolving {wide.index.duplicated().sum()} duplicate timestamps using mean aggregation")
                wide = wide.groupby(level=0).mean()
            
            # Sort by timestamp
            wide = wide.sort_index()
            
            # Handle sparsity with controlled forward/back filling
            wide = wide.ffill(limit=5).bfill(limit=5).fillna(0)
            
            # Convert to dictionary format for time series
            self.time_series = {
                "timestamp": wide.index.to_list(),
                **{c: wide[c].astype("float32").to_list() for c in wide.columns}
            }
            
            # Store field origins for reference
            self.cache["field_origins"] = field_origins
            
            # Store the wide DataFrame in cache for direct access if needed
            self.cache["wide_df"] = wide
            
            logger.info(f"Successfully processed {len(wide.columns)} telemetry fields with {len(wide)} time points")
            
            # Post-process specific fields for better units
            self._post_process_units()
            
        except Exception as e:
            # Handle any errors in processing
            logger.error(f"Error in _process_telemetry_data: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Provide a minimal time series if processing fails
            self.time_series = {"timestamp": timestamps[:min(1000, len(timestamps))]}

    def _post_process_units(self) -> None:
        """Post-process specific fields to standardize units."""
        # Process altitude fields
        for field in list(self.time_series.keys()):
            # Convert GLOBAL_POSITION_INT relative_alt from mm to m
            if "GLOBAL_POSITION_INT_relative_alt" in field and max(self.time_series[field]) > 1000:
                logger.info(f"Converting {field} from mm to m")
                self.time_series[field] = [val / 1000.0 for val in self.time_series[field]]
            
            # Convert GPS lat/lon from 1e7 degrees to degrees
            if any(pat in field for pat in ["GPS_RAW_INT_lat", "GPS_RAW_INT_lon", 
                                           "GLOBAL_POSITION_INT_lat", "GLOBAL_POSITION_INT_lon"]):
                if max(abs(val) for val in self.time_series[field]) > 180:
                    logger.info(f"Converting {field} from 1e7 degrees to degrees")
                    self.time_series[field] = [val / 1e7 for val in self.time_series[field]]
            
            # Convert battery voltage if needed (from mV to V)
            if "voltage" in field.lower() and max(self.time_series[field]) > 100:
                logger.info(f"Converting {field} from mV to V")
                self.time_series[field] = [val / 1000.0 for val in self.time_series[field]]

    # -------------------------------------------------------------------------
    # PUBLIC ENTRY
    # -------------------------------------------------------------------------
    def analyze_for_query(self, query: str) -> Dict[str, Any]:
        """Fast, on-demand answer builder.  (KPIs / anomalies are cached)."""
        if not self.time_series.get("timestamp"):
            return {"error": "No usable telemetry found."}

        now = datetime.now(timezone.utc)
        if ("metrics" not in self.cache or
                (now - self.cache.get("ts", now)).total_seconds() > 60):
            self.cache.update({
                "metrics":  self._calc_metrics(),
                "anomalies": self._detect_anomalies(),
                "kpis": self._calculate_kpis(),
                "ts": now,
            })

        q = query.lower()
        out: Dict[str, Any] = {}

        # ------- altitude
        if "altitude" in q or "height" in q:
            alt_analysis = self._analyze_altitude()
            if alt_analysis:
                out["altitude_analysis"] = alt_analysis

        # ------- battery
        if "battery" in q or "voltage" in q or "power" in q:
            bat_analysis = self._analyze_battery()
            if bat_analysis:
                out["battery_analysis"] = bat_analysis
                
        # ------- velocity/speed
        if "speed" in q or "velocity" in q:
            speed_analysis = self._analyze_speed()
            if speed_analysis:
                out["speed_analysis"] = speed_analysis
                
        # ------- GPS quality
        if "gps" in q or "satellite" in q or "fix" in q:
            gps_analysis = self._analyze_gps()
            if gps_analysis:
                out["gps_analysis"] = gps_analysis
                
        # ------- flight performance
        if "performance" in q or "flight quality" in q:
            out["performance_analysis"] = self.cache.get("kpis", {})

        # Add standard metrics and anomalies
        out.setdefault("metrics", self.cache["metrics"])
        out.setdefault("anomalies", self.cache["anomalies"])
        return out

    # -------------------------------------------------------------------------
    # SPECIALIZED ANALYSIS METHODS
    # -------------------------------------------------------------------------
    # def _analyze_altitude(self) -> Dict[str, Any]:
    #     """Perform detailed altitude analysis with improved handling of different altitude sources."""
    #     # Define altitude field priority list with known field characteristics
    #     altitude_fields_priority = [
    #         # Field name, is_mm_units, is_absolute, description
    #         ("GLOBAL_POSITION_INT_relative_alt", False, False, "MAVLink relative altitude (already in m)"),
    #         ("ALTITUDE_altitude_relative", False, False, "MAVLink relative altitude (already in m)"),
    #         ("TERRAIN_REPORT_current_height", False, False, "MAVLink terrain relative height (already in m)"),
    #         ("VFR_HUD_alt", False, True, "MAVLink VFR HUD altitude (usually absolute, in m)"),
    #         ("LOCAL_POSITION_NED_z", False, False, "MAVLink local position Z (already in m, negated)"),
    #         ("GPS_RAW_INT_alt", False, True, "GPS altitude above MSL (usually absolute, in m)"),
    #         ("AHRS_altitude", False, True, "AHRS altitude (usually absolute, in m)"),
    #         ("AHRS2_altitude", False, True, "AHRS2 altitude (usually absolute, in m)"),
    #         ("AHRS3_altitude", False, True, "AHRS3 altitude (usually absolute, in m)"),
    #     ]
        
    #     logger.info("Starting altitude analysis")
        
    #     # Check all fields in order of priority
    #     alt_field = None
    #     alt_is_mm = False
    #     alt_is_absolute = False
    #     alt_description = None
        
    #     for field, is_mm, is_absolute, description in altitude_fields_priority:
    #         if field in self.time_series:
    #             alt_field = field
    #             alt_is_mm = is_mm
    #             alt_is_absolute = is_absolute
    #             alt_description = description
    #             logger.info(f"Selected altitude field: {field} ({description})")
    #             break
        
    #     # If no exact match found, try partial matching for fallback
    #     if not alt_field:
    #         # Look for any field containing altitude or height keywords
    #         for key in self.time_series.keys():
    #             if key != "timestamp" and any(term in key.lower() for term in ["alt", "height", "terrain"]):
    #                 alt_field = key
    #                 # Make educated guess about format
    #                 alt_is_mm = "relative_alt" in key.lower() and max(self.time_series[key]) > 1000
    #                 alt_is_absolute = any(term in key.lower() for term in ["gps", "position", "amsl", "absolute"])
    #                 alt_description = "Fallback altitude field (format estimated)"
    #                 logger.info(f"Using fallback altitude field: {key} (estimated format)")
    #                 break
        
    #     # If still no altitude field found, give up
    #     if not alt_field:
    #         logger.warning("No usable altitude field found in telemetry data")
    #         return {}
        
    #     # Get raw altitude values
    #     alt_values_raw = np.array(self.time_series[alt_field])
        
    #     # Apply conversion for mm values if needed
    #     if alt_is_mm or (max(alt_values_raw) > 1000 and "relative_alt" in alt_field):
    #         logger.info(f"Converting {alt_field} from mm to m")
    #         alt_values = alt_values_raw / 1000.0
    #     else:
    #         alt_values = alt_values_raw
            
    #     # Special handling for LOCAL_POSITION_NED.z which is negative of height
    #     if "LOCAL_POSITION_NED_z" in alt_field:
    #         logger.info("Negating LOCAL_POSITION_NED.z to get height")
    #         alt_values = -alt_values

    #     # Handle absolute altitudes (convert to relative)
    #     if alt_is_absolute:
    #         logger.info("Processing absolute altitude to extract relative height")
            
    #         # Sort values and use percentile method to estimate ground level
    #         sorted_vals = np.sort(alt_values)
            
    #         # Use 10th percentile as ground level to be robust against outliers
    #         ground_idx = min(int(len(sorted_vals) * 0.1), len(sorted_vals) - 1)
    #         ground_level_estimate = sorted_vals[max(0, ground_idx)]
            
    #         logger.info(f"Estimated ground level: {ground_level_estimate:.1f}m")
            
    #         # Verify this is reasonable (must be positive and not too large)
    #         if ground_level_estimate > 0 and ground_level_estimate < 10000:
    #             # Convert to relative altitude by subtracting ground level
    #             alt_values = alt_values - ground_level_estimate
    #             logger.info(f"Converted absolute to relative: {np.min(alt_values):.1f}m to {np.max(alt_values):.1f}m")
    #         else:
    #             logger.warning(f"Unreasonable ground level estimate: {ground_level_estimate:.1f}m")
    #             # If estimate is unreasonable, try a different approach
    #             # Use the minimum value as reference
    #             ground_level_estimate = np.min(alt_values)
    #             alt_values = alt_values - ground_level_estimate
    #             logger.info(f"Used minimum as reference: {np.min(alt_values):.1f}m to {np.max(alt_values):.1f}m")
        
    #     # Final safety check for unreasonable values
    #     max_expected_altitude = 10000  # 10km - max reasonable UAV altitude
    #     if np.max(alt_values) > max_expected_altitude:
    #         logger.warning(f"Altitude values suspiciously high: {np.max(alt_values):.1f}m, applying correction")
    #         # Try to determine correct scale factor
    #         if np.max(alt_values) > 10000:
    #             scale_factor = 1000.0
    #         else:
    #             scale_factor = 10.0
    #         alt_values = alt_values / scale_factor
    #         logger.info(f"Scaled altitude values by 1/{scale_factor}")
        
    #     # Get timestamps for phase detection
    #     timestamps = self.time_series["timestamp"]
        
    #     # Find takeoff and landing points
    #     takeoff_idx, landing_idx = self._detect_takeoff_landing(alt_values)
    #     logger.info(f"Detected takeoff/landing indices: {takeoff_idx}, {landing_idx}")
        
    #     # Calculate climb/descent rates
    #     try:
    #         # Convert timestamps to seconds for rate calculation
    #         time_values = np.array([pd.to_datetime(ts).timestamp() for ts in timestamps])
    #         time_diffs = np.diff(time_values)
            
    #         # Protect against zero time differences
    #         time_diffs = np.maximum(time_diffs, 0.001)
            
    #         # Calculate vertical speed
    #         climb_rates = np.diff(alt_values) / time_diffs
            
    #         max_climb_rate = float(np.max(climb_rates))
    #         max_descent_rate = float(np.min(climb_rates))
            
    #         logger.info(f"Max climb/descent rates: {max_climb_rate:.2f}m/s, {max_descent_rate:.2f}m/s")
            
    #         max_climb_idx = np.argmax(climb_rates)
    #         max_descent_idx = np.argmin(climb_rates)
            
    #     except Exception as e:
    #         logger.error(f"Error calculating climb rates: {str(e)}")
    #         climb_rates = np.zeros(len(alt_values)-1)
    #         max_climb_rate = 0.0
    #         max_descent_rate = 0.0
    #         max_climb_idx = None
    #         max_descent_idx = None
        
    #     # Calculate key statistics
    #     stats = {
    #         "max": float(np.max(alt_values)),
    #         "min": float(np.min(alt_values)),
    #         "mean": float(np.mean(alt_values)),
    #         "median": float(np.median(alt_values)),
    #         "std": float(np.std(alt_values)),
    #         "range": float(np.max(alt_values) - np.min(alt_values))
    #     }
        
    #     logger.info(f"Altitude statistics: max={stats['max']:.1f}m, min={stats['min']:.1f}m, range={stats['range']:.1f}m")
        
    #     # Return comprehensive analysis
    #     return {
    #         "field_used": alt_field,
    #         "is_absolute_altitude": alt_is_absolute,
    #         "description": alt_description,
    #         "conversion_applied": alt_is_mm or alt_is_absolute,
    #         "statistics": stats,
    #         "flight_phases": {
    #             "takeoff_time": timestamps[takeoff_idx] if takeoff_idx is not None else None,
    #             "landing_time": timestamps[landing_idx] if landing_idx is not None else None,
    #             "max_climb_rate": max_climb_rate,
    #             "max_descent_rate": max_descent_rate,
    #             "flight_duration": (
    #                 (pd.to_datetime(timestamps[landing_idx]) - pd.to_datetime(timestamps[takeoff_idx])).total_seconds()
    #                 if takeoff_idx is not None and landing_idx is not None else None
    #             )
    #         }
    #     }

    def _analyze_altitude(self) -> Dict[str, Any]:
        """Return realistic altitude stats plus take-off / landing info."""
        # ── candidate fields, ordered by preference ----------------------------
        priority = [
            ("GLOBAL_POSITION_INT_relative_alt", True,  False,
            "MAVLink relative altitude (mm → m)"),
            ("ALTITUDE_altitude_relative",       False, False,
            "MAVLink relative altitude (m)"),
            ("TERRAIN_REPORT_current_height",    False, False,
            "Terrain-relative height (m)"),
            ("VFR_HUD_alt",                      False, True,
            "VFR-HUD absolute altitude (m)"),
            ("LOCAL_POSITION_NED_z",             False, False,
            "Local NED Z (negated m)"),
            ("GPS_RAW_INT_alt",                  False, True,
            "GPS MSL altitude (absolute m)"),
            ("AHRS_altitude",                    False, True, "AHRS altitude"),
            ("AHRS2_altitude",                   False, True, "AHRS2 altitude"),
            ("AHRS3_altitude",                   False, True, "AHRS3 altitude"),
        ]

        alt_field = alt_is_mm = alt_is_abs = False
        description = ""
        for f, mm, abs_, desc in priority:
            if f in self.time_series:
                alt_field, alt_is_mm, alt_is_abs, description = f, mm, abs_, desc
                break

        # fallback: anything containing “alt” / “height”
        if not alt_field:
            for key in self.time_series:
                if key == "timestamp":
                    continue
                lk = key.lower()
                if any(tok in lk for tok in ("alt", "height", "terrain")):
                    alt_field = key
                    alt_is_mm = "relative_alt" in lk and max(self.time_series[key]) > 1000
                    alt_is_abs = any(tok in lk for tok in ("gps", "position", "amsl", "absolute"))
                    description = "Fallback altitude field (format estimated)"
                    break

        if not alt_field:
            logger.warning("No altitude field found")
            return {}

        # ── raw values ---------------------------------------------------------
        vals = np.asarray(self.time_series[alt_field], dtype=float)

        # If the *current* magnitudes look like “already metres”, suppress the second division
        if alt_is_mm and vals.max() < 300:      # <300 m ⇒ not mm any more
            alt_is_mm = False

        # → convert only if needed
        if alt_is_mm or vals.max() > 1000:      # still looks like mm
            vals /= 1000.0
            conversion_applied = True
        else:
            conversion_applied = False

        # LOCAL_POSITION_NED.z sign convention
        if "LOCAL_POSITION_NED_z" in alt_field:
            vals = -vals

        # absolute → relative
        if alt_is_abs:
            ground = np.percentile(vals, 10)
            ground = ground if 0 < ground < 10000 else vals.min()
            vals = vals - ground

        alt_values = vals

        # ── timestamps ----------------------------------------------------------
        ts = [pd.to_datetime(t) for t in self.time_series["timestamp"]]
        if len(ts) < 3:
            return {}

        take_idx, land_idx = self._detect_takeoff_landing(alt_values)

        # climb / descent rates
        t_sec = np.asarray([t.timestamp() for t in ts])
        dz = np.diff(alt_values)
        dt = np.diff(t_sec)
        mask = dt >= 0.05
        rates = np.divide(dz[mask], dt[mask], out=np.zeros_like(dz[mask]), where=dt[mask] > 0)
        rates = rates[np.abs(rates) < 50]

        stats = {
            "max":    float(alt_values.max()),
            "min":    float(alt_values.min()),
            "mean":   float(alt_values.mean()),
            "median": float(np.median(alt_values)),
            "std":    float(alt_values.std()),
            "range":  float(alt_values.ptp()),
        }

        def safe(idx):
            return ts[idx] if idx is not None and 0 <= idx < len(ts) else None

        return {
            "field_used":           alt_field,
            "is_absolute_altitude": alt_is_abs,
            "description":          description,
            "conversion_applied":   conversion_applied,
            "statistics":           stats,
            "flight_phases": {
                "takeoff_time":     safe(take_idx),
                "landing_time":     safe(land_idx),
                "max_climb_rate":   float(rates.max()) if rates.size else 0.0,
                "max_descent_rate": float(rates.min()) if rates.size else 0.0,
                "flight_duration": (
                    (safe(land_idx) - safe(take_idx)).total_seconds()
                    if take_idx is not None and land_idx is not None else None
                ),
            },
        }


    # def _analyze_battery(self) -> Dict[str, Any]:
    #     """Perform detailed battery analysis."""
    #     # Try to find battery-related fields
    #     # voltage_key = self._pick_key(["voltage_battery", "volt"])
    #     current_key = self._pick_key(["current_battery", "current"])
    #     remaining_key = self._pick_key(["battery_remaining", "remaining"])
        
    #     result = {"fields_used": []}
        
    #     # Analyze voltage if available
    #     if voltage_key:
    #         result["fields_used"].append(voltage_key)
    #         voltage_values = np.array(self.time_series[voltage_key])
            
    #         # Normalize values based on likely scale
    #         if np.max(voltage_values) > 100:  # Likely in millivolts
    #             voltage_values = voltage_values / 1000.0
                
    #         result["voltage"] = {
    #             "initial": float(voltage_values[0]),
    #             "final": float(voltage_values[-1]),
    #             "min": float(np.min(voltage_values)),
    #             "max": float(np.max(voltage_values)),
    #             "drop_percent": float((voltage_values[0] - voltage_values[-1]) / voltage_values[0] * 100)
    #             if voltage_values[0] > 0 else 0
    #         }
        
    #     # Analyze current if available
    #     if current_key:
    #         result["fields_used"].append(current_key)
    #         current_values = np.array(self.time_series[current_key])
            
    #         # Normalize values based on likely scale
    #         if np.max(current_values) > 1000:  # Likely in milliamps
    #             current_values = current_values / 1000.0
                
    #         result["current"] = {
    #             "min": float(np.min(current_values)),
    #             "max": float(np.max(current_values)),
    #             "mean": float(np.mean(current_values)),
    #             "peak_times": [
    #                 self.time_series["timestamp"][i] 
    #                 for i in np.where(current_values > np.mean(current_values) + 2*np.std(current_values))[0]
    #             ][:5]  # Limit to 5 peak times
    #         }
        
    #     # Analyze remaining capacity if available
    #     if remaining_key:
    #         result["fields_used"].append(remaining_key)
    #         remaining_values = np.array(self.time_series[remaining_key])
            
    #         result["remaining"] = {
    #             "initial": float(remaining_values[0]),
    #             "final": float(remaining_values[-1]),
    #             "consumption_rate": float((remaining_values[0] - remaining_values[-1]) / len(remaining_values))
    #             if len(remaining_values) > 1 else 0
    #         }
            
    #     # If we have both voltage and current, estimate power
    #     if voltage_key and current_key:
    #         voltage_values = np.array(self.time_series[voltage_key])
    #         current_values = np.array(self.time_series[current_key])
            
    #         # Normalize if needed
    #         if np.max(voltage_values) > 100:
    #             voltage_values = voltage_values / 1000.0
    #         if np.max(current_values) > 1000:
    #             current_values = current_values / 1000.0
                
    #         # Calculate power (P = V * I)
    #         power_values = voltage_values * current_values
            
    #         result["power"] = {
    #             "min": float(np.min(power_values)),
    #             "max": float(np.max(power_values)),
    #             "mean": float(np.mean(power_values)),
    #             "total_energy_wh": float(np.trapz(power_values) / 3600)  # Integrate power over time (approx)
    #         }
            
    #     return result

    def _analyze_battery(self) -> Dict[str, Any]:
        """Perform detailed battery analysis."""
        # Prefer pack-sum, then SYS_STATUS, then first cell
        voltage_key   = self._pick_key(["voltages_sum", "voltage_battery", "voltages[0]"])
        current_key   = self._pick_key(["current_battery", "current"])
        remaining_key = self._pick_key(["battery_remaining", "remaining"])
        
        result: Dict[str, Any] = {"fields_used": []}
        ts = [pd.to_datetime(t).timestamp() for t in self.time_series["timestamp"]]

        # ——— Voltage ———
        if voltage_key:
            result["fields_used"].append(voltage_key)
            v = np.array(self.time_series[voltage_key], dtype=float)
            # mV→V
            if v.max() > 100:
                v = v / 1000.0
            result["voltage"] = {
                "initial":      float(v[0]),
                "final":        float(v[-1]),
                "min":          float(v.min()),
                "max":          float(v.max()),
                "drop_percent": float((v[0] - v[-1]) / v[0] * 100) if v[0] > 0 else 0.0
            }

        # ——— Current ———
        if current_key:
            result["fields_used"].append(current_key)
            c = np.array(self.time_series[current_key], dtype=float)
            # mA→A
            if c.max() > 1000:
                c = c / 1000.0
            mean_c = float(c.mean())
            std_c  = float(c.std())
            # Peak times > mean+2σ
            peaks = np.where(c > mean_c + 2*std_c)[0]
            peak_times = [self.time_series["timestamp"][i].isoformat()
                        for i in peaks][:5]
            result["current"] = {
                "min":         float(c.min()),
                "max":         float(c.max()),
                "mean":        mean_c,
                "std":         std_c,
                "peak_times":  peak_times
            }

        # ——— Remaining Capacity ———
        if remaining_key:
            result["fields_used"].append(remaining_key)
            r = np.array(self.time_series[remaining_key], dtype=float)
            duration = ts[-1] - ts[0] if len(ts) > 1 else 1.0
            result["remaining"] = {
                "initial":         float(r[0]),
                "final":           float(r[-1]),
                "consumption_pct_per_s":
                    float((r[0] - r[-1]) / duration) if duration > 0 else 0.0
            }

        # ——— Power & Energy ———
        if voltage_key and current_key:
            # reuse normalized v, c
            power = v * c
            # integrate P over real time to Wh
            energy_wh = float(np.trapz(power, x=ts) / 3600.0)
            result["power"] = {
                "min":            float(power.min()),
                "max":            float(power.max()),
                "mean":           float(power.mean()),
                "total_energy_wh": energy_wh
            }

        return result

    
    # def _analyze_speed(self) -> Dict[str, Any]:
    #     """Perform detailed speed analysis."""
    #     # Look for speed-related fields
    #     groundspeed_key = self._pick_key(["groundspeed", "ground_speed"])
    #     airspeed_key = self._pick_key(["airspeed", "air_speed"])
    #     velocity_keys = [k for k in self.time_series.keys() if any(p in k.lower() for p in ["vx", "vy", "vz"])]
        
    #     result = {"fields_used": []}
        
    #     # Analyze groundspeed if available
    #     if groundspeed_key:
    #         result["fields_used"].append(groundspeed_key)
    #         speed_values = np.array(self.time_series[groundspeed_key])
            
    #         result["groundspeed"] = {
    #             "max": float(np.max(speed_values)),
    #             "mean": float(np.mean(speed_values)),
    #             "std": float(np.std(speed_values)),
    #             "percentile_95": float(np.percentile(speed_values, 95))
    #         }
            
    #     # Analyze airspeed if available
    #     if airspeed_key:
    #         result["fields_used"].append(airspeed_key)
    #         speed_values = np.array(self.time_series[airspeed_key])
            
    #         result["airspeed"] = {
    #             "max": float(np.max(speed_values)),
    #             "mean": float(np.mean(speed_values)),
    #             "std": float(np.std(speed_values)),
    #             "percentile_95": float(np.percentile(speed_values, 95))
    #         }
            
    #     # If we have velocity components, calculate 3D velocity
    #     if len(velocity_keys) >= 2:
    #         result["fields_used"].extend(velocity_keys)
    #         # Combine velocity components (using available ones)
    #         vel_components = []
    #         for component in ["vx", "vy", "vz"]:
    #             key = self._pick_key([component])
    #             if key:
    #                 vel_components.append(np.array(self.time_series[key]) / 100.0)  # Convert cm/s to m/s
    #             else:
    #                 vel_components.append(np.zeros(len(self.time_series["timestamp"])))
                    
    #         # Calculate 3D velocity magnitude
    #         if len(vel_components) >= 2:  # At least 2D velocity
    #             velocity_magnitude = np.sqrt(sum(v**2 for v in vel_components))
                
    #             result["velocity_3d"] = {
    #                 "max": float(np.max(velocity_magnitude)),
    #                 "mean": float(np.mean(velocity_magnitude)),
    #                 "std": float(np.std(velocity_magnitude))
    #             }
                
    #     return result

    def _analyze_speed(self) -> Dict[str, Any]:
        """Perform detailed speed analysis."""
        # Look for speed-related fields
        groundspeed_key = self._pick_key(["groundspeed", "ground_speed"])
        airspeed_key   = self._pick_key(["airspeed",    "air_speed"])
        # Identify any 3D velocity components
        velocity_keys  = [k for k in self.time_series.keys()
                        if any(seg in k.lower() for seg in ["vx", "vy", "vz"])]

        result: Dict[str, Any] = {"fields_used": []}

        # Helper: convert knots → m/s if values exceed 50
        def _ensure_ms(arr: np.ndarray) -> np.ndarray:
            return arr * 0.514444 if arr.max() > 50 else arr

        # ———– Grounds­peed ———–
        if groundspeed_key:
            result["fields_used"].append(groundspeed_key)
            gs = np.array(self.time_series[groundspeed_key], dtype=float)
            gs = _ensure_ms(gs)
            result["groundspeed"] = {
                "max":           float(gs.max()),
                "mean":          float(gs.mean()),
                "std":           float(gs.std()),
                "percentile_95": float(np.percentile(gs, 95)),
            }

        # ———– Air­speed ———–
        if airspeed_key:
            result["fields_used"].append(airspeed_key)
            ap = np.array(self.time_series[airspeed_key], dtype=float)
            ap = _ensure_ms(ap)
            result["airspeed"] = {
                "max":           float(ap.max()),
                "mean":          float(ap.mean()),
                "std":           float(ap.std()),
                "percentile_95": float(np.percentile(ap, 95)),
            }

        # ———– 3D Velocity ———–
        if len(velocity_keys) >= 2:
            result["fields_used"].extend(velocity_keys)
            # build component arrays (cm/s → m/s)
            comps: List[np.ndarray] = []
            for axis in ["vx", "vy", "vz"]:
                key = self._pick_key([axis])
                if key:
                    vals = np.array(self.time_series[key], dtype=float)
                    comps.append(vals / 100.0)
                else:
                    comps.append(np.zeros(len(self.time_series["timestamp"])))
            vel3 = np.sqrt(sum(c**2 for c in comps))
            result["velocity_3d"] = {
                "max":  float(vel3.max()),
                "mean": float(vel3.mean()),
                "std":  float(vel3.std()),
            }

        return result

    # def _analyze_gps(self) -> Dict[str, Any]:
    #     """
    #     Analyse GPS quality and position data.
    #     """
    #     # ---------- pick available field names --------------------------------
    #     fix_type_key  = self._pick_key(["fix_type"])
    #     satellites_key = self._pick_key(["satellites_visible", "satellites"])
    #     lat_key       = self._pick_key(["lat"])
    #     lon_key       = self._pick_key(["lon"])
    #     ts_key        = "timestamp"          # always present in self.time_series

    #     result: Dict[str, Any] = {"fields_used": []}

    #     # -------------------- FIX-TYPE STATISTICS -----------------------------
    #     if fix_type_key:
    #         result["fields_used"].append(fix_type_key)
    #         fix_vals = np.asarray(self.time_series[fix_type_key])

    #         uniq, counts = np.unique(fix_vals, return_counts=True)
    #         changes = np.nonzero(np.diff(fix_vals) != 0)[0]
    #         transitions = [
    #             {
    #                 "time": str(self.time_series[ts_key][i + 1]),
    #                 "from": int(fix_vals[i]),
    #                 "to": int(fix_vals[i + 1]),
    #             }
    #             for i in changes
    #         ]

    #         result["fix_type"] = {
    #             "counts": {int(t): int(c) for t, c in zip(uniq, counts)},
    #             "transitions": transitions[:10],
    #             "no_fix_percentage": float(np.sum(fix_vals < 2) / len(fix_vals) * 100),
    #             "good_fix_percentage": float(np.sum(fix_vals >= 3) / len(fix_vals) * 100),
    #         }

    #     # -------------------- SATELLITE STATISTICS ----------------------------
    #     if satellites_key:
    #         result["fields_used"].append(satellites_key)
    #         sats = np.asarray(self.time_series[satellites_key])
    #         result["satellites"] = {
    #             "min": int(sats.min()),
    #             "max": int(sats.max()),
    #             "mean": float(sats.mean()),
    #             "poor_signal_percentage": float(np.sum(sats < 6) / len(sats) * 100),
    #         }

    #     # -------------------- POSITION / DISTANCE -----------------------------
    #     if lat_key and lon_key:
    #         result["fields_used"].extend([lat_key, lon_key])

    #         lat = np.asarray(self.time_series[lat_key], dtype=float)
    #         lon = np.asarray(self.time_series[lon_key], dtype=float)

    #         # *** NEW: force timestamp column to datetime64 ***
    #         ts_all = np.array(self.time_series[ts_key], dtype="datetime64[ns]")

    #         # Convert 1 e7-scaled integers → degrees if needed
    #         if np.abs(lat).max() > 90:
    #             lat /= 1e7
    #         if np.abs(lon).max() > 180:
    #             lon /= 1e7

    #         # Keep only ‘good’ rows
    #         mask = (lat != 0) & (lon != 0)
    #         if fix_type_key:
    #             mask &= (np.asarray(self.time_series[fix_type_key]) >= 3)

    #         if mask.sum() < 2:
    #             result["position"] = {"error": "No reliable GPS data"}
    #             return result

    #         lat_g = lat[mask]
    #         lon_g = lon[mask]
    #         ts_g  = ts_all[mask]

    #         # Great-circle distances (Haversine)
    #         def hav_km(lat1, lon1, lat2, lon2):
    #             R = 6371.0
    #             dlat = np.radians(lat2 - lat1)
    #             dlon = np.radians(lon2 - lon1)
    #             a = (
    #                 np.sin(dlat / 2) ** 2
    #                 + np.cos(np.radians(lat1))
    #                 * np.cos(np.radians(lat2))
    #                 * np.sin(dlon / 2) ** 2
    #             )
    #             return 2 * R * np.arcsin(np.sqrt(a))

    #         seg_km = hav_km(lat_g[:-1], lon_g[:-1], lat_g[1:], lon_g[1:])

    #         # Speed sanity filter (> 120 m s-¹ → reject)
    #         dt_sec = (ts_g[1:] - ts_g[:-1]) / np.timedelta64(1, "s")
    #         vmax = 120.0  # m s-¹
    #         bad = (dt_sec <= 0) | ((seg_km * 1000.0 / dt_sec) > vmax)
    #         seg_km[bad] = 0.0

    #         total_km = float(seg_km.sum())

    #         result["position"] = {
    #             "start_lat": float(lat_g[0]),
    #             "start_lon": float(lon_g[0]),
    #             "end_lat": float(lat_g[-1]),
    #             "end_lon": float(lon_g[-1]),
    #             "distance_traveled_km": total_km,
    #             "return_distance_km": float(
    #                 hav_km(lat_g[0], lon_g[0], lat_g[-1], lon_g[-1])
    #             ),
    #         }

    #     return result

    def _analyze_gps(self) -> Dict[str, Any]:
        """
        Analyse GPS quality and position data.
        """
        # ---------- field selection ------------------------------------------
        fix_type_key   = self._pick_key(["fix_type"])
        satellites_key = self._pick_key(["satellites_visible", "satellites"])
        lat_key        = self._pick_key(["lat"])
        lon_key        = self._pick_key(["lon"])
        ts_key         = "timestamp"

        result: Dict[str, Any] = {"fields_used": []}

        # -------------------- FIX-TYPE STATISTICS ----------------------------
        if fix_type_key:
            result["fields_used"].append(fix_type_key)
            fix_vals = np.asarray(self.time_series[fix_type_key], dtype=int)
            ts_all   = np.array(self.time_series[ts_key], dtype="datetime64[ns]")

            uniq, counts = np.unique(fix_vals, return_counts=True)
            changes = np.nonzero(np.diff(fix_vals) != 0)[0]
            transitions = [
                {
                    "time": str(ts_all[i + 1]),
                    "from": int(fix_vals[i]),
                    "to":   int(fix_vals[i + 1]),
                }
                for i in changes
            ]

            # ----- dropout metrics ----------------
            no_fix_mask           = (fix_vals == 0)
            zero_fix_sample_count = int(no_fix_mask.sum())
            dropout_events         = [tr for tr in transitions if tr["to"] == 0]
            dropout_total          = len(dropout_events)
            first_loss_time        = dropout_events[0]["time"] if dropout_events else None

            # longest continuous 0-fix stretch
            if no_fix_mask.any():
                padded     = np.r_[0, no_fix_mask.astype(int), 0]
                diffs      = np.diff(padded)
                starts     = np.where(diffs == 1)[0]
                ends       = np.where(diffs == -1)[0]
                durations  = ((ts_all[ends - 1] - ts_all[starts])
                            / np.timedelta64(1, "s")).astype(float)
                longest_sec = float(durations.max()) if durations.size else 0.0
            else:
                longest_sec = 0.0

            result.update(
                {
                    "gps_signal_loss_count":          dropout_total,
                    "gps_signal_dropouts":            dropout_total,
                    "gps_signal_first_loss_time":     first_loss_time,
                    "gps_signal_longest_loss_duration_sec":longest_sec,
                    "gps_no_fix_percentage":   float(np.sum(fix_vals == 0) / len(fix_vals) * 100),
                    "gps_good_fix_percentage": float(np.sum(fix_vals >= 3) / len(fix_vals) * 100),
                    "gps_fix_transitions": transitions[:10], # max 10 transitions
                    "gps_fix_type_counts": {int(t): int(c) for t, c in zip(uniq, counts)},
                    "gps_zero_fix_samples":    zero_fix_sample_count
                }
            )

        # ----------- SATELLITE STATISTICS ----------
        if satellites_key:
            result["fields_used"].append(satellites_key)
            sats = np.asarray(self.time_series[satellites_key], dtype=int)
            result["satellites"] = {
                "min": int(sats.min()),
                "max": int(sats.max()),
                "mean": float(sats.mean()),
                "poor_signal_percentage": float(np.sum(sats < 6) / len(sats) * 100),
            }

        # ----------- POSITION / DISTANCE ------------
        if lat_key and lon_key:
            result["fields_used"].extend([lat_key, lon_key])

            lat = np.asarray(self.time_series[lat_key], dtype=float)
            lon = np.asarray(self.time_series[lon_key], dtype=float)
            ts_all = np.array(self.time_series[ts_key], dtype="datetime64[ns]")

            # Convert 1 e7-scaled integers → degrees
            if np.abs(lat).max() > 90:
                lat /= 1e7
            if np.abs(lon).max() > 180:
                lon /= 1e7

            mask = (lat != 0) & (lon != 0)
            if fix_type_key:
                mask &= (fix_vals >= 3)  # keep only good fixes

            if mask.sum() < 2:
                result["position"] = {"error": "No reliable GPS data"}
                return result

            lat_g, lon_g, ts_g = lat[mask], lon[mask], ts_all[mask]

            # Haversine distance in km
            def hav_km(lat1, lon1, lat2, lon2):
                R = 6371.0
                dlat = np.radians(lat2 - lat1)
                dlon = np.radians(lon2 - lon1)
                a = (np.sin(dlat / 2) ** 2 +
                    np.cos(np.radians(lat1)) *
                    np.cos(np.radians(lat2)) *
                    np.sin(dlon / 2) ** 2)
                return 2 * R * np.arcsin(np.sqrt(a))

            seg_km = hav_km(lat_g[:-1], lon_g[:-1], lat_g[1:], lon_g[1:])
            dt_sec = (ts_g[1:] - ts_g[:-1]) / np.timedelta64(1, "s")
            vmax   = 120.0
            seg_km[(dt_sec <= 0) | ((seg_km * 1000 / dt_sec) > vmax)] = 0.0

            result["position"] = {
                "start_lat": float(lat_g[0]),
                "start_lon": float(lon_g[0]),
                "end_lat":   float(lat_g[-1]),
                "end_lon":   float(lon_g[-1]),
                "distance_traveled_km": float(seg_km.sum()),
                "return_distance_km": float(
                    hav_km(lat_g[0], lon_g[0], lat_g[-1], lon_g[-1])
                ),
            }

        return result

    
    def _analyze_rc_signal(self) -> Dict[str, Any]:
        """
        Analyse RC-link quality and detect signal-loss events.
        If no usable RC data is present → {"error": "..."}.
        """
        result: Dict[str, Any] = {"fields_used": []}

        # Determine link-OK / link-lost for every sample
        link_ok: Optional[np.ndarray] = None

        # Preferred source: RSSI (% or 0-255)
        rssi_key = self._pick_key(["rssi"])
        if rssi_key:
            result["fields_used"].append(rssi_key)
            rssi_raw = np.asarray(self.time_series[rssi_key], dtype=float)

            # normalise to percent
            rssi_pct = (rssi_raw / 255.0) * 100.0 if rssi_raw.max() > 1.0 else rssi_raw * 100.0
            result["rssi"] = {
                "min":  float(rssi_pct.min()),
                "max":  float(rssi_pct.max()),
                "mean": float(rssi_pct.mean()),
            }

            # ≤ 5 % is considered lost
            link_ok = (rssi_pct > 5.0).astype(int)

        else:
            # Fallback: raw RC channel pulses (µs)
            chan_keys = [k for k in self.time_series if "chan" in k.lower() and "raw" in k.lower()]
            if chan_keys:
                result["fields_used"].extend(chan_keys)

                ts_len = len(self.time_series["timestamp"])
                link_ok = np.zeros(ts_len, dtype=int)
                for k in chan_keys:
                    vals = np.asarray(self.time_series[k], dtype=float)
                    link_ok = link_ok | (vals > 900.0).astype(int)    # any pulse >900 µs → link OK

                result["rssi"] = None

        # If we still have no data, bail out
        if link_ok is None or link_ok.size == 0:
            return {"error": "No RC signal or RSSI data in telemetry."}

        # Build transitions & basic counters
        loss_samples, transitions = self._rc__build_transitions(link_ok.astype(bool))
        result["rc_signal_transitions"] = transitions[:10]
        result["rc_signal_zero_samples"]  = loss_samples

        # Higher-level dropout statistics
        dropout_events = [tr for tr in transitions if tr["to"] == 0]
        result["rc_signal_loss_count"] = len(dropout_events)
        result["rc_signal_dropouts"] = len(dropout_events)
        result["rc_signal_first_loss_time"] = dropout_events[0]["time"] if dropout_events else None

        # longest continuous lost streak
        ts = np.array(self.time_series["timestamp"], dtype="datetime64[ns]")
        lost = (link_ok == 0)
        if lost.any():
            padded = np.r_[0, lost.astype(int), 0]
            diffs  = np.diff(padded)
            starts = np.where(diffs == 1)[0]
            ends   = np.where(diffs == -1)[0]
            durations = ((ts[ends - 1] - ts[starts]) / np.timedelta64(1, "s")).astype(float)
            result["rc_signal_longest_loss_duration_sec"] = float(durations.max()) if durations.size else 0.0
        else:
            result["rc_signal_longest_loss_duration_sec"] = 0.0

        return result


    def _rc__build_transitions(self, link_ok: np.ndarray) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Helper for `_analyze_rc_signal` – generate loss/recovery transitions.

        Parameters
        ----------
        link_ok : np.ndarray[bool]
            True where link is healthy, False where lost.

        Returns
        -------
        loss_count : int
            Total number of samples with link lost.
        transitions : list[dict]
            List of {time, from, to} edges (1 = OK, 0 = lost).
        """
        changes = np.nonzero(np.diff(link_ok.astype(int)) != 0)[0]
        transitions = [
            {
                "time": str(self.time_series["timestamp"][i + 1]),
                "from": int(link_ok[i]),
                "to":   int(link_ok[i + 1]),
            }
            for i in changes
        ]
        loss_count = int((~link_ok).sum())
        return loss_count, transitions

    # -------------------------------------------------------------------------
    # utility methods
    # -------------------------------------------------------------------------
    def _pick_key(self, patterns: List[str]) -> Optional[str]:
        """Find first key in time_series matching any of the patterns."""
        for key in self.time_series:
            if key == "timestamp":
                continue
            lck = key.lower()
            if any(p in lck for p in patterns):
                return key
        return None

    def _detect_takeoff_landing(
        self,
        altitude_values: np.ndarray,
        *,
        min_flight_alt: float = 2.0,       # m above “ground” that must be exceeded
        min_sustain_sec: float = 3.0       # seconds the aircraft must stay airborne
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Return indices (take-off_idx, landing_idx) inside *altitude_values*.

        • Automatically estimates the sampling-rate – no hard-coded Hz needed.  
        • Uses a rolling median of the first 5 % of samples as ground reference.  
        • Employs hysteresis (+min_flight_alt going up, +0.5 m coming down) so we
        don’t oscillate around the threshold.  
        • Requires the altitude to be above the threshold for *min_sustain_sec*
        before we call it ‘airborne’, and the same condition when coming down.
        """
        if len(altitude_values) < 10:
            return None, None  # not enough data to be meaningful

        # Ground reference = median of the first 5 % of the log
        first_chunk = altitude_values[: max(5, int(0.05 * len(altitude_values)))]
        ground_level = float(np.median(first_chunk))

        # Build a simple time-axis in seconds (assume uniform sampling)
        ts = np.arange(len(altitude_values), dtype="float32")
        if len(ts) >= 2:
            approx_dt = np.median(np.diff(ts)) or 1.0
            ts = ts * approx_dt

        # Hysteresis thresholds
        up_thr   = ground_level + min_flight_alt          # must cross this to be ‘airborne’
        down_thr = ground_level + 0.5                     # must drop below to be ‘landed’

        airborne = altitude_values > up_thr
        on_ground = altitude_values < down_thr

        # Convolve with a window long enough to satisfy *min_sustain_sec*
        sustain_samples = max(1, int(min_sustain_sec / (ts[1] - ts[0])))
        kernel = np.ones(sustain_samples, dtype=int)

        # True when condition is met for >= sustain_samples consecutively
        sustained_airborne = np.convolve(airborne, kernel, "same") >= sustain_samples
        sustained_ground   = np.convolve(on_ground, kernel, "same") >= sustain_samples

        # take-off = first transition ground → sustained_airborne
        takeoff_idx = None
        for i in range(1, len(sustained_airborne)):
            if sustained_airborne[i] and not sustained_airborne[i - 1]:
                takeoff_idx = i
                break

        # landing = last transition sustained_airborne → ground (after take-off)
        landing_idx = None
        if takeoff_idx is not None:
            for i in range(len(sustained_ground) - 1, takeoff_idx, -1):
                if sustained_ground[i] and not sustained_ground[i - 1]:
                    landing_idx = i
                    break

        return takeoff_idx, landing_idx

        
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate great-circle distance between two points in kilometers."""
        # Convert degrees to radians
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        r = 6371  # Radius of earth in kilometers
        return c * r

    # metrics & anomalies
    def _calc_metrics(self) -> Dict[str, Dict[str, float]]:
        metrics: Dict[str, Dict[str, float]] = {}
        for k, vals in self.time_series.items():
            if k == "timestamp":
                continue
            arr = np.asarray(vals, dtype="float32")
            metrics[k] = {
                "min":  float(arr.min()),
                "max":  float(arr.max()),
                "mean": float(arr.mean()),
                "std":  float(arr.std(ddof=0)),
                "variance": float(np.var(arr, ddof=0)),
                "count": len(arr)
            }
        return metrics

    def _detect_anomalies(self) -> List[Dict[str, Any]]:
        keys = [k for k in self.time_series if k != "timestamp"]
        if not keys or len(self.time_series["timestamp"]) < 10:
            return []

        # Limit to key metrics to avoid excessive dimensionality
        important_keys = []
        for pattern in ["alt", "battery", "volt", "current", "speed", "vx", "vy", "vz", "roll", "pitch", "yaw"]:
            matching_keys = [k for k in keys if pattern in k.lower()]
            if matching_keys:
                important_keys.extend(matching_keys[:2])  # At most 2 per pattern
                
        # If still too many, limit to most important ones
        if len(important_keys) > 10:
            important_keys = important_keys[:10]
        
        # If no important keys found, use a subset of available keys
        if not important_keys and keys:
            important_keys = keys[:min(10, len(keys))]
            
        if not important_keys:
            return []
            
        # Prepare data for anomaly detection
        try:
            X = np.column_stack([self.time_series[k] for k in important_keys]).astype("float32")
            # --- use a fresh scaler each call to avoid stale state ---
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            # ---------------------------------------------------------
            detector = IsolationForest(
                contamination=0.05, random_state=42, n_estimators=100
            )
            lbl = detector.fit_predict(X_scaled)
            
            decision_scores = detector.decision_function(X_scaled)
            
            anomalies = []
            for i, flag in enumerate(lbl):
                if flag == -1:  # Anomaly
                    # Determine which variable contributed most to the anomaly
                    point_scaled = X_scaled[i]
                    distances = np.abs(point_scaled - np.mean(X_scaled, axis=0))
                    most_anomalous_idx = np.argmax(distances)
                    most_anomalous_feature = important_keys[most_anomalous_idx]
                    
                    # Calculate severity (normalized score)
                    severity = float(np.abs(decision_scores[i]))
                    
                    anomalies.append({
                        "timestamp": self.time_series["timestamp"][i],
                        "type": f"{most_anomalous_feature}_anomaly",
                        "primary_factor": most_anomalous_feature,
                        "severity": severity,
                        "metrics": {k: float(X[i, idx]) for idx, k in enumerate(important_keys)},
                        "description": self._generate_anomaly_description(most_anomalous_feature, X[i, most_anomalous_idx])
                    })
            
            # Sort by severity
            return sorted(anomalies, key=lambda x: x["severity"], reverse=True)
        except Exception as e:
            logger.error(f"Error in anomaly detection: {str(e)}")
            logger.error(traceback.format_exc())
            return []
            
    def _generate_anomaly_description(self, feature: str, value: float) -> str:
        """Generate a human-readable description of an anomaly."""
        feature_type = None
        for pattern, ftype in [
            (("alt", "height"), "altitude"),
            (("vx", "vy", "vz", "speed", "ground", "air"), "velocity"),
            (("roll", "pitch", "yaw"), "attitude"),
            (("volt", "current", "battery", "remain"), "power"),
            (("gps", "fix", "satellite"), "navigation")
        ]:
            if any(p in feature.lower() for p in pattern):
                feature_type = ftype
                break
        
        if not feature_type:
            return f"Unusual value in {feature}"
            
        if feature_type == "altitude":
            return f"Abnormal altitude reading of {value:.1f}"
        elif feature_type == "velocity":
            return f"Unexpected {feature} measurement of {value:.1f}"
        elif feature_type == "attitude":
            return f"Unusual {feature} angle of {value:.1f} degrees"
        elif feature_type == "power":
            if "volt" in feature.lower():
                return f"Voltage anomaly: {value:.2f}V"
            elif "current" in feature.lower():
                return f"Current spike: {value:.2f}A"
            else:
                return f"Power system anomaly in {feature}: {value:.1f}"
        elif feature_type == "navigation":
            if "fix" in feature.lower():
                return f"GPS fix type changed to {int(value)}"
            else:
                return f"Navigation anomaly in {feature}: {value:.1f}"
        
        return f"Unusual value in {feature}: {value:.1f}"
    
    def _calculate_kpis(self) -> Dict[str, float]:
        """Calculate key performance indicators for the flight."""
        kpis = {}
        
        # Flight efficiency (based on altitude stability and power usage)
        alt_key = self._pick_key(["relative_alt", "_alt", "height"])
        if alt_key:
            alt_values = np.array(self.time_series[alt_key])
            # Normalize if needed
            if "relative_alt" in alt_key and np.max(alt_values) > 1000:
                alt_values = alt_values / 1000.0
                
            # Calculate altitude stability
            alt_stability = 1.0 / (1.0 + np.std(alt_values) / (np.mean(alt_values) + 0.1))
            kpis["altitude_stability"] = float(alt_stability)
        
        # Battery efficiency
        bat_key = self._pick_key(["battery_remaining", "voltage_battery"])
        if bat_key:
            bat_values = np.array(self.time_series[bat_key])
            # Calculate drain rate
            if len(bat_values) > 1:
                drain_rate = (bat_values[0] - bat_values[-1]) / len(bat_values)
                kpis["battery_efficiency"] = float(1.0 / (1.0 + drain_rate * 10))  # Normalize
        
        # Flight control quality (based on attitude stability)
        attitude_keys = []
        for att in ["roll", "pitch", "yaw"]:
            key = self._pick_key([att])
            if key:
                attitude_keys.append(key)
                
        if attitude_keys:
            att_stabilities = []
            for key in attitude_keys:
                values = np.array(self.time_series[key])
                stability = 1.0 / (1.0 + np.std(values))
                att_stabilities.append(stability)
                
            kpis["attitude_stability"] = float(np.mean(att_stabilities))
        
        # Overall performance score
        if kpis:
            kpis["overall_performance"] = float(np.mean(list(kpis.values())))
            
        return kpis

    # -------------------------------------------------------------------------
    # Add new filtering methods
    # -------------------------------------------------------------------------
    def _filter_relevant_metrics(self, query: str) -> Dict[str, Dict[str, float]]:
        """
        Extract metrics relevant to a specific query from the telemetry data.
        This method analyzes the query semantically to determine which metrics
        are most relevant and returns their statistics.
        
        Args:
            query: User query string
            
        Returns:
            Dictionary of relevant metrics with their statistics
        """
        if not self.time_series.get("timestamp"):
            return {"error": "No usable telemetry found."}
            
        # Get all available metrics with basic stats
        if "metrics" not in self.cache:
            self.cache["metrics"] = self._calc_metrics()
        
        all_metrics = self.cache["metrics"]
        
        # Convert query to lowercase for easier matching
        q = query.lower()
        
        # Define relevance categories for different query types
        relevance_map = {
            "altitude": ["alt", "height", "elevation", "climb", "ascent", "descent"],
            "battery": ["battery", "volt", "current", "power", "charge", "energy"],
            "speed": ["speed", "velocity", "groundspeed", "airspeed", "vx", "vy", "vz"],
            "position": ["position", "lat", "lon", "gps", "location", "coordinate"],
            "attitude": ["roll", "pitch", "yaw", "attitude", "orientation", "rotation"],
            "motor": ["motor", "throttle", "rpm", "esc", "rotor", "propeller"],
            "general": ["flight", "stats", "overview", "summary", "telemetry", "data"]
        }
        
        # Determine relevant categories based on query
        relevant_categories = []
        for category, keywords in relevance_map.items():
            if any(keyword in q for keyword in keywords):
                relevant_categories.append(category)
                
        # If no specific category was matched, include general flight metrics
        if not relevant_categories or 'general' in relevant_categories:
            relevant_categories = list(relevance_map.keys())
            
        # Create patterns to match for each category
        patterns = []
        for category in relevant_categories:
            patterns.extend(relevance_map[category])
            
        # Filter metrics based on patterns
        relevant_metrics = {}
        
        # First pass: exact matches
        exact_matches = 0
        for field_name, field_stats in all_metrics.items():
            field_lower = field_name.lower()
            if any(pattern in field_lower for pattern in patterns):
                relevant_metrics[field_name] = field_stats
                exact_matches += 1
                
        # If we have too few exact matches, include more metrics
        if exact_matches < 3:
            # Include metrics from important categories
            priority_categories = ["altitude", "battery", "speed"]
            additional_patterns = []
            for category in priority_categories:
                if category in relevance_map:
                    additional_patterns.extend(relevance_map[category])
                    
            for field_name, field_stats in all_metrics.items():
                if field_name not in relevant_metrics:
                    field_lower = field_name.lower()
                    if any(pattern in field_lower for pattern in additional_patterns):
                        relevant_metrics[field_name] = field_stats
        
        # If still empty, include key metrics
        if not relevant_metrics:
            for field_name, field_stats in all_metrics.items():
                field_lower = field_name.lower()
                if any(term in field_lower for term in ["alt", "bat", "volt", "speed", "gps"]):
                    relevant_metrics[field_name] = field_stats
                    
            # Ensure we have at least some metrics
            if not relevant_metrics and all_metrics:
                # Include up to 5 key metrics
                key_fields = list(all_metrics.keys())[:min(5, len(all_metrics))]
                for field in key_fields:
                    relevant_metrics[field] = all_metrics[field]
        
        return relevant_metrics
    
    def _filter_relevant_anomalies(self, query: str) -> List[Dict[str, Any]]:
        """
        Filter anomalies based on the user query to return the most relevant ones.
        
        Args:
            query: User query string
            
        Returns:
            List of anomaly dictionaries relevant to the query
        """
        if not self.time_series.get("timestamp"):
            return []
            
        # Ensure anomalies are detected and cached
        if "anomalies" not in self.cache:
            self.cache["anomalies"] = self._detect_anomalies()
            
        all_anomalies = self.cache["anomalies"]
        
        # If no anomalies or empty query, return all anomalies
        if not all_anomalies or not query:
            return all_anomalies
            
        # Convert query to lowercase for matching
        q = query.lower()
        
        # Define relevance categories for different anomaly types
        relevance_map = {
            "altitude": ["alt", "height", "elevation", "climb", "descent"],
            "battery": ["battery", "volt", "current", "power", "energy"],
            "speed": ["speed", "velocity", "vx", "vy", "vz"],
            "gps": ["gps", "position", "lat", "lon", "fix", "satellite"],
            "attitude": ["roll", "pitch", "yaw", "attitude", "orientation"],
            "system": ["error", "warning", "fault", "issue", "problem", "anomaly"]
        }
        
        # Determine relevant categories based on query
        relevant_categories = []
        for category, keywords in relevance_map.items():
            if any(keyword in q for keyword in keywords):
                relevant_categories.append(category)
                
        # If no specific category was matched, check if query asks about problems in general
        if not relevant_categories:
            if any(term in q for term in ["problem", "issue", "anomaly", "concern", "error"]):
                # Include all categories for general problem queries
                relevant_categories = list(relevance_map.keys())
            else:
                # Default to return all anomalies if query is too vague
                return all_anomalies
                
        # Create patterns to match for each category
        patterns = []
        for category in relevant_categories:
            patterns.extend(relevance_map[category])
            
        # Filter anomalies based on patterns
        relevant_anomalies = []
        for anomaly in all_anomalies:
            # Check if primary factor or type matches any pattern
            primary_factor = anomaly.get("primary_factor", "").lower()
            anomaly_type = anomaly.get("type", "").lower()
            description = anomaly.get("description", "").lower()
            
            if any(pattern in primary_factor or pattern in anomaly_type or pattern in description for pattern in patterns):
                relevant_anomalies.append(anomaly)
                
        # If no matches found but we had anomalies, return all of them (better to show all than none)
        if not relevant_anomalies and all_anomalies:
            return all_anomalies
            
        return relevant_anomalies

    def _extract_unit_info(self, field_name: str, column_name: str) -> None:
        """
        Extract unit information from field names and store for later conversion.
        
        This method attempts to determine the unit for a field based on:
        1. Field name matching to known unit patterns
        2. Message type conventions from MAVLink
        3. Embedded unit information in column names or metadata
        
        Args:
            field_name: Full field name with message type prefix
            column_name: Original column name from DataFrame
        """
        lower_col = column_name.lower()
        
        # Look for unit patterns in column name 
        # Some logs have units in parentheses or brackets like "voltage(mV)" or "altitude[m]"
        unit_patterns = [
            r'\(([a-zA-Z%/]+)\)',  # (mV), (deg), etc.
            r'\[([a-zA-Z%/]+)\]',  # [mV], [deg], etc.
            r'_([a-zA-Z%/]+)$'     # _mV, _deg, etc.
        ]
        
        embedded_unit = None
        for pattern in unit_patterns:
            match = re.search(pattern, column_name)
            if match:
                embedded_unit = match.group(1)
                break
                
        # If we found an embedded unit, use it
        if embedded_unit:
            self.unit_info[field_name] = {
                "unit": embedded_unit,
                "scale": 1.0,  # Default scale factor
                "source": "embedded"
            }
            return
            
        # Otherwise, check against our known field mappings
        for key_field, info in self.FIELD_TO_UNIT_MAP.items():
            if key_field in lower_col:
                self.unit_info[field_name] = {
                    "unit": info["unit"],
                    "scale": info["scale"],
                    "source": "field_mapping"
                }
                return
                
        # If we still don't have unit info, try to infer from field name
        if "lat" in lower_col or "lon" in lower_col:
            # Latitude/longitude fields often use 1e7 encoding
            self.unit_info[field_name] = {
                "unit": "deg",
                "scale": 1e-7 if self._check_value_range(field_name, 1e6, 9e7) else 1.0,
                "source": "inferred"
            }
        elif "alt" in lower_col or "height" in lower_col:
            # Altitude fields might be in mm, cm, or m
            if self._check_value_range(field_name, 1000, 1e6):
                # Likely millimeters
                self.unit_info[field_name] = {
                    "unit": "m",
                    "scale": 1e-3,
                    "source": "inferred"
                }
            elif self._check_value_range(field_name, 100, 1000):
                # Likely centimeters
                self.unit_info[field_name] = {
                    "unit": "m",
                    "scale": 1e-2,
                    "source": "inferred"
                }
            else:
                # Likely meters
                self.unit_info[field_name] = {
                    "unit": "m",
                    "scale": 1.0,
                    "source": "inferred"
                }
        elif "volt" in lower_col:
            # Voltage often in millivolts
            if self._check_value_range(field_name, 1000, 50000):
                self.unit_info[field_name] = {
                    "unit": "V",
                    "scale": 1e-3,
                    "source": "inferred"
                }
            else:
                self.unit_info[field_name] = {
                    "unit": "V",
                    "scale": 1.0,
                    "source": "inferred"
                }
        elif "current" in lower_col:
            # Current often in 10mA or centiamperes
            if self._check_value_range(field_name, 100, 50000):
                self.unit_info[field_name] = {
                    "unit": "A",
                    "scale": 0.01,
                    "source": "inferred"
                }
            else:
                self.unit_info[field_name] = {
                    "unit": "A",
                    "scale": 1.0,
                    "source": "inferred"
                }
        else:
            # Default unit info with no conversion
            self.unit_info[field_name] = {
                "unit": "unknown",
                "scale": 1.0,
                "source": "default"
            }

    def _check_value_range(self, field_name: str, min_val: float, max_val: float) -> bool:
        """
        Check if values in a field are mostly within a specified range.
        Used for unit inference when explicit unit data is not available.
        
        Args:
            field_name: Name of the field to check
            min_val: Minimum expected value
            max_val: Maximum expected value
            
        Returns:
            True if most values in the field are within the specified range
        """
        # Get data for the field from telemetry DataFrame
        for msg_type, df in self.telemetry.items():
            col_name = field_name.replace(f"{msg_type}_", "")
            if col_name in df.columns:
                values = pd.to_numeric(df[col_name], errors='coerce').dropna()
                if not values.empty:
                    # Check if at least 80% of values are in range
                    in_range = ((values >= min_val) & (values <= max_val)).mean()
                    return in_range >= 0.8
                    
        return False