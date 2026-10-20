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
            <ul>
                <li v-for="msg in filteredData" :key="msg[0] + msg[1]">
                    [{{ timeFormatter(msg[0]) }}]: {{ msg[2] }}
                </li>
            </ul>
        </div>
    </div>
</template>

<script>
import { store } from "../Globals.js";
import { useWidget, widgetProps } from "./useWidget.js";

export default {
    name: "MessageViewer",
    props: widgetProps,
    emits: ["close"],
    setup(props, { emit }) {
        return useWidget(props, emit, {
            name: "MessageViewer",
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
        filteredData() {
            // this seems necessary to force a recomputation
            this.dependOnParams();
            return this.state.textMessages.filter(
                (key) => key[0] < this.cursorTime,
            );
        },
    },
    watch: {
        filteredData: function () {
            const container = this.$el.querySelector(".uav-widget__content");
            container.scrollTop = container.scrollHeight;
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
    methods: {
        timeFormatter(milliseconds) {
            const seconds = (milliseconds / 1000) % 60;
            const totalMinutes = Math.floor(milliseconds / 1000 / 60);
            const hours = Math.floor(totalMinutes / 60);
            const minutes = totalMinutes % 60;
            return [
                hours.toFixed(0).padStart(2, "0"),
                minutes.toFixed(0).padStart(2, "0"),
                seconds.toFixed(1).padStart(4, "0"),
            ].join(":");
        },
        setTime(time) {
            this.cursorTime = time;
        },
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
    },
};
</script>

<style scoped>
/* All shell rules live in src/styles/widget.css */
</style>
