<template>
<!-- HEADER -->
    <div class="nav-side-menu col-sm-4 col-md-3 col-lg-2" :class="mode" @toggle="toggle">
        <h1 class="brand"> <b>TLog</b>viewer<i class="fas fa-plane"></i></h1>
        <!-- TABHOLDER -->
        <ul>
            <div class="tabholder">
                <!-- Home -->
                <a :class="selected === 'home' ? 'selected' : ''" @click="selected='home'">
                <i class="fas fa-home"></i> Home </a>
                <!-- Plot -->
                <a :class="selected === 'plot' ? 'selected' : ''" @click="selected='plot'"
                   v-if="state.processDone"> <i class="fas fa-pen"></i> Plot </a>
                <!-- 3D -->
                <a :class="selected ==='3d' ? 'selected' : ''" @click="selected='3d'"
                   v-if="state.map_available && state.show_map">  <i class="fas fa-cube"></i> 3D </a>
                <a :class="selected ==='3d' ? 'selected' : ''" @click="state.show_map=trueselected='3d'"
                   v-if="state.map_available && !state.show_map">3D</a>
            </div>
        </ul>
        <!-- TOGGLE MENU -->
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

                    <!-- CAMERA -->
                    <div>
                        <label><i class="fas fa-camera"></i> Camera</label>
                        <select class="cesium-button" v-model="state.cameraType">
                            <option value="free">Free</option>
                            <option value="follow">Follow</option>
                        </select>
                    </div>
                    <!-- CHECKBOXES -->
                    <div>
                        <label><input type="checkbox" v-model="state.showWaypoints"> Waypoints</label>
                        <label><input type="checkbox" v-model="state.showTrajectory"> Trajectory</label>
                    </div>
                    <div v-if="state.processDone">
                        <label v-if="state.params"><input type="checkbox" v-model="state.show_params"> Show
                            Parameters</label>
                        <label><input type="checkbox" v-model="state.show_radio"> Show Radio Sticks</label>
                        <label v-if="state.textMessages"><input type="checkbox" v-model="state.show_messages"> Show
                            Messages</label>
                    </div>
                    <!-- WINGSPAN -->
                    <div>
                        <label><i class="fa fa-fighter-jet"></i> Wingspan (m)
                            <input max="15" min="0.1" step="0.01" type="range"
                            class="custom-range" v-model="state.modelScale">
                            <input class="wingspan-text" size="5" type="text" v-model="state.modelScale">
                        </label>
                    </div>
                </div>
            </b-collapse>
        </div>
        <button class="light-mode-button"> Dark Mode
            <input type="checkbox"
            :checked="(mode === 'dark') ? 'checked' : false"
            @change="toggle"
            />
        </button>
    </div>
</template>
<script>
/* eslint-disable */
import Dropzone from './SideBarFileManager'
import MessageMenu from './SideBarMessageMenu'
import {store} from './Globals.js'
import PlotSetup from './PlotSetup'

export default {
    name: 'sidebar',
    data () {
        return {
            selected: 'home',
            state: store,
            mode: 'dark'
        }
    },
    components: {PlotSetup, MessageMenu, Dropzone},
    methods: {
        toggle () {
      if (this.mode === "dark") {
        this.mode = "light"
      } else {
        this.mode = "dark"
      }
        }
    }
}
</script>
<style>

/* NAV SIDE MENU */

    .nav-side-menu {
        overflow-x: hidden;
        padding: 0;
        background-color: #2e2e2e;
        position: fixed;
        top: 0px;
        height: 100%;
        color: #ffff;
    }
    .nav-side-menu .toggle-btn {
        display: none;
    }

    /* UL/LI */

    .nav-side-menu ul,
    .nav-side-menu li {
        list-style: none;
        padding: 0px;
        margin: 0px;
        line-height: 35px;
        cursor: pointer;
    }

    .nav-side-menu ul .sub-menu li.active a,
    .nav-side-menu li .sub-menu li.active a {
        color: #cc8812;
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
        background-color: #555d66;
        -webkit-transition: all 1s ease;
        -moz-transition: all 1s ease;
        -o-transition: all 1s ease;
        -ms-transition: all 1s ease;
        transition: all 1s ease;
    }

    i {
        margin: 10px;
    }

    /* SCROLLBAR */

    ::-webkit-scrollbar {
        width: 12px;
        background-color: rgba(0, 0, 0, 0);
    }

    ::-webkit-scrollbar-thumb {
        border-radius: 5px;
        box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.1);
        -webkit-box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.1);
        -moz-box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.1);
        background-color: #864920;
    }

    .custom-control-inline {
        margin-right: 0;
    }

    /* BRAND */

    .fa-plane {
        margin: 8px;
        font-size: 18px;
    }
         
    .brand {
        text-align: center;
        font-size: 22px;
        padding-left: 20px;
        line-height: 50px;
        background-color: #585858;
        color: #eeeeee;
        display: block;
    }

    /* TABHOLDER */

    .tabholder {
        display: flex;
        flex-flow: row wrap;
        justify-content: space-evenly;
        overflow: hidden;
        padding-bottom: 10px;
    }

    .tabholder a {
        float: left;
        padding: 2px 10px 2px 5px;
    }

    a.selected {
        background-color: #818181;
        color: #fff !important;
    }

    .tabholder a:hover {
        background-color: #686868;
        -webkit-transition: all 1s ease;
        -moz-transition: all 1s ease;
        -o-transition: all 1s ease;
        transition: all 1s ease;
    }

    /* LABELS */

    label {
        display: block;
        padding: 6px;
    }

    .wingspan-text {
        width: 20%;
        border: none;
        border-radius: 3px;
        background-color: rgb(175, 177, 175);
    }

    /* LIGHT MODE */

    .light-mode-button {
        position: absolute; 
        left: 0 ; right: 0; bottom: 0; 
        text-decoration: none;
        padding: 5px;
        margin: 0 auto;
        border: none;
        background-color: #585858;
        color: #fff;
        display: none;
    }

    .light-mode-button:hover {
        background-color: #686868;
    }

    .light {
        background: rgb(241, 241, 241);
        color: rgb(230, 103, 0);
    }

    .dark {
        background-color: #2e2e2e;
    }
    /* MEDIA QUERIES */

    /* MAX */
    
    @media only screen and (max-width: 768px) {
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
            background-color: #ffffffde;
            color: rgb(58, 58, 58);
            height: auto;
            width: 40px;
            text-align: center;
            -webkit-border-radius: 2px;
            -moz-border-radius: 2px;
            border-radius: 2px;
        }

          main {
            margin-top: 110px;
        }

        .col-sm-4 {
            max-width: 100%;
        }

        .col-lg-10 {
            max-width: 100%;
            height: 85%;
        }
    }
    
    /* MIN */

    @media (min-width: 767px) {
        .nav-side-menu .menu-list .menu-content {
            display: block;
            height: 100%;
        }

        main {
            height: 100%;
        }

        .light-mode-button {
            display: block;
        }
    }

    @media only screen and (min-width: 996px) {
        .nav-side-menu {
            max-width: 20%;
        }

        .col-lg-10 {
            max-width: 80%;
        }
    }

    @media only screen and (min-width: 2000px) {
        .nav-side-menu {
        max-width: 11%;  
        }

        .col-lg-10 {
            max-width: 89.2%;
        }
    }
</style>
