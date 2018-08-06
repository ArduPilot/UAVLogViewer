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
            timeline: false,
            animation: false,
            requestRenderMode: true
          })

        this.position = Cesium.Cartesian3.fromDegrees(newVal[0], newVal[1], newVal[2])
        this.hpRoll = new Cesium.HeadingPitchRoll(0, 0, 0)
        this.fixedFrameTransform = Cesium.Transforms.localFrameToFixedFrameGenerator('north', 'west')
        this.model = this.viewer.scene.primitives.add(Cesium.Model.fromGltf({
          url: require('../assets/Cesium_Air.glb'),
          modelMatrix: Cesium.Transforms.headingPitchRollToFixedFrame(this.position, this.hpRoll, Cesium.Ellipsoid.WGS84, this.fixedFrameTransform),
          minimumPixelSize: 128
        }))
      }
      this.polyline = this.viewer.entities.add({
        name: 'Orange line with black outline at height and following the surface',
        polyline: {
          positions: Cesium.Cartesian3.fromDegreesArrayHeights(newVal),
          width: 5,
          material: new Cesium.PolylineGlowMaterialProperty({
            glowPower: 0.2,
            color: Cesium.Color.BLUE
          })
        }
      })
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
