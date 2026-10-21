<template>
    <div class="cesium-settings-defaultContainer">
        <!-- a label column and a control column, so that the controls line up -->
        <div class="cesium-settings-display">
            <label for="settings-camera"
                ><i class="fa-solid fa-camera"></i> Camera</label
            >
            <select
                id="settings-camera"
                v-model="state.cameraType"
                class="cesium-button"
            >
                <option value="free">Free</option>
                <option value="follow">Follow</option>
            </select>
            <div class="checks">
                <label
                    ><input v-model="state.showWaypoints" type="checkbox" />
                    <i class="fa-solid fa-location-dot"></i> Waypoints</label
                >
                <label
                    ><input v-model="state.showTrajectory" type="checkbox" />
                    <i class="fa-solid fa-route"></i> Trajectory</label
                >
            </div>
            <!-- the sliders for quick changes, the fields for exact values -->
            <label for="settings-wingspan"
                ><i class="fa-solid fa-jet-fighter"></i> Wingspan (m)</label
            >
            <div class="control-row">
                <input
                    v-model="state.modelScale"
                    aria-label="Wingspan slider"
                    type="range"
                    min="0.1"
                    max="15"
                    step="0.01"
                />
                <input
                    id="settings-wingspan"
                    v-model="state.modelScale"
                    class="wingspan-text"
                    size="5"
                    type="text"
                />
            </div>
            <label for="settings-offset"
                ><i class="fa-solid fa-arrows-up-down"></i> Altitude Offset
                (m)</label
            >
            <div class="control-row">
                <input
                    v-model="state.heightOffset"
                    aria-label="Altitude offset slider"
                    type="range"
                    min="-5000"
                    max="5000"
                    step="0.1"
                />
                <input
                    id="settings-offset"
                    v-model="state.heightOffset"
                    class="wingspan-text"
                    size="5"
                    type="number"
                />
            </div>
            <label for="settings-trajectory"
                ><i class="fa-solid fa-map"></i> Trajectory Source</label
            >
            <div class="control-row">
                <select
                    id="settings-trajectory"
                    v-model="state.trajectorySource"
                    class="cesium-button"
                >
                    <option v-for="item in state.trajectorySources" :key="item">
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
            <!-- each comparison: its colour under the label, its source under the main one -->
            <template
                v-for="(src, idx) in state.comparisonTrajectories"
                :key="'cmp' + idx"
            >
                <span
                    class="traj-color-swatch"
                    :style="{ backgroundColor: comparisonColor(idx) }"
                ></span>
                <div class="control-row">
                    <select
                        class="cesium-button"
                        :aria-label="'Comparison source ' + (idx + 1)"
                        :value="src"
                        @change="updateComparison(idx, $event.target.value)"
                    >
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
            </template>
            <label for="settings-attitude"
                ><i class="fa-solid fa-compass"></i> Attitude Source</label
            >
            <select
                id="settings-attitude"
                v-model="state.attitudeSource"
                class="cesium-button"
            >
                <option v-for="item in attitudeSources" :key="item">
                    {{ item }}
                </option>
            </select>
        </div>
    </div>
</template>

<script>
import { store } from "@/components/Globals.js";

export default {
    name: "CesiumSettingsWidget",
    data() {
        return {
            state: store,
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
            this.state.comparisonTrajectories[idx] = value;
        },
    },
};
</script>

<style scoped>
.cesium-settings-defaultContainer {
    z-index: 1;
    height: fit-content;
    position: relative;
    font-weight: 400;
    line-height: 1.5;
    color: #fff;
    font-family: sans-serif;
    font-size: 16px;
    box-sizing: border-box;
    overflow: hidden;
    background-color: rgb(40 40 40 / 70%);
    padding: 8px 10px;
    border-radius: 5px;
    border: 1px solid #444;
}

/* scrolls when the comparison sources make it taller than the 3D view leaves room for */
.cesium-settings-display {
    display: grid;
    grid-template-columns: max-content minmax(0, 1fr);
    gap: 6px 10px;
    align-items: center;
    width: 340px;
    max-height: 400px;
    overflow: auto;
    font: bold 12px sans-serif;
}

.cesium-settings-display select {
    width: 100%;
    margin: 0;
}

.checks {
    grid-column: 1 / -1;
    display: flex;
    gap: 16px;
}

.control-row {
    display: flex;
    align-items: center;
    gap: 6px;
}

.control-row input[type="range"],
.control-row select {
    flex: 1;
    min-width: 0;
}

/* wide enough for an offset such as -2672.92 */
.control-row .wingspan-text {
    flex: 0 0 72px;
    width: 72px;
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
    justify-self: end;
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 2px;
    border: 1px solid #fff;
    flex: 0 0 auto;
}
</style>
