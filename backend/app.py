import os
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymavlink import mavutil

app = Flask(__name__)
CORS(app, resources={r"/chat": {"origins": "http://localhost:8080"}})

openai.api_key = ""
BIN_FILE_PATH = '/Users/rahulpanchal/Desktop/Project/UAVLogViewer/backend/UAV.bin'

def parse_dataflash_summary(log_path):
    mlog = mavutil.mavlink_connection(log_path, dialect='ardupilotmega', robust_parsing=True)

    max_alt, min_alt = None, None
    max_speed, max_speed_time = None, None
    max_batt_temp = None
    max_num_sats = None
    gps_signal_lost_times = []
    rc_signal_lost_times = []
    voltage_readings = []
    voltage_drop_time = None
    last_voltage = None
    max_ground_speed = None
    max_ground_speed_time = None
    error_msgs = []
    warning_msgs = []
    flight_armed = False
    flight_start_time, flight_end_time = None, None
    total_points = 0

    last_num_sats = None
    last_rc = None
    # Try to get times based on ARM/DISARM, altitude or mode transitions

    while True:
        msg = mlog.recv_match(blocking=False)
        if msg is None:
            break
        msg_type = msg.get_type()
        total_points += 1

        # Arm/Disarm detection (flight start/end)
        if hasattr(msg, 'Armed'):
            if not flight_armed and getattr(msg, 'Armed') == 1:
                flight_start_time = getattr(msg, 'TimeMS', None) or getattr(msg, 'TimeUS', None)
                flight_armed = True
            elif flight_armed and getattr(msg, 'Armed') == 0:
                flight_end_time = getattr(msg, 'TimeMS', None) or getattr(msg, 'TimeUS', None)
                flight_armed = False

        # Altitude
        for alt_field in ['Alt', 'AltMSL', 'RelAlt', 'height', 'heightMax']:
            if hasattr(msg, alt_field):
                alt = getattr(msg, alt_field)
                if isinstance(alt, (int, float)):
                    if max_alt is None or alt > max_alt:
                        max_alt = alt
                    if min_alt is None or alt < min_alt:
                        min_alt = alt

        # Battery temp (varies by field)
        for temp_field in ['Temp', 'Temperature', 'BattTemp', 'maxTemperature']:
            if hasattr(msg, temp_field):
                temp = getattr(msg, temp_field)
                if isinstance(temp, (int, float)):
                    if max_batt_temp is None or temp > max_batt_temp:
                        max_batt_temp = temp

        # Battery voltage (for anomaly)
        for volt_field in ['Volt', 'voltage', 'Vbat', 'Battery', 'Voltage', 'Volt1']:
            if hasattr(msg, volt_field):
                volt = getattr(msg, volt_field)
                if isinstance(volt, (int, float)):
                    voltage_readings.append((getattr(msg, 'TimeMS', None) or getattr(msg, 'TimeUS', None), volt))
                    if last_voltage is not None and abs(volt - last_voltage) > 2:  # Adjust threshold as needed
                        voltage_drop_time = getattr(msg, 'TimeMS', None) or getattr(msg, 'TimeUS', None)
                    last_voltage = volt

        # GPS satellites
        for sat_field in ['NSats', 'SatCount', 'NumSats', 'gpsNum']:
            if hasattr(msg, sat_field):
                num_sats = getattr(msg, sat_field)
                if isinstance(num_sats, (int, float)):
                    if max_num_sats is None or num_sats > max_num_sats:
                        max_num_sats = num_sats
                    # Detect GPS loss
                    if num_sats < 4 and (last_num_sats is None or last_num_sats >= 4):
                        gps_signal_lost_times.append(getattr(msg, 'TimeMS', None) or getattr(msg, 'TimeUS', None))
                    last_num_sats = num_sats

        # RC signal loss (look for zero or messages)
        for rc_field in ['RCIN', 'RC', 'RCInput', 'rcSn']:
            if hasattr(msg, rc_field):
                rcval = getattr(msg, rc_field)
                if isinstance(rcval, (int, float)) and rcval == 0 and (last_rc is None or last_rc != 0):
                    rc_signal_lost_times.append(getattr(msg, 'TimeMS', None) or getattr(msg, 'TimeUS', None))
                last_rc = rcval

        # Speed / Ground Speed
        for spd_field in ['Spd', 'GroundSpeed', 'xSpeed', 'ySpeed', 'zSpeed']:
            if hasattr(msg, spd_field):
                spd = getattr(msg, spd_field)
                t = getattr(msg, 'TimeMS', None) or getattr(msg, 'TimeUS', None)
                if isinstance(spd, (int, float)):
                    if max_speed is None or spd > max_speed:
                        max_speed = spd
                        max_speed_time = t

        # Explicit ground speed (for DJI logs)
        if hasattr(msg, 'xSpeed') and hasattr(msg, 'ySpeed'):
            ground_speed = (getattr(msg, 'xSpeed') ** 2 + getattr(msg, 'ySpeed') ** 2) ** 0.5
            t = getattr(msg, 'TimeMS', None) or getattr(msg, 'TimeUS', None)
            if max_ground_speed is None or ground_speed > max_ground_speed:
                max_ground_speed = ground_speed
                max_ground_speed_time = t

        # Message text, error/warning detection
        if hasattr(msg, 'Message'):
            message_text = getattr(msg, 'Message').lower()
            if 'error' in message_text or 'critical' in message_text or 'fail' in message_text or 'overheat' in message_text:
                error_msgs.append(message_text)
            elif 'warn' in message_text or 'anomaly' in message_text or 'signal lost' in message_text:
                warning_msgs.append(message_text)

        # Severity field (for Ardu logs)
        if hasattr(msg, 'severity') and hasattr(msg, 'text'):
            sev = getattr(msg, 'severity')
            text = getattr(msg, 'text', '').lower()
            if sev is not None and sev >= 3:  # 0=emergency, 1=alert, 2=critical, 3=error
                error_msgs.append(text)
            elif sev == 2:
                warning_msgs.append(text)

    # Estimate flight time (fallback)
    duration = None
    if flight_start_time and flight_end_time:
        duration = (flight_end_time - flight_start_time) / 1000  # ms to sec

    # Sudden battery voltage drop
    voltage_drop_detected = None
    if voltage_drop_time:
        voltage_drop_detected = f"Sudden voltage drop detected at {voltage_drop_time} ms"

    summary = {
        'max_altitude': max_alt,
        'min_altitude': min_alt,
        'max_speed': max_speed,
        'max_speed_time': max_speed_time,
        'max_batt_temp': max_batt_temp,
        'max_num_sats': max_num_sats,
        'gps_signal_lost_times': gps_signal_lost_times,
        'rc_signal_lost_times': rc_signal_lost_times,
        'voltage_drop': voltage_drop_detected,
        'max_ground_speed': max_ground_speed,
        'max_ground_speed_time': max_ground_speed_time,
        'error_msgs': error_msgs,
        'warning_msgs': warning_msgs,
        'flight_start_time': flight_start_time,
        'flight_end_time': flight_end_time,
        'duration_sec': duration,
        'total_points': total_points,
    }
    return summary

def build_context_text(summary):
    context = [f"Flight Log Summary:"]
    for k, v in summary.items():
        context.append(f"- {k}: {v}")
    return "\n".join(context)

def ask_llm(question, context):
    prompt = (
        "You are a drone log analyst AI. Use ONLY the provided summary of a UAV Dataflash log to answer the user's question. "
        "If the answer cannot be determined from the summary, say so.\n\n"
        f"{context}\n\n"
        f"User Question: {question}\n\n"
        "Answer:"
    )
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256
    )
    return response.choices[0].message.content.strip()

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question', '').strip()
    summary = parse_dataflash_summary(BIN_FILE_PATH)
    context_text = build_context_text(summary)
    answer = ask_llm(question, context_text)
    return jsonify({'answer': answer})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
