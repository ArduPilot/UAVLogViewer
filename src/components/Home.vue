<template>
    <div id="vuewrapper" style="height: 100%">
        <template
            v-if="(state.mapLoading && !state.mapError) || state.plotLoading"
        >
            <div id="waiting">
                <atom-spinner
                    :animation-duration="1000"
                    :color="'#64e9ff'"
                    :size="300"
                />
            </div>
        </template>
        <TxInputsViewer
            v-if="state.mapAvailable && state.showMap && state.showRadio"
            @close="state.showRadio = false"
        ></TxInputsViewer>
        <ParamViewer
            v-if="state.showParams"
            @close="state.showParams = false"
        ></ParamViewer>
        <MessageViewer
            v-if="state.showMessages"
            @close="state.showMessages = false"
        ></MessageViewer>
        <DeviceIDViewer
            v-if="state.showDeviceIDs"
            @close="state.showDeviceIDs = false"
        ></DeviceIDViewer>
        <AttitudeViewer
            v-if="state.showAttitude"
            @close="state.showAttitude = false"
        ></AttitudeViewer>
        <MagFitTool
            v-if="state.showMagfit"
            :resizeable="false"
            @close="state.showMagfit = false"
        ></MagFitTool>
        <EkfHelperTool
            v-if="state.showEkfHelper"
            @close="state.showEkfHelper = false"
        ></EkfHelperTool>
        <div class="container-fluid" style="height: 100%; overflow: hidden">
            <sidebar />

            <main
                class="col-md-9 ms-sm-auto col-lg-10 flex-column d-sm-flex"
                role="main"
            >
                <div
                    v-if="state.plotOn"
                    class="row"
                    :class="[state.showMap ? 'h-50' : 'h-100']"
                >
                    <div class="col-12">
                        <Plotly />
                    </div>
                </div>
                <div
                    v-if="state.showMap"
                    class="row"
                    :class="[state.plotOn ? 'h-50' : 'h-100']"
                >
                    <div class="col-12 noPadding">
                        <CesiumViewer
                            v-if="
                                state.mapAvailable && mapOk && !state.mapError
                            "
                            ref="cesiumViewer"
                        />
                        <div v-if="state.mapError" class="map-error-container">
                            <i class="fa-solid fa-triangle-exclamation"></i>
                            <h3>Map Initialization Failed</h3>
                            <p>{{ state.mapError }}</p>
                            <button
                                class="btn btn-outline-info btn-sm"
                                @click="
                                    state.mapError = null;
                                    state.showMap = false;
                                "
                            >
                                Dismiss
                            </button>
                        </div>
                        <div
                            v-else-if="!(state.mapAvailable && mapOk)"
                            class="map-error-container"
                        >
                            <i class="fa-solid fa-map-location-dot"></i>
                            <h3>No Map Data</h3>
                            <p>
                                This log file does not contain enough GPS or
                                trajectory data to display on the map.
                            </p>
                            <button
                                class="btn btn-outline-info btn-sm"
                                @click="state.showMap = false"
                            >
                                Close Map
                            </button>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    </div>
</template>

<script>
import isOnline from "is-online";
import Plotly from "@/components/Plotly.vue";
import CesiumViewer from "@/components/CesiumViewer.vue";
import Sidebar from "@/components/Sidebar.vue";
import TxInputsViewer from "@/components/widgets/TxInputsViewer.vue";
import ParamViewer from "@/components/widgets/ParamViewer.vue";
import MessageViewer from "@/components/widgets/MessageViewer.vue";
import DeviceIDViewer from "@/components/widgets/DeviceIDViewer.vue";
import AttitudeViewer from "@/components/widgets/AttitudeWidget.vue";
import { keepRaw, store } from "@/components/Globals.js";
import { AtomSpinner } from "epic-spinners";
import { Color } from "cesium";
import colormap from "colormap";
import { DataflashDataExtractor } from "@/tools/dataflashDataExtractor";
import { MavlinkDataExtractor } from "@/tools/mavlinkDataExtractor";
import { DjiDataExtractor } from "@/tools/djiDataExtractor";
import { zoneOfFlight } from "@/shared/lib/flightTime.js";
import MagFitTool from "@/components/widgets/MagFitTool.vue";
import EkfHelperTool from "@/components/widgets/EkfHelperTool.vue";

// any other log type is DataFlash
const EXTRACTORS = { tlog: MavlinkDataExtractor, dji: DjiDataExtractor };

export default {
    name: "Home",
    components: {
        Sidebar,
        Plotly,
        CesiumViewer,
        AtomSpinner,
        TxInputsViewer,
        ParamViewer,
        MessageViewer,
        DeviceIDViewer,
        AttitudeViewer,
        MagFitTool,
        EkfHelperTool,
    },
    data() {
        return {
            state: store,
            dataExtractor: null,
        };
    },
    computed: {
        mapOk() {
            return (
                this.state.flightModeChanges !== undefined &&
                this.state.currentTrajectory !== undefined &&
                this.state.currentTrajectory.length > 0 &&
                (Object.keys(this.state.timeAttitude).length > 0 ||
                    Object.keys(this.state.timeAttitudeQ).length > 0)
            );
        },
        setOfModes() {
            const set = [];
            if (!this.state.flightModeChanges) {
                return [];
            }
            for (const mode of this.state.flightModeChanges) {
                if (!set.includes(mode[1])) {
                    set.push(mode[1]);
                }
            }
            return set;
        },
    },
    watch: {
        "state.showMap"() {
            this.$nextTick(() => this.$eventHub.$emit("force-resize-plotly"));
        },
    },
    created() {
        this.$eventHub.$on("messagesDoneLoading", this.extractFlightData);
        this.$eventHub.$on("cesium-time-changed", this.seekParams);
        this.state.messages = keepRaw({});
        this.state.timeAttitude = [];
        this.state.timeAttitudeQ = [];
        this.state.currentTrajectory = [];
        isOnline().then((a) => {
            this.state.isOnline = a;
        });
    },
    beforeUnmount() {
        this.$eventHub.$off("messagesDoneLoading", this.extractFlightData);
        this.$eventHub.$off("cesium-time-changed", this.seekParams);
    },
    methods: {
        extractFlightData() {
            // chosen per log: a page can load a tlog and later a DataFlash log
            this.dataExtractor =
                EXTRACTORS[this.state.logType] ?? DataflashDataExtractor;
            if (
                "FMTU" in this.state.messages &&
                this.state.messages.FMTU.length === 0
            ) {
                this.state.processStatus = "ERROR PARSING?";
            }
            // each step deletes the messages it no longer needs, so the order matters
            this.extractTimeline();
            this.extractVehicleAndParams();
            if (this.state.textMessages.length === 0) {
                this.state.textMessages =
                    this.dataExtractor.extractTextMessages(this.state.messages);
            }
            delete this.state.messages.MSG;

            if (this.state.colors.length === 0) {
                this.generateColorMMap();
            }
            this.extractAttitudeData();
            this.extractTrajectoryData();
            this.extractMetadata();
            delete this.state.messages.AHR2;
            delete this.state.messages.POS;
            delete this.state.messages.GPS;

            this.state.fences = this.dataExtractor.extractFences(
                this.state.messages,
            );

            this.state.processStatus = "Processed!";
            this.state.processDone = true;
            // Change to plot view after 2 seconds so the Processed status is readable
            setTimeout(() => {
                this.$eventHub.$emit("set-selected", "plot");
            }, 2000);

            // Only set showMap to true if it is available and was previously unavailable
            if (!this.state.mapAvailable) {
                this.state.mapAvailable =
                    this.state.currentTrajectory.length > 0;
                if (this.state.mapAvailable) {
                    this.state.showMap = true;
                }
            }
        },

        extractTimeline() {
            if (this.state.flightModeChanges.length === 0) {
                this.state.flightModeChanges =
                    this.dataExtractor.extractFlightModes(this.state.messages);
            }
            delete this.state.messages.MODE;

            if (this.state.events.length === 0) {
                this.state.events = this.dataExtractor.extractEvents(
                    this.state.messages,
                );
            }
            delete this.state.messages.STAT;
            delete this.state.messages.EV;

            if (this.state.mission.length === 0) {
                this.state.mission = this.dataExtractor.extractMission(
                    this.state.messages,
                );
            }
            delete this.state.messages.CMD;
        },

        // parameter values at the playback time
        seekParams(time) {
            this.state.params?.seek(time);
        },

        extractVehicleAndParams() {
            this.state.vehicle = this.dataExtractor.extractVehicleType(
                this.state.messages,
            );
            if (this.state.params === undefined) {
                this.state.params = keepRaw(
                    this.dataExtractor.extractParams(this.state.messages),
                );
                if (this.state.params !== undefined) {
                    this.state.defaultParams =
                        this.dataExtractor.extractDefaultParams(
                            this.state.messages,
                        );
                }
            }
            if (this.state.vehicle === "quadcopter") {
                this.state.vehicle +=
                    this.state.params?.get("FRAME_TYPE") === 0 ? "+" : "x";
            }
        },

        extractAttitudeData() {
            this.state.attitudeSources =
                this.dataExtractor.extractAttitudeSources(this.state.messages);
            const { quaternions, eulers } = this.state.attitudeSources;
            if (quaternions.length > 0) {
                this.state.attitudeSource = quaternions[0];
                this.state.timeAttitudeQ = keepRaw(
                    this.dataExtractor.extractAttitudeQ(
                        this.state.messages,
                        quaternions[0],
                    ),
                );
            } else if (eulers.length > 0) {
                this.state.attitudeSource = eulers[0];
                this.state.timeAttitude = keepRaw(
                    this.dataExtractor.extractAttitude(
                        this.state.messages,
                        eulers[0],
                    ),
                );
            }
            const list = Object.keys(this.state.timeAttitude);
            this.state.lastTime = Number.parseInt(list[list.length - 1]);
        },

        extractTrajectoryData() {
            this.state.trajectorySources =
                this.dataExtractor.extractTrajectorySources(
                    this.state.messages,
                );
            if (this.state.trajectorySources.length === 0) {
                return;
            }
            const first = this.state.trajectorySources[0];
            this.state.trajectorySource = first;
            this.state.trajectories = keepRaw(
                this.dataExtractor.extractTrajectory(
                    this.state.messages,
                    first,
                ),
            );
            try {
                this.state.currentTrajectory = keepRaw(
                    this.state.trajectories[first].trajectory,
                );
                this.state.timeTrajectory = keepRaw(
                    this.state.trajectories[first].timeTrajectory,
                );
            } catch {
                console.log("unable to load trajectory");
            }
        },

        extractMetadata() {
            try {
                const gps = this.state.messages?.GPS?.time_boot_ms
                    ? this.state.messages.GPS
                    : this.state.messages["GPS[0]"];
                // tlog and DJI logs have no GPS time to extract here: their parser already
                // sent the start time with the metadata, so keep that one
                const startTime = this.dataExtractor.extractStartTime(gps);
                if (startTime !== undefined) {
                    this.state.metadata = { ...this.state.metadata, startTime };
                }
            } catch (error) {
                console.log("unable to load metadata");
                console.log(error);
            }
            // where the flight was (also without GPS messages): the plots show the local time there
            this.state.metadata = {
                ...this.state.metadata,
                timeZone: zoneOfFlight(this.state.currentTrajectory),
            };
            try {
                this.state.namedFloats =
                    this.dataExtractor.extractNamedValueFloatNames(
                        this.state.messages,
                    );
                console.log(this.state.namedFloats);
            } catch (error) {
                console.log("unable to load named floats");
                console.log(error);
            }
        },

        generateColorMMap() {
            const colorMapOptions = {
                colormap: "hsv",
                nshades: Math.max(11, this.setOfModes.length),
                format: "rgbaString",
                alpha: 1,
            };
            // colormap used on legend.
            this.state.cssColors = colormap(colorMapOptions);

            // colormap used on Cesium
            colorMapOptions.format = "float";
            this.state.colors = keepRaw(
                colormap(colorMapOptions).map(
                    (rgba) => new Color(rgba[0], rgba[1], rgba[2]),
                ),
            );
        },
    },
};
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
body {
    margin: 0;
    padding: 0;
}

.container-fluid {
    padding-left: 0;
    padding-right: 0;
}

/* <main> is a column outside a .row, which Bootstrap 5 does not pad; without the gutter the
   rows inside it would start 12px early, under the sidebar */
.row {
    --bs-gutter-x: 0;
}

div .col-12 {
    padding-left: 0;
    padding-right: 0;
}

i {
    margin: 10px;
}

i .dropdown {
    float: right;
}

.noPadding {
    padding-left: 4px;
    padding-right: 6px;
    max-height: 100%;
}

div #waiting {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1000;
    display: block;
    background-color: black;
    opacity: 0.75;
    text-align: center;
}

.map-error-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    background-color: #1a1e24;
    color: #e0e6ed;
    text-align: center;
    padding: 2rem;
    border: 1px solid #3d4450;
    border-radius: 8px;
    margin: 10px;
}

.map-error-container i {
    font-size: 3rem;
    color: #fc0;
    margin-bottom: 1rem;
}

.map-error-container h3 {
    margin-bottom: 0.5rem;
    color: #64e9ff;
}

.map-error-container p {
    max-width: 500px;
    margin-bottom: 1.5rem;
    color: #acb6c2;
}

/* ATOM SPINNER */

div .atom-spinner {
    margin: auto;
    margin-top: 15%;
}
</style>
<style>
/* links are white unless a rule says otherwise: Bootstrap reads its link colors from these */
#app {
    --bs-link-color-rgb: 255, 255, 255;
    --bs-link-hover-color-rgb: 255, 255, 255;
}

#app a {
    text-decoration: none;
}
</style>
