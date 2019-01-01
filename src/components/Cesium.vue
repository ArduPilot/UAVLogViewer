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
import {store} from './Globals.js'

Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJmNTJjOWYzZS1hMDA5LTRjNDQtYTBhYi1iZWQ2NTc5YzliNWIiLCJpZCI6MjczNywiaWF0IjoxNTM0Mzg3NzM3fQ.Qe6EcCmGUfM_FRKYuJEORsT4tQAvRkdmFyNk9bkARqM'

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
            startTimeMs: 0,
            cssColors: []
        }
    },
    created () {
        this.viewer = null
        this.colors = []

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
        let imageryProviders = Cesium.createDefaultImageryProviderViewModels()
        imageryProviders.push(new Cesium.ProviderViewModel({
            name: 'StatKart',
            iconUrl: require('../assets/statkart.jpg'),
            tooltip: 'Statkart aerial imagery \nhttp://statkart.no/',
            creationFunction: function () {
                return new Cesium.UrlTemplateImageryProvider({
                    url: 'http://opencache.statkart.no/gatekeeper/gk/gk.open_gmaps?layers=topo4&zoom={z}&x={x}&y={y}',
                    credit: 'Map tiles by Statkart.'
                })
            }
        }))
        imageryProviders.push(new Cesium.ProviderViewModel({
            name: 'Eniro',
            iconUrl: require('../assets/eniro.png'),
            tooltip: 'Eniro aerial imagery \nhttp://map.eniro.com/',
            creationFunction: function () {
                return new Cesium.UrlTemplateImageryProvider({
                    // url: 'http://map.eniro.com/geowebcache/service/tms1.0.0/map/{z}/{x}/{reverseY}.png',
                    url: '/eniro/{z}/{x}/{reverseY}.png',
                    credit: 'Map tiles by Eniro.'
                })
            }
        }))
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
                    shadows: true,
                    imageryProviderViewModels: imageryProviders
                })

            this.viewer.scene.debugShowFramesPerSecond = true
            this.viewer.terrainProvider = Cesium.createWorldTerrain()
            // this.viewer.scene.postProcessStages.fxaa.enabled = false
            this.viewer.scene.postProcessStages.ambientOcclusion.enabled = false
            this.viewer.scene.postProcessStages.bloom.enabled = false
            this.clickableTrajectory = this.viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection())
            this.trajectory = this.viewer.entities.add(new Cesium.Entity())
            this.trajectoryUpdateTimeout = null
            this.viewer.scene.globe.enableLighting = true
            this.viewer.scene.postRender.addEventListener(this.onFrameUpdate)
            this.viewer.animation.viewModel.setShuttleRingTicks([0.1, 0.25, 0.5, 0.75, 1, 2, 5, 10, 15])

            this.viewer.shadowMap.maxmimumDistance = 10000.0
            this.viewer.shadowMap.softShadows = true
            this.viewer.shadowMap.size = 4096

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
            document.addEventListener('setzoom', this.onTimelineZoom)
            this.$eventHub.$on('rangeChanged', this.onRangeChanged)
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
                this.state.cameraType = data[9]
                this.changeCamera()
                console.log('setting camera to ' + position + ' ' + direction)
                this.viewer.camera.up = up
                this.viewer.camera.position = position
                this.viewer.camera.direction = direction
            }
            this.state.map_loading = false
            setTimeout(this.updateTimelineColors, 500)
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

        getTimeStart () {
            let date = null
            try {
                date = Cesium.JulianDate.fromDate(this.state.metadata.startTime)
            } catch (e) {
                console.log(e)
                date = Cesium.JulianDate.fromDate(new Date(2015, 2, 25, 16))
            }
            return date
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
        // onRangeChanged (event) {
        //     this.viewer.timeline.zoomTo(this.msToCesiumTime(event[0]), this.msToCesiumTime(event[1]))
        // },
        updateTimelineColors ()
        {
            let start = this.cesiumTimeToMs(this.viewer.timeline._startJulian)
            let end = this.cesiumTimeToMs(this.viewer.timeline._endJulian)

            let timeline = document.getElementsByClassName('cesium-timeline-bar')[0]
            let colors = []
            let previousColor = null
            for (let change of this.state.flight_mode_changes) {
                if (change[0] > start && change[0] < end) {
                    if (previousColor === null) {
                        previousColor = this.getModeColor(change[0] - 1)
                        colors.push([0, previousColor])
                    }
                    let percentage = (change[0] - start) * 100 / (end - start)
                    colors.push([percentage - 0.001, previousColor])
                    colors.push([percentage, this.getModeColor(change[0])])
                    previousColor = this.getModeColor(change[0])
                }
            }
            colors.push([100, previousColor])

            let string = 'linear-gradient(to right'
            for (let change of colors) {
                string = string + ', rgba(' + change[1].red * 150    + ',' + change[1].green * 150 + ',' + change[1].blue * 150 + ', 100) ' + change[0] + '%'
            }
            string = string + ')'
            timeline.style.background = string
        },
        onTimelineZoom (event) {
            this.timelineStart = event.startJulian
            this.timelineStop = event.endJulian

            let start = this.cesiumTimeToMs(event.startJulian)
            let end = this.cesiumTimeToMs(event.endJulian)
            this.state.timeRange = [start, end]
            this.updateTimelineColors()

            if (this.trajectoryUpdateTimeout !== null) {
                clearTimeout(this.trajectoryUpdateTimeout)
            }
            setTimeout(this.plotTrajectories, 500)
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
                this.viewer.clock.currentTime = Cesium.JulianDate.addSeconds(this.getTimeStart(), (this.lastHoveredTime - this.startTimeMs) / 1000, new Cesium.JulianDate())
            }
            this.onLeftUp()
        },

        onMove (movement) {
            if (this.showClickableTrajectory) {
                if (this.isDragging) {
                    if (this.mouseIsOnPoint(movement.endPosition)) {
                        this.$eventHub.$emit('cesium-time-changed', this.lastHoveredTime)
                        this.viewer.clock.currentTime = Cesium.JulianDate.addSeconds(this.getTimeStart(), (this.lastHoveredTime - this.startTimeMs) / 1000, new Cesium.JulianDate())
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
            let current = (this.viewer.clock.currentTime.secondsOfDay)
            current = current > this.viewer.clock.startTime.secondsOfDay ? current : current + 86400
            this.$eventHub.$emit('cesium-time-changed', (current - this.viewer.clock.startTime.secondsOfDay) * 1000 + this.startTimeMs)
            if (this.viewer.clock.currentTime < this.timelineStart ||
                this.viewer.clock.currentTime > this.timelineStop) {
                this.viewer.clock.currentTime = this.timelineStart.clone()
            }
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
            this.state.timeRange = [this.startTimeMs, this.startTimeMs + timespan]
            let viewer = this.viewer
            this.start = this.getTimeStart()
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
                // this.clickableTrajectory.add({
                //     position: position,
                //     pixelSize: 10,
                //     show: false,
                //     color: this.getModeColor(pos[3]),
                //     id: {time: pos[3]}
                // })
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
            if (Object.keys(this.state.time_attitudeQ).length > 0) {
                console.log('plotting with QUATERNIOS')
                fixedFrameTransform = Cesium.Transforms.localFrameToFixedFrameGenerator('north', 'east')
                for (let atti in this.state.time_attitudeQ) {
                    if (this.state.time_attitudeQ.hasOwnProperty(atti)) {
                        let att = this.state.time_attitudeQ[atti]

                        let q1 = att[0]
                        let q2 = att[1]
                        let q3 = att[2]
                        let q4 = att[3]

                        let roll = Math.atan2(2.0 * (q1 * q2 + q3 * q4), 1.0 - 2.0 * (q2 * q2 + q3 * q3))
                        let pitch = Math.asin(2.0 * (q1 * q3 - q4 * q2))
                        if (isNaN(pitch)) {
                            pitch = 0
                        }
                        let yaw = Math.atan2(2.0 * (q1 * q4 + q2 * q3), 1.0 - 2.0 * (q3 * q3 + q4 * q4))
                        // TODO: fix this coordinate system!
                        let hpRoll = Cesium.Transforms.headingPitchRollQuaternion(position, new Cesium.HeadingPitchRoll(-yaw, -pitch, roll - 3.14), Cesium.Ellipsoid.WGS84, fixedFrameTransform)
                        let time = Cesium.JulianDate.addSeconds(this.start, (atti - this.startTimeMs) / 1000, new Cesium.JulianDate())
                        sampledOrientation.addSample(time, hpRoll)
                    }
                }
            } else {
                console.log('plotting with attitude')
                for (let atti in this.state.time_attitude) {
                    if (this.state.time_attitude.hasOwnProperty(atti)) {
                        let att = this.state.time_attitude[atti]
                        let hpRoll = Cesium.Transforms.headingPitchRollQuaternion(position, new Cesium.HeadingPitchRoll(att[2], att[1], att[0]), Cesium.Ellipsoid.WGS84, fixedFrameTransform)
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
                    scale: this.modelScale / 10
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
                            width: 1,
                            material: oldColor
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
                    width: 1,
                    material: oldColor
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
        },
        timeRange () {
            if (this.state.timeRange !== null) {
                return this.state.timeRange
            }
        },
        modelScale () {
            return this.state.modelScale
        },
        cameraType () {
            return this.state.cameraType
        },
        showTrajectory () {
            return this.state.showTrajectory
        },
        showClickableTrajectory () {
            return this.state.showClickableTrajectory
        },
        showWaypoints () {
            return this.state.showWaypoints
        }
    },
    watch: {
        modelScale (scale) {
            let value = parseFloat(scale)
            if (!isNaN(value)) {
                this.model.model.scale = value / 10
                this.viewer.scene.requestRender()
            }
        },
        timeRange (range) {
            try {
                if (Math.abs(this.msToCesiumTime(range[0]).secondsOfDay - this.viewer.timeline._startJulian.secondsOfDay) > 1 ||
                    Math.abs(this.msToCesiumTime(range[1]).secondsOfDay - this.viewer.timeline._endJulian.secondsOfDay) > 1) {
                    this.viewer.timeline.zoomTo(this.msToCesiumTime(range[0]), this.msToCesiumTime(range[1]))
                }
            } catch (e) {
                console.log(e)
            }
        },
        cameraType () {
            this.changeCamera()
        },
        showTrajectory () {
            this.updateVisibility()
        },
        showClickableTrajectory () {
            this.updateVisibility()
        },
        showWaypoints () {
            this.updateVisibility()
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
        margin: 0;
    }

  input#collapsible {
      display: none;
  }

  .lbl-toggle {
      display: block;
      text-transform: uppercase;
      text-align: center;
      cursor: pointer;
      transition: all 0.25s ease-out;
      margin: 0;
  }

  .lbl-toggle:hover {
      color: #5b5b5b;
  }

  .lbl-toggle::before {
      content: ' ';
      display: inline-block;

      border-top: 5px solid transparent;
      border-bottom: 5px solid transparent;
      border-left: 5px solid currentColor;
      vertical-align: middle;
      margin-right: .7rem;
      transform: translateY(-2px);

      transition: transform .2s ease-out;
  }

  .toggle:checked + .lbl-toggle::before {
      transform: rotate(90deg) translateX(-3px);
  }

  .collapsible-content {
      max-height: 0px;
      overflow: hidden;
      transition: max-height .25s ease-in-out;
  }

  .toggle:checked + .lbl-toggle + .collapsible-content {
      max-height: 350px;
  }

  .toggle:checked + .lbl-toggle {
      border-bottom-right-radius: 0;
      border-bottom-left-radius: 0;
  }

  .collapsible-content .content-inner {
      background: rgba(250, 224, 66, .2);
      border-bottom: 1px solid rgba(250, 224, 66, .45);
      border-bottom-left-radius: 7px;
      border-bottom-right-radius: 7px;
      padding: .5rem 1rem;
  }
</style>
