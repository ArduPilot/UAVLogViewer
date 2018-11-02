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

      <div class="demo-container">
          <div>
            <label>Camera</label>
              <select class="cesium-button" v-model="cameraType" @change="changeCamera()">
                  <option value="free">Free</option>
                  <option value="follow">Follow</option>
              </select>
          </div>
          <div>
              <label><input @change="updateVisibility()" type="checkbox" v-model="showWaypoints">Waypoints</label>
          </div>
          <div>
              <label><input @change="updateVisibility()" type="checkbox" v-model="showTrajectory">Trajectory</label>
          </div>
          <div>
              <label><input @change="updateVisibility()" type="checkbox" v-model="showClickableTrajectory">Clickable Trajectory</label>
          </div>

      </div>
    </div>

  </div>
</template>

<script>
import Cesium from 'cesium/Cesium'
import 'cesium/Widgets/widgets.css'
import colormap from 'colormap'
import {store} from './Globals.js'

function getMinTime (data) {
    return data.reduce((min, p) => p[3] < min ? p[3] : min, data[0][3])
}
function getMaxTime (data) {
    return data.reduce((max, p) => p[3] > max ? p[3] : max, data[0][3])
}

export default {
    name: 'Cesium',

    data () {
        return {
            state: store,
            showWaypoints: true,
            startTimeMs: 0,
            cameraType: 'free',
            showTrajectory: true,
            showClickableTrajectory: false
        }
    },
    created () {
        this.viewer = null
        this.colors = []
        this.cssColors = []
        this.lastHoveredTime = 0
        this.model = null
        this.clickableTrajectory = null
        this.waypoints = null
        this.trajectory = null

        this.$eventHub.$on('hoveredTime', this.showAttitude)
        this.state.map_loading = true
    },
    beforeDestroy () {
        this.$eventHub.$off('hoveredTime')
    },
    mounted () {
        if (this.viewer == null) {
            this.viewer = new Cesium.Viewer(
                'cesiumContainer',
                {
                    homeButton: false,
                    timeline: true,
                    animation: true,
                    requestRenderMode: true,
                    shouldAnimate: false,
                    scene3DOnly: true,
                    selectionIndicator: false,
                    shadows: true
                })

            this.viewer.scene.debugShowFramesPerSecond = true
            this.viewer.terrainProvider = Cesium.createWorldTerrain()
            // this.viewer.scene.postProcessStages.fxaa.enabled = false
            this.viewer.scene.postProcessStages.ambientOcclusion.enabled = false
            this.viewer.scene.postProcessStages.bloom.enabled = false
            this.clickableTrajectory = this.viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection())
            this.trajectory = this.viewer.entities.add(new Cesium.Entity())
            this.trajectoryUpdateTimeout = null

            this.viewer.scene.postRender.addEventListener(this.onFrameUpdate)
            this.viewer.animation.viewModel.setShuttleRingTicks([0.1, 0.25, 0.5, 0.75, 1, 2, 5, 10, 15])

            // Attach hover handler
            let handler = new Cesium.ScreenSpaceEventHandler(this.viewer.scene.canvas)
            handler.setInputAction(this.onMove, Cesium.ScreenSpaceEventType.MOUSE_MOVE)
            handler.setInputAction(this.onLeftDown, Cesium.ScreenSpaceEventType.LEFT_DOWN)
            handler.setInputAction(this.onClick, Cesium.ScreenSpaceEventType.LEFT_CLICK)
            handler.setInputAction(this.onLeftUp, Cesium.ScreenSpaceEventType.LEFT_UP)
            this.viewer.camera.moveEnd.addEventListener(this.onCameraUpdate)

            Cesium.knockout.getObservable(this.viewer.clockViewModel, 'shouldAnimate').subscribe(this.onAnimationChange)
        }
        let start = [Cesium.Cartographic.fromDegrees(this.state.current_trajectory[0][0],
            this.state.current_trajectory[0][1])]
        let promise = Cesium.sampleTerrainMostDetailed(this.viewer.terrainProvider, start)
        Cesium.when(promise, function (updatedPositions) {
            this.heightOffset = updatedPositions[0].height
            this.processTrajectory(this.state.current_trajectory)
            this.addModel()
            this.plotTrajectories()
            this.plotMission(this.state.mission)
            if (this.$route.query.hasOwnProperty('cam')) {
                let data = this.$route.query.cam.split(',')
                let position = new Cesium.Cartesian3(
                    parseFloat(data[0]),
                    parseFloat(data[1]),
                    parseFloat(data[2])
                )
                let direction = new Cesium.Cartesian3(
                    parseFloat(data[3]),
                    parseFloat(data[4]),
                    parseFloat(data[5])
                )
                let up = new Cesium.Cartesian3(
                    parseFloat(data[6]),
                    parseFloat(data[7]),
                    parseFloat(data[8])
                )
                this.cameraType = data[9]
                this.changeCamera()
                console.log('setting camera to ' + position + ' ' + direction)
                this.viewer.camera.up = up
                this.viewer.camera.position = position
                this.viewer.camera.direction = direction
            }
            this.state.map_loading = false
        }.bind(this))
    },

    methods:
    {
        onCameraUpdate () {
            console.log(this.viewer.camera)
            let query = Object.create(this.$route.query) // clone it
            let cam = this.viewer.camera
            query['cam'] = [
                cam.position.x.toFixed(2),
                cam.position.y.toFixed(2),
                cam.position.z.toFixed(2),
                cam.direction.x.toFixed(2),
                cam.direction.y.toFixed(2),
                cam.direction.z.toFixed(2),
                cam.up.x.toFixed(2),
                cam.up.y.toFixed(2),
                cam.up.z.toFixed(2),
                this.cameraType].join(',')
            this.$router.push({query: query})
        },
        mouseIsOnPoint (point) {
        // Checks if there is a trajectory point under the coordinate "point"
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
        changeCamera () {
            if (this.cameraType === 'follow') {
                this.viewer.trackedEntity = this.model
            } else {
                this.viewer.trackedEntity = undefined
            }
        },
        onAnimationChange (isAnimating) {
            this.$eventHub.$emit('animation-changed', isAnimating)
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

        onClick (movement) {
            if (this.mouseIsOnPoint(movement.position)) {
                this.$eventHub.$emit('cesium-time-changed', this.lastHoveredTime)
                this.viewer.clock.currentTime = Cesium.JulianDate.addSeconds(Cesium.JulianDate.fromDate(new Date(2015, 2, 25, 16)), (this.lastHoveredTime - this.startTimeMs) / 1000, new Cesium.JulianDate())
            }
            this.onLeftUp()
        },

        onMove (movement) {
            if (this.showClickableTrajectory) {
                if (this.isDragging) {
                    if (this.mouseIsOnPoint(movement.endPosition)) {
                        this.$eventHub.$emit('cesium-time-changed', this.lastHoveredTime)
                        this.viewer.clock.currentTime = Cesium.JulianDate.addSeconds(Cesium.JulianDate.fromDate(new Date(2015, 2, 25, 16)), (this.lastHoveredTime - this.startTimeMs) / 1000, new Cesium.JulianDate())
                    }
                } else {
                    if (this.mouseIsOnPoint(movement.endPosition)) {
                        this.viewer.container.style.cursor = 'pointer'
                    } else {
                        this.viewer.container.style.cursor = 'default'
                    }
                }
            }
        },

        onFrameUpdate () {
        // emits in "boot_time_ms" units.
            this.$eventHub.$emit('cesium-time-changed', (this.viewer.clock.currentTime.secondsOfDay - this.viewer.clock.startTime.secondsOfDay) * 1000 + this.startTimeMs)
        },

        generateColorMMap () {
            let colorMapOptions = {
                colormap: 'hsv',
                nshades: Math.max(12, this.setOfModes.length),
                format: 'rgbaString',
                alpha: 1
            }
            // colormap used on legend.
            this.cssColors = colormap(colorMapOptions)

            // colormap used on Cesium
            colorMapOptions.format = 'float'
            this.colors = []
            // this.translucentColors = []
            for (let rgba of colormap(colorMapOptions)) {
                this.colors.push(new Cesium.Color(rgba[0], rgba[1], rgba[2]))
                // this.translucentColors.push(new Cesium.Color(rgba[0], rgba[1], rgba[2], 0.1))
            }
        },

        cesiumTimeToMs (time) {
            return this.startTimeMs + (time.secondsOfDay - this.start.secondsOfDay) * 1000
        },

        msToCesiumTime (ms) {
            return Cesium.JulianDate.addSeconds(this.start, (ms - this.startTimeMs) / 1000, new Cesium.JulianDate())
        },

        showAttitude (time) {
            this.viewer.scene.requestRender()
            this.viewer.clock.currentTime = this.msToCesiumTime(time)
        },

        processTrajectory () {
            this.points = this.state.current_trajectory
            this.generateColorMMap()
            // process time_boot_ms into cesium time
            this.startTimeMs = getMinTime(this.points)
            let timespan = getMaxTime(this.points) - this.startTimeMs
            let viewer = this.viewer
            this.start = Cesium.JulianDate.fromDate(new Date(2015, 2, 25, 16))
            this.stop = Cesium.JulianDate.addSeconds(this.start, Math.round(timespan / 1000), new Cesium.JulianDate())
            // Make sure viewer is at the desired time.
            viewer.clock.startTime = this.start.clone()
            this.timelineStart = this.start
            this.timelineStop = this.stop
            viewer.clock.stopTime = this.stop.clone()
            viewer.clock.currentTime = this.start.clone()
            viewer.clock.clockRange = Cesium.ClockRange.LOOP_STOP
            viewer.clock.multiplier = 1
            // Set timeline to simulation bounds
            viewer.timeline.zoomTo(this.start, this.stop)
            let position
            this.positions = []
            this.sampledPos = new Cesium.SampledPositionProperty()

            // clean entities
            if (this.clickableTrajectory !== null) {
                this.clickableTrajectory.removeAll()
            }
            console.log('3')
            // Create sampled position
            for (let pos of this.points) {
                position = Cesium.Cartesian3.fromDegrees(pos[0], pos[1], pos[2] + this.heightOffset)
                this.positions.push(position)
                let time = Cesium.JulianDate.addSeconds(this.start, (pos[3] - this.startTimeMs) / 1000, new Cesium.JulianDate())
                this.sampledPos.addSample(time, position)
                this.clickableTrajectory.add({
                    position: position,
                    pixelSize: 10,
                    show: false,
                    color: this.getModeColor(pos[3]),
                    id: {time: pos[3]}
                })
            }
            console.log('finished')
        },
        addModel () {
            console.log('model')
            let points = this.points
            // Create sampled aircraft orientation
            let position = Cesium.Cartesian3.fromDegrees(points[0][0], points[0][1], points[0][2] + this.heightOffset)
            let fixedFrameTransform = Cesium.Transforms.localFrameToFixedFrameGenerator('north', 'west')
            let sampledOrientation = new Cesium.SampledProperty(Cesium.Quaternion)
            if (Object.keys(this.state.time_attitude).length > 0) {
                console.log('plotting with attitude')
                for (let atti in this.state.time_attitude) {
                    if (this.state.time_attitude.hasOwnProperty(atti)) {
                        let att = this.state.time_attitude[atti]
                        let hpRoll = Cesium.Transforms.headingPitchRollQuaternion(position, new Cesium.HeadingPitchRoll(att[2], att[1], att[0]), Cesium.Ellipsoid.WGS84, fixedFrameTransform)
                        let time = Cesium.JulianDate.addSeconds(this.start, (atti - this.startTimeMs) / 1000, new Cesium.JulianDate())
                        sampledOrientation.addSample(time, hpRoll)
                    }
                }
            } else {
                for (let atti in this.state.time_attitudeQ) {
                    if (this.state.time_attitudeQ.hasOwnProperty(atti)) {
                        let att = this.state.time_attitudeQ[atti]
                        let temp = Cesium.HeadingPitchRoll.fromQuaternion(new Cesium.Quaternion(att[0], att[1], att[2], att[3]))
                        let hpRoll = Cesium.Transforms.headingPitchRollQuaternion(position, new Cesium.HeadingPitchRoll(temp.heading, temp.pitch, temp.roll), Cesium.Ellipsoid.WGS84, fixedFrameTransform)
                        let time = Cesium.JulianDate.addSeconds(this.start, (atti - this.startTimeMs) / 1000, new Cesium.JulianDate())
                        sampledOrientation.addSample(time, hpRoll)
                    }
                }
            }

            // Add airplane model with interpolated position and orientation
            this.model = this.viewer.entities.add({
                availability: new Cesium.TimeIntervalCollection([new Cesium.TimeInterval({
                    start: this.start,
                    stop: this.stop
                })]),
                position: this.sampledPos,
                orientation: sampledOrientation,
                model: {
                    uri: this.getVehicleModel(),
                    minimumPixelSize: 6,
                    scale: 0.5
                }
            })
        },
        plotTrajectories () {
            let oldEntities = this.trajectory._children.slice()

            // Add polyline representing the path under the points
            let startTime = this.cesiumTimeToMs(this.timelineStart)
            let endTime = this.cesiumTimeToMs(this.timelineStop)
            let oldColor = this.getModeColor(this.points[0][3])
            let trajectory = []

            let first = 0
            let last = this.points.length

            for (let i in this.points) {
                if (this.points[i][3] < startTime) {
                    first = i
                } else if (this.points[i][3] < endTime) {
                    last = i
                }
            }

            for (let pos of this.points.slice(first, last)) {
                this.position = Cesium.Cartesian3.fromDegrees(pos[0], pos[1], pos[2] + this.heightOffset)
                trajectory.push(this.position)
                let color = this.getModeColor(pos[3])

                if (color !== oldColor) {
                    this.viewer.entities.add({
                        parent: this.trajectory,
                        polyline: {
                            positions: trajectory,
                            width: 2,
                            material: new Cesium.PolylineOutlineMaterialProperty({
                                color: oldColor,
                                outlineWidth: 1,
                                outlineColor: Cesium.Color.BLACK
                            })
                        }
                    })
                    oldColor = color
                    trajectory = [this.position]
                }
            }
            this.viewer.entities.add({
                parent: this.trajectory,
                polyline: {
                    positions: trajectory,
                    width: 2,
                    material: new Cesium.PolylineOutlineMaterialProperty({
                        color: oldColor,
                        outlineWidth: 1,
                        outlineColor: Cesium.Color.BLACK
                    })
                }
            })
            if (!this.$route.query.hasOwnProperty('cam')) {
                this.viewer.zoomTo(this.viewer.entities)
            }
            for (let entity of oldEntities) {
                this.viewer.entities.remove(entity)
            }
            this.viewer.scene.requestRender()
        },
        plotMission (points) {
            let cesiumPoints = []
            for (let pos of points) {
                let position = Cesium.Cartesian3.fromDegrees(pos[0], pos[1], pos[2] + this.heightOffset)
                cesiumPoints.push(position)
            }
            // Add polyline representing the path under the points
            this.waypoints = this.viewer.entities.add({
                polyline: {
                    positions: cesiumPoints,
                    width: 1,
                    material: Cesium.Color.WHITE
                }
            })
        },

        getModeColor (time) {
            return this.colors[this.setOfModes.indexOf(this.getMode(time))]
        },
        getMode (time) {
            for (let mode in this.state.flight_mode_changes) {
                if (this.state.flight_mode_changes[mode][0] > time) {
                    if (mode - 1 < 0) {
                        return this.state.flight_mode_changes[0][1]
                    }
                    return this.state.flight_mode_changes[mode - 1][1]
                }
            }
            return this.state.flight_mode_changes[this.state.flight_mode_changes.length - 1][1]
        },
        updateVisibility () {
            this.waypoints.show = this.showWaypoints
            this.trajectory.show = this.showTrajectory

            let len = this.clickableTrajectory.length
            for (let i = 0; i < len; ++i) {
                this.clickableTrajectory.get(i).show = this.showClickableTrajectory
            }
            this.viewer.scene.requestRender()
        },
        getVehicleModel () {
            let type = this.state.vehicle
            if (type === 'submarine') {
                return require('../assets/bluerovsimple.glb')
            }
            if (type === 'quadcopter') {
                return require('../assets/quad.glb')
            }
            return require('../assets/plane.glb')
        }
    },

    computed: {
        setOfModes () {
            let set = []
            for (let mode of this.state.flight_mode_changes) {
                if (!set.includes(mode[1])) {
                    set.push(mode[1])
                }
            }
            return set
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
    color: #eee;
    font-family: sans-serif;
    font-size: 9pt;
  }

  .infoPanel {
    background: rgba(42, 42, 42, 0.8);
    margin: 5px;
    border: 1px solid #444;
    border-radius: 10px;
    font-size:100%;
    font-weight: bold;
    float: left;
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

  .cesium-button {

      display: inline-block;
      position: relative;
      background: #303336;
      border: 1px solid #444;
      color: #edffff;
      fill: #edffff;
      border-radius: 4px;
      padding: 5px 12px;
      margin: 2px 3px;
      cursor: pointer;
      overflow: hidden;
      -moz-user-select: none;
      -webkit-user-select: none;
      -ms-user-select: none;
      user-select: none;
  }

  .demo-container {
      background-color: #303336;
      border-radius: 5px;
      padding: 5px;
      margin: 5px 3px;
      float: left;
  }
  .demo-container input {
      vertical-align: middle;
      margin-top: 0;
      margin-right: 5px;
  }
    .demo-container div {
        margin: 3px;
    }
</style>
