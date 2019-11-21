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
                for (let i in paramData.time_boot_ms) {
                    params.push(
                        [
                            paramData.time_boot_ms[i],
                            paramData.Name[i],
                            paramData.Value[i]
                        ]
                    )
                }
            }
            if ('PARAM_VALUE' in messages) {
                let paramData = messages['PARAM_VALUE']
                for (let i in paramData.time_boot_ms) {
                    params.push(
                        [
                            paramData.time_boot_ms[i],
                            paramData.param_id[i].replace(/[^a-z0-9A-Z_]/ig, ''),
                            paramData.param_value[i]
                        ]
                    )
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
                for (let i in textMsgs.time_boot_ms) {
                    texts.push([textMsgs.time_boot_ms[i], textMsgs.severity[i], textMsgs.text[i]])
                }
            }
            if ('MSG' in messages) {
                let textMsgs = messages['MSG']
                for (let i in textMsgs.time_boot_ms) {
                    texts.push([textMsgs.time_boot_ms[i], 0, textMsgs.Message[i]])
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
                for (let i in gpsData.time_boot_ms) {
                    if (gpsData.lat[i] !== 0) {
                        if (startAltitude === null) {
                            startAltitude = gpsData.relative_alt[i]
                        }
                        trajectory.push(
                            [
                                gpsData.lon[i],
                                gpsData.lat[i],
                                gpsData.relative_alt[i] - startAltitude,
                                gpsData.time_boot_ms[i]
                            ]
                        )
                        this.state.time_trajectory[gpsData.time_boot_ms[i]] = [
                            gpsData.lon[i],
                            gpsData.lat[i],
                            gpsData.relative_alt[i],
                            gpsData.time_boot_ms[i]]
                    }
                }
            } else if ('AHR2' in messages) {
                let gpsData = messages['AHR2']
                for (let i in gpsData.time_boot_ms) {
                    if (gpsData.Lat[i] !== 0) {
                        if (startAltitude === null) {
                            startAltitude = gpsData.Alt[i]
                        }
                        trajectory.push(
                            [
                                gpsData.Lng[i],
                                gpsData.Lat[i],
                                gpsData.Alt[i] - startAltitude,
                                gpsData.time_boot_ms[i]
                            ]
                        )
                        this.state.time_trajectory[gpsData.time_boot_ms[i]] = [
                            gpsData.Lng[i],
                            gpsData.Lat[i],
                            (gpsData.Alt[i] - startAltitude) / 1000,
                            gpsData.time_boot_ms[i]]
                    }
                }
            } else if ('GPS' in messages) {
                let gpsData = messages['GPS']
                for (let i in gpsData.time_boot_ms) {
                    if (gpsData.Lat[i] !== 0) {
                        if (startAltitude === null) {
                            startAltitude = gpsData.Alt[i]
                        }
                        trajectory.push(
                            [
                                gpsData.Lng[i],
                                gpsData.Lat[i],
                                gpsData.Alt[i] - startAltitude,
                                gpsData.time_boot_ms[i]
                            ]
                        )
                        this.state.time_trajectory[gpsData.time_boot_ms[i]] = [
                            gpsData.Lng[i],
                            gpsData.Lat[i],
                            gpsData.Alt[i] - startAltitude,
                            gpsData.time_boot_ms[i]]
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
                for (let i in attitudeMsgs.time_boot_ms) {
                    attitudes[parseInt(attitudeMsgs.time_boot_ms[i])] =
                        [
                            attitudeMsgs.roll[i],
                            attitudeMsgs.pitch[i],
                            attitudeMsgs.yaw[i]
                        ]
                }
            } else if ('AHR2' in messages) {
                let attitudeMsgs = messages['AHR2']
                for (let i in attitudeMsgs.time_boot_ms) {
                    attitudes[parseInt(attitudeMsgs.time_boot_ms[i])] =
                        [
                            attitudeMsgs.Roll[i],
                            attitudeMsgs.Pitch[i],
                            attitudeMsgs.Yaw[i]
                        ]
                }
            } else if ('ATT' in messages) {
                let attitudeMsgs = messages['ATT']
                for (let i in attitudeMsgs.time_boot_ms) {
                    attitudes[parseInt(attitudeMsgs.time_boot_ms[i])] =
                        [
                            attitudeMsgs.Roll[i],
                            attitudeMsgs.Pitch[i],
                            attitudeMsgs.Yaw[i]
                        ]
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
                let msgs = messages['HEARTBEAT']
                modes = [[msgs.time_boot_ms[0], msgs.asText[0]]]
                for (let i in msgs.time_boot_ms) {
                    if (msgs.asText[i] === undefined) {
                        msgs.asText[i] = 'Unknown'
                    }
                    if (msgs.asText[i] !== modes[modes.length - 1][1]) {
                        modes.push([msgs.time_boot_ms[i], msgs.asText[i]])
                    }
                }
            } else if ('MODE' in messages) {
                let msgs = messages['MODE']
                modes = [[msgs.time_boot_ms[0], msgs.asText[0]]]
                for (let i in msgs.time_boot_ms) {
                    if (msgs.asText[i] !== modes[modes.length - 1][1]) {
                        modes.push([msgs.time_boot_ms[i], msgs.asText[i]])
                    }
                }
            }
            return modes
        },
        extractMission (messages) {
            let wps = []
            if ('CMD' in messages) {
                let cmdMsgs = messages['CMD']
                for (let i in cmdMsgs.time_boot_ms) {
                    if (cmdMsgs.Lat[i] !== 0) {
                        let lat = cmdMsgs.Lat[i]
                        let lon = cmdMsgs.Lng[[i]]
                        if (Math.abs(lat) > 180) {
                            lat = lat / 10e6
                            lon = lon / 10e6
                        }
                        wps.push([lon, lat, cmdMsgs.Alt[i]])
                    }
                }
            }
            return wps
        },
        extractVehicleType (messages) {
            if ('MSG' in messages) {
                let msgs = messages['MSG']
                for (let i in msgs.time_boot_ms) {
                    if (msgs.Message[i].indexOf('ArduPlane') > -1) {
                        return 'airplane'
                    }
                    if (msgs.Message[i].indexOf('ArduSub') > -1) {
                        return 'submarine'
                    }
                    if (msgs.Message[i].toLowerCase().indexOf('rover') > -1) {
                        return 'boat'
                    }
                    if (msgs.Message[i].indexOf('Tracker') > -1) {
                        return 'tracker'
                    }
                }
                return 'quadcopter'
            }
            if ('HEARTBEAT' in messages) {
                return messages['HEARTBEAT'].craft[0]
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
        background: rgba(41, 41, 41, 0.678);
        padding: 5px;
        border-collapse: separate;
        margin: 8px;
        border-radius: 5px;
        font-weight: bold;
        float: left;
        box-shadow: inset 0 0 10px rgb(0, 0, 0);
        letter-spacing: 1px;
    }

    /* ATOM SPINNER */

      div .atom-spinner {
        margin: auto;
        margin-top: 15%;
    }

</style>
