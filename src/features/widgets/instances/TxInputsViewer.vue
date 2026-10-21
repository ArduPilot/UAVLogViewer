<template>
    <div
        :id="getDivName()"
        class="uav-widget uav-widget--radio uav-widget--no-resize"
        :style="{
            width: width + 'px',
            height: height + 'px',
            top: top + 'px',
            left: left + 'px',
        }"
    >
        <span class="uav-widget__move"></span>
        <span class="uav-widget__close" @click="close()"></span>
        <div class="uav-widget__content uav-widget__content--fixed">
            <div class="circle">
                <div
                    id="left"
                    class="stick"
                    :style="{
                        'margin-left': leftStickLeft - 3 + 'px',
                        'margin-top': leftStickTop - 3 + 'px',
                    }"
                ></div>
            </div>
            <div class="circle">
                <div
                    id="right"
                    class="stick"
                    :style="{
                        'margin-left': rightStickLeft - 3 + 'px',
                        'margin-top': rightStickTop - 3 + 'px',
                    }"
                ></div>
            </div>
        </div>
    </div>
</template>

<script>
import { store } from "@/shared/stores/index.js";
import { useWidget, widgetProps } from "@/features/widgets/core/useWidget.js";
import { Interpolator } from "@/shared/lib/interpolator.js";

export default {
    name: "TxInputsViewer",
    props: { ...widgetProps, resizeable: { type: Boolean, default: false } },
    emits: ["close"],
    setup(props, { emit }) {
        return useWidget(props, emit, {
            name: "TxInputsViewer",
            width: 294,
            height: 150,
            left: 50,
            top: 12,
        });
    },
    data() {
        return {
            state: store,
            throttle: 50,
            yaw: 50,
            pitch: 50,
            roll: 50,
            rollMap: 0,
            pitchMap: 1,
            throttleMap: 2,
            yawMap: 3,
            channels: [50, 50, 50, 50],
        };
    },
    computed: {
        leftStickLeft() {
            return -29 + (0.01 * this.channels[this.yawMap] * this.width) / 2;
        },
        leftStickTop() {
            if (this.state.radioMode === "2") {
                return (
                    0.02 *
                        (100 - this.channels[this.throttleMap]) *
                        this.circleHeight -
                    22
                );
            }
            return (
                0.02 *
                    (100 - this.channels[this.pitchMap]) *
                    this.circleHeight -
                22
            );
        },
        rightStickLeft() {
            return -29 + 0.01 * this.channels[this.rollMap] * (this.width / 2);
        },
        rightStickTop() {
            if (this.state.radioMode === "2") {
                return (
                    0.02 *
                        (100 - this.channels[this.pitchMap]) *
                        this.circleHeight -
                    22
                );
            }
            return (
                0.02 *
                    (100 - this.channels[this.throttleMap]) *
                    this.circleHeight -
                22
            );
        },
        circleHeight() {
            return this.height * (69 / 150);
        },
    },
    beforeUnmount() {
        this.closed = true;
        this.$eventHub.$off("cesium-time-changed", this.setTime);
        this.$eventHub.$off("hoveredTime", this.setTime);
    },
    mounted() {
        this.init();
    },
    methods: {
        waitForMessage(fieldname) {
            this.$eventHub.$emit("loadType", fieldname.split(".")[0]);
            let interval;
            let counter = 0;
            return new Promise((resolve, reject) => {
                interval = setInterval(() => {
                    if (this.state.messages[fieldname.split(".")[0]]) {
                        clearInterval(interval);
                        counter += 1;
                        resolve();
                    } else if (counter > 6) {
                        console.log("not resolving");
                        clearInterval(interval);
                        reject(new Error("Could not load messageType"));
                    }
                }, 2000);
            });
        },
        setTime(time) {
            try {
                const sticks = this.interpolated.at(time);
                let reverses = [1, 1, 1, 1];
                if (this.state.params.get("RC1_REV") !== undefined) {
                    reverses = [
                        Number.parseFloat(this.state.params.get("RC1_REV")),
                        Number.parseFloat(this.state.params.get("RC2_REV")),
                        Number.parseFloat(this.state.params.get("RC3_REV")),
                        Number.parseFloat(this.state.params.get("RC4_REV")),
                    ];
                }
                let trims = [1500, 1500, 1500, 1500];
                if (this.state.params.get("RC4_TRIM") !== undefined) {
                    trims = [
                        this.state.params.get("RC4_TRIM"),
                        this.state.params.get("RC3_TRIM"),
                        this.state.params.get("RC2_TRIM"),
                        this.state.params.get("RC1_TRIM"),
                    ];
                }
                if (this.state.params.get("RCMAP_ROLL") !== undefined) {
                    // validate as some logs have weird values here...
                    if (
                        this.state.params.get("RCMAP_ROLL") > 0 &&
                        this.state.params.get("RCMAP_ROLL") < 4
                    ) {
                        this.rollMap =
                            Number.parseInt(
                                this.state.params.get("RCMAP_ROLL"),
                            ) - 1;
                        this.pitchMap =
                            Number.parseInt(
                                this.state.params.get("RCMAP_PITCH"),
                            ) - 1;
                        this.throttleMap =
                            Number.parseInt(
                                this.state.params.get("RCMAP_THROTTLE"),
                            ) - 1;
                        this.yawMap =
                            Number.parseInt(
                                this.state.params.get("RCMAP_YAW"),
                            ) - 1;
                    }
                }
                this.channels = [
                    ((sticks[0] - trims[3]) * reverses[0] + 1500 - 1000) / 10,
                    ((sticks[1] - trims[2]) * reverses[1] + 1500 - 1000) / 10,
                    ((sticks[2] - trims[1]) * reverses[2] + 1500 - 1000) / 10,
                    ((sticks[3] - trims[0]) * reverses[3] + 1500 - 1000) / 10,
                ];
            } catch (e) {
                console.log(e);
            }
        },
        init() {
            this.waitForMessage("RC_CHANNELS.*").then(() => {
                const x = this.state.messages.RC_CHANNELS.time_boot_ms;
                const y = [];
                const msg = this.state.messages.RC_CHANNELS;
                for (const i in msg.time_boot_ms) {
                    y.push([
                        msg.chan1_raw[i],
                        msg.chan2_raw[i],
                        msg.chan3_raw[i],
                        msg.chan4_raw[i],
                    ]);
                }
                if (this.closed) {
                    return;
                }
                this.interpolated = new Interpolator(x, y);
                this.$eventHub.$on("cesium-time-changed", this.setTime);
            });
            this.waitForMessage("RCIN.*").then(() => {
                const x = this.state.messages.RCIN.time_boot_ms;
                const y = [];

                const msg = this.state.messages.RCIN;
                for (const i in msg.time_boot_ms) {
                    y.push([msg.C1[i], msg.C2[i], msg.C3[i], msg.C4[i]]);
                }
                if (this.closed) {
                    return;
                }
                this.interpolated = new Interpolator(x, y);
                this.$eventHub.$on("cesium-time-changed", this.setTime);
                this.$eventHub.$on("hoveredTime", this.setTime);
            });
        },
    },
};
</script>

<style scoped>
.uav-widget--radio {
    min-width: 294px;
    min-height: 150px;
    background: rgb(1 160 139);
    border: 3px groove rgb(1 133 111 / 54.1%);
    border-radius: 20px;
    box-shadow: inset 0 0 8px 6px rgb(0 87 72 / 41.1%);
    font-size: 10px;
    text-transform: uppercase;
    overflow: visible; /* was hidden — clipping killed the corner handles */
    box-sizing: border-box;
}

/* Content keeps the pill shape even though the widget's overflow is now visible */
.uav-widget--radio .uav-widget__content {
    border-radius: 20px;
    overflow: hidden;
}

/* Move — flush top-left corner, border-radius mirrors the 20px widget corner */
.uav-widget--radio .uav-widget__move {
    top: 0;
    left: 0;
    width: 26px;
    height: 24px;
    border-radius: 20px 0;
    background: rgb(0 36 27 / 25%);
    color: rgb(255 255 255 / 92%);
    font-size: 14px;
}

.uav-widget--radio .uav-widget__move:hover {
    background: rgb(0 36 27 / 55%);
    color: #fff;
}

/* Close — flush top-right corner, mirrored border-radius */
.uav-widget--radio .uav-widget__close {
    top: 0;
    right: 0;
    width: 26px;
    height: 24px;
    border-radius: 0 20px;
    background: rgb(0 36 27 / 25%);
    color: rgb(255 255 255 / 92%);
    font-size: 12px;
}

.uav-widget--radio .uav-widget__close:hover {
    background: rgb(0 36 27 / 55%);
    color: #fff;
}

div.circle {
    border: double 4px rgb(2 145 121 / 98%);
    background: rgb(116 116 116);
    background:
        radial-gradient(
            circle,
            rgb(24 24 24 / 76%) 0%,
            rgb(0 0 0 / 88.9%) 100%
        ),
        linear-gradient(
            90deg,
            transparent 49.55%,
            darkgreen 49.75%,
            darkgreen 50.25%,
            transparent 50.25%
        ),
        linear-gradient(
            transparent 49.55%,
            darkgreen 49.75%,
            darkgreen 50.25%,
            transparent 50.25%
        );
    margin: 1px;
    border-radius: 50%;
    width: 48%;
    height: 98%;
    float: left;
    box-shadow: 0 0 14px -1px rgb(1 82 65 / 61%);
}

div.stick {
    border-radius: 50%;
    width: 12px;
    height: 12px;
    background-color: rgb(221 221 221);
    border: 1px solid rgb(139 139 139);
    margin-left: 48%;
    display: inline-block;
    box-shadow: inset 0 0 4px 2px rgb(102 102 102 / 87.7%);
}
</style>
