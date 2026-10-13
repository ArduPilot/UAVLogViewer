import "../mavextra/mavextra";
import "../mavextra/mymavextra";
import { markRaw, reactive } from "vue";
import { eventHub } from "../eventHub.js";

// Log data the app only replaces, never edits in place (messages, trajectories, attitudes,
// parameters, plot data, Cesium colors): Vue keeps it as it is instead of proxying every object
// and array in it. Assigning it to the store still updates whatever shows it.
export function keepRaw(value) {
    return value !== null && typeof value === "object" ? markRaw(value) : value;
}

// The app's shared state. Components use it as "state: store" in data() and change it directly.
export const store = reactive({
    // currentTrajectory: [],
    trajectorySource: "",
    trajectories: {},
    timeTrajectory: {},
    timeAttitude: {},
    timeAttitudeQ: {},
    logType: "",
    defaultParams: {},
    showParams: false,
    showRadio: false,
    showMessages: false,
    showDeviceIDs: false,
    showAttitude: false,
    showEkfHelper: false,
    flightModeChanges: [],
    file: null,
    events: [],
    cssColors: [],
    colors: [],
    mapAvailable: false,
    mission: [],
    fences: [],
    showFences: true,
    showMap: false,
    showMagfit: false,
    currentTime: false,
    processDone: false,
    plotOn: false,
    processStatus: "Pre-processing...",
    processPercentage: -1,
    mapLoading: false,
    mapError: null,
    plotLoading: false,
    timeRange: null,
    textMessages: [],
    namedFloats: [],
    metadata: null,
    // cesium menu:
    modelScale: 1.0,
    heightOffset: 0.0,
    showClickableTrajectory: false,
    showTrajectory: true,
    trajectorySources: [],
    // Extra trajectory sources overlaid for comparison with the primary one.
    comparisonTrajectories: [],
    // Solid colors used (by index) to draw the comparison trajectory overlays.
    comparisonTrajectoryColors: [
        "#00ffff",
        "#ff00ff",
        "#ffff00",
        "#ff8000",
        "#00ff80",
        "#8000ff",
    ],
    attitudeSources: {},
    attitudeSource: null,
    showWaypoints: true,
    cameraType: "follow",
    expressions: [], // holds message name
    expressionErrors: [],
    plotCache: {},
    allAxis: [0, 1, 2, 3, 4, 5],
    allColors: [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467BD",
        "#8C564B",
    ],
    radioMode: "2",
    /* global _COMMIT_ */
    commit: _COMMIT_.slice(0, 6),
    /* global _BUILDDATE_ */
    buildDate: _BUILDDATE_,
    childPlots: [],
});

// Everything derived from the loaded log. Cleared before a new log is parsed (e.g. a second log
// sent by an embedding page), so nothing carries over from the previous one: flight modes,
// parameters, trajectories, and plots whose cached data belongs to the old log.
// First y axis / color that no plotted expression uses (the last one when all are taken)
export function firstFreeAxis(state) {
    return (
        state.allAxis.find(
            // saved presets may hold the axis as a string
            (axis) =>
                !state.expressions.some((field) => Number(field.axis) === axis),
        ) ?? state.allAxis.at(-1)
    );
}

export function firstFreeColor(state) {
    return (
        state.allColors.find(
            (color) =>
                !state.expressions.some((field) => field.color === color),
        ) ?? state.allColors.at(-1)
    );
}

// Remove every plotted expression (the plot panel redraws or closes through its watcher)
export function clearExpressions(state) {
    state.expressions.splice(0);
}

export function resetLogState() {
    Object.assign(store, {
        mapAvailable: false,
        showMap: false,
        mapError: null,
        files: undefined,
        flightModeChanges: [],
        events: [],
        mission: [],
        fences: [],
        textMessages: [],
        namedFloats: [],
        metadata: null,
        params: undefined,
        defaultParams: {},
        trajectorySource: "",
        trajectorySources: [],
        trajectories: {},
        currentTrajectory: [],
        timeTrajectory: {},
        timeAttitude: {},
        timeAttitudeQ: {},
        attitudeSources: {},
        attitudeSource: null,
        timeRange: null,
        expressions: [],
        expressionErrors: [],
        plotCache: {},
        // the mode color palette is sized for the log's flight modes
        colors: [],
        cssColors: [],
    });
    // params is not reactive: widgets that list it recompute on this event, and would otherwise
    // keep rendering the previous log's parameters from a cache
    eventHub.$emit("paramsUpdated");
}
