<template>
    <div id="cesiumContainer"></div>
</template>

<script>
import Cesium from 'cesium/Cesium'
import 'cesium/Widgets/widgets.css'

let colors = [Cesium.Color.BLUE,
  Cesium.Color.BLUEVIOLET,
  Cesium.Color.BROWN,
  Cesium.Color.CHARTREUSE,
  Cesium.Color.DARKORANGE,
  Cesium.Color.GREENYELLOW,
  Cesium.Color.RED,
  Cesium.Color.AQUA,
  Cesium.Color.FUCHSIA]

function getModeColor (time, modes) {
  for (let mode in modes) {
    if (modes[mode][0] > time) {
      return colors[mode]
    }
  }
}
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
    }
    this.plotTrajectory(this.trajectory)
  },
  watch: {
    trajectory: function (newVal, oldVal) {
      this.plotTrajectory(newVal)
    },
    data () {
      return {
        viewer: null,
        polyline: null,
        model: null,
        hpRoll: null,
        position: null,
        fixedFrameTransform: null,
        startTimeMs: 0
      }
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
        let sampledPos = new Cesium.SampledPositionProperty()
        for (let pos of points) {
          position = Cesium.Cartesian3.fromDegrees(pos[0], pos[1], pos[2])
          let time = Cesium.JulianDate.addSeconds(start, (pos[3] - this.startTimeMs) / 1000, new Cesium.JulianDate())
          sampledPos.addSample(time, position)
          viewer.entities.add({
            position: position,
            point: {
              pixelSize: 10,
              color: getModeColor(pos[3], this.modes)
            },
            properties: {
              time: pos[3]
            }
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
                let time = entity.id.properties.getValue('time').time
                _this.$emit('cesiumhover', time)
                viewer.clock.currentTime = Cesium.JulianDate.addSeconds(start, (time - _this.startTimeMs) / 1000, new Cesium.JulianDate())
                window.entity = entity
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
          },
          // Show the path as a pink line sampled in 1 second increments.
          path: {
            resolution: 1,
            material: new Cesium.PolylineGlowMaterialProperty({
              glowPower: 0.1,
              color: Cesium.Color.GREY
            }),
            width: 10
          }
        })
        this.viewer.zoomTo(this.viewer.entities)
      }
    }
}
</script>

<style scoped>
  #cesiumContainer {
    display: flex;
    height: 100%;
  }
</style>
