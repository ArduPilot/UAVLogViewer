<template>
  <div id="wrapper">
    <div id="cesiumContainer"></div>
    <div id="toolbar">
      <table class="infoPanel">
        <tbody>
          <tr v-for="(mode, index) in setOfModes" v-bind:key="index">
            <td class="mode"  v-bind:style="{ color: cssColors[index] } ">{{ mode }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import Cesium from 'cesium/Cesium'
import 'cesium/Widgets/widgets.css'
import colormap from 'colormap'

function getMinTime (data) {
  return data.reduce((min, p) => p[3] < min ? p[3] : min, data[0][3])
}
function getMaxTime (data) {
  return data.reduce((max, p) => p[3] > max ? p[3] : max, data[0][3])
}

export default {
  name: 'Cesium',
  props: ['trajectory', 'attitudes', 'modes'],
  mounted () {
    if (this.viewer == null) {
      this.viewer = new Cesium.Viewer(
        'cesiumContainer',
        {
          homeButton: false,
          timeline: true,
          animation: true,
          requestRenderMode: true,
          shouldAnimate: false
        })
      this.viewer.scene.debugShowFramesPerSecond = true
      this.pointCollection = this.viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection())
      this.viewer.scene.postRender.addEventListener(this.onFrameUpdate)

      // Attach hover handler
      let handler = new Cesium.ScreenSpaceEventHandler(this.viewer.scene.canvas)
      handler.setInputAction(this.onMove, Cesium.ScreenSpaceEventType.MOUSE_MOVE)
      handler.setInputAction(this.onLeftDown, Cesium.ScreenSpaceEventType.LEFT_DOWN)
      handler.setInputAction(this.onLeftUp, Cesium.ScreenSpaceEventType.LEFT_UP)
    }
    this.plotTrajectory(this.trajectory)
  },
  watch: {
    trajectory: function (newVal, oldVal) {
      this.plotTrajectory(newVal)
    }
  },
  data () {
    return {
      viewer: null,
      polyline: null,
      model: null,
      hpRoll: null,
      position: null,
      fixedFrameTransform: null,
      startTimeMs: 0,
      pointsCollection: null,

      colors: [],
      cssColors: [],
      lastHoveredTime: 0

    }
  },
  computed:
    {
      setOfModes () {
        let set = []
        for (let mode of this.modes) {
          if (!set.includes(mode[1])){
            set.push(mode[1])
          }
        }
        return set
      }
    },
  methods:
    {
      mouseIsOnPoint (point) {
        let pickedObjects = this.viewer.scene.drillPick(point)
        if (Cesium.defined(pickedObjects)) {
          // tries to read the time of each entioty under the mouse, returns once one is found.
          for (let entity of pickedObjects) {
            try {
              let time = entity.id.time
              if (time !== undefined) {
                this.lastHoveredTime = time
                return true
              }
              return
            } catch (e) {
            }
          }
        }
        return false
      },

      onLeftDown (movement) {
        if (this.mouseIsOnPoint(movement.position)) {
          this.isDragging = true
          this.viewer.scene.screenSpaceCameraController.enableInputs = false
        }
      },

      onLeftUp (movement) {
        this.isDragging = false
        this.viewer.container.style.cursor = 'default'
        this.viewer.scene.screenSpaceCameraController.enableInputs = true
      },
      onMove (movement) {
        if (this.isDragging) {
          if (this.mouseIsOnPoint(movement.endPosition)) {
            this.$emit('cesium-time-changed', this.lastHoveredTime)
            this.viewer.clock.currentTime = Cesium.JulianDate.addSeconds(Cesium.JulianDate.fromDate(new Date(2015, 2, 25, 16)), (this.lastHoveredTime - this.startTimeMs) / 1000, new Cesium.JulianDate())
          }
        } else {
          if (this.mouseIsOnPoint(movement.endPosition)) {
            this.viewer.container.style.cursor = 'pointer'
          } else {
            this.viewer.container.style.cursor = 'default'
          }
        }
      },
      onFrameUpdate() {
        // emits in "boot_time_ms" units.
        this.$emit('cesium-time-changed', (this.viewer.clock.currentTime.secondsOfDay - this.viewer.clock.startTime.secondsOfDay)*1000 + this.startTimeMs)
      },
      generateColorMMap() {
        let colorMapOptions = {
          colormap: 'hsv',
          nshades: Math.max(12, this.modes.length),
          format: 'rgbaString',
          alpha: 1
        }
        // colormap used on legend.
        this.cssColors = colormap(colorMapOptions)

        // colormap used on Cesium
        colorMapOptions.format = 'float'
        this.colors = []
        for (let rgba of colormap(colorMapOptions)) {
          this.colors.push(new Cesium.Color(rgba[0], rgba[1], rgba[2]))
        }
      },
      showAttitude (time) {
        let start = Cesium.JulianDate.fromDate(new Date(2015, 2, 25, 16))
        this.viewer.clock.currentTime = Cesium.JulianDate.addSeconds(start, (time - this.startTimeMs) / 1000, new Cesium.JulianDate())
        this.viewer.scene.requestRender()
      },
      plotTrajectory (points) {
        this.generateColorMMap()
        this.startTimeMs = getMinTime(points)
        let timespan = getMaxTime(points) - this.startTimeMs
        let viewer = this.viewer
        let start = Cesium.JulianDate.fromDate(new Date(2015, 2, 25, 16))
        let stop = Cesium.JulianDate.addSeconds(start, Math.round(timespan / 1000), new Cesium.JulianDate())

        // Make sure viewer is at the desired time.
        viewer.clock.startTime = start.clone()
        viewer.clock.stopTime = stop.clone()
        viewer.clock.currentTime = start.clone()
        viewer.clock.clockRange = Cesium.ClockRange.LOOP_STOP
        viewer.clock.multiplier = 1

        // Set timeline to simulation bounds
        viewer.timeline.zoomTo(start, stop)
        let position
        let positions = []
        let sampledPos = new Cesium.SampledPositionProperty()

        // clean entities
        if (this.pointCollection !== null)
        {
          this.pointCollection.removeAll()
        }
        this.viewer.entities.removeAll()

        // Plot new points
        for (let pos of points) {
          position = Cesium.Cartesian3.fromDegrees(pos[0], pos[1], pos[2])
          positions.push(position)
          let time = Cesium.JulianDate.addSeconds(start, (pos[3] - this.startTimeMs) / 1000, new Cesium.JulianDate())
          sampledPos.addSample(time, position)
          this.pointCollection.add({
            position: position,
            pixelSize: 10,
            color: this.getModeColor(pos[3]),
            id: {time: pos[3]}
          })
        }

        // Create polyline
        let fixedFrameTransform = Cesium.Transforms.localFrameToFixedFrameGenerator('north', 'west')
        let sampledOrientation = new Cesium.SampledProperty(Cesium.Quaternion)
        for (let atti in this.attitudes) {
          if (this.attitudes.hasOwnProperty(atti)) {
            let att = this.attitudes[atti]
            let hpRoll = Cesium.Transforms.headingPitchRollQuaternion(position, new Cesium.HeadingPitchRoll(att[2], att[1], att[0]), Cesium.Ellipsoid.WGS84, fixedFrameTransform)
            let time = Cesium.JulianDate.addSeconds(start, (atti - this.startTimeMs) / 1000, new Cesium.JulianDate())
            sampledOrientation.addSample(time, hpRoll)
          }
        }

        viewer.entities.add({
          // Set the entity availability to the same interval as the simulation time.
          availability: new Cesium.TimeIntervalCollection([new Cesium.TimeInterval({
            start: start,
            stop: stop
          })]),
          // Use our computed positions
          position: sampledPos,
          // Automatically compute orientation based on position movement.
          orientation: sampledOrientation,
          // Load the Cesium plane model to represent the entity
          model: {
            uri: require('../assets/Cesium_Air.glb'),
            minimumPixelSize: 64
          }
        })
        this.viewer.entities.add({
          polyline: {
            positions: positions
          },
          width: 2
        })
        this.viewer.zoomTo(this.viewer.entities)
      },
      getModeColor (time) {
        for (let mode in this.modes) {
          if (this.modes.hasOwnProperty(mode)) {
            if (this.modes[mode][0] > time) {
              return this.colors[mode - 1]
            }
          }
        }
        return this.colors[this.modes.length-1]
      }
    }
}
</script>

<style scoped>
  #cesiumContainer {
    display: flex;
    height: 100%;
  }

  #loadingOverlay h1 {
    text-align: center;
    position: relative;
    top: 50%;
    margin-top: -0.5em;
  }

  .sandcastle-loading #loadingOverlay {
    display: block;
  }

  .sandcastle-loading #toolbar {
    display: none;
  }

  #toolbar {
    margin: 5px;
    padding: 2px 5px;
    position: absolute;
    top: 0;
  }

  .infoPanel {
    background: rgba(42, 42, 42, 0.8);
    margin: 5px;
    border: 1px solid #444;
    border-radius: 10px;
    font-size:100%;
    font-weight: bold;
  }
  .infoPanel > tbody{
    padding:15px;
  }

  #wrapper{
    width: 100%;
    height: 100%;
  }
  .mode {
    padding-left: 10px;
    padding-right: 10px;
  }

</style>
