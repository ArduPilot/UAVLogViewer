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
            <span class="close" @click="close()"> X </span>
            <Attitude :roll="roll" :pitch="pitch" />
        </div>
    </div>
</template>

<script>
import { store } from "../Globals.js";
import { useWidget, widgetProps } from "./useWidget.js";
import AttitudeIndicator from "./flightIndicators/AttitudeIndicator.vue";
import { Interpolator } from "./interpolator.js";

export default {
    name: "AttitudeViewer",
    components: {
        Attitude: AttitudeIndicator,
    },
    // the indicator does not scale: the window moves but does not resize
    props: { ...widgetProps, resizeable: { type: Boolean, default: false } },
    emits: ["close"],
    setup(props, { emit }) {
        return useWidget(props, emit, {
            name: "AttitudeViewer",
            width: 250,
            height: 250,
            left: 500,
            top: 12,
        });
    },
    data() {
        return {
            state: store,
            roll: 0,
            pitch: 0,
        };
    },
    computed: {
        filteredData() {
            this.dependOnParams();
            return Object.keys(this.state.params?.values ?? {}).filter(
                (key) => key.indexOf(this.filter.toUpperCase()) !== -1,
            );
        },
    },

    mounted() {
        let x, y, msg;
        if ("ATTITUDE" in this.state.messages) {
            x = this.state.messages.ATTITUDE.time_boot_ms;
            y = [];
            msg = this.state.messages.ATTITUDE;
            for (const i in msg.time_boot_ms) {
                y.push([
                    (msg.roll[i] * -180) / Math.PI,
                    (msg.pitch[i] * 180) / Math.PI,
                ]);
            }
        } else if ("ATT" in this.state.messages) {
            x = this.state.messages.ATT.time_boot_ms;
            y = [];
            msg = this.state.messages.ATT;
            for (const i in msg.time_boot_ms) {
                y.push([-msg.Roll[i], msg.Pitch[i]]);
            }
        }
        this.interpolated = new Interpolator(x, y);
        this.$eventHub.$on("cesium-time-changed", this.setTime);
        this.$eventHub.$on("hoveredTime", this.setTime);
    },
    beforeUnmount() {
        this.$eventHub.$off("cesium-time-changed", this.setTime);
        this.$eventHub.$off("hoveredTime", this.setTime);
    },
    methods: {
        setTime(time) {
            const rp = this.interpolated.at(time);
            this.roll = rp[0];
            this.pitch = rp[1];
        },
    },
};
</script>

<style scoped>
div #paneAttitudeViewer {
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

div #paneAttitudeViewer::after {
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
    height: 100%;
    overflow: hidden;
    user-select: none;
}

.close {
    position: absolute;
    top: 3px;
    right: 6px;
    z-index: 1;
    cursor: pointer;
}

div#paneContent ul {
    list-style: none;
    line-height: 22px;
    padding: 16px;
    margin: 0;
}
</style>
