from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink2
import pandas as pd
import numpy as np
import os
import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Set, Union
import concurrent.futures
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelemetryParser:
    """
    Advanced telemetry parser that handles multiple UAV log formats.
    
    Supports:
    - MAVLink telemetry logs (.tlog)
    - ArduPilot DataFlash logs (.bin)
    - PX4 ULog files (.ulg/.ulog) via fallback to pyulog if available
    
    Features:
    - Automatic format detection
    - Efficient extraction of mission-critical telemetry
    - Timestamp deduplication and alignment
    - Proper handling of unit conversions
    - Intelligent field selection with fallbacks
    """
    
    # Define critical message types and fields for efficient parsing
    # These are the most commonly needed fields for flight analysis
    ESSENTIAL_MESSAGES = {
        # Position and Altitude
        'GLOBAL_POSITION_INT': ['time_boot_ms', 'lat', 'lon', 'alt', 'relative_alt', 'vx', 'vy', 'vz', 'hdg'],
        'LOCAL_POSITION_NED': ['time_boot_ms', 'x', 'y', 'z', 'vx', 'vy', 'vz'],
        'ALTITUDE': ['time_usec', 'altitude_monotonic', 'altitude_amsl', 'altitude_local', 'altitude_relative', 'altitude_terrain', 'bottom_clearance'],
        'TERRAIN_REPORT': ['lat', 'lon', 'spacing', 'terrain_height', 'current_height'],
        'VFR_HUD': ['airspeed', 'groundspeed', 'heading', 'throttle', 'alt', 'climb'],
        
        # Attitude and Navigation
        'ATTITUDE': ['time_boot_ms', 'roll', 'pitch', 'yaw', 'rollspeed', 'pitchspeed', 'yawspeed'],
        'AHRS': ['roll', 'pitch', 'yaw', 'altitude', 'lat', 'lng'],
        'AHRS2': ['roll', 'pitch', 'yaw', 'altitude', 'lat', 'lng'],
        'AHRS3': ['roll', 'pitch', 'yaw', 'altitude', 'lat', 'lng'],
        'NAV_CONTROLLER_OUTPUT': ['nav_roll', 'nav_pitch', 'alt_error', 'aspd_error', 'xtrack_error', 'nav_bearing', 'target_bearing', 'wp_dist'],
        
        # System Status
        'SYS_STATUS': ['voltage_battery', 'current_battery', 'battery_remaining', 'drop_rate_comm', 'errors_comm'],
        'BATTERY_STATUS': ['id', 'battery_function', 'type', 'temperature', 'voltages', 'current_battery', 'current_consumed', 'energy_consumed', 'battery_remaining', 'time_remaining'],
        'POWER_STATUS': ['Vcc', 'Vservo', 'flags'],
        'MEMINFO': ['brkval', 'freemem', 'freemem32'],
        
        # GPS and Satellites
        'GPS_RAW_INT': ['time_usec', 'fix_type', 'lat', 'lon', 'alt', 'eph', 'epv', 'vel', 'cog', 'satellites_visible'],
        'GPS2_RAW': ['time_usec', 'fix_type', 'lat', 'lon', 'alt', 'eph', 'epv', 'vel', 'cog', 'satellites_visible'],
        'GPS_STATUS': ['satellites_visible', 'satellite_prn', 'satellite_used', 'satellite_elevation', 'satellite_azimuth', 'satellite_snr'],
        
        # Mode and Commands
        'HEARTBEAT': ['type', 'autopilot', 'base_mode', 'custom_mode', 'system_status', 'mavlink_version'],
        'COMMAND_ACK': ['command', 'result', 'progress', 'result_param2', 'target_system', 'target_component'],
        'STATUSTEXT': ['severity', 'text'],
        'MISSION_CURRENT': ['seq', 'total', 'mission_state', 'mission_mode'],
        
        # Control and Motors
        'SERVO_OUTPUT_RAW': ['time_usec', 'port', 'servo1_raw', 'servo2_raw', 'servo3_raw', 'servo4_raw', 'servo5_raw', 'servo6_raw', 'servo7_raw', 'servo8_raw'],
        'RC_CHANNELS': ['time_boot_ms', 'chan1_raw', 'chan2_raw', 'chan3_raw', 'chan4_raw', 'chan5_raw', 'chan6_raw', 'chan7_raw', 'chan8_raw', 'chan9_raw', 'chan10_raw', 'chan11_raw', 'chan12_raw', 'chan13_raw', 'chan14_raw', 'chan15_raw', 'chan16_raw', 'chan17_raw', 'chan18_raw', 'rssi'],
        'ESC_TELEMETRY_1_TO_4': ['temperature', 'voltage', 'current', 'totalcurrent', 'rpm', 'count'],
    }
    
    # Field translations and alternates for when primary fields aren't available
    FIELD_ALTERNATES = {
        'altitude': [
            'GLOBAL_POSITION_INT.relative_alt',   # First choice (mm)
            'VFR_HUD.alt',                        # Second choice (m)
            'ALTITUDE.altitude_relative',         # Third choice (m)
            'TERRAIN_REPORT.current_height',      # Fourth choice (m)
            'AHRS.altitude',                      # Fifth choice (units vary)
            'AHRS2.altitude',                     # Sixth choice
        ],
        'battery_voltage': [
            'BATTERY_STATUS.voltages[0]',
            'SYS_STATUS.voltage_battery',
            'POWER_STATUS.Vcc',
        ],
        'battery_current': [
            'BATTERY_STATUS.current_battery',
            'SYS_STATUS.current_battery',
        ],
        'battery_remaining': [
            'BATTERY_STATUS.battery_remaining',
            'SYS_STATUS.battery_remaining',
        ],
        'gps_fix': [
            'GPS_RAW_INT.fix_type',
            'GPS2_RAW.fix_type',
        ],
    }
    
    # Units conversion factors for different fields
    UNIT_CONVERSIONS = {
        'GLOBAL_POSITION_INT.lat': 1e-7,        # Convert from 1e7 degrees to degrees
        'GLOBAL_POSITION_INT.lon': 1e-7,        # Convert from 1e7 degrees to degrees
        'GLOBAL_POSITION_INT.relative_alt': 1e-3, # Convert from mm to m
        'GLOBAL_POSITION_INT.alt': 1e-3,        # Convert from mm to m
        'GPS_RAW_INT.lat': 1e-7,                # Convert from 1e7 degrees to degrees
        'GPS_RAW_INT.lon': 1e-7,                # Convert from 1e7 degrees to degrees
        'GPS_RAW_INT.alt': 1e-3,                # Convert from mm to m
        'GPS2_RAW.lat': 1e-7,                   # Convert from 1e7 degrees to degrees
        'GPS2_RAW.lon': 1e-7,                   # Convert from 1e7 degrees to degrees
        'GPS2_RAW.alt': 1e-3,                   # Convert from mm to m
    }

    def __init__(self, file_path: str):
        """Initialize the telemetry parser with the specified log file."""
        self.file_path = file_path
        self.file_extension = os.path.splitext(file_path)[1].lower()
        self.use_pyulog = False
        
        # Check for format compatibility
        if self.file_extension not in ['.tlog', '.bin', '.log', '.ulg', '.ulog']:
            raise ValueError(f"Unsupported file format: {self.file_extension}. "
                            f"Supported formats: .tlog, .bin, .log, .ulg, .ulog")
            
        # For ULog files, we'll use pyulog if available
        if self.file_extension in ['.ulg', '.ulog']:
            try:
                import pyulog
                self.use_pyulog = True
                logger.info(f"Using pyulog parser for {self.file_extension} file")
            except ImportError:
                logger.warning("pyulog not available, falling back to pymavlink")
                
        logger.info(f"Initialized parser for {file_path}")

    def parse(self) -> Dict[str, pd.DataFrame]:
        """Parse the telemetry log and return a dictionary of DataFrames for each message type."""
        start_time = time.time()
        logger.info(f"Starting to parse {self.file_path}")
        
        # Use appropriate parser based on file format
        if self.use_pyulog:
            data = self._parse_ulog()
        else:
            data = self._parse_mavlink()
            
        # Process telemetry data
        processed_data = self._process_dataframes(data)
        
        # Measure and log performance
        elapsed = time.time() - start_time
        total_rows = sum(len(df) for df in processed_data.values())
        logger.info(f"Parsing completed in {elapsed:.2f}s. Extracted {len(processed_data)} message types with {total_rows} total data points")
        
        return processed_data
    
    def _parse_mavlink(self) -> Dict[str, List[Dict[str, Any]]]:
        """Parse MAVLink-based log files (.tlog, .bin)."""
        # Initialize connection with appropriate dialect
        try:
            mlog = mavutil.mavlink_connection(self.file_path, dialect="common")
        except Exception as e:
            logger.error(f"Failed to initialize MAVLink connection: {str(e)}")
            raise
            
        data: Dict[str, List[Dict[str, Any]]] = {}
        msg_count = 0
        
        # Determine which message types to extract
        msg_types_to_extract = list(self.ESSENTIAL_MESSAGES.keys())
        
        # Process messages in the log
        try:
            while True:
                msg = mlog.recv_match(type=msg_types_to_extract, blocking=False)
                if msg is None:
                    break
                    
                msg_type = msg.get_type()
                
                # Skip non-essential message types
                if msg_type not in self.ESSENTIAL_MESSAGES:
                    continue
                
                # Extract message data including timestamp
                try:
                    msg_dict = msg.to_dict()
                    
                    # Add timestamp from message metadata
                    msg_dict["timestamp"] = pd.to_datetime(msg._timestamp, unit='s')
                    
                    # Store message data
                    if msg_type not in data:
                        data[msg_type] = []
                    data[msg_type].append(msg_dict)
                    
                    # Count processed messages
                    msg_count += 1
                    
                    # Log progress for large files
                    if msg_count % 100000 == 0:
                        logger.info(f"Processed {msg_count} messages...")
                        
                except Exception as e:
                    logger.warning(f"Error processing message {msg_type}: {str(e)}")
                    continue
                    
        except KeyboardInterrupt:
            logger.warning("Parsing interrupted by user")
        except Exception as e:
            logger.error(f"Error parsing MAVLink data: {str(e)}")
            raise
            
        logger.info(f"Processed {msg_count} total messages from {len(data)} message types")
        return data
    
    def _parse_ulog(self) -> Dict[str, List[Dict[str, Any]]]:
        """Parse PX4 ULog files using pyulog."""
        try:
            import pyulog
            from pyulog.core import ULog
            
            # Parse the ULog file
            ulog = ULog(self.file_path)
            
            # Convert ULog data to our expected format
            data: Dict[str, List[Dict[str, Any]]] = {}
            
            # Map PX4 topics to MAVLink message types where possible
            topic_mapping = {
                'vehicle_local_position': 'LOCAL_POSITION_NED',
                'vehicle_global_position': 'GLOBAL_POSITION_INT',
                'vehicle_attitude': 'ATTITUDE', 
                'vehicle_status': 'HEARTBEAT',
                'battery_status': 'BATTERY_STATUS',
                'vehicle_gps_position': 'GPS_RAW_INT',
                'actuator_outputs': 'SERVO_OUTPUT_RAW',
                'vehicle_air_data': 'VFR_HUD',
            }
            
            # Process each data item in the ULog
            for d in ulog.data_list:
                topic_name = d.name
                
                # Map PX4 topic to MAVLink message type if possible
                msg_type = topic_mapping.get(topic_name, topic_name)
                
                # Convert timestamps to datetime
                timestamps = pd.to_datetime(d.data['timestamp'], unit='us')
                
                # Process each row of data
                rows = []
                for i in range(len(timestamps)):
                    row = {field: d.data[field][i] for field in d.data.keys() if field != 'timestamp'}
                    row['timestamp'] = timestamps[i]
                    rows.append(row)
                
                # Store the data
                data[msg_type] = rows
                
            return data
            
        except ImportError:
            logger.error("pyulog is required to parse ULog files. Please install it with: pip install pyulog")
            raise
        except Exception as e:
            logger.error(f"Error parsing ULog file: {str(e)}")
            raise
    
    def _process_dataframes(self, data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, pd.DataFrame]:
        """Convert raw message dictionaries to processed DataFrames."""
        processed_data: Dict[str, pd.DataFrame] = {}
        
        for msg_type, messages in data.items():
            if not messages:
                continue
                
            # Create a DataFrame from the message data
            try:
                df = pd.DataFrame(messages)
                
                # Ensure timestamp is a datetime and convert to index
                if 'timestamp' in df.columns:
                    # Handle duplicate timestamps using microsecond offset method
                    if not df['timestamp'].is_unique:
                        # Group by timestamp and add increasing microsecond offsets
                        timestamp_groups = df.groupby('timestamp').cumcount()
                        df['timestamp'] = df['timestamp'] + pd.to_timedelta(timestamp_groups, unit='us')
                        
                    # Sort by timestamp
                    df = df.sort_values('timestamp')
                    
                    # Set timestamp as index
                    df.set_index('timestamp', inplace=True)
                
                # Apply unit conversions for specific fields
                for col in df.columns:
                    conversion_key = f"{msg_type}.{col}"
                    if conversion_key in self.UNIT_CONVERSIONS:
                        df[col] = df[col] * self.UNIT_CONVERSIONS[conversion_key]
                
                # Handle list-type fields like 'voltages' in BATTERY_STATUS
                for col in df.columns:
                    if isinstance(df[col].iloc[0], list) if len(df) > 0 else False:
                        # Extract first element for simple fields like voltages[0]
                        try:
                            df[f"{col}[0]"] = df[col].apply(lambda x: x[0] if x and len(x) > 0 else None)
                        except:
                            # Skip if extraction fails
                            pass
                
                # Store the processed DataFrame
                processed_data[msg_type] = df
                
            except Exception as e:
                logger.warning(f"Error processing DataFrame for {msg_type}: {str(e)}")
                continue
                
        return processed_data
    
    def get_key_metrics(self) -> Dict[str, Any]:
        """Extract key flight metrics from the telemetry data."""
        # This requires parsing the data first - future enhancement
        return {
            "status": "Call parse() first, then access metrics through the TelemetryAnalyzer class"
        }

# Example usage
# parser = TelemetryParser("flight_log.tlog")
# telemetry_data = parser.parse()
# analyzer = TelemetryAnalyzer(telemetry_data)  # Pass to analyzer for further processing
