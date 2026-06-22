<template>
    <div id="wrapper">
        <div id="toolbar">
          <table class="infoPanel">
                <select class="color-coding-select" v-model="selectedColorCoder" v-on:change="updateColor">
                    <option :key="key"  :value="key" v-for="(value, key) in useableColorCoders">
                        {{ key }}
                    </option>
                </select>
              <tbody>
                <tr v-bind:key="mode[0]" v-for="mode in colorCodeLegend">
                    <td class="mode" v-bind:style="{ color: mode.color } ">{{ mode.name }}</td>
                </tr>
              </tbody>
            </table>
            <CesiumSettingsWidget />
        </div>
        <div id="cesiumContainer"></div>
        <div id="distanceLegend" v-show="scaleBarLabel">
            <div class="distanceLegendLabel">{{ scaleBarLabel }}</div>
            <div class="distanceLegendBar" :style="{ width: scaleBarWidth + 'px' }"></div>
        </div>
    </div>
</template>

<script>
import {
    Color,
    ProviderViewModel,
    UrlTemplateImageryProvider,
    Viewer, CesiumTerrainProvider,
    PointPrimitiveCollection,
    Entity,
    ScreenSpaceEventHandler,
    ScreenSpaceEventType,
    knockout,
    Cartographic,
    sampleTerrainMostDetailed,
    HeadingPitchRange,
    JulianDate,
    ClockRange,
    Cartesian3,
    Cartesian2,
    SampledProperty,
    BoundingSphere,
    LabelStyle,
    SampledPositionProperty,
    Transforms,
    PolylineDashMaterialProperty,
    TimeInterval,
    TimeIntervalCollection,
    HeadingPitchRoll,
    Ellipsoid,
    EllipsoidGeodesic,
    Quaternion,
    defined,
    ColorBlendMode,
    NearFarScalar,
    SingleTileImageryProvider,
    Rectangle,
    GeometryInstance,
    PolylineGeometry,
    ColorGeometryInstanceAttribute,
    PolylineColorAppearance,
    Primitive,
    ShaderSource,
    ImageMaterialProperty
} from 'cesium'

import { DateTime } from 'luxon'
import tzlookup from 'tz-lookup'

import { store } from './Globals.js'
import { DataflashDataExtractor } from '../tools/dataflashDataExtractor'
import { MavlinkDataExtractor } from '../tools/mavlinkDataExtractor'
import { DjiDataExtractor } from '../tools/djiDataExtractor'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import CesiumSettingsWidget from './widgets/CesiumSettingsWidget.vue'
import ColorCoderMode from './cesiumExtra/colorCoderMode.js'
import ColorCoderRange from './cesiumExtra/colorCoderRange.js'
import ColorCoderPlot from './cesiumExtra/colorCoderPlot.js'

import {
    generateHull,
    smoothGrid,
    interpolateToGrid,
    expandPolygon,
    isPointInPolygon
} from './cesiumExtra/boundingPolygon.js'

// Self-hosted terrain + non-ion imagery: no Cesium ion token required.
// Default imagery is keyless Esri World Imagery (reliable, no key / domain / rate limits).
const ESRI_WORLD_IMAGERY_URL =
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
const ESRI_CREDIT = 'Imagery © Esri, Maxar, Earthstar Geographics'
const MAPTILER_SATELLITE_URL =
    'https://api.maptiler.com/tiles/satellite-v2/{z}/{x}/{y}.jpg?key=o3JREHNnXex8WSPPm2BU'

const colorCoderMode = new ColorCoderMode(store)
const colorCoderRange = new ColorCoderRange(store)

function getMinTime (data) {
    // returns the minimum time in the array. Used to define the time range
    return data.reduce((min, p) => p[3] < min ? p[3] : min, data[0][3])
}

function getMaxTime (data) {
    // returns the maximum time in   the array. Used to define the time range
    return data.reduce((max, p) => p[3] > max ? p[3] : max, data[0][3])
}

export default {
    name: 'CesiumViewer',

    data () {
        return {
            state: store,
            startTimeMs: 0,
            lastEmitted: 0,
            colorCoder: null,
            selectedColorCoder: 'Mode',
            scaleBarLabel: '',
            scaleBarWidth: 0
        }
    },
    components: {
        CesiumSettingsWidget
    },
    created () {
        this.updateShader()
        // The objects declared here are not watched by Vue
        this.viewer = null // Cesium viewer instance
        this.model = null // Vehicle model
        this.waypoints = null // Autopilot Waypoints
        this.trajectory = null // GPS trajectory (in degrees)
        this.correctedTrajectory = [] // GPS trajectory (Cartographic array)

        // Link time with plot updates
        this.$eventHub.$on('hoveredTime', this.showAttitude)
        // This fires up the loading spinner
        this.state.mapLoading = true
        this.state.mapError = null
    },
    beforeDestroy () {
        this.$eventHub.$off('hoveredTime')
    },
    mounted () {
        // create eniro, statkart, and openseamap providers
        this.asyncSetup()
    },
    methods: {
        async asyncSetup () {
            try {
                if (this.viewer == null) {
                    if (this.state.isOnline) {
                        this.viewer = this.createViewer(true)
                        if (this.state.vehicle !== 'boat') {
                            try {
                                // Self-hosted ArduPilot SRTM terrain (same origin), replaces ion.
                                this.viewer.terrainProvider = await CesiumTerrainProvider.fromUrl('/quantized/')
                            } catch (e) {
                                // Fall back to the ellipsoid so the 3D view still works.
                                console.warn('quantized terrain unavailable, using ellipsoid:', e)
                            }
                        }
                    } else {
                        this.viewer = this.createViewer(false)
                    }
                    this.viewer.scene.debugShowFramesPerSecond = true

                    this.viewer.scene.postProcessStages.ambientOcclusion.enabled = false
                    this.viewer.scene.postProcessStages.bloom.enabled = false
                    this.clickableTrajectory = this.viewer.scene.primitives.add(new PointPrimitiveCollection())
                    this.trajectory = this.viewer.entities.add(new Entity())
                    this.trajectoryUpdateTimeout = null
                    this.viewer.scene.globe.enableLighting = true
                    this.viewer.scene.postRender.addEventListener(this.onFrameUpdate)
                    this.viewer.scene.postRender.addEventListener(this.onFrameUpdate)
                    this.viewer.camera.moveEnd.addEventListener(this.updateScaleBar)
                    this.viewer.scene.morphComplete.addEventListener(
                        () => {
                            this.viewer.zoomTo(this.viewer.entities)
                        })
                    this.viewer.animation.viewModel.setShuttleRingTicks([0.1, 0.25, 0.5, 0.75, 1, 2, 5, 10, 15])
                    this.viewer.scene.globe.depthTestAgainstTerrain = true
                    this.viewer.shadowMap.maxmimumDistance = 10000.0
                    this.viewer.shadowMap.softShadows = true
                    this.viewer.shadowMap.size = 4096
                    this.viewer.animation.viewModel.timeFormatter = (date, _viewModel) => {
                        const isoString = JulianDate.toIso8601(date)
                        let dateTime = DateTime.fromISO(isoString)
                        // get zone from current cesium location
                        const cameraPosition = this.viewer.camera.positionCartographic
                        const longitude = cameraPosition.longitude * 180 / Math.PI
                        const latitude = cameraPosition.latitude * 180 / Math.PI

                        const timezone = tzlookup(latitude, longitude)
                        dateTime = dateTime.setZone(timezone)
                        // If you want to set a specific timezone
                        // dateTime = dateTime.setZone("America/Chicago");
                        const offset = dateTime.offsetNameShort || dateTime.offsetNameLong
                        return `${dateTime.toLocaleString(DateTime.TIME_SIMPLE)} (${offset})`
                    }
                    // Attach hover handler
                    const handler = new ScreenSpaceEventHandler(this.viewer.scene.canvas)
                    handler.setInputAction(this.onMove, ScreenSpaceEventType.MOUSE_MOVE)
                    handler.setInputAction(this.onLeftDown, ScreenSpaceEventType.LEFT_DOWN)
                    handler.setInputAction(this.onClick, ScreenSpaceEventType.LEFT_CLICK)
                    handler.setInputAction(this.onLeftUp, ScreenSpaceEventType.LEFT_UP)
                    // TODO: fix saving and sharing state
                    // this.viewer.camera.moveEnd.addEventListener(this.onCameraUpdate)

                    knockout.getObservable(this.viewer.clockViewModel, 'shouldAnimate')
                        .subscribe(this.onAnimationChange)
                    const layers = this.viewer.scene.imageryLayers
                    const xofs = 0.00001
                    const options = {
                        url: require('../assets/home2.png').default,
                        tileWidth: 1920,
                        tileHeight: 1080,
                        rectangle: Rectangle.fromDegrees(-48.530077110530044 + xofs, -27.490619277419633,
                            -48.52971476731231 + xofs, -27.49044182943895),
                        credit: 'potato'
                    }
                    console.log(options)
                    layers.addImageryProvider(new SingleTileImageryProvider(options))
                    this.viewer.scene.globe.translucency.frontFaceAlphaByDistance = new NearFarScalar(
                        50.0,
                        0.4,
                        150.0,
                        1.0
                    )
                    this.viewer.scene.globe.translucency.enabled = true
                    this.viewer.scene.screenSpaceCameraController.enableCollisionDetection = false
                    this.viewer.scene.globe.undergroundColor = Color.MIDNIGHTBLUE
                    this.viewer.scene.globe.undergroundColorAlphaByDistance.near = 2
                    this.viewer.scene.globe.undergroundColorAlphaByDistance.far = 10
                    this.viewer.scene.globe.undergroundColorAlphaByDistance.nearValue = 0.2
                    this.viewer.scene.globe.undergroundColorAlphaByDistance.farValue = 1.0
                }
                this.addBathymetryButton()
                this.addCenterVehicleButton()
                this.addFitContentsButton()
                this.addCloseButton()

                for (const pos of this.state.currentTrajectory) {
                    this.correctedTrajectory.push(Cartographic.fromDegrees(pos[0], pos[1], pos[2]))
                }

                if (this.state.vehicle !== 'boat' && this.state.isOnline && this.correctedTrajectory.length > 0) {
                    const promise = sampleTerrainMostDetailed(this.viewer.terrainProvider, this.correctedTrajectory)
                    promise.then(async (result) => { await this.setup2(result) })
                        .catch(() => this.setup2(this.correctedTrajectory))
                } else {
                    this.setup2(this.correctedTrajectory)
                }
            } catch (e) {
                console.error('Error in Cesium asyncSetup:', e)
                this.state.mapLoading = false
                this.state.mapError = 'Failed to initialize 3D map: ' + (e.message || 'Unknown error')
            }
        },
        updateShader () {
            // eslint-disable-next-line camelcase
            ShaderSource._czmBuiltinsAndUniforms.czm_translateRelativeToEye =
            ShaderSource._czmBuiltinsAndUniforms.czm_translateRelativeToEye.replace(
                'low - czm_encodedCameraPositionMCLow;',
                '(low - czm_encodedCameraPositionMCLow) * (1.0 + czm_epsilon7);'
            )
        },
        async updateColor () {
            const newCoder = this.availableColorCoders[this.selectedColorCoder]
            await this.waitForMessages(newCoder.requiredMessages)
            this.colorCoder = newCoder
        },
        createViewer (online) {
            if (online) {
                console.log('creating online viewer')
                const imageryProviders = this.createAdditionalProviders()
                return new Viewer(
                    'cesiumContainer',
                    {
                        homeButton: false,
                        geocoder: false,
                        timeline: true,
                        animation: true,
                        requestRenderMode: true,
                        shouldAnimate: false,
                        scene3DOnly: false,
                        selectionIndicator: false,
                        shadows: true,
                        // No ion: custom keyless imagery list, and an empty terrain list so
                        // the base layer picker can't fall back to ion's Cesium World Terrain.
                        imageryProviderViewModels: imageryProviders,
                        selectedImageryProviderViewModel: this.esriProvider,
                        terrainProviderViewModels: [],
                        orderIndependentTranslucency: false,
                        useBrowserRecommendedResolution: false
                    }
                )
            }
            console.log('creating offline viewer')
            return new Viewer(
                'cesiumContainer',
                {
                    homeButton: false,
                    timeline: true,
                    animation: true,
                    requestRenderMode: true,
                    shouldAnimate: false,
                    scene3DOnly: false,
                    selectionIndicator: false,
                    shadows: true,
                    orderIndependentTranslucency: false,
                    baseLayerPicker: false,
                    imageryProvider: false,
                    geocoder: false,
                    useBrowserRecommendedResolution: false
                }
            )
        },

        createAdditionalProviders () {
            // Base layer picker options. All keyless / non-ion. Esri satellite is the
            // default (this.esriProvider); StatKart, MapTiler, Eniro and OpenSeaMap follow.
            const imageryProviders = []
            this.esriProvider = new ProviderViewModel({
                name: 'Satellite (Esri)',
                iconUrl: require('../assets/maptiler.png').default,
                tooltip: 'Esri World Imagery (satellite)',
                creationFunction: function () {
                    return new UrlTemplateImageryProvider({
                        url: ESRI_WORLD_IMAGERY_URL,
                        // Esri World Imagery has near-global coverage to z18; z19+ is spotty
                        // (returns "Map data not yet available" tiles in rural areas). Cap at 18
                        // so Cesium upsamples instead of showing those placeholders.
                        maximumLevel: 18,
                        credit: ESRI_CREDIT
                    })
                }
            })
            imageryProviders.push(this.esriProvider)
            imageryProviders.push(new ProviderViewModel({
                name: 'StatKart',
                iconUrl: require('../assets/statkart.jpg').default,
                tooltip: 'Statkart aerial imagery \nhttp://statkart.no/',
                creationFunction: function () {
                    return new UrlTemplateImageryProvider({
                        url: 'http://opencache.statkart.no/gatekeeper/gk/gk.open_gmaps?layers=topo4&zoom={z}&x={x}&y={y}',
                        credit: 'Map tiles by Statkart.'
                    })
                }
            }))
            imageryProviders.push(new ProviderViewModel({
                name: 'MapTiler',
                iconUrl: require('../assets/maptiler.png').default,
                tooltip: 'Maptiler satellite imagery http://maptiler.com/',
                creationFunction: function () {
                    return new UrlTemplateImageryProvider({
                        url: MAPTILER_SATELLITE_URL,
                        minimumLevel: 0,
                        maximumLevel: 20,
                        credit: 'https://www.maptiler.com/copyright'
                    })
                }
            }))
            imageryProviders.push(new ProviderViewModel({
                name: 'Eniro',
                iconUrl: require('../assets/eniro.png').default,
                tooltip: 'Eniro aerial imagery \nhttp://map.eniro.com/',
                creationFunction: function () {
                    return new UrlTemplateImageryProvider({
                        url: '/eniro/{z}/{x}/{reverseY}.png',
                        credit: 'Map tiles by Eniro.'
                    })
                }
            }))
            imageryProviders.push(new ProviderViewModel({
                name: 'OpenSeaMap',
                iconUrl: require('../assets/openseamap.png').default,
                tooltip: 'OpenSeaMap Nautical Maps \nhttp://openseamap.org/',
                parameters: {
                    transparent: 'true',
                    format: 'image/png'
                },
                creationFunction: function () {
                    return [
                        new UrlTemplateImageryProvider({
                            url: 'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png',
                            credit: 'Map tiles by OpenStreetMap.'
                        }),
                        new UrlTemplateImageryProvider({
                            url: 'https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png',
                            credit: 'Map tiles by OpenSeaMap.'
                        })
                    ]
                }
            }))
            return imageryProviders
        },

        async setup2 (updatedPositions) {
            try {
                /*
                * Second step of setup, happens after the height of the starting point has been returned by Cesium
                * */
                if (!updatedPositions || updatedPositions.length === 0) {
                    throw new Error('No GPS trajectory available in this log file.')
                }
                // Terrain height sampled per trajectory point (same order as the points);
                // processTrajectory uses it to clamp the rendered track to the ground.
                this.terrainHeights = updatedPositions.map(p => p.height)
                this.state.trajectorySource = this.state.trajectorySources[0]
                this.loadTrajectory(this.state.trajectorySource)
                // Trajectory altitude is absolute AMSL (orthometric); our self-hosted terrain is
                // raw SRTM (also orthometric), so Cesium renders both with the same geoid offset
                // and the vehicle sits at the right height above the visible ground. No terrain
                // offset is added. (This would be wrong against ellipsoidal terrain, e.g. ion.)
                this.state.heightOffset = 0
                this.processTrajectory(this.state.currentTrajectory)
                this.addModel()
                this.updateAndPlotTrajectory()
                this.plotComparisonTrajectories()
                await this.plotMission(this.state.mission)
                this.plotFences(this.state.fences)
                document.addEventListener('setzoom', this.onTimelineZoom)
                this.$eventHub.$on('rangeChanged', this.onRangeChanged)

                // TODO: Find a better way to know that cesium finished loading
                setTimeout(() => { this.state.mapLoading = false }, 2000)
                // Default to a framed top-down view of the flight (not vehicle-follow, which
                // frames a point and ends up too wide to find the flight). Follow is available
                // via the centre-vehicle button.
                this.state.cameraType = 'free'
                this.changeCamera()
                setTimeout(this.updateTimelineColors, 500)
                setInterval(this.updateGlobeOpacity, 1000)
                setTimeout(() => {
                    this.fitTrajectoryBounds()
                }, 1000)
            } catch (e) {
                console.error('Error in Cesium setup2:', e)
                this.state.mapLoading = false
                this.state.mapError = e.message || 'Unknown error during map processing'
            }
        },
        async waitForMessages (messages) {
            for (const message of messages) {
                this.$eventHub.$emit('loadType', message)
            }
            let interval
            const _this = this
            let counter = 0
            return new Promise((resolve, reject) => {
                interval = setInterval(function () {
                    for (const message of messages) {
                        if (!_this.state.messages[message]) {
                            counter += 1
                            if (counter > 30) { // 30 * 300ms = 9 s timeout
                                console.log('not resolving')
                                clearInterval(interval)
                                reject(new Error(`Could not load messageType ${message}`))
                            }
                            return
                        }
                    }
                    clearInterval(interval)
                    console.log('resolved for ' + messages)
                    resolve()
                }, 300)
            })
        },
        updateGlobeOpacity () {
            /*
            Makes the Globe transparent when the vehicle is underground/underwater. Called every 1 second
            */
            if (!this.viewer.clock.currentTime) {
                console.log('no time')
                return
            }
            const cartesian = this.model.position.getValue(
                this.viewer.clock.currentTime
            )
            if (!cartesian) {
                return
            }
            const position = Cartographic.fromCartesian(cartesian)
            const height = position.height

            const update = function (updatedPositions) {
                const altitude = height - updatedPositions[0].height
                const globe = this.viewer.scene.globe
                if (altitude < 0) {
                    globe.showGroundAtmosphere = true
                    globe.translucency.enabled = true
                } else {
                    globe.translucency.enabled = false
                }
            }.bind(this)

            if (this.state.vehicle === 'boat') {
                update([position])
                console.log('skipping sample')
            } else {
                const promise = sampleTerrainMostDetailed(this.viewer.terrainProvider,
                    [position])
                promise.then(update).catch(() => {})
            }
        },
        addCloseButton () {
            /* Creates the close button on the Cesium toolbar */
            const toolbar = document.getElementsByClassName('cesium-viewer-toolbar')[0]

            let closeButton = document.createElement('span')
            if (closeButton.classList) {
                closeButton.classList.add('cesium-navigationHelpButton-wrapper')
            } else {
                closeButton.className += ' ' + 'cesium-navigationHelpButton-wrapper'
            }
            closeButton.innerHTML = '' +
                '<button type="button" ' +
                'id="cesium-close-button" ' +
                'class="cesium-button cesium-toolbar-button cesium-close-button" ' +
                'title="Close 3D view">' +
                '<svg viewbox="0 0 40 40">' +
                '<path class="close-x" d="M 10,10 L 30,30 M 30,10 L 10,30" />' +
                '</svg>' +
                '</button>'.trim()
            toolbar.append(closeButton)
            closeButton = document.getElementById('cesium-close-button')
            closeButton.addEventListener('click', () => {
                this.state.showMap = false
                this.$nextTick(function () {
                    this.$eventHub.$emit('force-resize-plotly')
                })
            })
        },
        addBathymetryButton () {
            /* Creates the bathymetry button on the Cesium toolbar */
            const toolbar = document.getElementsByClassName('cesium-viewer-toolbar')[0]

            let bathymetryButton = document.createElement('span')
            if (bathymetryButton.classList) {
                bathymetryButton.classList.add('cesium-navigationHelpButton-wrapper')
            } else {
                bathymetryButton.className += ' ' + 'cesium-navigationHelpButton-wrapper'
            }
            bathymetryButton.innerHTML = '' +
              '<button type="button" ' +
              'id="cesium-bathymetry-button" ' +
              'class="cesium-button cesium-toolbar-button"' +
              'title="Toggle Bathymetry">' +
              '<i class="fas fa-ship" style="font-style: unset;"></i>' +
              '</button>'.trim()
            toolbar.append(bathymetryButton)
            bathymetryButton = document.getElementById('cesium-bathymetry-button')
            bathymetryButton.addEventListener('click', () => {
                this.plotBathymetry()
                this.viewer.scene.requestRender()
            })
        },
        addFitContentsButton () {
            /* Creates the close button on the Cesium toolbar */
            const toolbar = document.getElementsByClassName('cesium-viewer-toolbar')[0]

            let closeButton = document.createElement('span')
            if (closeButton.classList) {
                closeButton.classList.add('cesium-navigationHelpButton-wrapper')
            } else {
                closeButton.className += ' ' + 'cesium-navigationHelpButton-wrapper'
            }
            closeButton.innerHTML = '' +
                '<button type="button" ' +
                'id="cesium-fit-button" ' +
                'class="cesium-button cesium-toolbar-button"' +
                'title="Re-center view">' +
                '<i class="fas fa-solid fa-expand" style="font-style: unset;"></i>' +
                '</svg>' +
                '</button>'.trim()
            toolbar.append(closeButton)
            closeButton = document.getElementById('cesium-fit-button')
            closeButton.addEventListener('click', () => {
                this.$nextTick(() => {
                    this.state.cameraType = 'free'
                    this.changeCamera()
                    this.fitTrajectoryBounds()
                })
            })
        },
        addCenterVehicleButton () {
            /* Creates the close button on the Cesium toolbar */
            const toolbar = document.getElementsByClassName('cesium-viewer-toolbar')[0]

            let closeButton = document.createElement('span')
            if (closeButton.classList) {
                closeButton.classList.add('cesium-navigationHelpButton-wrapper')
            } else {
                closeButton.className += ' ' + 'cesium-navigationHelpButton-wrapper'
            }
            closeButton.innerHTML = '' +
                '<button type="button" ' +
                'id="cesium-center-vehicle-button" ' +
                'class="cesium-button cesium-toolbar-button"' +
                'title="Center vehicle">' +
                '<i class="fas fa-solid fa-car" style="font-style: unset;"></i>' +
                '</svg>' +
                '</button>'.trim()
            toolbar.append(closeButton)
            closeButton = document.getElementById('cesium-center-vehicle-button')
            closeButton.addEventListener('click', () => {
                this.$nextTick(() => {
                    this.state.cameraType = 'follow'
                    this.changeCamera()
                })
            })
        },
        onCameraUpdate () {
            const query = Object.create(this.$route.query) // clone it
            const cam = this.viewer.camera
            query.cam = [
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
            this.$router.push({ query: query })
        },

        getTimeStart () {
            let date = null
            try {
                date = JulianDate.fromDate(this.state.metadata.startTime)
            } catch (e) {
                console.log(e)
                date = JulianDate.fromDate(new Date(2015, 2, 25, 16))
            }
            return date
        },

        mouseIsOnPoint (point) {
            // Checks if there is a trajectory point under the coordinate "point"
            const pickedObjects = this.viewer.scene.drillPick(point)
            if (defined(pickedObjects)) {
                // tries to read the time of each entioty under the mouse, returns once one is found.
                for (const entity of pickedObjects) {
                    try {
                        const time = entity.id.time
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
            if (this.cameraType === 'follow' && this.viewer.trackedEntity !== this.model) {
                this.viewer.trackedEntity = this.model
            } else {
                this.viewer.trackedEntity = undefined
            }
        },
        fitTrajectoryBounds () {
            // Frame the flight so it fills ~2/3 of the view, never zooming tighter than a ~100 m
            // view (so a hover/stationary flight stays visible). Use a 3D bounding sphere of the
            // actual track positions so the view accounts for terrain elevation (framing a 2D
            // rectangle puts the camera at ellipsoid height 0 and ends up below high terrain).
            if (!this.points || this.points.length === 0) {
                this.viewer.flyTo(this.viewer.entities)
                return
            }
            const cartesians = []
            for (const p of this.points) {
                if (isFinite(p[0]) && isFinite(p[1]) && isFinite(p[2])) {
                    cartesians.push(Cartesian3.fromDegrees(p[0], p[1], p[2]))
                }
            }
            if (cartesians.length === 0) {
                return
            }
            const sphere = BoundingSphere.fromPoints(cartesians)
            // x1.5 -> flight fills ~2/3 of the view; floor radius 50 m -> view never under ~100 m
            sphere.radius = Math.max(sphere.radius * 1.5, 50)
            this.viewer.camera.flyToBoundingSphere(sphere, { duration: 1.5 })
        },
        updateScaleBar () {
            // Traditional map scale bar (bottom-right): measure the ground distance spanned by
            // one pixel at the bottom-centre of the view and pick a round value for the bar.
            if (!this.viewer) {
                return
            }
            const scene = this.viewer.scene
            const width = scene.canvas.clientWidth
            const height = scene.canvas.clientHeight
            const globe = scene.globe
            const left = scene.camera.getPickRay(new Cartesian2((width / 2) | 0, height - 1))
            const right = scene.camera.getPickRay(new Cartesian2(1 + ((width / 2) | 0), height - 1))
            const leftPos = left && globe.pick(left, scene)
            const rightPos = right && globe.pick(right, scene)
            if (!defined(leftPos) || !defined(rightPos)) {
                this.scaleBarLabel = ''
                return
            }
            const lc = globe.ellipsoid.cartesianToCartographic(leftPos)
            const rc = globe.ellipsoid.cartesianToCartographic(rightPos)
            this._geodesic = this._geodesic || new EllipsoidGeodesic()
            this._geodesic.setEndPoints(lc, rc)
            const pixelDistance = this._geodesic.surfaceDistance
            if (!(pixelDistance > 0)) {
                this.scaleBarLabel = ''
                return
            }
            const steps = [1, 2, 3, 5, 10, 20, 30, 50, 100, 200, 300, 500, 1000, 2000, 3000, 5000,
                10000, 20000, 30000, 50000, 100000, 200000, 300000, 500000, 1000000, 2000000, 5000000]
            const maxBarPx = 120
            let distance
            for (let i = steps.length - 1; i >= 0; i--) {
                if (steps[i] / pixelDistance < maxBarPx) {
                    distance = steps[i]
                    break
                }
            }
            if (distance === undefined) {
                this.scaleBarLabel = ''
                return
            }
            this.scaleBarWidth = Math.round(distance / pixelDistance)
            this.scaleBarLabel = distance >= 1000 ? (distance / 1000) + ' km' : distance + ' m'
        },
        onAnimationChange (isAnimating) {
            this.$eventHub.$emit('animation-changed', isAnimating)
        },
        // onRangeChanged (event) {
        //     this.viewer.timeline.zoomTo(this.msToCesiumTime(event[0]), this.msToCesiumTime(event[1]))
        // },
        updateTimelineColors () {
            const start = this.cesiumTimeToMs(this.viewer.timeline._startJulian)
            const end = this.cesiumTimeToMs(this.viewer.timeline._endJulian)

            const timeline = document.getElementsByClassName('cesium-timeline-bar')[0]
            let colors = []
            let previousColor = null
            for (const change of this.state.flightModeChanges) {
                if (change[0] < start || previousColor === null) {
                    previousColor = this.getModeColor(change[0])
                    colors = [[0, previousColor]]
                }
                if ((change[0] > start) && change[0] < end) {
                    const percentage = (change[0] - start) * 100 / (end - start)
                    colors.push([percentage - 0.001, previousColor])
                    colors.push([percentage, this.getModeColor(change[0])])
                    previousColor = this.getModeColor(change[0])
                }
            }
            colors.push([100, previousColor])

            let string = 'linear-gradient(to right'
            if (colors.length > 1) {
                for (const change of colors) {
                    string = string + ', rgba(' + change[1].red * 150 + ',' + change[1].green * 150 + ',' +
                        change[1].blue * 150 + ', 100) ' + change[0] + '%'
                }

                string = string + ')'
                timeline.style.background = string
            }
        },
        onTimelineZoom (event) {
            this.timelineStart = event.startJulian
            this.timelineStop = event.endJulian

            const start = this.cesiumTimeToMs(event.startJulian)
            const end = this.cesiumTimeToMs(event.endJulian)
            this.state.timeRange = [start, end]
            this.updateTimelineColors()

            if (this.trajectoryUpdateTimeout !== null) {
                clearTimeout(this.trajectoryUpdateTimeout)
            }
            setTimeout(this.updateAndPlotTrajectory, 500)
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
                this.viewer.clock.currentTime =
                    JulianDate.addSeconds(
                        this.getTimeStart(),
                        (this.lastHoveredTime - this.startTimeMs) / 1000,
                        new JulianDate())
            }
            this.onLeftUp()
        },

        onMove (movement) {
            if (this.showClickableTrajectory) {
                if (this.isDragging) {
                    if (this.mouseIsOnPoint(movement.endPosition)) {
                        this.$eventHub.$emit('cesium-time-changed', this.lastHoveredTime)
                        this.viewer.clock.currentTime =
                            JulianDate.addSeconds(
                                this.getTimeStart(),
                                (this.lastHoveredTime - this.startTimeMs) / 1000,
                                new JulianDate()
                            )
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
            const newFrameTime = (current - this.viewer.clock.startTime.secondsOfDay) * 1000 + this.startTimeMs
            if (newFrameTime === this.lastEmitted) {
                // False alarm.
                return
            }
            this.lastEmitted = newFrameTime
            this.$eventHub.$emit(
                'cesium-time-changed',
                newFrameTime
            )
            if (this.viewer.clock.currentTime < this.timelineStart ||
                this.viewer.clock.currentTime > this.timelineStop) {
                this.viewer.clock.currentTime = this.timelineStart.clone()
            }
        },

        cesiumTimeToMs (time) {
            let result = (time.secondsOfDay - this.start.secondsOfDay)
            if (result < 0) {
                result += 86400
            }
            return this.startTimeMs + result * 1000
        },

        msToCesiumTime (ms) {
            return JulianDate.addSeconds(this.start, (ms - this.startTimeMs) / 1000, new JulianDate())
        },

        showAttitude (time) {
            this.viewer.scene.requestRender()
            this.viewer.clock.currentTime = this.msToCesiumTime(time)
        },

        processTrajectory () {
            this.correctedTrajectory = []
            this.points = this.state.trajectories[this.state.trajectorySource].trajectory
            // Clamp the rendered track to the terrain surface so it never disappears below the
            // opaque ground (pre-GPS-lock samples whose AMSL is under the local terrain). Terrain
            // heights were sampled per point in setup2; points above terrain keep their true AMSL.
            // Done here (not just setup2) because loadTrajectory re-extracts points asynchronously.
            if (this.terrainHeights && this.terrainHeights.length === this.points.length) {
                for (let i = 0; i < this.points.length; i++) {
                    if (this.terrainHeights[i] > this.points[i][2]) {
                        this.points[i][2] = this.terrainHeights[i]
                    }
                }
            }
            for (const pos of this.points) {
                this.correctedTrajectory.push(Cartographic.fromDegrees(pos[0], pos[1], pos[2]))
            }
            // process time_boot_ms into cesium time
            this.startTimeMs = getMinTime(this.points)
            const timespan = getMaxTime(this.points) - this.startTimeMs
            this.state.timeRange = [this.startTimeMs, this.startTimeMs + timespan]
            const viewer = this.viewer
            this.start = this.getTimeStart()
            this.stop = JulianDate.addSeconds(this.start, Math.round(timespan / 1000), new JulianDate())
            // Make sure viewer is at the desired time.
            viewer.clock.startTime = this.start.clone()
            this.timelineStart = this.start
            this.timelineStop = this.stop
            viewer.clock.stopTime = this.stop.clone()
            viewer.clock.clockRange = ClockRange.LOOP_STOP
            viewer.clock.multiplier = 1
            // Set timeline to simulation bounds
            viewer.timeline.zoomTo(this.start, this.stop)
            let position
            this.positions = []
            this.sampledPos = new SampledPositionProperty()

            // clean entities
            if (this.clickableTrajectory !== null) {
                this.clickableTrajectory.removeAll()
            }
            // Create sampled position
            const isBoat = this.state.vehicle === 'boat'
            for (const posIndex in this.points) {
                const pos = this.points[posIndex]
                if (isBoat) {
                    position = Cartesian3.fromDegrees(pos[0], pos[1], 0)
                } else {
                    position = Cartesian3.fromDegrees(
                        pos[0],
                        pos[1],
                        pos[2] + this.heightOffset
                    )
                }
                this.positions.push(position)
                const time = JulianDate.addSeconds(
                    this.start,
                    (pos[3] - this.startTimeMs) / 1000, new JulianDate())

                this.sampledPos.addSample(time, position)
                // this.clickableTrajectory.add({
                //     position: position,
                //     pixelSize: 10,
                //     show: false,
                //     color: this.getModeColor(pos[3]),
                //     id: {time: pos[3]}
                // })
                if (this.model !== null) {
                    this.model.position = this.sampledPos
                }
            }
        },
        aggregateDepth (bathymetry, positions) {
            const positionsWithDepth = []
            let lastIndex = 0

            for (const index in positions.time_boot_ms) {
                while (bathymetry.time_boot_ms[lastIndex] < positions.time_boot_ms[index] &&
                    lastIndex < bathymetry.time_boot_ms.length - 1) {
                    lastIndex++
                }
                if (bathymetry.time_boot_ms[lastIndex] >= positions.time_boot_ms[index]) {
                    positionsWithDepth.push({
                        latitude: positions.Lat[index] * 1e-7,
                        longitude: positions.Lng[index] * 1e-7,
                        depth: bathymetry.Dist[lastIndex]
                    })
                }
            }
            return positionsWithDepth
        },
        async plotBathymetry () {
            const requiredMessages = ['RFND', 'POS']
            for (const message of requiredMessages) {
                this.$eventHub.$emit('loadType', message)
            }
            while (!(this.state.messages.RFND || this.state.messages['RFND[0]']) || !this.state.messages.POS) {
                await new Promise(resolve => setTimeout(resolve, 100))
            }
            const bathymetry = this.state.messages.RFND || this.state.messages['RFND[0]']
            let positionsWithDepth = this.aggregateDepth(bathymetry, this.state.messages.POS)

            // Filter out outliers and invalid readings
            const depths = positionsWithDepth.map(p => p.depth).filter(d => d > 0.1)
            const mean = depths.reduce((a, b) => a + b, 0) / depths.length
            const stdDev = Math.sqrt(depths.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / depths.length)

            positionsWithDepth = positionsWithDepth.filter(p => {
                return p.depth > 0.1 &&
                      Math.abs(p.depth - mean) < 2.5 * stdDev &&
                      p.latitude !== 0 && p.longitude !== 0
            })

            // Normalize coordinates to 1000x1000 space
            const minLat = Math.min(...positionsWithDepth.map(p => p.latitude))
            const maxLat = Math.max(...positionsWithDepth.map(p => p.latitude))
            const minLng = Math.min(...positionsWithDepth.map(p => p.longitude))
            const maxLng = Math.max(...positionsWithDepth.map(p => p.longitude))

            const normalizedPoints = positionsWithDepth.map(p => ({
                x: ((p.longitude - minLng) / (maxLng - minLng)) * 1000,
                y: ((p.latitude - minLat) / (maxLat - minLat)) * 1000,
                depth: p.depth
            }))

            // Generate and expand hull
            const hull = generateHull(normalizedPoints)
            const margin = 50 // Adjustable margin
            const expandedHull = expandPolygon(hull, margin)

            // Create canvas
            const canvas = document.createElement('canvas')
            const ctx = canvas.getContext('2d')
            const width = 512
            const height = 512
            canvas.width = width
            canvas.height = height

            // Create grid with improved interpolation
            const gridSize = 200
            const grid = interpolateToGrid(normalizedPoints, gridSize)
            const smoothedGrid = smoothGrid(grid, 1)

            // Find depth range for color scaling
            let minDepth = Infinity
            let maxDepth = -Infinity
            smoothedGrid.forEach(row => row.forEach(depth => {
                if (depth !== null) {
                    minDepth = Math.min(minDepth, depth)
                    maxDepth = Math.max(maxDepth, depth)
                }
            }))

            const cellWidth = width / gridSize
            const cellHeight = height / gridSize

            // Draw bathymetry
            const imageData = new ImageData(width, height)
            for (let i = 0; i < gridSize; i++) {
                for (let j = 0; j < gridSize; j++) {
                    const depth = smoothedGrid[i][j]
                    if (depth === null) continue

                    const normalizedDepth = (depth - minDepth) / (maxDepth - minDepth)
                    const r = Math.floor(100 * (1 - normalizedDepth))
                    const g = Math.floor(149 * (1 - normalizedDepth))
                    const b = Math.floor(237 * (1 - normalizedDepth * 0.5))

                    const x = Math.floor(i * cellWidth)
                    const y = Math.floor(j * cellHeight)
                    for (let dx = 0; dx < cellWidth + 1; dx++) {
                        for (let dy = 0; dy < cellHeight + 1; dy++) {
                            const pixelX = x + dx
                            const pixelY = y + dy
                            const idx = (pixelY * width + pixelX) * 4

                            if (isPointInPolygon(pixelX / width * 1000, pixelY / height * 1000, expandedHull)) {
                                imageData.data[idx] = r
                                imageData.data[idx + 1] = g
                                imageData.data[idx + 2] = b
                                imageData.data[idx + 3] = 255 // Fully opaque inside hull
                            } else {
                                imageData.data[idx + 3] = 0 // Transparent outside hull
                            }
                        }
                    }
                }
            }
            ctx.putImageData(imageData, 0, 0)

            // Draw contour lines
            ctx.save()
            ctx.beginPath()
            expandedHull.forEach((point, i) => {
                const x = (point.x / 1000) * width
                const y = (point.y / 1000) * height
                if (i === 0) ctx.moveTo(x, y)
                else ctx.lineTo(x, y)
            })
            ctx.closePath()
            ctx.clip()

            const contourLevels = 10
            ctx.strokeStyle = 'rgba(0,0,0,0.2)'
            ctx.lineWidth = 0.5

            for (let level = 0; level < contourLevels; level++) {
                const threshold = minDepth + (maxDepth - minDepth) * (level / contourLevels)
                ctx.beginPath()

                for (let i = 0; i < gridSize - 1; i++) {
                    for (let j = 0; j < gridSize - 1; j++) {
                        const x = i * cellWidth
                        const y = j * cellHeight
                        const cell = [
                            smoothedGrid[i][j],
                            smoothedGrid[i + 1][j],
                            smoothedGrid[i + 1][j + 1],
                            smoothedGrid[i][j + 1]
                        ]

                        if (cell.includes(null)) continue

                        if ((cell[0] < threshold && cell[1] >= threshold) ||
                            (cell[0] >= threshold && cell[1] < threshold)) {
                            ctx.moveTo(x + cellWidth, y)
                            ctx.lineTo(x + cellWidth, y + cellHeight)
                        }

                        if ((cell[0] < threshold && cell[3] >= threshold) ||
                            (cell[0] >= threshold && cell[3] < threshold)) {
                            ctx.moveTo(x, y + cellHeight)
                            ctx.lineTo(x + cellWidth, y + cellHeight)
                        }
                    }
                }
                ctx.stroke()
            }
            ctx.restore()

            // Draw hull outline
            ctx.beginPath()
            expandedHull.forEach((point, i) => {
                const x = (point.x / 1000) * width
                const y = (point.y / 1000) * height
                if (i === 0) ctx.moveTo(x, y)
                else ctx.lineTo(x, y)
            })
            ctx.closePath()
            ctx.strokeStyle = 'rgba(0,0,0,0.5)'
            ctx.lineWidth = 2
            ctx.stroke()

            // Create the rectangle with the canvas texture
            const rectangle = Rectangle.fromCartographicArray(
                positionsWithDepth.map(p => Cartographic.fromDegrees(p.longitude, p.latitude))
            )

            this.viewer.entities.add({
                rectangle: {
                    coordinates: rectangle,
                    material: new ImageMaterialProperty({
                        image: canvas,
                        transparent: true,
                        repeat: new Cartesian2(1, -1),
                        offset: new Cartesian2(0, 1)
                    }),
                    outline: true,
                    outlineColor: Color.BLACK
                }
            })
            this.viewer.scene.requestRender()
        },

        // Hull generation helper function remains the same as before,
        addModel () {
            if (this.model !== null) {
                this.viewer.entities.remove(this.model)
            }
            const points = this.points
            // Create sampled aircraft orientation
            const position = Cartesian3.fromDegrees(
                points[0][0], points[0][1], points[0][2] + this.heightOffset
            )
            let fixedFrameTransform = Transforms.localFrameToFixedFrameGenerator('north', 'west')
            const sampledOrientation = new SampledProperty(Quaternion)
            if (Object.keys(this.state.timeAttitudeQ).length > 0) {
                fixedFrameTransform = Transforms.localFrameToFixedFrameGenerator('north', 'east')
                for (const atti in this.state.timeAttitudeQ) {
                    if (this.state.timeAttitudeQ[atti]) {
                        const att = this.state.timeAttitudeQ[atti]

                        const q1 = att[0]
                        const q2 = att[1]
                        const q3 = att[2]
                        const q4 = att[3]

                        const roll = Math.atan2(2.0 * (q1 * q2 + q3 * q4), 1.0 - 2.0 * (q2 * q2 + q3 * q3))
                        let pitch = Math.asin(2.0 * (q1 * q3 - q4 * q2))
                        if (isNaN(pitch)) {
                            pitch = 0
                        }
                        const yaw = Math.atan2(2.0 * (q1 * q4 + q2 * q3), 1.0 - 2.0 * (q3 * q3 + q4 * q4))
                        // TODO: fix this coordinate system!
                        const hpRoll = Transforms.headingPitchRollQuaternion(
                            position,
                            new HeadingPitchRoll(-yaw, -pitch, roll - 3.14),
                            Ellipsoid.WGS84,
                            fixedFrameTransform
                        )

                        const time = JulianDate.addSeconds(
                            this.start, (atti - this.startTimeMs) / 1000,
                            new JulianDate())

                        sampledOrientation.addSample(time, hpRoll)
                    }
                }
            } else {
                for (const atti in this.state.timeAttitude) {
                    if (this.state.timeAttitude[atti]) {
                        const att = this.state.timeAttitude[atti]
                        const hpRoll = Transforms.headingPitchRollQuaternion(
                            position,
                            new HeadingPitchRoll(att[2], att[1], att[0]),
                            Ellipsoid.WGS84,
                            fixedFrameTransform
                        )

                        const time = JulianDate.addSeconds(
                            this.start, (atti - this.startTimeMs) / 1000,
                            new JulianDate()
                        )
                        sampledOrientation.addSample(time, hpRoll)
                    }
                }
            }

            // Reused by the comparison-trajectory vehicles (position differs, orientation shared).
            this.sampledOrientation = sampledOrientation
            // Add airplane model with interpolated position and orientation
            this.model = this.viewer.entities.add({
                availability: new TimeIntervalCollection([new TimeInterval({
                    start: this.start,
                    stop: this.stop
                })]),
                position: this.sampledPos,
                orientation: sampledOrientation,
                model: {
                    uri: this.getVehicleModel(),
                    minimumPixelSize: 15,
                    scale: this.modelScale / 10
                },
                viewFrom: new Cartesian3(5, 0, 3)
            })
            this.changeCamera()
            if (this.state.vehicle === 'boat') {
                setTimeout(() => {
                    this.viewer.flyTo(this.model, { offset: new HeadingPitchRange(0, -0.5, 100) }).then(() => {
                        this.changeCamera()
                    })
                }, 3000)
            }
        },
        async updateAndPlotTrajectory () {
            if (!this.colorCoder) {
                this.colorCoder = this.availableColorCoders[this.selectedColorCoder]
            }
            const isBoat = this.state.vehicle === 'boat'
            const startTime = this.cesiumTimeToMs(this.timelineStart)
            const endTime = this.cesiumTimeToMs(this.timelineStop)
            const geometryInstances = []
            let currentSegment = []
            let currentColor = this.getModeColor(this.points[0][3])

            let first = 0
            let last = this.points.length

            for (const i in this.points) {
                if (this.points[i][3] < startTime) {
                    first = i
                } else if (this.points[i][3] < endTime) {
                    last = i
                }
            }

            for (const pos of this.points.slice(first, last)) {
                const position = Cartesian3.fromDegrees(
                    pos[0],
                    pos[1],
                    isBoat ? 0.1 : pos[2] + this.heightOffset
                )

                const newColor = this.getModeColor(pos[3])

                if (!Color.equals(newColor, currentColor)) {
                    currentSegment.push(position)
                    if (currentSegment.length > 1) {
                        geometryInstances.push(new GeometryInstance({
                            geometry: new PolylineGeometry({
                                positions: currentSegment,
                                width: 3.0
                            }),
                            attributes: {
                                color: ColorGeometryInstanceAttribute.fromColor(currentColor)
                            }
                        }))
                    }

                    currentColor = newColor
                    currentSegment = [position]
                } else {
                    currentSegment.push(position)
                }
            }

            if (currentSegment.length > 1) {
                geometryInstances.push(new GeometryInstance({
                    geometry: new PolylineGeometry({
                        positions: currentSegment,
                        width: 3.0
                    }),
                    attributes: {
                        color: ColorGeometryInstanceAttribute.fromColor(currentColor)
                    }
                }))
            }

            // Remove old trajectory primitives
            this.viewer.scene.primitives.remove(this.trajectoryPrimitive)

            if (!this.showTrajectory) {
                this.viewer.scene.requestRender()
                return
            }
            // Create a new primitive with the geometry instances
            this.trajectoryPrimitive = new Primitive({
                geometryInstances: geometryInstances,
                appearance: new PolylineColorAppearance()
            })

            this.viewer.scene.primitives.add(this.trajectoryPrimitive)
            this.viewer.scene.primitives.raiseToTop(this.trajectoryPrimitive)
            this.viewer.scene.requestRender()
        },

        async plotMission (points) {
            console.log(points)
            const cesiumPoints = []
            const cesiumPointsOrig = []

            for (const pos of points) {
                const position = Cartographic.fromDegrees(pos[0], pos[1], pos[2])
                if (isNaN(pos[0]) || isNaN(pos[1]) || isNaN(pos[2])) {
                    continue
                }
                cesiumPoints.push(position)
                cesiumPointsOrig.push(position)
            }
            if (this.state.vehicle !== 'boat') {
                sampleTerrainMostDetailed(this.viewer.terrainProvider, cesiumPoints, true).then((finalPoints) => {
                    this.plotMissionPoints(finalPoints, cesiumPointsOrig, points)
                }).catch(() => this.plotMissionPoints(cesiumPointsOrig, cesiumPointsOrig, points))
            } else {
                this.plotMissionPoints(cesiumPointsOrig, cesiumPointsOrig, points)
            }
        },

        plotMissionPoints (finalPoints, cesiumPointsOrig, points) {
            // Resolve each waypoint's height per its MAV_FRAME (a mission can mix frames):
            //   GLOBAL (0) / GLOBAL_INT (5)                -> alt is absolute AMSL
            //   GLOBAL_RELATIVE_ALT (3) / _INT (6)         -> alt is above home
            //   GLOBAL_TERRAIN_ALT (10) / _INT (11)        -> alt is above terrain
            // finalPoints[i].height is the sampled terrain; cesiumPointsOrig[i].height is the
            // raw alt. Our terrain is orthometric (same datum as AMSL), so absolute alt renders
            // at the right height above the visible ground (geoid cancels) just like the track.
            // Home altitude (AMSL) for relative frames is the home waypoint (seq 0).
            let homeAlt = 0
            for (let i = 0; i < points.length; i++) {
                if (points[i][5] === 0) {
                    homeAlt = points[i][2]
                    break
                }
            }
            for (let i = 0; i < cesiumPointsOrig.length; i++) {
                const frame = points[i][6]
                const alt = points[i][2]
                if (frame === 10 || frame === 11) {
                    finalPoints[i].height += alt
                } else if (frame === 3 || frame === 6) {
                    finalPoints[i].height = homeAlt + alt
                } else {
                    // GLOBAL/absolute. Use the raw alt directly: cesiumPointsOrig shares its
                    // Cartographic objects with the terrain-sampled array, so its height has
                    // been overwritten with terrain.
                    finalPoints[i].height = alt
                }
            }

            this.waypoints = this.viewer.entities.add({
                polyline: {
                    positions: finalPoints.map(
                        (pos) => Cartesian3.fromRadians(pos.longitude, pos.latitude, pos.height)
                    ),
                    width: 1,
                    material: new PolylineDashMaterialProperty({
                        color: Color.WHITE,
                        dashLength: 8.0
                    })
                }
            })
            const labelPoints = finalPoints.map(
                (pos) => Cartesian3.fromRadians(pos.longitude, pos.latitude, pos.height + 0.3)
            )
            for (const i in labelPoints) {
                this.viewer.entities.add({
                    parent: this.waypoints,
                    position: labelPoints[i],
                    label: {
                        text: `${points[i][5]}`,
                        font: '12px sans-serif',
                        style: LabelStyle.FILL_AND_OUTLINE,
                        fillColor: Color.WHITE,
                        outlineColor: Color.BLACK,
                        showBackground: false,
                        outlineWidth: 3
                    }
                })
            }
        },
        plotFences (fencesList) {
            this.fences = []
            for (const fence of fencesList) {
                const cesiumPoints = []
                if (fence.length === 1) {
                    if (fence[0][2] === 0) {
                        continue
                    }
                    const pos = fence[0]
                    this.fences.push(this.viewer.entities.add({
                        position: Cartesian3.fromDegrees(pos[0], pos[1]),
                        ellipse: {
                            semiMinorAxis: pos[2],
                            semiMajorAxis: pos[2],
                            material: Color.ORANGE.withAlpha(0.5)
                        }
                    }))
                    continue
                }
                for (const pos of fence) {
                    const position = Cartesian3.fromDegrees(pos[0], pos[1])
                    cesiumPoints.push(position)
                }
                // we need to close the polygon
                if (cesiumPoints.length === 0) {
                    continue
                }
                const lastPos = fence[0]
                cesiumPoints.push(Cartesian3.fromDegrees(lastPos[0], lastPos[1]))

                // Add polyline representing the path under the points
                this.fences.push(this.viewer.entities.add({
                    polyline: {
                        positions: cesiumPoints,
                        width: 1,
                        clampToGround: true,
                        material: new PolylineDashMaterialProperty({
                            color: Color.ORANGE,
                            dashLength: 8.0
                        })
                    }
                }))
            }
        },

        getModeColor (time) {
            if (this.colorCoder === undefined) {
                return new Color(1, 1, 1, 1)
            }
            return this.colorCoder.getColor(time)
        },
        getMode (time) {
            for (const mode in this.state.flightModeChanges) {
                if (this.state.flightModeChanges[mode][0] > time) {
                    if (mode - 1 < 0) {
                        return this.state.flightModeChanges[0][1]
                    }
                    return this.state.flightModeChanges[mode - 1][1]
                }
            }
            return this.state.flightModeChanges[this.state.flightModeChanges.length - 1][1]
        },
        updateVisibility () {
            this.waypoints.show = this.showWaypoints
            this.trajectory.show = this.showTrajectory
            this.fences.show = this.showFences

            const len = this.clickableTrajectory.length
            for (let i = 0; i < len; ++i) {
                this.clickableTrajectory.get(i).show = this.showClickableTrajectory
            }
            this.viewer.scene.requestRender()
        },
        getVehicleModel () {
            const type = this.state.vehicle
            if (type === 'submarine') {
                return require('../assets/bluerovsimple.glb').default
            }
            if (type === 'quadcopter+') {
                return require('../assets/quadp.glb').default
            }
            if (type === 'quadcopterx' || type === 'quadcopter') {
                return require('../assets/quadx.glb').default
            }
            if (type === 'boat') {
                return require('../assets/boat.glb').default
            }
            return require('../assets/plane.glb').default
        },
        getDataExtractor () {
            if (this.state.logType === 'tlog') {
                return MavlinkDataExtractor
            } else if (this.state.logType === 'dji') {
                return DjiDataExtractor
            }
            return DataflashDataExtractor
        },
        loadTrajectory (source) {
            this.waitForMessages([source]).then(() => {
                const dataExtractor = this.getDataExtractor()
                this.state.trajectories = dataExtractor.extractTrajectory(this.state.messages, source)
                this.processTrajectory()
            })
        },
        async plotComparisonTrajectories () {
            if (!this.viewer) {
                return
            }
            // Remove the previously drawn comparison overlays and their vehicles.
            if (this.comparisonPrimitives) {
                for (const primitive of this.comparisonPrimitives) {
                    this.viewer.scene.primitives.remove(primitive)
                }
            }
            this.comparisonPrimitives = []
            if (this.comparisonModels) {
                for (const model of this.comparisonModels) {
                    this.viewer.entities.remove(model)
                }
            }
            this.comparisonModels = []
            const sources = this.state.comparisonTrajectories || []
            if (sources.length === 0 || !this.showTrajectory) {
                this.viewer.scene.requestRender()
                return
            }
            const dataExtractor = this.getDataExtractor()
            const isBoat = this.state.vehicle === 'boat'
            const colors = this.state.comparisonTrajectoryColors
            for (let idx = 0; idx < sources.length; idx++) {
                const source = sources[idx]
                if (!source) {
                    continue
                }
                try {
                    await this.waitForMessages([source])
                } catch (e) {
                    console.warn('comparison trajectory source unavailable:', source, e)
                    continue
                }
                const trajectories = dataExtractor.extractTrajectory(this.state.messages, source)
                if (!trajectories[source]) {
                    continue
                }
                const points = trajectories[source].trajectory
                const positions = []
                const sampledPos = new SampledPositionProperty()
                for (const pos of points) {
                    const cartesian = Cartesian3.fromDegrees(
                        pos[0],
                        pos[1],
                        isBoat ? 0.1 : pos[2] + this.heightOffset
                    )
                    positions.push(cartesian)
                    if (this.start !== undefined && this.startTimeMs !== undefined) {
                        const time = JulianDate.addSeconds(
                            this.start, (pos[3] - this.startTimeMs) / 1000, new JulianDate())
                        sampledPos.addSample(time, cartesian)
                    }
                }
                if (positions.length < 2) {
                    continue
                }
                const color = Color.fromCssColorString(colors[idx % colors.length])
                const primitive = new Primitive({
                    geometryInstances: new GeometryInstance({
                        geometry: new PolylineGeometry({
                            positions: positions,
                            width: 3.0
                        }),
                        attributes: {
                            color: ColorGeometryInstanceAttribute.fromColor(color)
                        }
                    }),
                    appearance: new PolylineColorAppearance()
                })
                this.viewer.scene.primitives.add(primitive)
                this.comparisonPrimitives.push(primitive)

                // Vehicle that flies the comparison track on the shared clock, tinted with the
                // source's color so it can be told apart from the primary vehicle. Lets you read
                // each source's position at the same instant in time.
                if (this.start !== undefined && this.stop !== undefined) {
                    const comparisonModel = this.viewer.entities.add({
                        availability: new TimeIntervalCollection([new TimeInterval({
                            start: this.start,
                            stop: this.stop
                        })]),
                        position: sampledPos,
                        orientation: this.sampledOrientation,
                        model: {
                            uri: this.getVehicleModel(),
                            minimumPixelSize: 15,
                            scale: this.modelScale / 10,
                            color: color,
                            colorBlendMode: ColorBlendMode.MIX,
                            colorBlendAmount: 0.7
                        }
                    })
                    this.comparisonModels.push(comparisonModel)
                }
            }
            this.viewer.scene.requestRender()
        },
        loadAttitude (source) {
            this.waitForMessages([source]).then(() => {
                let dataExtractor = null
                if (this.state.logType === 'tlog') {
                    dataExtractor = MavlinkDataExtractor
                } else {
                    dataExtractor = DataflashDataExtractor
                }
                try {
                    this.state.timeAttitudeQ = []
                    this.state.timeAttitude = dataExtractor.extractAttitude(this.state.messages, source)
                } catch {
                    this.state.timeAttitude = []
                    this.state.timeAttitudeQ = dataExtractor.extractAttitudeQ(this.state.messages, source)
                }
                this.addModel()
            })
        }
    },
    computed: {
        availableColorCoders () {
            const coders = {
                Mode: colorCoderMode,
                range: colorCoderRange
            }
            for (const key in this.state.plotCache) {
                coders[key] = new ColorCoderPlot(store, key)
            }
            return coders
        },
        useableColorCoders () {
            // check if requiredMessages for each color coder are present
            // iterates on key:value pais of this.availableColorCoders and filters them
            // based on the requiredMessages property
            const colorCoders = {}
            for (const [key, value] of Object.entries(this.availableColorCoders)) {
                if (value.requiredMessages.every(m => Object.keys(this.state.messageTypes).includes(m))) {
                    colorCoders[key] = value
                }
            }
            return colorCoders
        },

        colorCodeLegend () {
            return this.colorCoder?.getLegend() ?? []
        },
        setOfModes () {
            const set = []
            for (const mode of this.state.flightModeChanges) {
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
            return undefined
        },
        modelScale () {
            // TODO: scale the model instead
            if (this.state.vehicle === 'submarine') {
                return this.state.modelScale * 6.86
            }
            return this.state.modelScale
        },
        heightOffset () {
            return parseFloat(this.state.heightOffset)
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
        },
        showFences () {
            return this.state.showFences
        },
        trajectorySource () {
            return this.state.trajectorySource
        },
        comparisonTrajectories () {
            return this.state.comparisonTrajectories
        },
        attitudeSource () {
            return this.state.attitudeSource
        },
        radioMode () {
            return this.state.radioMode
        }
    },
    watch: {
        modelScale (scale) {
            const value = parseFloat(scale)
            if (!isNaN(value)) {
                this.model.model.scale = value / 10
                if (this.comparisonModels) {
                    for (const model of this.comparisonModels) {
                        model.model.scale = value / 10
                    }
                }
                this.viewer.scene.requestRender()
            }
        },
        heightOffset (offset) {
            const value = parseFloat(offset)
            if (!isNaN(value)) {
                this.updateAndPlotTrajectory()
                this.processTrajectory()
                this.addModel()
                this.plotComparisonTrajectories()
                this.viewer.scene.requestRender()
            }
        },
        colorCoder () {
            this.updateAndPlotTrajectory()
            this.processTrajectory()
            this.viewer.scene.requestRender()
        },
        timeRange (range) {
            try {
                if (range[1] > range[0]) {
                    const cesiumStart = this.msToCesiumTime(range[0]).secondsOfDay
                    const plotlyStart = this.viewer.timeline._startJulian.secondsOfDay
                    const cesiumEnd = this.msToCesiumTime(range[1]).secondsOfDay
                    const plotlyEnd = this.viewer.timeline._endJulian.secondsOfDay
                    // If range has changed more than 1 second
                    if (Math.abs(cesiumStart - plotlyStart) > 1 || Math.abs(cesiumEnd - plotlyEnd) > 1) {
                        this.viewer.timeline.zoomTo(this.msToCesiumTime(range[0]), this.msToCesiumTime(range[1]))
                    }
                }
            } catch (e) {
                console.log(e)
            }
        },
        cameraType () {
            this.changeCamera()
        },
        showTrajectory () {
            this.updateAndPlotTrajectory()
            this.plotComparisonTrajectories()
        },
        showClickableTrajectory () {
            this.updateVisibility()
        },
        showWaypoints () {
            this.updateVisibility()
        },
        trajectorySource () {
            this.loadTrajectory(this.state.trajectorySource)
        },
        comparisonTrajectories: {
            handler () {
                this.plotComparisonTrajectories()
            },
            deep: true
        },
        attitudeSource () {
            this.loadAttitude(this.state.attitudeSource)
        }
    }
}

</script>

<style scoped>
    #cesiumContainer {
        display: flex;
        height: 100%;
    }

    #distanceLegend {
        position: absolute;
        bottom: 34px;
        right: 10px;
        z-index: 5;
        color: #fff;
        font-size: 11px;
        font-family: sans-serif;
        text-align: center;
        text-shadow: 0 0 3px #000, 0 0 3px #000;
        pointer-events: none;
        user-select: none;
    }

    #distanceLegend .distanceLegendLabel {
        margin-bottom: 1px;
    }

    #distanceLegend .distanceLegendBar {
        height: 5px;
        min-width: 2px;
        margin: 0 auto;
        background: rgba(255, 255, 255, 0.55);
        border: 1px solid #fff;
        border-top: none;
        box-sizing: border-box;
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
        padding: 5px 5px;
        position: absolute;
        top: 0;
        color: #eee;
        font-family: 'Montserrat', sans-serif;
        font-size: 9pt;
        z-index: 1;
        height: fit-content;
        display: flex;
    }

    /* INFO PANEL */

    .infoPanel {
      top: 10px;
      background-color: rgba(40, 40, 40, 0.7);
      padding: 10px;
      padding-left: 25px;
      border-radius: 5px;
      border: 1px solid #444;
    }

    #wrapper {
        width: 100%;
        height: 100%;
        position: relative;
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

<style>

/* TOOLBAR BUTTONS */

    .cesium-toolbar-button {
        background-color: rgb(61, 58, 56);
        border-radius: 3px;
    }

    .cesium-toolbar-button:hover {
        background-color: rgb(102, 90, 79);
        color: #fff;
        box-shadow: none;
        border: #5b5b5b;
        -webkit-transition: all 1s ease;
        -moz-transition: all 1s ease;
        -o-transition: all 1s ease;
        transition: all 1s ease;
    }

    /* HELP BUTTON */

    .cesium-navigation-help-button svg {
        width: 27px;
        padding-left: 3px;
        color: #fff;
    }

    /* CLOSE BUTTON */

     .cesium-close-button svg {
        stroke: white;
        stroke-width: 2px;
        width: 25px;
    }

    .color-coding-select {
      margin: 4px;
    }
</style>
