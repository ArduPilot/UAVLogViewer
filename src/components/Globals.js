/* eslint-disable camelcase */

import '../mavextra/mavextra'

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
    file: null,
    events: [],
    cssColors: [],
    colors: [],
    map_available: false,
    mission: [],
    show_map: false,
    currentTime: false,
    processDone: false,
    plot_on: false,
    processStatus: 'Pre-processing...',
    processPercentage: -1,
    map_loading: false,
    plot_loading: false,
    timeRange: null,
    textMessages: [],
    metadata: null,
    // cesium menu:
    modelScale: 1.0,
    showClickableTrajectory: false,
    showTrajectory: true,
    showWaypoints: true,
    cameraType: 'follow',
    expressions: [], // holds message name
    expressionErrors: [],
    allAxis: [0, 1, 2, 3, 4, 5],
    allColors: [
        '#1f77b4',
        '#ff7f0e',
        '#2ca02c',
        '#d62728',
        '#9467BD',
        '#8C564B'],
    /* global _COMMIT_ */
    commit: _COMMIT_.slice(0, 6),
    /* global _BUILDDATE_ */
    buildDate: _BUILDDATE_
}
