<template>
    <div class="cesium-settings-defaultContainer">
        <div class="gear-icon" @click="toggleSettings">⚙</div>
        <div v-show="isSettingsVisible" class="cesium-settings-display">
            <label>Camera</label>
            <select v-model="state.cameraType" class="cesium-button">
                <option value="free">Free</option>
                <option value="follow">Follow</option>
            </select>
            <!-- CHECKBOXES -->
            <div>
                <label
                    ><input v-model="state.showWaypoints" type="checkbox" />
                    Waypoints</label
                >
                <label
                    ><input v-model="state.showTrajectory" type="checkbox" />
                    Trajectory</label
                >
            </div>
            <!-- WINGSPAN -->
            <div>
                <label
                    >Wingspan
                    <input
                        v-model="state.modelScale"
                        class="wingspan-text"
                        size="5"
                        type="text"
                    />
                    (m)
                </label>
            </div>
            <!-- ALTITUDE OFFSET -->
            <div>
                <label>
                    Altitude Offset
                    <input
                        v-model="state.heightOffset"
                        class="wingspan-text"
                        size="5"
                        type="number"
                    />
                    (m)
                </label>
            </div>
            <!-- Trajectory Source -->
            <div>
                <label> Trajectory Source</label>
                <div class="traj-source-row">
                    <select
                        v-model="state.trajectorySource"
                        class="cesium-button traj-source-select"
                    >
                        <!-- eslint-disable-next-line vue/no-v-html vue/no-unused-vars -->
                        <option
                            v-for="item in state.trajectorySources"
                            :key="item"
                        >
                            {{ item }}
                        </option>
                    </select>
                    <button
                        class="traj-icon-button"
                        title="Compare another source"
                        @click="addComparison"
                    >
                        +
                    </button>
                </div>
                <div
                    v-for="(src, idx) in state.comparisonTrajectories"
                    :key="'cmp' + idx"
                    class="traj-source-row"
                >
                    <span
                        class="traj-color-swatch"
                        :style="{ backgroundColor: comparisonColor(idx) }"
                    ></span>
                    <select
                        class="cesium-button traj-source-select"
                        :value="src"
                        @change="updateComparison(idx, $event.target.value)"
                    >
                        <!-- eslint-disable-next-line vue/no-v-html vue/no-unused-vars -->
                        <option
                            v-for="item in state.trajectorySources"
                            :key="item"
                        >
                            {{ item }}
                        </option>
                    </select>
                    <button
                        class="traj-icon-button"
                        title="Remove comparison"
                        @click="removeComparison(idx)"
                    >
                        ✕
                    </button>
                </div>
            </div>
            <!-- Attitude Source -->
            <div>
                <label> Attitude Source</label>
                <select v-model="state.attitudeSource" class="cesium-button">
                    <!-- eslint-disable-next-line vue/no-v-html vue/no-unused-vars -->
                    <option v-for="item in attitudeSources" :key="item">
                        {{ item }}
                    </option>
                </select>
            </div>
        </div>
    </div>
</template>

<script>
import { store } from "../Globals.js";

export default {
    name: "CesiumSettingsWidget",
    props: {
        snappable: { type: Boolean, default: false },
        fixedAspectRatio: { type: Boolean, default: false },
        aspectRatio: { type: Number, default: 2 },
    },
    data() {
        return {
            state: store,
            isSettingsVisible: false,
        };
    },
    computed: {
        attitudeSources() {
            return [
                ...this.state.attitudeSources.quaternions,
                ...this.state.attitudeSources.eulers,
            ];
        },
    },
    methods: {
        toggleSettings() {
            this.isSettingsVisible = !this.isSettingsVisible;
        },
        comparisonColor(idx) {
            const colors = this.state.comparisonTrajectoryColors;
            return colors[idx % colors.length];
        },
        addComparison() {
            // Default the new row to the first source not already shown.
            const used = new Set([
                this.state.trajectorySource,
                ...this.state.comparisonTrajectories,
            ]);
            const next =
                this.state.trajectorySources.find((s) => !used.has(s)) ||
                this.state.trajectorySources[0] ||
                "";
            this.state.comparisonTrajectories.push(next);
        },
        removeComparison(idx) {
            this.state.comparisonTrajectories.splice(idx, 1);
        },
        updateComparison(idx, value) {
            this.$set(this.state.comparisonTrajectories, idx, value);
        },
    },
};
</script>

<style scoped>
/* Gear Icon styling */
.gear-icon {
    cursor: pointer;
    font-size: 30px;
    position: absolute;
    top: -10px;
    left: 7px;
    z-index: 2;
}

.cesium-settings-defaultContainer {
    z-index: 1;
    height: fit-content;
    position: relative;
    font-weight: 400;
    line-height: 1.5;
    color: #ffffff;
    font-family: sans-serif;
    font-size: 16px;
    box-sizing: border-box;
    min-width: 30px; /* Width of gear icon + padding */
    min-height: 30px; /* Height of gear icon + padding */
    overflow: hidden;
    background-color: rgba(40, 40, 40, 0.7);
    padding: 7px;
    padding-left: 25px;
    border-radius: 5px;
    border: 1px solid #444;
}

.cesium-settings-display {
    max-height: 400px; /* Estimate the maximum height of your content; you may need to adjust this */
    overflow: hidden; /* To hide the content that exceeds the max-height */
    font: bold 12px sans-serif;
}

.traj-source-row {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 2px;
}

.traj-source-select {
    flex: 1;
    display: block;
}

.traj-icon-button {
    background: #303336;
    border: 1px solid #444;
    color: #edffff;
    border-radius: 4px;
    width: 22px;
    height: 22px;
    line-height: 1;
    cursor: pointer;
    padding: 0;
    flex: 0 0 auto;
}

.traj-icon-button:hover {
    background: #665a4f;
}

.traj-color-swatch {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 2px;
    border: 1px solid #fff;
    flex: 0 0 auto;
}
</style>
