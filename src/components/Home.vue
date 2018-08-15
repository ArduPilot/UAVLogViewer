<template>
  <div id='vuewrapper' style="height: 100%;">

    <div class="container-fluid" style="height: 100%; overflow: hidden;">

    <div class="nav-side-menu col-md-3 col-lg-2">
      <div class="brand">TLog Viewer</div>
      <i class="fa fa-bars fa-2x toggle-btn" v-b-toggle.menucontent></i>

      <div class="menu-list">

        <b-collapse visible id="menucontent" class="menu-content collapse out">
          <li v-if="filterPlottable.length"  v-b-toggle.products >
            <a class="section" href="#"><i class="fas fa-signature fa-lg"></i> Plot <i class="fas fa-caret-down"></i></a>
          </li>
          <b-collapse  class="sub-menu collapse" id="products">
            <li v-for="item in filterPlottable" :key="'li' + item">
              <a :key="'a' + item" href="#" @click="plot(item)">{{ item }}</a>
            </li>
          </b-collapse>
          <Dropzone ref="dropzone"  v-on:messages="updateData"/>
        </b-collapse>

      </div>
    </div>


      <main role="main" class="col-md-9 ml-sm-auto col-lg-10 flex-column d-sm-flex" style="height: 100%;">
        <div class="row flex-grow-1" >
          <div class="col-12 noPadding">
            <Cesium ref="cesium"
                    v-if="current_trajectory.length"
                    v-on:cesiumhover="updateCursor"
                    v-bind:modes="flight_modes"
                    v-bind:trajectory="current_trajectory"
                    v-bind:attitudes="time_attitude"/>
          </div>
        </div>
        <div v-if="current_data" class="row h-50">
          <div class="col-12 noPadding">
            <Plotly  v-on:attitude="updateAttitude" v-bind:cursor="plot_cursor" v-bind:plot-data="current_data"/>
          </div>
        </div>
      </main>


    </div>
  </div>
</template>

<script>
import Dropzone from './Dropzone'
import Plotly from './Plotly'
import Cesium from './Cesium'

export default {
  name: 'Home',
  data () {
    return {
      messages: {},
      message_types: [],
      current_data: null,
      current_trajectory: [],
      time_trajectory: {},
      time_attitude: {},
      plot_cursor: null,
      flight_modes: []
    }
  },
  methods: {
    updateData () {
      this.messages = this.$refs.dropzone.messages
      this.message_types = Object.keys(this.messages).sort()
      this.time_attitude = this.extractAttitudes(this.messages)
      this.current_trajectory = this.extractTrajectory(this.messages)
      this.flight_modes = this.extractFlightModes(this.messages)
    },
    plot (item) {
      this.current_data = this.messages[item]
    },
    extractTrajectory (messages) {
      let gpsData = messages['GLOBAL_POSITION_INT']
      let trajectory = []
      for (let pos of gpsData) {
        if (pos.lat !== 0) {
          trajectory.push([pos.lon, pos.lat, pos.relative_alt, pos.time_boot_ms])
          this.time_trajectory[pos.time_boot_ms] = [pos.lon, pos.lat, pos.relative_alt, pos.time_boot_ms]
        }
      }
      return trajectory
    },
    extractAttitudes (messages) {
      let attitudeMsgs = messages['ATTITUDE']
      let attitudes = {}
      for (let att of attitudeMsgs) {
        attitudes[att.time_boot_ms] = [att.roll, att.pitch, att.yaw]
      }
      return attitudes
    },
    updateAttitude (time) {
      this.$refs.cesium.showAttitude(time)
    },
    updateCursor (time) {
      this.plot_cursor = time
    },
    extractFlightModes (messages) {
      let modes = [[messages['HEARTBEAT'][0].time_boot_ms, messages['HEARTBEAT'][0].asText]]
      for (let message of messages['HEARTBEAT']) {
        if (message.asText !== modes[modes.length - 1][1]) {
          modes.push([message.time_boot_ms, message.asText])
        }
      }
      return modes
    }
  },
  computed: {
    filterPlottable () {
      return this.message_types.filter(function (message) {
        let valid = [
          'ATTITUDE',
          'GLOBAL_POSITION_INT',
          'GPS_RAW_INT',
          'NAV_CONTROLLER_OUTPUT',
          'SCALED_IMU2',
          'RC_CHANNELS',
          'RC_CHANNELS_RAW',
          'SCALED_PRESSURE']
        return valid.includes(message)
      })
    }
  },
  components: {
    Dropzone,
    Plotly,
    Cesium}
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
  .nav-side-menu {
    overflow-x: hidden;
    overflow-y: auto;
    font-family: verdana;
    font-size: 14px;
    font-weight: 200;
    background-color: #2e353d;
    position: fixed;
    top: 0px;
    /*width: 300px;*/
    height: 100%;
    color: #e1ffff;
  }
  .nav-side-menu .brand {
    background-color: #23282e;
    line-height: 50px;
    display: block;
    text-align: center;
    font-size: 17px;
    font-weight: bold;
  }
  .nav-side-menu .toggle-btn {
    display: none;
  }
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
    .nav-side-menu {
      position: relative;
      width: 100%;
      margin-bottom: 10px;
    }
    .nav-side-menu .toggle-btn {
      display: block;
      cursor: pointer;
      position: absolute;
      right: 10px;
      top: 10px;
      z-index: 10 !important;
      padding: 3px;
      background-color: #ffffff;
      color: #000;
      width: 40px;
      text-align: center;
    }
    .brand {
      text-align: left !important;
      font-size: 22px;
      padding-left: 20px;
      line-height: 50px !important;
    }
  }

  @media (min-width: 767px) {
    .nav-side-menu .menu-list .menu-content {
      display: block;
    }
  }
  body {
    margin: 0px;
    padding: 0px;
  }

  .section {
    font-size: 130%;
    /*font-weight: bold;  */
  }

  i {
    margin:10px;
  }

  i .dropdown{
    float: right;
  }

  ,noPadding {
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
