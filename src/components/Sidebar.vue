<template>
    <div class="nav-side-menu col-sm-4 col-md-3 col-lg-2">
        <div class="brand">TLog Viewer</div>
        <ul>
            <div class="tabholder">
                <a :class="selected==='home' ? 'selected' : ''" @click="selected='home'">HOME</a>
                <a :class="selected==='plot' ? 'selected' : ''" @click="selected='plot'"
                   v-if="state.processDone">PLOT</a>
                <a :class="selected==='3d' ? 'selected' : ''" @click="selected='3d'"
                   v-if="state.map_available && state.show_map">3D</a>
                <a :class="selected==='3d' ? 'selected' : ''" @click="state.show_map=trueselected='3d'"
                   v-if="state.map_available && !state.show_map">3D</a>
            </div>
        </ul>
        <i class="fa fa-bars fa-2x toggle-btn" v-b-toggle.menucontent></i>
        <div class="menu-list">
            <b-collapse class="menu-content collapse out" id="menucontent" visible>

                <div :style="{display: selected==='plot' ? '' : 'none' }">
                    <plotSetup/>
                    <message-menu/>
                </div>
                <div v-if="selected==='home'">
                    <Dropzone/>
                </div>
                <div v-if="selected==='3d' && state.map_available">
                    <!--<li v-if="!state.map_available" @click="state.map_available=true">-->
                    <!--<a class="section">-->
                    <!--<i class="fas fa-eye fa-lg"></i> Show 3D View</a>-->
                    <!--</li>-->
                    <!--<li v-if="state.map_available" @click="state.map_available=false">-->
                    <!--<a class="section">-->
                    <!--<i class="fas fa-eye-slash fa-lg"></i> Hide 3D View</a>-->
                    <!--</li>-->
                    <div>
                        <label>Camera</label>
                        <select class="cesium-button" v-model="state.cameraType">
                            <option value="free">Free</option>
                            <option value="follow">Follow</option>
                        </select>
                    </div>
                    <div>
                        <label><input type="checkbox" v-model="state.showWaypoints">Waypoints</label>
                        <label><input type="checkbox" v-model="state.showTrajectory">Trajectory</label>
                    </div>
                    <div v-if="state.processDone">
                        <label v-if="state.params"><input type="checkbox" v-model="state.show_params">Show
                            Parameters</label>
                        <label><input type="checkbox" v-model="state.show_radio">Show Radio Sticks</label>
                        <label v-if="state.textMessages"><input type="checkbox" v-model="state.show_messages">Show
                            Messages</label>
                    </div>
                    <div>
                        <label>Wingspan (m)
                            <input max="15" min="0.1" step="0.01" type="range" v-model="state.modelScale">
                            <input size="5" type="text" v-model="state.modelScale">
                        </label>
                    </div>
                </div>
            </b-collapse>
        </div>
    </div>
</template>
<script>
import Dropzone from './SideBarFileManager'
import MessageMenu from './SideBarMessageMenu'
import {store} from './Globals.js'
import PlotSetup from './PlotSetup'

export default {
    name: 'sidebar',
    data () {
        return {
            selected: 'home',
            state: store
        }
    },
    components: {PlotSetup, MessageMenu, Dropzone}
}
</script>
<style>
    .nav-side-menu {
        overflow-x: hidden;
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
        padding-left: 0;
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
            position: fixed;
            width: 100%;
            margin-bottom: 10px;
            height: auto;
            max-height: 100%;
            z-index: 1002;
        }

        .nav-side-menu .toggle-btn {
            display: block;
            cursor: pointer;
            position: absolute;
            right: 10px;
            top: 0px;
            z-index: 10 !important;
            padding: 3px;
            background-color: #ffffff;
            color: #000;
            height: auto;
            width: 40px;
            text-align: center;
            -webkit-border-radius: 3px;
            -moz-border-radius: 3px;
            border-radius: 3px;
        }

        .brand {
            text-align: left !important;
            font-size: 22px;
            padding-left: 20px;
            line-height: 50px !important;
        }

        main {
            height: 90%;
            margin-top: 50px;
        }
    }

    @media (min-width: 767px) {
        .nav-side-menu .menu-list .menu-content {
            display: block;
            height: 100%;
        }

        main {
            height: 100%;
        }
    }

    i {
        margin: 10px;
    }

    ::-webkit-scrollbar {
        width: 12px;
        background-color: rgba(0, 0, 0, 0);
    }

    ::-webkit-scrollbar-thumb {
        border-radius: 5px;
        box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.1);
        -webkit-box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.1);
        -moz-box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.1);
        background-color: #1c437f;
    }

    .custom-control-inline {
        margin-right: 0;
    }

    .tabholder {
        display: flex;
        justify-content: space-between;
        padding-left: 20px !important;
        padding-right: 20px !important;
        border-bottom: 1px solid white;
    }

    .tabholder a {
        border-top: 1px solid white;
        border-left: 1px solid white;
        border-right: 1px solid white;
        border-radius: 3px;
        padding-left: 5px;
        padding-right: 5px;
        font-weight: bold;
        background-color: #2E353D;
    }

    a.selected {
        margin-bottom: -1px;
    }

    .tabholder a:hover {
        background-color: #4f5b69;
        -webkit-transition: all 1s ease;
        -moz-transition: all 1s ease;
        -o-transition: all 1s ease;
        -ms-transition: all 1s ease;
        transition: all 1s ease;
    }

    label {
        display: block;
    }
</style>
