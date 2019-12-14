<template>
    <div id='vuewrapper' style="height: 100%;">
        <template v-if="state.map_loading || state.plot_loading">
            <div id="waiting">
                <atom-spinner
                    :animation-duration="1000"
                    :color="'#64e9ff'"
                    :size="300"
                />
            </div>
        </template>
        <TxInputs fixed-aspect-ratio v-if="state.map_available && state.show_map && state.show_radio"></TxInputs>
        <ParamViewer v-if="state.show_params"></ParamViewer>
        <MessageViewer v-if="state.show_messages"></MessageViewer>
        <div class="container-fluid" style="height: 100%; overflow: hidden;">

            <sidebar/>

            <main class="col-md-9 ml-sm-auto col-lg-10 flex-column d-sm-flex" role="main">

                <div class="row"
                     v-bind:class="[state.show_map ? 'h-50' : 'h-100']"
                     v-if="state.plot_on">
                    <div class="col-12">
                        <Plotly/>
                    </div>
                </div>
                <div class="row" v-bind:class="[state.plot_on ? 'h-50' : 'h-100']"
                     v-if="state.map_available && map_ok && state.show_map">
                    <div class="col-12 noPadding">
                        <CesiumViewer ref="cesiumViewer"/>
                    </div>
                </div>
            </main>

        </div>
    </div>
</template>

<script>
import Plotly from './Plotly'
import CesiumViewer from './CesiumViewer'
import Sidebar from './Sidebar'
import TxInputs from './widgets/TxInputs'
import ParamViewer from './widgets/ParamViewer'
import MessageViewer from './widgets/MessageViewer'
import {store} from './Globals.js'
import {AtomSpinner} from 'epic-spinners'
import {Color} from 'cesium/Cesium'
import colormap from 'colormap'
import {DataflashDataExtractor} from '../tools/dataflashDataExtractor'
import {MavlinkDataExtractor} from '../tools/mavlinkDataExtractor'

export default {
    name: 'Home',
    created () {
        this.$eventHub.$on('messages', this.extractFlightData)
        this.state.messages = {}
        this.state.time_attitude = []
        this.state.time_attitudeQ = []
        this.state.current_trajectory = []
    },
    beforeDestroy () {
        this.$eventHub.$off('messages')
    },
    data () {
        return {
            state: store,
            dataExtractor: null
        }
    },
    methods: {
        extractFlightData () {
            if (this.dataExtractor === null) {
                if (this.state.log_type === 'tlog') {
                    this.dataExtractor = MavlinkDataExtractor
                } else {
                    this.dataExtractor = DataflashDataExtractor
                }
            }
            if ('FMTU' in this.state.messages && this.state.messages['FMTU'].length === 0) {
                this.state.processStatus = 'ERROR PARSING?'
            }
            if (Object.keys(this.state.time_attitude).length === 0) {
                this.state.time_attitude = this.dataExtractor.extractAttitudes(this.state.messages)
            }
            let list = Object.keys(this.state.time_attitude)
            this.state.lastTime = parseInt(list[list.length - 1])

            if (Object.keys(this.state.time_attitudeQ).length === 0) {
                this.state.time_attitudeQ = this.dataExtractor.extractAttitudesQ(this.state.messages)
            }
            if (this.state.current_trajectory.length === 0) {
                let trajectories = this.dataExtractor.extractTrajectory(this.state.messages)
                this.state.current_trajectory = trajectories.trajectory
                this.state.time_trajectory = trajectories.time_trajectory
            }

            if (this.state.flight_mode_changes.length === 0) {
                this.state.flight_mode_changes = this.dataExtractor.extractFlightModes(this.state.messages)
            }
            if (this.state.armed_events.length === 0) {
                this.state.armed_events = this.dataExtractor.extractArmedEvents(this.state.messages)
            }
            if (this.state.mission.length === 0) {
                this.state.mission = this.dataExtractor.extractMission(this.state.messages)
            }
            this.state.vehicle = this.dataExtractor.extractVehicleType(this.state.messages)
            if (this.state.params === undefined) {
                this.state.params = this.dataExtractor.extractParams(this.state.messages)
                if (this.state.params !== undefined) {
                    this.$eventHub.$on('cesium-time-changed', (time) => {
                        this.state.params.seek(time)
                    })
                }
            }
            if (this.state.textMessages.length === 0) {
                this.state.textMessages = this.dataExtractor.extractTextMessages(this.state.messages)
            }
            if (this.state.colors.length === 0) {
                this.generateColorMMap()
            }
            this.state.processStatus = 'Processed!'
            this.state.processDone = true
            this.state.map_available = this.state.current_trajectory.length > 0
        },

        generateColorMMap () {
            let colorMapOptions = {
                colormap: 'hsv',
                nshades: Math.max(12, this.setOfModes.length),
                format: 'rgbaString',
                alpha: 1
            }
            // colormap used on legend.
            this.state.cssColors = colormap(colorMapOptions)

            // colormap used on Cesium
            colorMapOptions.format = 'float'
            this.state.colors = []
            // this.translucentColors = []
            for (let rgba of colormap(colorMapOptions)) {
                this.state.colors.push(new Color(rgba[0], rgba[1], rgba[2]))
                // this.translucentColors.push(new Cesium.Color(rgba[0], rgba[1], rgba[2], 0.1))
            }
        }
    },
    components: {
        Sidebar,
        Plotly,
        CesiumViewer,
        AtomSpinner,
        TxInputs,
        ParamViewer,
        MessageViewer
    },
    computed: {
        map_ok () {
            return (this.state.flight_mode_changes !== undefined &&
                    this.state.current_trajectory !== undefined &&
                    this.state.current_trajectory.length > 0 &&
                    (Object.keys(this.state.time_attitude).length > 0 ||
                        Object.keys(this.state.time_attitudeQ).length > 0))
        },
        setOfModes () {
            let set = []
            if (!this.state.flight_mode_changes) {
                return []
            }
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

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>

    .nav-side-menu ul :not(collapsed) .arrow:before,
    .nav-side-menu li :not(collapsed) .arrow:before {
        font-family: 'Montserrat', sans-serif;
        content: "\f078";
        display: inline-block;
        padding-left: 10px;
        padding-right: 10px;
        vertical-align: middle;
        float: right;
    }

    body {
        margin: 0;
        padding: 0;
    }

    .container-fluid {
        padding-left: 0;
        padding-right: 0;
    }

    div .col-12 {
        padding-left: 0;
        padding-right: 0;
    }

    i {
        margin: 10px;
    }

    i .dropdown {
        float: right;
    }

    .noPadding {
        padding-left: 4px;
        padding-right: 6px;
        max-height: 100%;
    }

    div #waiting {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 1000;
        display: block;
        background-color: black;
        opacity: 0.75;
        text-align: center;
    }
    /* ATOM SPINNER */

      div .atom-spinner {
        margin: auto;
        margin-top: 15%;
    }

</style>
