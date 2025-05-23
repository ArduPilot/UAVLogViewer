import os
from pymavlink import mavutil
import datetime
from typing import Dict, Any, List, Tuple, Optional 

# Main function to parse a MAVLink log file and extract telemetry info and timeseries data
def parse_mavlink_log(filepath: str) -> Dict[str, Any]:
    """
    Parses a MAVLink .bin log file and extracts key summary statistics, 
    time-series telemetry data, metadata, and critical flight events.

    Args:
        filepath (str): Path to the .bin log file.

    Returns:
        Dict[str, Any]: Parsed log data including summary, timeseries, metadata, and errors.
    """
    # Structure to store parsed data
    data = { 
        "summary": {
            "max_altitude_m": None, "total_flight_time_s": None,
            "gps_fix_lost_timestamps_s": [], "min_gps_sats": None, "max_gps_sats": None,
            "max_battery_temp_c": None, "critical_errors": [],
            "rc_signal_loss_timestamps_s": [], "flight_modes": [],
            "arm_time_utc": None, "disarm_time_utc": None,
        },
        "timeseries": {
            "altitude_agl": [], "gps_sats": [], "battery_voltage": [], "battery_current": [],
            "battery_remaining_pct": [], "attitude_pitch_deg": [], "attitude_roll_deg": [],
            "attitude_yaw_deg": [], "vibration_x": [], "vibration_y": [], "vibration_z": [],
            "battery_temperature_c": [],
        },
        "raw_message_counts": {},
        "metadata": {
            "filename": os.path.basename(filepath),
            "parse_time_utc": datetime.datetime.utcnow().isoformat() + "Z",
            "first_timestamp_us": None, "last_timestamp_us": None,
        }
    }
    
    # Initialize helper variables
    altitudes_agl: List[float] = []
    gps_sats_list: List[int] = []
    batt_temps_list: List[float] = []
    flight_mode_set: set[Any] = set()
    first_msg_time_us: Optional[float] = None
    last_msg_time_us: Optional[float] = None
    SAMPLING_INTERVAL_US = 5 * 1000 * 1000  
    last_sampled_time_us: Dict[str, float] = {}
    msg_count = 0
    mlog = None 

    try:
        print(f"Attempting to open MAVLink log: {filepath}")
        mlog = mavutil.mavlink_connection(filepath)
        
        # Handle failed connection
        if mlog is None: 
            print(f"MAVLink connection returned None for {filepath}. This might indicate an issue with the file or pymavlink.")
            data["summary"]["critical_errors"].append(f"Failed to establish MAVLink connection for {os.path.basename(filepath)}. The file might be corrupt or not a valid MAVLink log.")
            return data

        print(f"MAVLink log opened successfully: {filepath}. Type of mlog: {type(mlog)}")
        
        # Start reading MAVLink messages
        while True:
            msg = mlog.recv_match(blocking=True) 
            if not msg:
                print(f"No more messages from {filepath}. Assuming EOF or end of readable data after {msg_count} messages.")
                break 

            msg_count += 1
            msg_type = msg.get_type()

             # Count message type frequency
            data["raw_message_counts"][msg_type] = data["raw_message_counts"].get(msg_type, 0) + 1

            # Extract timestamp
            current_time_us = getattr(msg, 'TimeUS', None)
            if current_time_us is None and msg_type not in ['FMT', 'PARM', 'MSG', 'MULT', 'MODE', 'UNIT', 'FMTU']:
                if hasattr(msg, '_timestamp'): 
                    current_time_us = msg._timestamp * 1e6 
            
            # Track first and last timestamps
            if current_time_us is not None:
                if first_msg_time_us is None:
                    first_msg_time_us = current_time_us
                last_msg_time_us = current_time_us
                
                current_time_s = current_time_us / 1.0e6

                def should_sample(series_key: str, time_us: float) -> bool:
                    if time_us < last_sampled_time_us.get(series_key, 0) + SAMPLING_INTERVAL_US:
                        return False
                    last_sampled_time_us[series_key] = time_us
                    return True

                # Extract specific message types and values
                if msg_type == 'GPS':
                    if hasattr(msg, 'Alt'): altitudes_agl.append(msg.Alt)
                    if hasattr(msg, 'NSats'):
                        gps_sats_list.append(msg.NSats)
                        if should_sample('gps_sats', current_time_us):
                            data["timeseries"]["gps_sats"].append((round(current_time_s, 2), msg.NSats))
                    if hasattr(msg, 'Status') and msg.Status < 3:
                        data["summary"]["gps_fix_lost_timestamps_s"].append(round(current_time_s, 2))
                elif msg_type == 'GLOBAL_POSITION_INT':
                    if hasattr(msg, 'relative_alt'): 
                        alt_m = msg.relative_alt / 1000.0
                        altitudes_agl.append(alt_m)
                        if should_sample('altitude_agl', current_time_us):
                            data["timeseries"]["altitude_agl"].append((round(current_time_s, 2), round(alt_m, 2)))
                elif msg_type == 'VFR_HUD':
                    if hasattr(msg, 'alt'): 
                        altitudes_agl.append(msg.alt)
                        if should_sample('altitude_agl', current_time_us):
                            data["timeseries"]["altitude_agl"].append((round(current_time_s, 2), round(msg.alt, 2)))

                elif msg_type == 'BATTERY_STATUS':
                    if hasattr(msg, 'temperature') and msg.temperature != 32767:
                        temp_c = msg.temperature / 100.0
                        batt_temps_list.append(temp_c)
                        if should_sample('battery_temperature_c', current_time_us):
                                data["timeseries"]["battery_temperature_c"].append((round(current_time_s, 2), round(temp_c, 2)))
                    if hasattr(msg, 'voltages') and isinstance(msg.voltages, list) and len(msg.voltages) > 0:
                        voltage = msg.voltages[0] / 1000.0 
                        if voltage > 5 and should_sample('battery_voltage', current_time_us):
                            data["timeseries"]["battery_voltage"].append((round(current_time_s, 2), round(voltage, 2)))
                    if hasattr(msg, 'current_battery') and msg.current_battery != -1:
                        if should_sample('battery_current', current_time_us):
                            data["timeseries"]["battery_current"].append((round(current_time_s, 2), msg.current_battery / 100.0))
                    if hasattr(msg, 'battery_remaining') and msg.battery_remaining != -1:
                        if should_sample('battery_remaining_pct', current_time_us):
                            data["timeseries"]["battery_remaining_pct"].append((round(current_time_s, 2), msg.battery_remaining))
                
                elif msg_type == 'SYS_STATUS':
                    if hasattr(msg, 'voltage_battery'): 
                        voltage = msg.voltage_battery / 1000.0
                        if voltage > 5 and should_sample('battery_voltage', current_time_us):
                            if not any(ts[0] == round(current_time_s, 2) for ts in data["timeseries"]["battery_voltage"]):
                                data["timeseries"]["battery_voltage"].append((round(current_time_s, 2), round(voltage,2)))
                
                elif msg_type == 'STATUSTEXT':
                    if hasattr(msg, 'text') and ('ERR' in msg.text.upper() or 'FAIL' in msg.text.upper() or 'ERROR' in msg.text.upper()):
                        data["summary"]["critical_errors"].append(f"{round(current_time_s, 2)}s: {msg.text}")
                elif msg_type == 'EV': 
                    if hasattr(msg, 'Id') and ('FS_ACTN' in msg.Id.upper() or 'FAILSAFE' in msg.Id.upper()):
                        data["summary"]["critical_errors"].append(f"{round(current_time_s, 2)}s: Event - {msg.Id}")
                        if "RC" in msg.Id.upper(): 
                                data["summary"]["rc_signal_loss_timestamps_s"].append(round(current_time_s,2))
                    if hasattr(msg, 'Id') and 'ARMED' in msg.Id.upper():
                        data["summary"]["arm_time_utc"] = datetime.datetime.utcfromtimestamp(current_time_s).isoformat() + "Z"
                    if hasattr(msg, 'Id') and 'DISARMED' in msg.Id.upper():
                        data["summary"]["disarm_time_utc"] = datetime.datetime.utcfromtimestamp(current_time_s).isoformat() + "Z"

                elif msg_type == 'MODE': 
                    if hasattr(msg, 'Mode'): flight_mode_set.add(msg.Mode)
                
                elif msg_type == 'ATT':
                    if should_sample('attitude_pitch_deg', current_time_us) and all(hasattr(msg, attr) for attr in ['Pitch', 'Roll', 'Yaw']):
                        data["timeseries"]["attitude_pitch_deg"].append((round(current_time_s, 2), round(msg.Pitch, 2)))
                        data["timeseries"]["attitude_roll_deg"].append((round(current_time_s, 2), round(msg.Roll, 2)))
                        data["timeseries"]["attitude_yaw_deg"].append((round(current_time_s, 2), round(msg.Yaw, 2)))
                elif msg_type == 'VIBE':
                    if should_sample('vibration_x', current_time_us) and all(hasattr(msg, attr) for attr in ['VibeX', 'VibeY', 'VibeZ']):
                        data["timeseries"]["vibration_x"].append((round(current_time_s, 2), round(msg.VibeX, 2)))
                        data["timeseries"]["vibration_y"].append((round(current_time_s, 2), round(msg.VibeY, 2)))
                        data["timeseries"]["vibration_z"].append((round(current_time_s, 2), round(msg.VibeZ, 2)))
    
    except AttributeError as ae: 
        print(f"AttributeError during MAVLink parsing for {filepath}: {ae}")
        data["summary"]["critical_errors"].append(f"Parser attribute error for {os.path.basename(filepath)}: {str(ae)}")
    except Exception as e: 
        print(f"General error during MAVLink parsing for {filepath}: {e}")
        import traceback
        traceback.print_exc() 
        data["summary"]["critical_errors"].append(f"Parser error for {os.path.basename(filepath)}: {str(e)}")
    
    # Attempt to close the MAVLink connection if possible
    finally:
        if mlog and hasattr(mlog, 'close') and callable(mlog.close):
            try:
                mlog.close()
                print(f"MAVLink log file explicitly closed: {filepath}")
            except Exception as e_close:
                print(f"Error closing MAVLink log file {filepath}: {e_close}")
        elif mlog: 
            print(f"Warning: mlog object for {filepath} does not have a standard close method or is not callable. File might not be properly released by pymavlink.")

    # Post-processing summary calculations
    if altitudes_agl: data["summary"]["max_altitude_m"] = round(max(altitudes_agl), 2)
    if gps_sats_list:
        data["summary"]["min_gps_sats"] = min(gps_sats_list) if gps_sats_list else None
        data["summary"]["max_gps_sats"] = max(gps_sats_list) if gps_sats_list else None
    if batt_temps_list: data["summary"]["max_battery_temp_c"] = round(max(batt_temps_list), 2)
    
    data["summary"]["flight_modes"] = list(flight_mode_set)

    if first_msg_time_us is not None and last_msg_time_us is not None and first_msg_time_us <= last_msg_time_us :
        data["summary"]["total_flight_time_s"] = round((last_msg_time_us - first_msg_time_us) / 1.0e6, 2)
        data["metadata"]["first_timestamp_us"] = first_msg_time_us
        data["metadata"]["last_timestamp_us"] = last_msg_time_us
    else:
        data["summary"]["total_flight_time_s"] = 0
        if not any("Could not determine valid flight duration" in err for err in data["summary"]["critical_errors"]):
             data["summary"]["critical_errors"].append("Warning: Could not determine valid flight duration from timestamps.")

    # Remove duplicate timestamps and downsample long series
    data["summary"]["gps_fix_lost_timestamps_s"] = sorted(list(set(data["summary"]["gps_fix_lost_timestamps_s"])))
    data["summary"]["rc_signal_loss_timestamps_s"] = sorted(list(set(data["summary"]["rc_signal_loss_timestamps_s"])))
    
    MAX_TIMESERIES_POINTS = 75 
    for key in data["timeseries"]:
        if len(data["timeseries"][key]) > MAX_TIMESERIES_POINTS:
            step = max(1, len(data["timeseries"][key]) // MAX_TIMESERIES_POINTS)
            data["timeseries"][key] = data["timeseries"][key][::step]

    print(f"Finished parsing attempt. Parsed {msg_count} MAVLink messages from {os.path.basename(filepath)}.")
    return data