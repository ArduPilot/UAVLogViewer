<template>
    <div
        :id="getDivName()"
        class="uav-widget"
        :style="{
            width: width + 'px',
            height: height + 'px',
            top: top + 'px',
            left: left + 'px',
        }"
    >
        <span class="uav-widget__move"></span>
        <span class="uav-widget__resize"></span>
        <span class="uav-widget__close" @click="close()"></span>
        <div class="uav-widget__content">
            <table>
                <thead>
                    <tr>
                        <th>Property</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(value, key) in decodedSolution" :key="key">
                        <td>{{ key }}</td>
                        <td>{{ value }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<script>
import { store } from "../Globals.js";
import { useWidget, widgetProps } from "./useWidget.js";

// The EKF solution status bits, bit 0 first (nav_filter_status in ArduPilot)
const SOLUTION_FLAGS = [
    "attitude",
    "horizVel",
    "vertVel",
    "horizPosRel",
    "horizPosAbs",
    "vertPos",
    "terrainAlt",
    "constPosMode",
    "predHorizPosRel",
    "predHorizPosAbs",
    "takeoffDetected",
    "takeoff",
    "touchdown",
    "usingGps",
    "gpsGlitching",
    "gpsQualityGood",
    "initialized",
    "rejectingAirspeed",
    "deadReckoning",
];

export default {
    name: "EkfHelperViewer",
    props: widgetProps,
    emits: ["close"],
    setup(props, { emit }) {
        return useWidget(props, emit, {
            name: "EkfHelperViewer",
            width: 220,
            height: 215,
            left: 310,
            top: 0,
        });
    },
    data() {
        return {
            filter: "",
            state: store,
            cursorTime: 0,
        };
    },
    computed: {
        closestIndex() {
            const messages = this.state.messages["XKF4[0]"];
            if (!messages) {
                return 0;
            }
            for (const index in messages.time_boot_ms) {
                if (messages.time_boot_ms[index] > this.cursorTime) {
                    return index;
                }
            }
            return 0;
        },
        solutionValue() {
            const messages = this.state.messages["XKF4[0]"];
            if (!this.closestIndex || !messages) {
                return 0;
            }
            return messages.SS[this.closestIndex];
        },
        decodedSolution() {
            const solution = this.solutionValue;
            return Object.fromEntries(
                SOLUTION_FLAGS.map((name, bit) => [
                    name,
                    Boolean(solution & (2 ** bit)),
                ]),
            );
        },
    },
    created() {
        this.$eventHub.$on("cesium-time-changed", this.setTime);
        this.$eventHub.$on("hoveredTime", this.setTime);
    },
    beforeUnmount() {
        this.$eventHub.$off("cesium-time-changed", this.setTime);
        this.$eventHub.$off("hoveredTime", this.setTime);
    },
    mounted() {
        this.init();
    },
    methods: {
        setTime(time) {
            this.cursorTime = time;
        },
        waitForMessage(fieldname) {
            this.$eventHub.$emit("loadType", fieldname.split(".")[0]);
            let interval;
            // gives up after 7 tries (it counted only after success, so it polled forever)
            let counter = 0;
            return new Promise((resolve, reject) => {
                interval = setInterval(() => {
                    if (this.state.messages[fieldname.split(".")[0]]) {
                        clearInterval(interval);
                        resolve();
                    } else if (++counter > 6) {
                        console.log("not resolving");
                        clearInterval(interval);
                        reject(new Error("Could not load messageType"));
                    }
                }, 2000);
            });
        },
        init() {
            // a log without EKF status leaves the table empty
            this.waitForMessage("EKF4.SS").catch((e) =>
                console.warn("EKF helper:", e.message),
            );
        },
    },
};
</script>

<style scoped>
/* All shell rules, handles, close button, and content layout come
   from src/styles/widget.css. */
</style>
