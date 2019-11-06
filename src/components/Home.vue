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
                <div id="toolbar">
                    <table class="infoPanel">
                        <tbody>
                        <tr v-bind:key="index" v-for="(mode, index) in setOfModes">
                            <td class="mode" v-bind:style="{ color: state.cssColors[index] } ">{{ mode }}</td>
                        </tr>
                        </tbody>
                    </table>
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
import {ParamSeeker} from '../tools/paramseeker'
import {Color} from 'cesium/Cesium'
import colormap from 'colormap'

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
            state: store
        }
    },
    methods: {
        extractFlightData () {
            if ('FMTU' in this.state.messages && this.state.messages['FMTU'].length === 0) {
                this.state.processStatus = 'ERROR PARSING'
                return
            }
            if (Object.keys(this.state.time_attitude).length === 0) {
                this.state.time_attitude = this.extractAttitudes(this.state.messages)
            }
            let list = Object.keys(this.state.time_attitude)
            this.state.lastTime = parseInt(list[list.length - 1])

            if (Object.keys(this.state.time_attitudeQ).length === 0) {
                this.state.time_attitudeQ = this.extractAttitudesQ(this.state.messages)
            }
            if (this.state.current_trajectory.length === 0) {
                this.state.current_trajectory = this.extractTrajectory(this.state.messages)
            }

            if (this.state.flight_mode_changes.length === 0) {
                this.state.flight_mode_changes = this.extractFlightModes(this.state.messages)
            }
            if (this.state.mission.length === 0) {
                this.state.mission = this.extractMission(this.state.messages)
            }
            this.state.vehicle = this.extractVehicleType(this.state.messages)
            if (this.state.params === undefined) {
                this.state.params = this.extractParams(this.state.messages)
            }
            if (this.state.textMessages.length === 0) {
                this.state.textMessages = this.extractTextMessages(this.state.messages)
            }
            if (this.state.colors.length === 0) {
                this.generateColorMMap()
            }
            this.state.processStatus = 'Processed!'
            this.state.processDone = true
            this.state.map_available = this.state.current_trajectory.length > 0
            this.state.show_map = this.state.map_available
        },

        extractParams (messages) {
            let params = []
            if ('PARM' in messages) {
                let paramData = messages['PARM']
                for (let data of paramData) {
                    params.push([data.time_boot_ms, data.Name, data.Value])
                }
            }
            if ('PARAM_VALUE' in messages) {
                let paramData = messages['PARAM_VALUE']
                for (let data of paramData) {
                    params.push([data.time_boot_ms, data.param_id.replace(/[^a-z0-9A-Z_]/ig, ''), data.param_value])
                }
            }
            if (params.length > 0) {
                let seeker = new ParamSeeker(params)
                this.$eventHub.$on('cesium-time-changed', (time) => {
                    seeker.seek(time)
                })
                return seeker
            } else {
                return undefined
            }
        },

        extractTextMessages (messages) {
            let texts = []
            if ('STATUSTEXT' in messages) {
                let textMsgs = messages['STATUSTEXT']
                for (let data of textMsgs) {
                    texts.push([data.time_boot_ms, data.severity, data.text])
                }
            }
            if ('MSG' in messages) {
                let textMsgs = messages['MSG']
                for (let data of textMsgs) {
                    texts.push([data.time_boot_ms, 0, data.Message])
                }
            }
            return texts
        },

        extractTrajectory (messages) {
            let trajectory = []
            this.state.time_trajectory = {}
            let startAltitude = null
            if ('GLOBAL_POSITION_INT' in messages) {
                let gpsData = messages['GLOBAL_POSITION_INT']
                for (let pos of gpsData) {
                    if (pos.lat !== 0) {
                        if (startAltitude === null) {
                            startAltitude = pos.relative_alt
                        }
                        trajectory.push([pos.lon, pos.lat, pos.relative_alt - startAltitude, pos.time_boot_ms])
                        this.state.time_trajectory[pos.time_boot_ms] = [
                            pos.lon,
                            pos.lat,
                            pos.relative_alt,
                            pos.time_boot_ms]
                    }
                }
            } else if ('AHR2' in messages) {
                let gpsData = messages['AHR2']
                for (let pos of gpsData) {
                    if (pos.Lat !== 0) {
                        if (startAltitude === null) {
                            startAltitude = pos.Alt
                        }
                        trajectory.push([pos.Lng, pos.Lat, pos.Alt - startAltitude, pos.time_boot_ms])
                        this.state.time_trajectory[pos.time_boot_ms] = [
                            pos.Lng,
                            pos.Lat,
                            (pos.Alt - startAltitude) / 1000,
                            pos.time_boot_ms]
                    }
                }
            } else if ('GPS' in messages) {
                let gpsData = messages['GPS']
                for (let pos of gpsData) {
                    if (pos.lat !== 0) {
                        if (startAltitude === null) {
                            startAltitude = pos.Alt
                        }
                        trajectory.push([pos.Lng, pos.Lat, pos.Alt - startAltitude, pos.time_boot_ms])
                        this.state.time_trajectory[pos.time_boot_ms] = [
                            pos.Lng,
                            pos.Lat,
                            pos.Alt - startAltitude,
                            pos.time_boot_ms]
                    }
                }
            }
            // console.log(trajectory)
            // console.log(this.state.time_trajectory)
            // if (trajectory.length === 0) {
            //     trajectory.push([1, 1, 10, 0])
            //     trajectory.push([1, 1, 10, this.state.lastTime])
            //     this.state.time_trajectory[0] = [1, 1, 10, 0]
            //     this.state.time_trajectory[this.state.lastTime] = [1, 1, 10, this.state.lastTime]
            // }
            return trajectory
        },
        extractAttitudes (messages) {
            let attitudes = {}
            if ('ATTITUDE' in messages) {
                let attitudeMsgs = messages['ATTITUDE']
                for (let att of attitudeMsgs) {
                    attitudes[parseInt(att.time_boot_ms)] = [att.roll, att.pitch, att.yaw]
                }
            } else if ('AHR2' in messages) {
                let attitudeMsgs = messages['AHR2']
                for (let att of attitudeMsgs) {
                    attitudes[parseInt(att.time_boot_ms)] = [att.Roll, att.Pitch, att.Yaw]
                }
            } else if ('ATT' in messages) {
                let attitudeMsgs = messages['ATT']
                for (let att of attitudeMsgs) {
                    attitudes[parseInt(att.time_boot_ms)] = [att.Roll, att.Pitch, att.Yaw]
                }
            }
            return attitudes
        },
        extractAttitudesQ (messages) {
            let attitudes = {}
            if ('XKQ1' in messages && messages['XKQ1'].length > 0) {
                console.log('QUATERNIOS1')
                let attitudeMsgs = messages['XKQ1']
                for (let att of attitudeMsgs) {
                    attitudes[att.time_boot_ms] = [att.Q1, att.Q2, att.Q3, att.Q4]
                    // attitudes[att.time_boot_ms] = [att.Q1, att.Q2, att.Q3, att.Q4]
                }
                return attitudes
            } else if ('NKQ1' in messages && messages['NKQ1'].length > 0) {
                console.log('QUATERNIOS2')
                let attitudeMsgs = messages['NKQ1']
                for (let att of attitudeMsgs) {
                    // attitudes[att.time_boot_ms] = [att.Q2, att.Q3, att.Q4, att.Q1]
                    attitudes[att.time_boot_ms] = [att.Q1, att.Q2, att.Q3, att.Q4]
                }
                return attitudes
            }
            return []
        },
        extractFlightModes (messages) {
            let modes = []
            if ('HEARTBEAT' in messages) {
                modes = [[messages['HEARTBEAT'][0].time_boot_ms, messages['HEARTBEAT'][0].asText]]
                for (let message of messages['HEARTBEAT']) {
                    if (message.asText === undefined) {
                        message.asText = 'Unknown'
                    }
                    if (message.asText !== modes[modes.length - 1][1]) {
                        modes.push([message.time_boot_ms, message.asText])
                    }
                }
            } else if ('MODE' in messages) {
                modes = [[messages['MODE'][0].time_boot_ms, messages['MODE'][0].asText]]
                for (let message of messages['MODE']) {
                    if (message.asText !== modes[modes.length - 1][1]) {
                        modes.push([message.time_boot_ms, message.asText])
                    }
                }
            }
            return modes
        },
        extractMission (messages) {
            let wps = []
            if ('CMD' in messages) {
                let cmdMsgs = messages['CMD']
                for (let cmd of cmdMsgs) {
                    if (cmd.Lat !== 0) {
                        let lat = cmd.Lat
                        let lon = cmd.Lng
                        if (Math.abs(cmd.Lat) > 180) {
                            lat = lat / 10e6
                            lon = lon / 10e6
                        }
                        wps.push([lon, lat, cmd.Alt])
                    }
                }
            }
            return wps
        },
        extractVehicleType (messages) {
            if ('MSG' in messages) {
                for (let msg of messages['MSG']) {
                    if (msg.Message.indexOf('ArduPlane') > -1) {
                        return 'airplane'
                    }
                    if (msg.Message.indexOf('ArduSub') > -1) {
                        return 'submarine'
                    }
                    if (msg.Message.toLowerCase().indexOf('rover') > -1) {
                        return 'boat'
                    }
                    if (msg.Message.indexOf('Tracker') > -1) {
                        return 'tracker'
                    }
                }
                return 'quadcopter'
            }
            if ('HEARTBEAT' in messages) {
                return messages['HEARTBEAT'][0].craft
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
        font-family: FontAwesome;
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

    #toolbar {
        margin: 5px;
        padding: 2px 5px;
        position: absolute;
        top: 0;
        color: #eee;
        font-family: sans-serif;
        font-size: 9pt;
    }

    /* INFO PANEL */

    .infoPanel {
        background: rgba(42, 42, 42, 0.8);
        margin: 5px;
        border-radius: 10px;
        font-size: 100%;
        font-weight: bold;
        float: left;
    }

    .infoPanel > tbody {
        padding: 15px;
    }

    /* ATOM SPINNER */

      div .atom-spinner {
        margin: auto;
        margin-top: 15%;
    }

</style>
