
VALIDGCS = { 
    'MAV_TYPE_FIXED_WING': 1,
    'MAV_TYPE_QUADROTOR': 2,
    'MAV_TYPE_COAXIAL': 3,
    'MAV_TYPE_HELICOPTER': 4,
    'MAV_TYPE_ANTENNA_TRACKER': 5,
    'MAV_TYPE_AIRSHIP': 7,
    'MAV_TYPE_FREE_BALLOON': 8,
    'MAV_TYPE_ROCKET': 9,
    'MAV_TYPE_GROUND_ROVER': 10,
    'MAV_TYPE_SURFACE_BOAT': 11,
    'MAV_TYPE_SUBMARINE': 12,
    'MAV_TYPE_HEXAROTOR': 13,
    'MAV_TYPE_OCTOROTOR': 14,
    'MAV_TYPE_TRICOPTER': 15,
    'MAV_TYPE_FLAPPING_WING': 16,
    'MAV_TYPE_KITE': 17
}


def extract_attitude(messages):
        attitudes = {}
        if 'ATTITUDE' in messages:
            attitude_msgs = messages['ATTITUDE']
            for i in range(len(attitude_msgs['time_boot_ms'])):
                timestamp = int(attitude_msgs['time_boot_ms'][i])
                attitudes[timestamp] = [
                    attitude_msgs['roll'][i],
                    attitude_msgs['pitch'][i],
                    attitude_msgs['yaw'][i]
                ]
        return attitudes

def extract_flight_modes(messages):
    modes = []
    if 'HEARTBEAT' in messages:
        msgs = messages['HEARTBEAT']
        modes.append([msgs['time_boot_ms'][0], msgs['asText'][0]])
        for i in range(len(msgs['time_boot_ms'])):
            if msgs['type'][i] in VALIDGCS.values():
                current_mode = msgs['asText'][i] if msgs['asText'][i] is not None else 'Unknown'
                if current_mode != modes[-1][1]:
                    modes.append([msgs['time_boot_ms'][i], current_mode])
    return modes

def extract_events(messages):
    armed_state = []
    if 'HEARTBEAT' in messages:
        msgs = messages['HEARTBEAT']
        first_event = 'Armed' if (msgs['base_mode'][0] & 0b10000000) == 128 else 'Disarmed'
        armed_state.append([msgs['time_boot_ms'][0], first_event])
        for i in range(len(msgs['time_boot_ms'])):
            if msgs['type'][i] != 6:  # 6 typically maps to MAV_TYPE_GCS
                new_event = 'Armed' if (msgs['base_mode'][i] & 0b10000000) == 128 else 'Disarmed'
                if new_event != armed_state[-1][1]:
                    armed_state.append([msgs['time_boot_ms'][i], new_event])
    return armed_state

def extract_mission(messages):
    wps = []
    if 'CMD' in messages:
        cmd_msgs = messages['CMD']
        for i in range(len(cmd_msgs['time_boot_ms'])):
            if cmd_msgs['Lat'][i] != 0:
                lat = cmd_msgs['Lat'][i]
                lon = cmd_msgs['Lng'][i]
                if abs(lat) > 180:
                    lat = lat / 1e7
                    lon = lon / 1e7
                wps.append([lon, lat, cmd_msgs['Alt'][i]])
    return wps

def extract_vehicle_type(messages):
    if 'HEARTBEAT' in messages:
        heartbeat = messages['HEARTBEAT']
        if 'craft' in heartbeat:
            for value in heartbeat['craft']:
                if value is not None:
                    return value
    return None

'''
def extract_attitude_sources(messages):
    return {
        "quaternions": [],
        "eulers": ["ATTITUDE"]
    }
'''

def extract_trajectory_sources(messages):
    sources = []
    for key in ['GLOBAL_POSITION_INT', 'GPS_RAW_INT', 'AHRS2', 'AHRS3']:
        if key in messages:
            sources.append(key)
    return sources

def extract_trajectory(messages, source = 'GPS_RAW_INT'):
    ret = {}

    if 'GLOBAL_POSITION_INT' in messages and source == 'GLOBAL_POSITION_INT':
        trajectory = []
        time_trajectory = {}
        start_altitude = None
        gps_data = messages['GLOBAL_POSITION_INT']

        for i in range(len(gps_data['time_boot_ms'])):
            if gps_data['lat'][i] != 0:
                if start_altitude is None:
                    start_altitude = gps_data['relative_alt'][i]

                trajectory.append([
                    gps_data['lon'][i],
                    gps_data['lat'][i],
                    gps_data['relative_alt'][i] - start_altitude,
                    gps_data['time_boot_ms'][i]
                ])

                time_trajectory[gps_data['time_boot_ms'][i]] = [
                    gps_data['lon'][i],
                    gps_data['lat'][i],
                    gps_data['relative_alt'][i],
                    gps_data['time_boot_ms'][i]
                ]

        if trajectory:
            ret['GLOBAL_POSITION_INT'] = {
                'startAltitude': start_altitude,
                'trajectory': trajectory,
                'timeTrajectory': time_trajectory
            }

    if 'GPS_RAW_INT' in messages and source == 'GPS_RAW_INT':
        trajectory = []
        time_trajectory = {}
        start_altitude = None
        gps_data = messages['GPS_RAW_INT']

        for i in range(len(gps_data['time_boot_ms'])):
            if gps_data['lat'][i] != 0:
                if start_altitude is None:
                    start_altitude = gps_data['alt'][0] / 1000

                trajectory.append([
                    gps_data['lon'][i] * 1e-7,
                    gps_data['lat'][i] * 1e-7,
                    gps_data['alt'][i] / 1000 - start_altitude,
                    gps_data['time_boot_ms'][i]
                ])

                time_trajectory[gps_data['time_boot_ms'][i]] = [
                    gps_data['lon'][i] * 1e-7,
                    gps_data['lat'][i] * 1e-7,
                    gps_data['alt'][i] / 1000,
                    gps_data['time_boot_ms'][i]
                ]
        #print('trajector', trajectory)
        if trajectory:
            ret['GPS_RAW_INT'] = {
                'startAltitude': start_altitude,
                'trajectory': trajectory,
                'timeTrajectory': time_trajectory
            }

    if 'AHRS2' in messages and source == 'AHRS2':
        trajectory = []
        time_trajectory = {}
        start_altitude = None
        gps_data = messages['AHRS2']

        for i in range(len(gps_data['time_boot_ms'])):
            if start_altitude is None:
                start_altitude = gps_data['altitude'][0]

            trajectory.append([
                gps_data['lng'][i] * 1e-7,
                gps_data['lat'][i] * 1e-7,
                gps_data['altitude'][i] - start_altitude,
                gps_data['time_boot_ms'][i]
            ])

            time_trajectory[gps_data['time_boot_ms'][i]] = [
                gps_data['lng'][i] * 1e-7,
                gps_data['lat'][i] * 1e-7,
                gps_data['altitude'][i],
                gps_data['time_boot_ms'][i]
            ]

        if trajectory:
            ret['AHRS2'] = {
                'startAltitude': start_altitude,
                'trajectory': trajectory,
                'timeTrajectory': time_trajectory
            }

    if 'AHRS3' in messages and source == 'AHRS3':
        trajectory = []
        time_trajectory = {}
        start_altitude = None
        gps_data = messages['AHRS3']

        for i in range(len(gps_data['time_boot_ms'])):
            if gps_data['lat'][i] != 0:
                if start_altitude is None:
                    start_altitude = gps_data['altitude'][0]

                trajectory.append([
                    gps_data['lng'][i] * 1e-7,
                    gps_data['lat'][i] * 1e-7,
                    gps_data['altitude'][i] - start_altitude,
                    gps_data['time_boot_ms'][i]
                ])

                time_trajectory[gps_data['time_boot_ms'][i]] = [
                    gps_data['lng'][i] * 1e-7,
                    gps_data['lat'][i] * 1e-7,
                    gps_data['altitude'][i],
                    gps_data['time_boot_ms'][i]
                ]

        if trajectory:
            ret['AHRS3'] = {
                'startAltitude': start_altitude,
                'trajectory': trajectory,
                'timeTrajectory': time_trajectory
            }

    return ret

def extract_text_messages(messages):
    texts = []
    if 'STATUSTEXT' in messages:
        text_msgs = messages['STATUSTEXT']
        for i in range(len(text_msgs['time_boot_ms'])):
            texts.append([text_msgs['time_boot_ms'][i], text_msgs['severity'][i], text_msgs['text'][i]])
    return texts


def extract_named_value_float_names(messages):
    if 'NAMED_VALUE_FLOAT' in messages:
        return list(set(messages['NAMED_VALUE_FLOAT']['name']))
    return []

