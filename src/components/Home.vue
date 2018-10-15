<template>
  <div id='vuewrapper' style="height: 100%;">

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
        <div class="row" v-if="state.map_on" v-bind:class="[state.plot_on ? 'h-50' : 'h-100']" >
          <div class="col-12 noPadding">
            <Cesium ref="cesium"
                    v-if="state.current_trajectory.length"/>
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
import {store} from './Globals.js'

function getMinAlt (data) {
    return data.reduce((min, p) => p.Alt < min ? p.Alt : min, data[0].Alt)
}

export default {
    name: 'Home',
    created () {
        this.$eventHub.$on('messages', this.updateData)
        this.state.messages = {}
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
            this.state.time_attitude = this.extractAttitudes(this.state.messages)
            this.state.time_attitudeQ = this.extractAttitudesQ(this.state.messages)
            this.state.current_trajectory = this.extractTrajectory(this.state.messages)
            this.state.flight_mode_changes = this.extractFlightModes(this.state.messages)
            this.state.map_on = true
            this.state.processStatus = 'Processed!'
        },

        extractTrajectory (messages) {
            let trajectory = []

            if ('GLOBAL_POSITION_INT' in messages) {
                let gpsData = messages['GLOBAL_POSITION_INT']
                for (let pos of gpsData) {
                    if (pos.lat !== 0) {
                        trajectory.push([pos.lon, pos.lat, pos.relative_alt, pos.time_boot_ms])
                        this.state.time_trajectory[pos.time_boot_ms] = [pos.lon, pos.lat, pos.relative_alt, pos.time_boot_ms]
                    }
                }
            } else if ('GPS' in messages) {
                let gpsData = messages['GPS']
                let min = getMinAlt(messages['GPS'])
                console.log('min alt: ' + min)
                for (let pos of gpsData) {
                    if (pos.lat !== 0) {
                        trajectory.push([pos.Lng, pos.Lat, pos.Alt - min, pos.time_boot_ms])
                        this.state.time_trajectory[pos.time_boot_ms] = [pos.Lng, pos.Lat, pos.Alt - min, pos.time_boot_ms]
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
            if ('XKQ1' in messages) {
                let attitudeMsgs = messages['XKQ1']
                for (let att of attitudeMsgs) {
                    attitudes[att.time_boot_ms] = [att.Q1, att.Q2, att.Q3, att.Q4]
                }
            }
            return attitudes
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
        }
    },
    components: {
        Sidebar,
        Plotly,
        Cesium}
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

</style>
