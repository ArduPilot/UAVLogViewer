<template>
  <div class="cesium-settings-defaultContainer">
    <div @click="toggleSettings" class="gear-icon">⚙</div>
        <div v-show="isSettingsVisible" class="cesium-settings-display">
          <label>Camera</label>
            <select class="cesium-button" v-model="state.cameraType">
                <option value="free">Free</option>
                <option value="follow">Follow</option>
            </select>
        <!-- CHECKBOXES -->
        <div>
            <label><input type="checkbox" v-model="state.showWaypoints">
            Waypoints</label>
            <label><input type="checkbox" v-model="state.showTrajectory">
            Trajectory</label>
        </div>
        <!-- WINGSPAN -->
        <div>
            <label>Wingspan
                <input class="wingspan-text" size="5" type="text" v-model="state.modelScale">
                (m)
            </label>
        </div>
        <!-- ALTITUDE OFFSET -->
        <div>
            <label> Altitude Offset
                <input class="wingspan-text" size="5" type="number" v-model="state.heightOffset">
                (m)
            </label>
        </div>
        <!-- Trajectory Source -->
        <div>
            <label> Trajectory Source</label>
            <select class="cesium-button" v-model="state.trajectorySource" style="display: block;">
                <!-- eslint-disable-next-line vue/no-v-html vue/no-unused-vars -->
                <option v-for="item in state.trajectorySources" :key="item">
                    {{item}}
                </option>
            </select>
        </div>
        <!-- Attitude Source -->
        <div>
            <label> Attitude Source</label>
            <select class="cesium-button" v-model="state.attitudeSource">
                <!-- eslint-disable-next-line vue/no-v-html vue/no-unused-vars -->
                <option v-for="item in attitudeSources" :key="item">
                    {{item}}
                </option>
            </select>
        </div>
      </div>
  </div>
</template>

<script>
import { store } from '../Globals.js'

export default {
    name: 'CesiumSettingsWidget',
    props: {
        snappable: { type: Boolean, default: false },
        fixedAspectRatio: { type: Boolean, default: false },
        aspectRatio: { type: Number, default: 2 }
    },
    data () {
        return {
            state: store,
            isSettingsVisible: false
        }
    },
    methods: {
        toggleSettings () {
            this.isSettingsVisible = !this.isSettingsVisible
        }
    },
    computed: {
        attitudeSources () {
            return [...this.state.attitudeSources.quaternions, ...this.state.attitudeSources.eulers]
        }
    }
}
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
</style>
