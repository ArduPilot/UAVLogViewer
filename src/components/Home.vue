<template>
  <div id='vuewrapper' style="height: 100%;">
      <template v-if="state.map_loading || state.plot_loading">
          <div id="waiting">
              <atom-spinner
                  :animation-duration="1000"
                  :size="300"
                  :color="'#64e9ff'"
              />
          </div>
      </template>
      <TxInputs v-if="state.map_on"></TxInputs>
    <div class="container-fluid" style="height: 100%; overflow: hidden;">

      <sidebar />

      <main role="main" class="col-md-9 ml-sm-auto col-lg-10 flex-column d-sm-flex">

        <div class="row"
             v-if="state.plot_on"
             v-bind:class="[state.map_on ? 'h-50' : 'h-100']">
          <div class="col-12">
            <Plotly />
          </div>
        </div>
        <div class="row" v-if="state.map_on && map_ok" v-bind:class="[state.plot_on ? 'h-50' : 'h-100']" >
          <div class="col-12 noPadding">
            <Cesium ref="cesium"/>
          </div>
        </div>
      </main>

    </div>
  </div>
</template>

<script>
import Plotly from './Plotly'
import Cesium from './Cesium'
import Sidebar from './Sidebar'
import TxInputs from './widgets/TxInputs'
import {store} from './Globals.js'
import {AtomSpinner} from 'epic-spinners'

import {ParamSeeker} from '../tools/paramseeker'

export default {
    name: 'Home',
    created () {
        this.$eventHub.$on('messages', this.updateData)
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
        updateData () {
            console.log('updatedata')
            if (Object.keys(this.state.time_attitude).length === 0) {
                this.state.time_attitude = this.extractAttitudes(this.state.messages)
            }
            if (Object.keys(this.state.time_attitudeQ).length === 0) {
                this.state.time_attitudeQ = this.extractAttitudesQ(this.state.messages)
            }
            if (this.state.current_trajectory.length === 0) {
                this.state.current_trajectory = this.extractTrajectory(this.state.messages)
            }
            this.state.flight_mode_changes = this.extractFlightModes(this.state.messages)
            this.state.mission = this.extractMission(this.state.messages)
            this.state.vehicle = this.extractVehicleType(this.state.messages)
            this.state.params = this.extractParams(this.state.messages)
            this.state.processStatus = 'Processed!'
            this.state.map_on = true
        },

        extractParams (messages) {
            let params = []
            if ('PARM' in messages) {
                let paramData = messages['PARM']
                for (let data of paramData) {
                    params.push([data.time_boot_ms, data.Name, data.Value])
                }
            }
            if (params.length > 0) {
                return new ParamSeeker(params)
            } else {
                return undefined
            }
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
                        this.state.time_trajectory[pos.time_boot_ms] = [pos.lon, pos.lat, pos.relative_alt, pos.time_boot_ms]
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
                        this.state.time_trajectory[pos.time_boot_ms] = [pos.Lng, pos.Lat, pos.Alt - startAltitude, pos.time_boot_ms]
                    }
                }
            }
            return trajectory
        },
        extractAttitudes (messages) {
            let attitudes = {}
            if ('ATTITUDE' in messages) {
                let attitudeMsgs = messages['ATTITUDE']
                for (let att of attitudeMsgs) {
                    attitudes[att.time_boot_ms] = [att.roll, att.pitch, att.yaw]
                }
            } else if ('AHR2' in messages) {
                let attitudeMsgs = messages['AHR2']
                for (let att of attitudeMsgs) {
                    attitudes[att.time_boot_ms] = [att.Roll, att.Pitch, att.Yaw]
                }
            } else if ('ATT' in messages) {
                let attitudeMsgs = messages['ATT']
                for (let att of attitudeMsgs) {
                    attitudes[att.time_boot_ms] = [att.Roll, att.Pitch, att.Yaw]
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
            let modes
            if ('HEARTBEAT' in messages) {
                modes = [[messages['HEARTBEAT'][0].time_boot_ms, messages['HEARTBEAT'][0].asText]]
                for (let message of messages['HEARTBEAT']) {
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
                        wps.push([cmd.Lng, cmd.Lat, cmd.Alt])
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
                    if (msg.Message.indexOf('Rover') > -1) {
                        return 'rover'
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
        }
    },
    components: {
        Sidebar,
        Plotly,
        Cesium,
        AtomSpinner,
        TxInputs
    },
    computed: {
        map_ok () {
            return (this.state.flight_mode_changes !== undefined &&
            this.state.current_trajectory !== undefined &&
            this.state.current_trajectory.length > 0 &&
                (Object.keys(this.state.time_attitude).length > 0 || Object.keys(this.state.time_attitudeQ).length > 0))
        }
    }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
  .nav-side-menu ul,
  .nav-side-menu li {
    list-style: none;
    padding: 0px;
    margin: 0px;
    line-height: 35px;
    cursor: pointer;
    /*
      .collapsed{
         .arrow:before{
                   font-family: FontAwesome;
                   content: "\f053";
                   display: inline-block;
                   padding-left:10px;
                   padding-right: 10px;
                   vertical-align: middle;
                   float:right;
              }
       }
  */
  }
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
  .nav-side-menu ul .active,
  .nav-side-menu li .active {
    border-left: 3px solid #d19b3d;
    background-color: #4f5b69;
  }
  .nav-side-menu ul .sub-menu li.active,
  .nav-side-menu li .sub-menu li.active {
    color: #d19b3d;
  }
  .nav-side-menu ul .sub-menu li.active a,
  .nav-side-menu li .sub-menu li.active a {
    color: #d19b3d;
  }
  .nav-side-menu ul .sub-menu li,
  .nav-side-menu li .sub-menu li {
    background-color: #181c20;
    border: none;
    line-height: 28px;
    border-bottom: 1px solid #23282e;
    margin-left: 0px;
  }
  .nav-side-menu ul .sub-menu li:hover,
  .nav-side-menu li .sub-menu li:hover {
    background-color: #020203;
  }
  .nav-side-menu ul .sub-menu li:before,
  .nav-side-menu li .sub-menu li:before {
    font-family: FontAwesome;
    content: "\f105";
    display: inline-block;
    padding-left: 10px;
    padding-right: 10px;
    vertical-align: middle;
  }
  .nav-side-menu li {
    padding-left: 0px;
    border-left: 3px solid #2e353d;
    border-bottom: 1px solid #23282e;
  }
  .nav-side-menu li a {
    text-decoration: none;
    color: #e1ffff;
  }
  .nav-side-menu li a i {
    padding-left: 10px;
    width: 20px;
    padding-right: 20px;
  }
  .nav-side-menu li:hover {
    border-left: 3px solid #d19b3d;
    background-color: #4f5b69;
    -webkit-transition: all 1s ease;
    -moz-transition: all 1s ease;
    -o-transition: all 1s ease;
    -ms-transition: all 1s ease;
    transition: all 1s ease;
  }
  @media (max-width: 767px) {
    main {
      height: 90%;
      margin-top: 50px;
    }
  }

  @media (min-width: 767px) {
    main {
      height: 100%;
    }
  }
  body {
    margin: 0px;
    padding: 0px;
  }

  div .col-12 {
      padding-left: 0;
      padding-right: 0;
  }

  i {
    margin:10px;
  }

  i .dropdown{
    float: right;
  }

  .container-fluid {
    padding-left: 0;
    padding-right: 0;
  }

  .noPadding {
    padding-left: 4px;
    padding-right: 6px;
   }
  ::-webkit-scrollbar {
    width: 12px;
    background-color: rgba(0,0,0,0); }

  ::-webkit-scrollbar-thumb {
    border-radius: 5px;
    -webkit-box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.1);
    background-color: #1c437f; }

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

    div .atom-spinner {
        margin: auto;
        margin-top: 15%;
    }

</style>
