<template>
  <div>
    <div id="cesiumContainer"></div>
    <div id="toolbar">
      <table class="infoPanel">
        <tbody>
          <tr v-for="(mode, index) in modes" v-bind:key="index">
            <td   v-bind:style="{ color: cssColors[index] } ">{{ mode[1] }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import Cesium from 'cesium/Cesium'
import 'cesium/Widgets/widgets.css'

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

      colors: [
        Cesium.Color.BLUE,
        Cesium.Color.BLUEVIOLET,
        Cesium.Color.BROWN,
        Cesium.Color.DARKORANGE,
        Cesium.Color.GREENYELLOW,
        Cesium.Color.RED,
        Cesium.Color.AQUA,
        Cesium.Color.FUCHSIA
      ],

      cssColors: [
        '#0000FF',
        '#8A2BE2',
        '#A52A2A',
        '#FF8C00',
        '#ADFF2F',
        '#FF0000',
        '#00FFFF',
        '#FF00FF'
      ]

    }
  },
  methods:
    {
      showAttitude (time) {
        let start = Cesium.JulianDate.fromDate(new Date(2015, 2, 25, 16))
        this.viewer.clock.currentTime = Cesium.JulianDate.addSeconds(start, (time - this.startTimeMs) / 1000, new Cesium.JulianDate())
        this.viewer.scene.requestRender()
      },
      plotTrajectory (points) {
        let _this = this
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

        let pointCollection = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection())

        for (let pos of points) {
          position = Cesium.Cartesian3.fromDegrees(pos[0], pos[1], pos[2])
          positions.push(position)
          let time = Cesium.JulianDate.addSeconds(start, (pos[3] - this.startTimeMs) / 1000, new Cesium.JulianDate())
          sampledPos.addSample(time, position)
          pointCollection.add({
            position: position,
            pixelSize: 10,
            color: this.getModeColor(pos[3]),
            id: {time: pos[3]}
          })
        }

        let handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
        handler.setInputAction(function (movement) {
          // get an array of all primitives at the mouse position
          var pickedObjects = viewer.scene.drillPick(movement.endPosition)
          if (Cesium.defined(pickedObjects)) {
            // Update the collection of picked entities.
            for (let entity of pickedObjects) {
              try {
                let time = entity.id.time
                if (time !== undefined) {
                  _this.$emit('cesiumhover', time)
                  viewer.clock.currentTime = Cesium.JulianDate.addSeconds(start, (time - _this.startTimeMs) / 1000, new Cesium.JulianDate())
                  window.entity = entity
                }
                return
              } catch (e) {
              }
            }
          }
        }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)

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
        return this.colors[this.modes.length]
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
    padding: 4px;
    border: 1px solid #444;
    border-radius: 4px;
    font-size:150%;
    font-weight: bold;
  }

</style>
