<template>
  <div
    :id="getDivName()"
    v-bind:style="{
      width: width + 'px',
      height: height + 'px',
      top: top + 'px',
      left: left + 'px'
    }"
  >
    <div id="paneContent">
      <span style="float: right; margin: 3px; cursor: pointer;" @click="close()"> X </span>
      <Attitude :roll="roll" :pitch="pitch" />
    </div>
  </div>
</template>

<script>
import { store } from '../Globals.js'
import { baseWidget } from './baseWidget'
import { Attitude } from 'vue-flight-indicators'

class Interpolator {
    // This class holds all joystick positions and returns the interpolated position at an arbitraty time.
    constructor (x, y) {
        this.x = x
        this.y = y
        this.currentIndex = 0
    }

    at (point) {
        /*
            Returns x at closest y. TODO: interpolate properly.
            */
        while (this.x[this.currentIndex] < point && this.currentIndex < this.x.length - 2) {
            this.currentIndex += 1
        }
        while (this.x[this.currentIndex] > point && this.currentIndex > 1) {
            this.currentIndex -= 1
        }
        return this.y[Math.max(0, Math.min(this.currentIndex, this.y.length - 1))]
    }
}

export default {
    name: 'AttitudeViewer',
    mixins: [baseWidget],
    props: {
        snappable: { type: Boolean, default: false },
        fixedAspectRatio: { type: Boolean, default: false },
        aspectRatio: { type: Number, default: 2 }
    },
    data () {
        return {
            name: 'AttitudeViewer',
            state: store,
            width: 256,
            height: 256,
            left: 500,
            top: 12,
            roll: 0,
            pitch: 0,
            forceRecompute: 1
        }
    },
    components: {
        Attitude
    },

    mounted () {
        let x, y, msg
        if ('ATTITUDE' in this.state.messages) {
            x = this.state.messages.ATTITUDE.time_boot_ms
            y = []
            msg = this.state.messages.ATTITUDE
            for (const i in msg.time_boot_ms) {
                y.push([msg.roll[i] * -180 / Math.PI, msg.pitch[i] * 180 / Math.PI])
            }
        } else if ('ATT' in this.state.messages) {
            x = this.state.messages.ATT.time_boot_ms
            y = []
            msg = this.state.messages.ATT
            for (const i in msg.time_boot_ms) {
                y.push([-msg.Roll[i], msg.Pitch[i]])
            }
        }
        this.interpolated = new Interpolator(x, y)
        this.$eventHub.$on('cesium-time-changed', this.setTime)
        this.$eventHub.$on('hoveredTime', this.setTime)
    },
    methods: {
        setTime (time) {
            const rp = this.interpolated.at(time)
            this.roll = rp[0]
            this.pitch = rp[1]
        },
        setup () {

        }
    },
    computed: {
        filteredData () {
            // eslint-disable-next-line
            let potato = this.forceRecompute
            return Object.keys(this.state.params.values).filter(key => key.indexOf(this.filter.toUpperCase()) !== -1)
        }
    }
}
</script>

<style scoped>
div #paneAttitudeViewer {
  min-width: 220px;
  min-height: 150px;
  position: absolute;
  background: rgba(253, 254, 255, 0.856);
  color: #141924;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  z-index: 10000;
  box-shadow: 9px 9px 3px -6px rgba(26, 26, 26, 0.699);
  border-radius: 5px;
  user-select: none;
}

div #paneAttitudeViewer::before {
  content: "\25e2";
  color: #ffffff;
  background-color: rgb(38, 53, 71);
  position: absolute;
  bottom: -1px;
  right: 0;
  width: 17px;
  height: 21px;
  padding: 2px 3px;
  border-radius: 10px 0px 1px 0px;
  box-sizing: border-box;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  cursor: se-resize;
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
  padding: 0px 2px;
  box-sizing: border-box;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  cursor: grab;
}

div#paneContent {
  height: 100%;
  overflow: auto;
  -webkit-user-select: none; /* Chrome all / Safari all */
  -moz-user-select: none; /* Firefox all */
  -ms-user-select: none; /* IE 10+ */
  user-select: none;
}

div#paneContent ul {
  list-style: none;
  line-height: 22px;
  padding: 16px;
  margin: 0;
}
</style>
