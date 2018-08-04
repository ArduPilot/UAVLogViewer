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
        this.viewer.scene.globe.enableLighting = true
      }
      window.potato = newVal
      console.log(newVal)
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
      polyline: null
    }
  },
  mounted () {
  }
}
</script>

<style scoped>
  #cesiumContainer {
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
    overflow: hidden;
  }
</style>
