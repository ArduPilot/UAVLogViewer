/* eslint-disable camelcase */

export var store = {
    // current_trajectory: [],
    trajectorySource: '',
    trajectories: {},
    time_trajectory: {},
    time_attitude: {},
    time_attitudeQ: {},
    log_type: '',
    show_params: false,
    show_radio: false,
    show_messages: false,
    flight_mode_changes: [],
    armed_events: [],
    cssColors: [],
    colors: [],
    map_available: false,
    mission: [],
    show_map: true,
    currentTime: false,
    processDone: false,
    plot_on: false,
    processStatus: 'Pre-processing...',
    processPercentage: -1,
    map_loading: false,
    plot_loading: false,
    timeRange: null,
    textMessages: [],
    // cesium menu:
    modelScale: 1.0,
    showClickableTrajectory: false,
    showTrajectory: true,
    showWaypoints: true,
    cameraType: 'follow',
    expressions: [], // holds message name
    allAxis: [0, 1, 2, 3, 4, 5],
    allColors: [
        '#1f77b4',
        '#ff7f0e',
        '#2ca02c',
        '#d62728',
        '#9467BD',
        '#8C564B']
}

// TODO: Move these to their own file mavextra.js

function fromEuler (roll, pitch, yaw) {
    /*
    Returns a Rotation Matrix3 as an array. The elements are ordered Row-major
    [ 0 1 2,
      3 4 5,
      6 7 8]
    */

    let mat = []
    let cp = Math.cos(pitch)
    let sp = Math.sin(pitch)
    let sr = Math.sin(roll)
    let cr = Math.cos(roll)
    let sy = Math.sin(yaw)
    let cy = Math.cos(yaw)

    mat.push(cp * cy)
    mat.push((sr * sp * cy) - (cr * sy))
    mat.push((cr * sp * cy) + (sr * sy))
    mat.push(cp * sy)
    mat.push((sr * sp * sy) + (cr * cy))
    mat.push((cr * sp * sy) - (sr * cy))
    mat.push(-sp)
    mat.push(sr * cp)
    mat.push(cr * cp)
    return mat
}

// eslint-disable-next-line
window.degrees = function (a) {
    return 57.2958 * a
}

window.radians = function (a) {
    return 0.0174533 * a
}

// convert m/s to Km/h
window.kmh = function (mps) {
    return mps * 3.6
}

// calculate barometric altitude
window.altitude = function (SCALED_PRESSURE, groundPressure, groundTemp) {
    if (groundPressure === null) {
        if (window.param('GND_ABS_PRESS')) {
            return 0
        }
    }
    groundPressure = window.param('GND_ABS_PRESS')
    if (groundTemp === null) {
        groundTemp = self.param('GND_TEMP', 0)
    }
    let scaling = groundPressure / (SCALED_PRESSURE.press_abs * 100.0)
    let temp = groundTemp + 273.15
    return Math.log(scaling) * temp * 29271.267 * 0.001
}

window.altitude2 = function (SCALED_PRESSURE, groundPressure, groundTemp) {
    // calculate barometric altitude'
    if (groundPressure == null) {
        if (window.param('GND_ABS_PRESS') === null) {
            return 0
        }
    }
    groundPressure = self.param('GND_ABS_PRESS', 1)
    if (groundTemp === null) {
        groundTemp = self.param('GND_TEMP', 0)
    }
    let scaling = SCALED_PRESSURE.press_abs * 100.0 / groundPressure
    let temp = groundTemp + 273.15
    return 153.8462 * temp * (1.0 - Math.exp(0.190259 * Math.log(scaling)))
}

window.mag_heading = function (RAW_IMU, ATTITUDE, declination, SENSOR_OFFSETS, ofs) {
    // calculate heading from raw magnetometer
    if (declination === undefined) {
        declination = window.degrees(window.params['COMPASS_DEC'])
    }
    let mag_x = RAW_IMU.xmag
    let mag_y = RAW_IMU.ymag
    let mag_z = RAW_IMU.zmag
    if (SENSOR_OFFSETS !== undefined && ofs !== undefined) {
        mag_x += ofs[0] - SENSOR_OFFSETS.mag_ofs_x
        mag_y += ofs[1] - SENSOR_OFFSETS.mag_ofs_y
        mag_z += ofs[2] - SENSOR_OFFSETS.mag_ofs_z
    }

    // go via a DCM matrix to match the APM calculation
    let dcm_matrix = fromEuler(ATTITUDE.roll, ATTITUDE.pitch, ATTITUDE.yaw)
    let cos_pitch_sq = 1.0 - (dcm_matrix[6] * dcm_matrix[6])
    let headY = mag_y * dcm_matrix[8] - mag_z * dcm_matrix[7]
    let headX = mag_x * cos_pitch_sq - dcm_matrix[6] * (mag_y * dcm_matrix[7] + mag_z * dcm_matrix[8])
    let heading = window.degrees(Math.atan2(-headY, headX)) + declination
    if (heading < -180) {
        heading += 360
    }
    return heading
}

window.mag_heading_df = function (MAG, ATT, declination, SENSOR_OFFSETS, ofs) {
    // calculate heading from raw magnetometer
    if (declination === undefined) {
        declination = window.degrees(window.params['COMPASS_DEC'])
    }
    let mag_x = MAG.MagX
    let mag_y = MAG.MagY
    let mag_z = MAG.MagZ
    if (SENSOR_OFFSETS !== undefined && ofs !== undefined) {
        mag_x += ofs[0] - SENSOR_OFFSETS.mag_ofs_x
        mag_y += ofs[1] - SENSOR_OFFSETS.mag_ofs_y
        mag_z += ofs[2] - SENSOR_OFFSETS.mag_ofs_z
    }

    // go via a DCM matrix to match the APM calculation
    let dcm_matrix = fromEuler(window.radians(ATT.Roll), window.radians(ATT.Pitch), window.radians(ATT.Yaw))
    let cos_pitch_sq = 1.0 - (dcm_matrix[6] * dcm_matrix[6])
    let headY = mag_y * dcm_matrix[8] - mag_z * dcm_matrix[7]
    let headX = mag_x * cos_pitch_sq - dcm_matrix[6] * (mag_y * dcm_matrix[7] + mag_z * dcm_matrix[8])
    let heading = window.degrees(Math.atan2(-headY, headX)) + declination
    if (heading < 0) {
        heading += 360
    }
    return heading
}
