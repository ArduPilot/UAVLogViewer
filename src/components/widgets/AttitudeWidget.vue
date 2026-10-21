<template>
    <div
        :id="getDivName()"
        :class="['uav-widget', { 'uav-widget--no-resize': !resizeable }]"
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
        <div class="uav-widget__content uav-widget__content--fixed">
            <Attitude :roll="roll" :pitch="pitch" />
        </div>
    </div>
</template>

<script>
import { store } from "@/components/Globals.js";
import { useWidget, widgetProps } from "./useWidget.js";
import AttitudeIndicator from "./flightIndicators/AttitudeIndicator.vue";
import { Interpolator } from "@/shared/lib/interpolator.js";

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
            return Object.keys(this.state.params?.values ?? {}).filter((key) =>
                key.includes(this.filter.toUpperCase()),
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
/* All shell rules, handles, close button, and fixed-content sizing come
   from src/styles/widget.css. Nothing widget-specific. */
</style>
