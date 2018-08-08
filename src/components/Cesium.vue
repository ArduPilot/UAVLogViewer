<template>
    <div id="cesiumContainer"></div>
</template>

<script>
import Cesium from 'cesium/Cesium'
import 'cesium/Widgets/widgets.css'

function getMinY(data) {
  return data.reduce((min, p) => p[3] < min ? p[3] : min, data[0][3]);
}
function getMaxY(data) {
  return data.reduce((max, p) => p[3] > max ? p[3] : max, data[0][3]);
}

export default {
  name: 'Cesium',
  props: ['trajectory', 'attitudes'],
  watch: {
    trajectory: function (newVal, oldVal) { // watch it
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
        this.startTimeMs = getMinY(newVal)
        let timespan = getMaxY(newVal) - this.startTimeMs
        let viewer = this.viewer
        var start = Cesium.JulianDate.fromDate(new Date(2015, 2, 25, 16))
        var stop = Cesium.JulianDate.addSeconds(start, Math.round(timespan / 1000), new Cesium.JulianDate())
        console.log(start, stop)

        // Make sure viewer is at the desired time.
        viewer.clock.startTime = start.clone()
        viewer.clock.stopTime = stop.clone()
        viewer.clock.currentTime = start.clone()
        viewer.clock.clockRange = Cesium.ClockRange.LOOP_STOP
        viewer.clock.multiplier = 1

        // Set timeline to simulation bounds
        viewer.timeline.zoomTo(start, stop)

        let sampledPos = new Cesium.SampledPositionProperty()
        for (let pos of newVal) {
          var position = Cesium.Cartesian3.fromDegrees(pos[0], pos[1], pos[2])
          let time = Cesium.JulianDate.addSeconds(start, (pos[3] - this.startTimeMs) / 1000, new Cesium.JulianDate())
          sampledPos.addSample(time, position)
        }
        let fixedFrameTransform = Cesium.Transforms.localFrameToFixedFrameGenerator('north', 'west')
        let sampledOrientation = new Cesium.SampledProperty(Cesium.Quaternion)
        for (var atti in this.attitudes) {
          if (this.attitudes.hasOwnProperty(atti)) {
            let att = this.attitudes[atti]
            console.log(this.attitudes[atti])
            let hpRoll = Cesium.Transforms.headingPitchRollQuaternion(position, new Cesium.HeadingPitchRoll(att[2], att[1], att[0]), Cesium.Ellipsoid.WGS84, fixedFrameTransform)
            let time = Cesium.JulianDate.addSeconds(start, (atti - this.startTimeMs) / 1000, new Cesium.JulianDate())
            sampledOrientation.addSample(time, hpRoll)
          }
        }

        let entity = viewer.entities.add({

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
              color: Cesium.Color.YELLOW
            }),
            width: 10
          }
        })

        // this.hpRoll = new Cesium.HeadingPitchRoll(0, 0, 0)
        // this.fixedFrameTransform = Cesium.Transforms.localFrameToFixedFrameGenerator('north', 'west')
        // this.model = this.viewer.scene.primitives.add(Cesium.Model.fromGltf({
        //   url: require('../assets/Cesium_Air.glb'),
        //   modelMatrix: Cesium.Transforms.headingPitchRollToFixedFrame(this.position, this.hpRoll, Cesium.Ellipsoid.WGS84, this.fixedFrameTransform),
        //   minimumPixelSize: 128
        // }))
      }
      // this.polyline = this.viewer.entities.add({
      //   name: 'Orange line with black outline at height and following the surface',
      //   polyline: {
      //     positions: Cesium.Cartesian3.fromDegreesArrayHeights(newVal),
      //     width: 5,
      //     material: new Cesium.PolylineGlowMaterialProperty({
      //       glowPower: 0.2,
      //       color: Cesium.Color.BLUE
      //     })
      //   }
      // })
      this.viewer.zoomTo(this.viewer.entities)
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
      startTimeMs: 0
    }
  },
  mounted () {
  },
  methods:
    {
      closestTrajectoryPoint (time, trajectory) {
        let result
        for (var key in trajectory) {
          var dist = key - time
          if ((dist < 0 && dist < result) || result === undefined) {
            result = key
          }
        }
        return trajectory[result]
      },
      closestAttitude (time, attitude) {
        let result
        for (var key in attitude) {
          var dist = key - time
          if ((dist < 0 && dist < result) || result === undefined) {
            result = key
          }
        }
        return attitude[result]
      },
      showAttitude: function (time) {
        let start = Cesium.JulianDate.fromDate(new Date(2015, 2, 25, 16))
        let current = Cesium.JulianDate.addSeconds(start, (time - this.startTimeMs)/1000 , new Cesium.JulianDate())
        this.viewer.clock.currentTime = current
        this.viewer.scene.requestRender()
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
