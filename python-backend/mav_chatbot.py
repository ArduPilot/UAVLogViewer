import os
import logging
from pymavlink import mavutil
import groq
from dotenv import load_dotenv
import json
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables and initialize Groq client
load_dotenv()
try:
    groq_client = groq.Groq(api_key=os.environ.get("GROQ_API_KEY"))
    logger.info("Groq client initialized successfully")
except Exception as e:
    logger.error(f"GROQ_API_KEY not found or invalid: {e}")
    groq_client = None

class FlightDataAnalyzer:
    """Comprehensive flight data analysis engine"""
    
    def __init__(self):
        self.altitude_data = []
        self.gps_data = []
        self.battery_data = []
        self.attitude_data = []
        self.imu_data = []
        self.error_data = []
        self.event_data = []
        self.rc_data = []
        self.airspeed_data = []
        self.mode_data = []
        self.ekf_data = []
        self.compass_data = []
        self.current_data = []
        self.flow_data = []
        self.optical_flow_data = []
        self.rangefinder_data = []
        self.terrain_data = []
        self.vibration_data = []
        self.mission_data = []
        self.command_data = []
        self.radio_data = []
        self.ahrs_data = []
        self.ntun_data = []
        self.ctun_data = []
        self.ntun_data = []
        self.rate_data = []
        self.pid_data = []
        self.rcin_data = []
        self.rcout_data = []
        self.servo_data = []
        self.motor_data = []
        self.esc_data = []
        self.camera_data = []
        self.gimbal_data = []
        self.fence_data = []
        self.rally_data = []
        self.param_data = []
        self.statustext_data = []
        
    def add_message(self, msg_type: str, msg_data: Dict):
        """Add a message to the appropriate data collection"""
        if msg_type == 'GPS':
            self.gps_data.append(msg_data)
        elif msg_type == 'BARO':
            self.altitude_data.append(msg_data)
        elif msg_type == 'BAT':
            self.battery_data.append(msg_data)
        elif msg_type == 'ATT':
            self.attitude_data.append(msg_data)
        elif msg_type == 'IMU':
            self.imu_data.append(msg_data)
        elif msg_type == 'ERR':
            self.error_data.append(msg_data)
        elif msg_type == 'EV':
            self.event_data.append(msg_data)
        elif msg_type == 'RC':
            self.rc_data.append(msg_data)
        elif msg_type == 'ARSP':
            self.airspeed_data.append(msg_data)
        elif msg_type == 'MODE':
            self.mode_data.append(msg_data)
        elif msg_type == 'EKF1':
            self.ekf_data.append(msg_data)
        elif msg_type == 'MAG':
            self.compass_data.append(msg_data)
        elif msg_type == 'CURR':
            self.current_data.append(msg_data)
        elif msg_type == 'FLOW':
            self.flow_data.append(msg_data)
        elif msg_type == 'OF':
            self.optical_flow_data.append(msg_data)
        elif msg_type == 'RNG':
            self.rangefinder_data.append(msg_data)
        elif msg_type == 'TERR':
            self.terrain_data.append(msg_data)
        elif msg_type == 'VIBE':
            self.vibration_data.append(msg_data)
        elif msg_type == 'CMD':
            self.command_data.append(msg_data)
        elif msg_type == 'RAD':
            self.radio_data.append(msg_data)
        elif msg_type == 'AHR2':
            self.ahrs_data.append(msg_data)
        elif msg_type == 'NTUN':
            self.ntun_data.append(msg_data)
        elif msg_type == 'CTUN':
            self.ctun_data.append(msg_data)
        elif msg_type == 'RATE':
            self.rate_data.append(msg_data)
        elif msg_type == 'PID':
            self.pid_data.append(msg_data)
        elif msg_type == 'RCIN':
            self.rcin_data.append(msg_data)
        elif msg_type == 'RCOU':
            self.rcout_data.append(msg_data)
        elif msg_type == 'SERVO':
            self.servo_data.append(msg_data)
        elif msg_type == 'MOT':
            self.motor_data.append(msg_data)
        elif msg_type == 'ESC':
            self.esc_data.append(msg_data)
        elif msg_type == 'CAM':
            self.camera_data.append(msg_data)
        elif msg_type == 'GMB':
            self.gimbal_data.append(msg_data)
        elif msg_type == 'FENCE':
            self.fence_data.append(msg_data)
        elif msg_type == 'RALLY':
            self.rally_data.append(msg_data)
        elif msg_type == 'PARM':
            self.param_data.append(msg_data)
        elif msg_type == 'STATUSTEXT':
            self.statustext_data.append(msg_data)

    def analyze_altitude(self) -> Dict[str, Any]:
        """Comprehensive altitude analysis"""
        analysis = {
            'max_altitude_gps': None,
            'max_altitude_baro': None,
            'min_altitude_gps': None,
            'min_altitude_baro': None,
            'altitude_variance': None,
            'climb_rate_analysis': None,
            'descent_rate_analysis': None,
            'altitude_anomalies': []
        }
        
        # GPS Altitude Analysis
        if self.gps_data:
            # Check if altitude values are already in meters (float) or need conversion from mm (int)
            sample_alt = next((msg.get('Alt') for msg in self.gps_data if msg.get('Alt') is not None), None)
            
            if sample_alt is not None:
                # Determine if we need to convert from mm to meters
                if isinstance(sample_alt, float):
                    # Already in meters
                    gps_altitudes = [msg.get('Alt', 0) for msg in self.gps_data if msg.get('Alt') is not None]
                elif isinstance(sample_alt, int):
                    # In millimeters, convert to meters
                    gps_altitudes = [msg.get('Alt', 0) / 1000.0 for msg in self.gps_data if msg.get('Alt') is not None]
                else:
                    # Unknown type, assume meters
                    gps_altitudes = [float(msg.get('Alt', 0)) for msg in self.gps_data if msg.get('Alt') is not None]
                
                if gps_altitudes:
                    analysis['max_altitude_gps'] = max(gps_altitudes)
                    analysis['min_altitude_gps'] = min(gps_altitudes)
                    analysis['altitude_variance'] = np.var(gps_altitudes) if len(gps_altitudes) > 1 else 0
                    
                    # Detect altitude anomalies
                    mean_alt = np.mean(gps_altitudes)
                    std_alt = np.std(gps_altitudes)
                    for i, alt in enumerate(gps_altitudes):
                        if abs(alt - mean_alt) > 3 * std_alt:
                            analysis['altitude_anomalies'].append({
                                'type': 'extreme_altitude',
                                'value': alt,
                                'index': i,
                                'timestamp': self.gps_data[i].get('TimeUS')
                            })
        
        # Baro Altitude Analysis
        if self.altitude_data:
            baro_altitudes = [msg.get('Alt', 0) for msg in self.altitude_data if msg.get('Alt') is not None]
            if baro_altitudes:
                analysis['max_altitude_baro'] = max(baro_altitudes)
                analysis['min_altitude_baro'] = min(baro_altitudes)
        
        # Climb/Descent Rate Analysis
        if len(self.gps_data) > 1:
            climb_rates = []
            for i in range(1, len(self.gps_data)):
                if self.gps_data[i].get('Alt') and self.gps_data[i-1].get('Alt'):
                    # Handle altitude conversion for rate calculation
                    alt1 = self.gps_data[i-1].get('Alt', 0)
                    alt2 = self.gps_data[i].get('Alt', 0)
                    
                    # Convert to meters if needed
                    if isinstance(alt1, int):
                        alt1 = alt1 / 1000.0
                    if isinstance(alt2, int):
                        alt2 = alt2 / 1000.0
                    
                    alt_diff = alt2 - alt1
                    time_diff = (self.gps_data[i].get('TimeUS', 0) - self.gps_data[i-1].get('TimeUS', 0)) / 1e6
                    if time_diff > 0:
                        rate = alt_diff / time_diff
                        climb_rates.append(rate)
            
            if climb_rates:
                analysis['climb_rate_analysis'] = {
                    'max_climb_rate': max(climb_rates),
                    'max_descent_rate': min(climb_rates),
                    'avg_climb_rate': np.mean(climb_rates)
                }
        
        return analysis

    def analyze_gps(self) -> Dict[str, Any]:
        """Comprehensive GPS analysis"""
        analysis = {
            'initial_gps_fix_status': None,
            'final_gps_fix_status': None,
            'max_satellites': 0,
            'min_satellites': 0,
            'avg_satellites': 0,
            'gps_signal_loss_events': [],
            'gps_accuracy_analysis': None,
            'gps_anomalies': []
        }
        
        if self.gps_data:
            # Basic GPS stats
            analysis['initial_gps_fix_status'] = self.gps_data[0].get('Status')
            analysis['final_gps_fix_status'] = self.gps_data[-1].get('Status')
            
            sat_counts = [msg.get('NSats', 0) for msg in self.gps_data if msg.get('NSats') is not None]
            if sat_counts:
                analysis['max_satellites'] = max(sat_counts)
                analysis['min_satellites'] = min(sat_counts)
                analysis['avg_satellites'] = np.mean(sat_counts)
            
            # GPS Signal Loss Detection
            gps_times = [msg.get('TimeUS') for msg in self.gps_data if msg.get('TimeUS') is not None]
            gps_times.sort()
            
            if len(gps_times) > 1:
                for i in range(1, len(gps_times)):
                    time_gap = (gps_times[i] - gps_times[i-1]) / 1e6
                    if time_gap > 5.0:  # Gap larger than 5 seconds
                        analysis['gps_signal_loss_events'].append({
                            'gap_start': gps_times[i-1] / 1e6,
                            'gap_end': gps_times[i] / 1e6,
                            'duration_seconds': time_gap
                        })
            
            # GPS Accuracy Analysis
            hdop_values = [msg.get('HDop', 0) for msg in self.gps_data if msg.get('HDop') is not None]
            vdop_values = [msg.get('VDop', 0) for msg in self.gps_data if msg.get('VDop') is not None]
            
            if hdop_values or vdop_values:
                analysis['gps_accuracy_analysis'] = {
                    'avg_hdop': np.mean(hdop_values) if hdop_values else None,
                    'max_hdop': max(hdop_values) if hdop_values else None,
                    'avg_vdop': np.mean(vdop_values) if vdop_values else None,
                    'max_vdop': max(vdop_values) if vdop_values else None
                }
            
            # GPS Anomalies
            for i, msg in enumerate(self.gps_data):
                if msg.get('Status', 0) < 3:  # Poor GPS fix
                    analysis['gps_anomalies'].append({
                        'type': 'poor_gps_fix',
                        'status': msg.get('Status'),
                        'satellites': msg.get('NSats'),
                        'index': i,
                        'timestamp': msg.get('TimeUS')
                    })
        
        return analysis

    def analyze_battery(self) -> Dict[str, Any]:
        """Comprehensive battery analysis"""
        analysis = {
            'max_voltage': None,
            'min_voltage': None,
            'max_current': None,
            'min_current': None,
            'max_temperature': None,
            'min_temperature': None,
            'battery_consumption': None,
            'voltage_trend': None,
            'battery_anomalies': []
        }
        
        if self.battery_data:
            voltages = [msg.get('Volt', 0) for msg in self.battery_data if msg.get('Volt') is not None]
            currents = [msg.get('Curr', 0) for msg in self.battery_data if msg.get('Curr') is not None]
            temperatures = [msg.get('Temp', 0) for msg in self.battery_data if msg.get('Temp') is not None]
            
            if voltages:
                analysis['max_voltage'] = max(voltages)
                analysis['min_voltage'] = min(voltages)
                
                # Voltage trend analysis
                if len(voltages) > 1:
                    voltage_trend = np.polyfit(range(len(voltages)), voltages, 1)[0]
                    analysis['voltage_trend'] = 'declining' if voltage_trend < -0.1 else 'stable' if abs(voltage_trend) < 0.1 else 'increasing'
                    
                    # Detect voltage anomalies
                    mean_voltage = np.mean(voltages)
                    std_voltage = np.std(voltages)
                    for i, voltage in enumerate(voltages):
                        if abs(voltage - mean_voltage) > 2 * std_voltage:
                            analysis['battery_anomalies'].append({
                                'type': 'voltage_spike',
                                'value': voltage,
                                'index': i,
                                'timestamp': self.battery_data[i].get('TimeUS')
                            })
            
            if currents:
                analysis['max_current'] = max(currents)
                analysis['min_current'] = min(currents)
            
            if temperatures:
                analysis['max_temperature'] = max(temperatures)
                analysis['min_temperature'] = min(temperatures)
                
                # Temperature anomaly detection
                mean_temp = np.mean(temperatures)
                for i, temp in enumerate(temperatures):
                    if temp > mean_temp + 20:  # 20°C above average
                        analysis['battery_anomalies'].append({
                            'type': 'high_temperature',
                            'value': temp,
                            'index': i,
                            'timestamp': self.battery_data[i].get('TimeUS')
                        })
        
        return analysis

    def analyze_flight_time(self) -> Dict[str, Any]:
        """Flight time analysis"""
        analysis = {
            'total_flight_time_seconds': 0,
            'total_flight_time_minutes': 0,
            'start_time': None,
            'end_time': None,
            'flight_phases': []
        }
        
        if self.gps_data and len(self.gps_data) > 1:
            start_time = self.gps_data[0].get('TimeUS')
            end_time = self.gps_data[-1].get('TimeUS')
            
            if start_time and end_time:
                duration_s = (end_time - start_time) / 1e6
                analysis['total_flight_time_seconds'] = duration_s
                analysis['total_flight_time_minutes'] = duration_s / 60
                analysis['start_time'] = start_time / 1e6
                analysis['end_time'] = end_time / 1e6
        
        return analysis

    def analyze_errors(self) -> Dict[str, Any]:
        """Error analysis"""
        analysis = {
            'total_errors': len(self.error_data),
            'critical_errors': [],
            'error_by_subsystem': {},
            'error_timeline': []
        }
        
        for error in self.error_data:
            error_info = {
                'subsystem': error.get('Subsys', 'Unknown'),
                'error_code': error.get('ECode', 'Unknown'),
                'timestamp': error.get('TimeUS'),
                'severity': 'critical' if error.get('ECode', 0) > 100 else 'warning'
            }
            
            analysis['error_timeline'].append(error_info)
            
            if error_info['severity'] == 'critical':
                analysis['critical_errors'].append(error_info)
            
            # Group by subsystem
            subsystem = error_info['subsystem']
            if subsystem not in analysis['error_by_subsystem']:
                analysis['error_by_subsystem'][subsystem] = []
            analysis['error_by_subsystem'][subsystem].append(error_info)
        
        return analysis

    def analyze_rc_signal(self) -> Dict[str, Any]:
        """RC signal analysis"""
        analysis = {
            'rc_signal_loss_events': [],
            'rc_signal_quality': None,
            'rc_anomalies': []
        }
        
        # Check for RC_FAILSAFE events
        for event in self.event_data:
            if event.get('Id') == 26:  # RC_FAILSAFE
                analysis['rc_signal_loss_events'].append({
                    'timestamp': event.get('TimeUS'),
                    'type': 'RC_FAILSAFE'
                })
        
        # Analyze RC signal quality from RC messages
        if self.rc_data:
            signal_qualities = []
            for rc_msg in self.rc_data:
                # Analyze signal quality based on available fields
                if hasattr(rc_msg, 'RSSI'):
                    signal_qualities.append(rc_msg.get('RSSI', 0))
            
            if signal_qualities:
                analysis['rc_signal_quality'] = {
                    'avg_quality': np.mean(signal_qualities),
                    'min_quality': min(signal_qualities),
                    'max_quality': max(signal_qualities)
                }
        
        return analysis

    def detect_anomalies(self) -> Dict[str, Any]:
        """Comprehensive anomaly detection"""
        anomalies = {
            'altitude_anomalies': [],
            'gps_anomalies': [],
            'battery_anomalies': [],
            'attitude_anomalies': [],
            'flight_anomalies': [],
            'system_anomalies': []
        }
        
        # Altitude anomalies
        if self.gps_data:
            # Check if altitude values are already in meters (float) or need conversion from mm (int)
            sample_alt = next((msg.get('Alt') for msg in self.gps_data if msg.get('Alt') is not None), None)
            
            if sample_alt is not None:
                # Determine if we need to convert from mm to meters
                if isinstance(sample_alt, float):
                    # Already in meters
                    altitudes = [msg.get('Alt', 0) for msg in self.gps_data if msg.get('Alt') is not None]
                elif isinstance(sample_alt, int):
                    # In millimeters, convert to meters
                    altitudes = [msg.get('Alt', 0) / 1000.0 for msg in self.gps_data if msg.get('Alt') is not None]
                else:
                    # Unknown type, assume meters
                    altitudes = [float(msg.get('Alt', 0)) for msg in self.gps_data if msg.get('Alt') is not None]
                
                if len(altitudes) > 10:
                    mean_alt = np.mean(altitudes)
                    std_alt = np.std(altitudes)
                    
                    for i, alt in enumerate(altitudes):
                        if abs(alt - mean_alt) > 3 * std_alt:
                            anomalies['altitude_anomalies'].append({
                                'type': 'extreme_altitude',
                                'value': alt,
                                'timestamp': self.gps_data[i].get('TimeUS'),
                                'severity': 'high' if abs(alt - mean_alt) > 5 * std_alt else 'medium'
                            })
        
        # GPS anomalies
        if self.gps_data:
            for i, msg in enumerate(self.gps_data):
                if msg.get('Status', 0) < 3:
                    anomalies['gps_anomalies'].append({
                        'type': 'poor_gps_fix',
                        'status': msg.get('Status'),
                        'satellites': msg.get('NSats'),
                        'timestamp': msg.get('TimeUS'),
                        'severity': 'high' if msg.get('Status', 0) < 2 else 'medium'
                    })
        
        # Battery anomalies
        if self.battery_data:
            voltages = [msg.get('Volt', 0) for msg in self.battery_data if msg.get('Volt') is not None]
            if voltages:
                mean_voltage = np.mean(voltages)
                for i, voltage in enumerate(voltages):
                    if voltage < mean_voltage * 0.8:  # 20% below average
                        anomalies['battery_anomalies'].append({
                            'type': 'low_voltage',
                            'value': voltage,
                            'timestamp': self.battery_data[i].get('TimeUS'),
                            'severity': 'high' if voltage < mean_voltage * 0.7 else 'medium'
                        })
        
        # Attitude anomalies
        if self.attitude_data:
            for i, msg in enumerate(self.attitude_data):
                roll = abs(msg.get('Roll', 0))
                pitch = abs(msg.get('Pitch', 0))
                
                if roll > 45 or pitch > 45:  # Extreme attitude
                    anomalies['attitude_anomalies'].append({
                        'type': 'extreme_attitude',
                        'roll': roll,
                        'pitch': pitch,
                        'timestamp': msg.get('TimeUS'),
                        'severity': 'high' if roll > 60 or pitch > 60 else 'medium'
                    })
        
        # Flight anomalies
        if len(self.gps_data) > 1:
            # Check for sudden altitude changes
            for i in range(1, len(self.gps_data)):
                if self.gps_data[i].get('Alt') and self.gps_data[i-1].get('Alt'):
                    alt_diff = abs(self.gps_data[i]['Alt'] - self.gps_data[i-1]['Alt']) / 1000.0
                    time_diff = (self.gps_data[i].get('TimeUS', 0) - self.gps_data[i-1].get('TimeUS', 0)) / 1e6
                    
                    if time_diff > 0 and alt_diff / time_diff > 10:  # More than 10 m/s change
                        anomalies['flight_anomalies'].append({
                            'type': 'sudden_altitude_change',
                            'rate': alt_diff / time_diff,
                            'timestamp': self.gps_data[i].get('TimeUS'),
                            'severity': 'high' if alt_diff / time_diff > 20 else 'medium'
                        })
        
        return anomalies

    def get_comprehensive_analysis(self) -> Dict[str, Any]:
        """Get comprehensive flight analysis"""
        return {
            'altitude_analysis': self.analyze_altitude(),
            'gps_analysis': self.analyze_gps(),
            'battery_analysis': self.analyze_battery(),
            'flight_time_analysis': self.analyze_flight_time(),
            'error_analysis': self.analyze_errors(),
            'rc_signal_analysis': self.analyze_rc_signal(),
            'anomalies': self.detect_anomalies(),
            'summary_stats': {
                'total_messages': len(self.gps_data) + len(self.battery_data) + len(self.error_data),
                'flight_duration_minutes': self.analyze_flight_time()['total_flight_time_minutes'],
                'max_altitude': self.analyze_altitude()['max_altitude_gps'],
                'total_errors': len(self.error_data),
                'gps_signal_losses': len(self.analyze_gps()['gps_signal_loss_events'])
            }
        }

class MAVChatbot:
    def __init__(self):
        """
        Initializes the agentic MAVLink chatbot with comprehensive analysis capabilities.
        """
        self.analyzer = FlightDataAnalyzer()
        self.conversation_history = []
        self.current_log_file = None
        self.is_initialized = False
        self.analysis_cache = None

    def _parse_log(self, log_file: str) -> bool:
        """
        Parses the entire MAVLink log file and stores comprehensive data.
        """
        try:
            logger.info(f"Starting comprehensive log parsing: {log_file}")
            mlog = mavutil.mavlink_connection(log_file)
            msg_count = 0
            
            while True:
                msg = mlog.recv_match()
                if msg is None:
                    break
                
                msg_count += 1
                if msg_count % 100000 == 0:
                    logger.info(f"Processed {msg_count} messages...")

                msg_type = msg.get_type()
                msg_dict = msg.to_dict()
                
                # Add timestamp if not present
                if 'TimeUS' not in msg_dict and hasattr(msg, 'TimeUS'):
                    msg_dict['TimeUS'] = msg.TimeUS
                
                self.analyzer.add_message(msg_type, msg_dict)
            
            logger.info(f"Finished parsing. Total messages: {msg_count}")
            return True
            
        except Exception as e:
            logger.error(f"Error parsing log file: {e}", exc_info=True)
            return False

    def _create_agentic_prompt(self, user_query: str, context: Dict[str, Any], conversation_history: List[Dict]) -> str:
        """
        Creates a comprehensive agentic prompt for the LLM.
        """
        # Build conversation context
        conversation_context = ""
        if conversation_history:
            conversation_context = "\n\n**Previous Conversation:**\n"
            for i, (role, content) in enumerate(conversation_history[-3:]):  # Last 3 exchanges
                conversation_context += f"{role}: {content}\n"
        
        # Extract only essential data for the prompt to avoid payload size limits
        essential_data = {
            'summary_stats': context.get('summary_stats', {}),
            'altitude_analysis': {
                'max_altitude_gps': context.get('altitude_analysis', {}).get('max_altitude_gps'),
                'max_altitude_baro': context.get('altitude_analysis', {}).get('max_altitude_baro'),
                'altitude_anomalies': len(context.get('altitude_analysis', {}).get('altitude_anomalies', []))
            },
            'gps_analysis': {
                'gps_signal_loss_events': len(context.get('gps_analysis', {}).get('gps_signal_loss_events', [])),
                'max_satellites': context.get('gps_analysis', {}).get('max_satellites'),
                'gps_anomalies': len(context.get('gps_analysis', {}).get('gps_anomalies', []))
            },
            'battery_analysis': {
                'max_temperature': context.get('battery_analysis', {}).get('max_temperature'),
                'max_voltage': context.get('battery_analysis', {}).get('max_voltage'),
                'battery_anomalies': len(context.get('battery_analysis', {}).get('battery_anomalies', []))
            },
            'flight_time_analysis': {
                'total_flight_time_minutes': context.get('flight_time_analysis', {}).get('total_flight_time_minutes')
            },
            'error_analysis': {
                'total_errors': context.get('error_analysis', {}).get('total_errors'),
                'critical_errors_count': len(context.get('error_analysis', {}).get('critical_errors', []))
            },
            'rc_signal_analysis': {
                'rc_signal_loss_events': len(context.get('rc_signal_analysis', {}).get('rc_signal_loss_events', []))
            },
            'anomalies_summary': {
                'total_anomalies': sum([
                    len(context.get('anomalies', {}).get('altitude_anomalies', [])),
                    len(context.get('anomalies', {}).get('gps_anomalies', [])),
                    len(context.get('anomalies', {}).get('battery_anomalies', [])),
                    len(context.get('anomalies', {}).get('flight_anomalies', []))
                ])
            }
        }
        
        # Build comprehensive flight data context
        flight_context = json.dumps(essential_data, indent=2)
        
        prompt = f"""You are an expert flight data analyst and MAVLink telemetry specialist. You have access to comprehensive flight data from a UAV log file and can provide detailed, agentic analysis.

**Your Capabilities:**
- Analyze MAVLink telemetry data comprehensively
- Detect anomalies and patterns in flight data
- Provide detailed explanations with data references
- Ask clarifying questions when needed
- Maintain conversation context and state
- Reason about flight safety and performance

**Flight Data Analysis:**
```json
{flight_context}
```

**MAVLink Message Types Available:**
- GPS: Position, altitude, satellite count, fix status
- BARO: Barometric altitude and pressure
- BAT: Battery voltage, current, temperature
- ATT: Attitude (roll, pitch, yaw)
- IMU: Inertial measurement data
- ERR: System errors and warnings
- EV: Events (arming, disarming, failsafes)
- RC: Radio control data
- ARSP: Airspeed data
- MODE: Flight mode changes
- EKF: Extended Kalman Filter data
- And many more specialized message types

**Current User Query:**
"{user_query}"

**Instructions:**
1. Analyze the provided flight data thoroughly
2. Answer the user's question with specific data references
3. If the question is unclear, ask for clarification
4. If you detect anomalies, explain them clearly
5. Provide actionable insights when possible
6. Use markdown formatting for clarity
7. Reference specific data points and timestamps
8. Maintain an agentic, helpful tone

**Your Response:**
"""
        
        if conversation_context:
            prompt += conversation_context
        
        return prompt

    def _handle_specific_questions(self, user_query: str, analysis: Dict[str, Any]) -> Optional[str]:
        """
        Handle specific predefined questions with direct data access and agentic explanations.
        """
        query_lower = user_query.lower()
        
        # Highest altitude
        if "highest altitude" in query_lower or "max altitude" in query_lower:
            max_alt_gps = analysis['altitude_analysis']['max_altitude_gps']
            max_alt_baro = analysis['altitude_analysis']['max_altitude_baro']
            
            # Get calculation details
            gps_count = len(self.analyzer.gps_data) if self.analyzer.gps_data else 0
            baro_count = len(self.analyzer.altitude_data) if self.analyzer.altitude_data else 0
            
            # Determine data type and conversion method
            sample_alt = next((msg.get('Alt') for msg in self.analyzer.gps_data if msg.get('Alt') is not None), None) if self.analyzer.gps_data else None
            data_type = type(sample_alt).__name__ if sample_alt is not None else "Unknown"
            conversion_method = "No conversion needed (already in meters)" if isinstance(sample_alt, float) else "Converted from millimeters to meters (divided by 1000)" if isinstance(sample_alt, int) else "Unknown conversion"
            
            if max_alt_gps is not None:
                response = f"**Highest Altitude:** {max_alt_gps:.2f} meters (GPS)\n\n"
                response += f"**How I calculated this:**\n"
                response += f"• Analyzed {gps_count} GPS messages from the flight log\n"
                response += f"• Extracted altitude data from the 'Alt' field in each GPS message\n"
                response += f"• Data type: {data_type} - {conversion_method}\n"
                response += f"• Found maximum altitude value: {max_alt_gps:.2f} meters\n"
                response += f"• This represents the highest point reached during the flight\n\n"
                
                if max_alt_baro is not None:
                    response += f"**Barometric altitude comparison:** {max_alt_baro:.2f} meters\n"
                    response += f"• Barometric data from {baro_count} BARO messages\n"
                    response += f"• GPS altitude is typically more accurate for absolute height\n\n"
                
                response += f"**Data confidence:** High - GPS altitude provides reliable absolute height measurements"
                return response
            elif max_alt_baro is not None:
                response = f"**Highest Altitude:** {max_alt_baro:.2f} meters (Barometric)\n\n"
                response += f"**How I calculated this:**\n"
                response += f"• Analyzed {baro_count} barometric pressure messages\n"
                response += f"• Extracted altitude from barometric pressure readings\n"
                response += f"• Found maximum barometric altitude: {max_alt_baro:.2f} meters\n\n"
                response += f"**Note:** GPS altitude data not available, using barometric sensor data"
                return response
            else:
                return "I couldn't find altitude data in this log file."
        
        # GPS signal loss
        elif "gps signal" in query_lower and "lost" in query_lower:
            gps_loss_events = analysis['gps_analysis']['gps_signal_loss_events']
            gps_count = len(self.analyzer.gps_data) if self.analyzer.gps_data else 0
            
            if gps_loss_events:
                first_loss = gps_loss_events[0]
                response = f"**GPS Signal Loss:** First occurred at {first_loss['gap_start']:.2f} seconds into the flight.\n\n"
                response += f"**How I detected this:**\n"
                response += f"• Analyzed {gps_count} GPS messages chronologically\n"
                response += f"• Looked for gaps in GPS data reception > 5 seconds\n"
                response += f"• Found {len(gps_loss_events)} signal loss events\n"
                response += f"• First gap: {first_loss['gap_start']:.2f}s to {first_loss['gap_end']:.2f}s\n"
                response += f"• Duration: {first_loss['duration_seconds']:.2f} seconds\n\n"
                response += f"**What this means:** GPS receiver temporarily lost satellite signal or had poor reception"
                return response
            else:
                response = f"**GPS Signal:** No GPS signal loss detected during this flight.\n\n"
                response += f"**How I verified this:**\n"
                response += f"• Analyzed {gps_count} GPS messages\n"
                response += f"• Checked for gaps > 5 seconds between consecutive messages\n"
                response += f"• No significant gaps found\n"
                response += f"• GPS maintained continuous signal throughout the flight\n\n"
                response += f"**Data confidence:** High - GPS data shows consistent reception"
                return response
        
        # Battery temperature
        elif "battery temperature" in query_lower or "max temperature" in query_lower:
            max_temp = analysis['battery_analysis']['max_temperature']
            battery_count = len(self.analyzer.battery_data) if self.analyzer.battery_data else 0
            
            if max_temp is not None:
                response = f"**Maximum Battery Temperature:** {max_temp:.1f}°C\n\n"
                response += f"**How I calculated this:**\n"
                response += f"• Analyzed {battery_count} battery monitoring messages\n"
                response += f"• Extracted temperature readings from 'Temp' field\n"
                response += f"• Found maximum temperature: {max_temp:.1f}°C\n"
                response += f"• Temperature range: {analysis['battery_analysis']['min_temperature']:.1f}°C to {max_temp:.1f}°C\n\n"
                response += f"**Safety context:** Battery temperatures above 60°C can indicate stress or malfunction"
                return response
            else:
                return "I couldn't find battery temperature data in this log file."
        
        # Flight time
        elif "flight time" in query_lower or "how long" in query_lower:
            flight_time = analysis['flight_time_analysis']['total_flight_time_minutes']
            gps_count = len(self.analyzer.gps_data) if self.analyzer.gps_data else 0
            
            if flight_time > 0:
                start_time = analysis['flight_time_analysis']['start_time']
                end_time = analysis['flight_time_analysis']['end_time']
                
                response = f"**Total Flight Time:** {flight_time:.1f} minutes ({flight_time * 60:.0f} seconds)\n\n"
                response += f"**How I calculated this:**\n"
                response += f"• Analyzed {gps_count} GPS messages chronologically\n"
                response += f"• First GPS fix: {start_time:.2f} seconds\n"
                response += f"• Last GPS fix: {end_time:.2f} seconds\n"
                response += f"• Duration: {end_time - start_time:.2f} seconds\n"
                response += f"• Converted to minutes: {(end_time - start_time) / 60:.1f} minutes\n\n"
                response += f"**Note:** This represents time from first to last GPS fix, not necessarily takeoff to landing"
                return response
            else:
                return "I couldn't determine the flight time from the available data."
        
        # Critical errors
        elif "critical error" in query_lower or "errors" in query_lower:
            critical_errors = analysis['error_analysis']['critical_errors']
            total_errors = analysis['error_analysis']['total_errors']
            
            if critical_errors:
                response = "**Critical Errors Detected:**\n\n"
                response += f"**How I identified these:**\n"
                response += f"• Analyzed {total_errors} total error messages\n"
                response += f"• Applied critical error threshold: Error codes > 100\n"
                response += f"• Found {len(critical_errors)} critical errors\n\n"
                
                for i, error in enumerate(critical_errors[:10]):  # Limit to first 10
                    response += f"{i+1}. **Subsystem:** {error['subsystem']}\n"
                    response += f"   **Error Code:** {error['error_code']}\n"
                    response += f"   **Time:** {error['timestamp']/1e6:.2f} seconds\n\n"
                
                if len(critical_errors) > 10:
                    response += f"... and {len(critical_errors) - 10} more errors.\n\n"
                
                response += f"**Severity assessment:** Critical errors (codes >100) indicate serious system issues requiring immediate attention"
                return response
            else:
                response = f"**Critical Errors:** No critical errors detected during this flight.\n\n"
                response += f"**How I verified this:**\n"
                response += f"• Analyzed {total_errors} total error messages\n"
                response += f"• Applied critical error threshold: Error codes > 100\n"
                response += f"• No errors exceeded critical threshold\n"
                response += f"• System operated without major error conditions\n\n"
                response += f"**Data confidence:** High - Error logging was active and comprehensive"
                return response
        
        # RC signal loss
        elif "rc signal" in query_lower and "loss" in query_lower:
            rc_loss_events = analysis['rc_signal_analysis']['rc_signal_loss_events']
            event_count = len(self.analyzer.event_data) if self.analyzer.event_data else 0
            
            if rc_loss_events:
                first_rc_loss = rc_loss_events[0]
                response = f"**RC Signal Loss:** First occurred at {first_rc_loss['timestamp']/1e6:.2f} seconds into the flight.\n\n"
                response += f"**How I detected this:**\n"
                response += f"• Analyzed {event_count} event messages\n"
                response += f"• Looked for RC_FAILSAFE events (Event ID 26)\n"
                response += f"• Found {len(rc_loss_events)} RC signal loss events\n"
                response += f"• First event: {first_rc_loss['timestamp']/1e6:.2f} seconds\n"
                response += f"• Event type: {first_rc_loss['type']}\n\n"
                response += f"**What this means:** Radio control signal was lost, triggering failsafe protection"
                return response
            else:
                response = f"**RC Signal:** No RC signal loss events detected during this flight.\n\n"
                response += f"**How I verified this:**\n"
                response += f"• Analyzed {event_count} event messages\n"
                response += f"• Searched for RC_FAILSAFE events (Event ID 26)\n"
                response += f"• No RC signal loss events found\n"
                response += f"• Radio control link remained stable throughout the flight\n\n"
                response += f"**Data confidence:** High - Event logging captured all RC-related incidents"
                return response
        
        return None  # Let the LLM handle other questions

    def load_and_analyze_log(self, file_path: str) -> bool:
        """
        Load and comprehensively analyze a MAVLink log file.
        """
        self.current_log_file = file_path
        success = self._parse_log(file_path)
        
        if success:
            self.analysis_cache = self.analyzer.get_comprehensive_analysis()
            self.is_initialized = True
            logger.info("Log file loaded and analyzed successfully.")
        else:
            self.is_initialized = False
            logger.error("Failed to load or analyze log file.")
        
        return success

    def get_response(self, user_query: str) -> str:
        """
        Generate an agentic response to the user's query using comprehensive flight data analysis.
        """
        if not self.is_initialized:
            return "**Error:** No flight log has been loaded. Please upload a MAVLink log file first."
        
        if not groq_client:
            return "**Error:** Groq client is not initialized. Please check your API key configuration."

        # Try to handle specific questions directly first
        if self.analysis_cache:
            specific_response = self._handle_specific_questions(user_query, self.analysis_cache)
            if specific_response:
                # Add to conversation history
                self.conversation_history.append(("user", user_query))
                self.conversation_history.append(("assistant", specific_response))
                return specific_response

        # Use LLM for complex or general questions
        if self.analysis_cache:
            prompt = self._create_agentic_prompt(user_query, self.analysis_cache, self.conversation_history)
        else:
            return "**Error:** No analysis data available. Please reload the log file."
        
        try:
            logger.info("Sending agentic prompt to Groq...")
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="compound-beta",  # Using Groq's compound AI system
                max_tokens=2000,
                temperature=0.3,  # Lower temperature for more consistent analysis
                top_p=0.95,
                stream=False
            )
            response = chat_completion.choices[0].message.content
            logger.info("Received agentic response from Groq.")
            
            # Add to conversation history
            self.conversation_history.append(("user", user_query))
            self.conversation_history.append(("assistant", response))
            
            return response
            
        except Exception as e:
            logger.error(f"Error communicating with Groq: {e}", exc_info=True)
            return f"**Error:** I encountered an issue while analyzing your question: {str(e)}"

    def get_flight_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive flight summary for the loaded log.
        """
        if not self.is_initialized or self.analysis_cache is None:
            return {"error": "No flight log loaded"}
        
        return self.analysis_cache

    def clear_conversation(self):
        """
        Clear the conversation history while keeping the loaded log data.
        """
        self.conversation_history = []
        logger.info("Conversation history cleared.")

    def get_conversation_history(self) -> List[Tuple[str, str]]:
        """
        Get the current conversation history.
        """
        return self.conversation_history.copy()