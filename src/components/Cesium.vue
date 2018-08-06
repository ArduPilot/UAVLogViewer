<template>
    <div id="cesiumContainer"></div>
</template>

<script>
import Cesium from 'cesium/Cesium'
import 'cesium/Widgets/widgets.css'

export default {
  name: 'Cesium',
  props: ['trajectory'],
  watch: {
    trajectory: function (newVal, oldVal) { // watch it
      if (this.viewer == null) {
        this.viewer = new Cesium.Viewer(
          'cesiumContainer',
          {
            homeButton: false,
            timeline: true,
            animation: true,
            requestRenderMode: false,
            shouldAnimate: false

          })
        let timespan = newVal[newVal.length - 1][3] - newVal[0][3]
        let viewer = this.viewer
        var start = Cesium.JulianDate.fromDate(new Date(2015, 2, 25, 16));
        var stop = Cesium.JulianDate.addSeconds(start, Math.round(timespan/1000), new Cesium.JulianDate());
        console.log(start, stop)

        // Make sure viewer is at the desired time.
        viewer.clock.startTime = start.clone()
        viewer.clock.stopTime = stop.clone()
        viewer.clock.currentTime = start.clone()
        viewer.clock.clockRange = Cesium.ClockRange.LOOP_STOP
        viewer.clock.multiplier = 1

        // Set timeline to simulation bounds
        viewer.timeline.zoomTo(start, stop);

        let sampledPos = new Cesium.SampledPositionProperty()
        for (let pos of newVal) {
          var position = Cesium.Cartesian3.fromDegrees(pos[0], pos[1], pos[2])
          let time = Cesium.JulianDate.addSeconds(start, (pos[3] - newVal[0][3]) / 1000, new Cesium.JulianDate())
          sampledPos.addSample(time, position)

          // Also create a point for each sample we generate.
          viewer.entities.add({
            position: position,
            point: {
              pixelSize: 8,
              color: Cesium.Color.TRANSPARENT,
              outlineColor: Cesium.Color.YELLOW,
              outlineWidth: 3
            }
          })
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
          orientation: new Cesium.VelocityOrientationProperty(sampledPos),
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
      fixedFrameTransform: null
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
      showAttitude: function (time, trajectory, attitudes) {
        let closestPoint = this.closestTrajectoryPoint(time, trajectory)
        let newpos = Cesium.Cartesian3.fromDegrees(closestPoint[0], closestPoint[1], closestPoint[2])
        let closestAtt = this.closestAttitude(time, attitudes)
        this.hpRoll.roll = closestAtt[0]
        this.hpRoll.pitch = closestAtt[1]
        this.hpRoll.heading = closestAtt[2]
        this.model.modelMatrix = Cesium.Transforms.headingPitchRollToFixedFrame(newpos, this.hpRoll, Cesium.Ellipsoid.WGS84, this.fixedFrameTransform)
        this.viewer.scene.requestRender()
      }
    }
}
</script>

<style scoped>
  #cesiumContainer {
    height: 47%;
    margin: 0;
    padding: 0;
    overflow: hidden;
    bottom: 0;
    position: fixed;
    width: 80%;
  }
</style>
