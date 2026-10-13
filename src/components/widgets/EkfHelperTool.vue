<template>
    <div
        :id="getDivName()"
        :style="{
            width: width + 'px',
            height: height + 'px',
            top: top + 'px',
            left: left + 'px',
        }"
    >
        <div id="paneContent">
            {{ solutionValue }} {{ closestIndex }}
            <span
                style="float: right; margin: 3px; cursor: pointer"
                @click="close()"
            >
                X
            </span>
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
            console.log(messages);
            if (!messages) {
                return 0;
            }
            for (const index in messages.time_boot_ms) {
                if (messages.time_boot_ms[index] > this.cursorTime) {
                    return index;
                }
            }
            console.log(
                messages.time_boot_ms[messages.time_boot_ms.length - 1],
            );
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
div #paneEkfHelperViewer {
    min-width: 220px;
    min-height: 150px;
    position: absolute;
    background: rgb(253 254 255 / 85.6%);
    color: #141924;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    z-index: 10000;
    box-shadow: 9px 9px 3px -6px rgb(26 26 26 / 69.9%);
    border-radius: 5px;
    user-select: none;
}

div #paneEkfHelperViewer::before {
    content: "\25e2";
    color: #fff;
    background-color: rgb(38 53 71);
    position: absolute;
    bottom: -1px;
    right: 0;
    width: 17px;
    height: 21px;
    padding: 2px 3px;
    border-radius: 10px 0 1px;
    box-sizing: border-box;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    cursor: se-resize;
}

div #paneEkfHelperViewer::after {
    content: "\2725";
    color: #2e3f54;
    position: absolute;
    top: 0;
    left: 0;
    width: 18px;
    height: 17px;
    margin-top: -3px;
    padding: 0 2px;
    box-sizing: border-box;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    cursor: grab;
}

div#paneContent {
    /* ends above the resize handle in the bottom-right corner */
    height: calc(100% - 22px);
    box-sizing: border-box;
    overflow: auto;
    padding: 20px 20px 0;
    user-select: none;
}

div#paneContent ul {
    list-style: none;
    line-height: 22px;
    padding: 16px;
    margin: 0;
}
</style>
