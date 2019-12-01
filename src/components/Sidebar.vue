<template>
<!-- HEADER -->
    <div class="nav-side-menu col-sm-4 col-md-3 col-lg-2" :class="mode" @toggle="toggle">
        <h1 class="brand"> <b>TLog</b>viewer<i class="fas fa-plane"></i></h1>
        <!-- TABHOLDER -->
        <i class="fa fa-bars fa-2x toggle-btn" v-b-toggle.menucontent></i>
        <b-collapse class="menu-content collapse out" id="menucontent" visible>
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
        </b-collapse>
        <!-- TOGGLE MENU -->
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
                        <label><input type="checkbox" v-model="state.showWaypoints">
                        Waypoints <i class="fa fa-map-marker"></i> </label>
                        <label><input type="checkbox" v-model="state.showTrajectory">
                        Trajectory <i class="fa fa-map" aria-hidden="true"></i> </label>
                    </div>
                    <div v-if="state.processDone">
                        <label v-if="state.params"><input type="checkbox" v-model="state.show_params"> Show
                            Parameters <i class="fa fa-cogs"></i> </label>
                        <label><input type="checkbox" v-model="state.show_radio">
                        Show Radio Sticks <i class="fa fa-gamepad"></i> </label>
                        <label v-if="state.textMessages"><input type="checkbox" v-model="state.show_messages"> Show
                            Messages <i class="fa fa-comment"></i> </label>
                    </div>
                    <!-- WINGSPAN -->
                    <div>
                        <label><i class="fa fa-fighter-jet" aria-hidden="true"></i> Wingspan (m)
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

a.section {
    margin-left: 8px;
}

/* NAV SIDE MENU */

    .nav-side-menu {
        overflow-x: hidden;
        padding: 0;
        background-color: #2e2e2e;
        position: fixed !important;
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
        background-color: #5c5b5a48;
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
        border-radius: 0px;
        box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.1);
        -webkit-box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.1);
        -moz-box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.1);
        background-color: #ac4e0f;
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
        margin-bottom: 0;
        background: rgb(94,94,93);
        background: linear-gradient(90deg, rgba(94,94,93,1) 20%, rgba(66, 65, 65, 0.856) 100%);
        color: #eeeeee;
        display: block;
    }

    /* TABHOLDER */

    .tabholder {
        display: flex;
        flex-flow: row wrap;
        justify-content: space-evenly;
        overflow: hidden;
        padding: 12px 0px 12px 0px;
        cursor: pointer;
    }

    .tabholder a {
        background:rgba(59, 59, 59, 0.829);
        float: left;
        padding: 2px 10px 2px 5px;
        border-radius: 15px 0px 15px 0px;
    }

    a.selected {
        color: #fff !important;
        background: rgb(150,150,150);
        background: linear-gradient(0deg, rgba(150, 150, 150, 0.808) 15%, rgba(63, 63, 63, 0.829) 100%);
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
        font-size: 12px;
        display: block;
        position: fixed;
        margin-left: 95px;
        bottom: 0; 
        text-decoration: none;
        padding: 6px;
        border: none;
        border-radius: 8px 8px 0px 0px;
        background-color: #58585856;
        background: linear-gradient(0deg, rgba(150, 150, 150, 0.486) 15%, rgba(63, 63, 63, 0.473) 100%);
        color: #fff;
    }

    .light-mode-button:hover {
        background-color: #686868;
    }

    .light {
        background: rgb(231, 231, 231);
        color: rgb(148, 147, 147);
    }

    .dark {
        background-color: #2e2e2e;
    }
    /* MEDIA QUERIES */

    /* MAX */
    
    @media only screen and (max-width: 768px) {
        .nav-side-menu {
            position: fixed !important;
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
            margin-top: 45px;
        }

        .col-sm-4 {
            max-width: 100%;
        }

        .col-lg-10 {
            max-width: 100%;
            height: 93%;
        }

        .light-mode-button {
            display: none;
        }
    }
    
    /* MIN */

    @media (min-width: 769px) {
        .nav-side-menu .menu-list .menu-content {
            display: block;
            height: 100%;
        }

        main {
            height: 100%;
        }

    }

    @media only screen and (min-width: 996px) {
        .nav-side-menu {
            max-width: 20% !important;
        }

        .col-lg-10 {
            max-width: 80% !important;
        }

         .light-mode-button {
            margin-left: 7%;
            display: block;
            position: fixed;
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
