<template>
<!-- HEADER -->
    <div class="nav-side-menu col-lg-2">

        <h1 class="brand">
            <a class="github" href="https://github.com/williangalvani/tlogviewer">
            <img :src="require('../assets/GitHub-Mark-64px.png')"/>
            </a>
            <a href="/"><b>TLog</b>viewer<i class="fas fa-plane"></i></a></h1>
        <!-- TABHOLDER -->
        <i class="fa fa-bars fa-2x toggle-btn" v-b-toggle.menucontent></i>
        <b-collapse class="menu-content collapse out" id="menucontent" visible>
            <div class="tabholder">
                <!-- Home -->
                <a :class="selected === 'home' ? 'selected' : ''" @click="selected='home'" v-if="!state.processDone">
                <i class="fas fa-home"></i>Home</a>
                <!-- Plot -->
                <a :class="selected === 'plot' ? 'selected' : ''" @click="selected='plot'"
                   v-if="state.processDone"> <i class="fas fa-chart-line"></i>Plot</a>
                <!-- 3D -->
                <a :class="selected ==='3d' ? 'selected' : ''" @click="selected='3d'"
                   v-if="state.map_available && state.show_map">  <i class="fas fa-cube"></i> 3D </a>
                <a :class="selected ==='3d' ? 'selected' : ''" @click="state.show_map=trueselected='3d'"
                   v-if="state.map_available && !state.show_map">3D</a>
                <!-- more -->
                <a :class="selected ==='other' ? 'selected' : ''" @click="selected='other'" v-if="state.processDone">
                    <i class="fas fa-ellipsis-v"></i>
                </a>
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
                    <span class="buildinfo">Commit {{state.commit}}</span>
                    <span class="buildinfo">Built {{state.buildDate}}</span>
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
                    <!-- WINGSPAN -->
                    <div>
                        <label><i class="fa fa-fighter-jet" aria-hidden="true"></i> Wingspan (m)
                            <input max="15" min="0.1" step="0.01" type="range"
                            class="custom-range" v-model="state.modelScale">
                            <input class="wingspan-text" size="5" type="text" v-model="state.modelScale">
                        </label>
                    </div>
                    <!-- Trajectory Source -->
                    <div>
                        <label><i class="fas fa-map"></i> Trajectory Source</label>
                        <select class="cesium-button" v-model="state.trajectorySource">
                            <!-- eslint-disable-next-line vue/no-v-html vue/no-unused-vars -->
                            <option v-for="(item, key) in state.trajectories" :key="key">
                                {{key}}
                            </option>
                        </select>
                    </div>
                </div>
                <div v-if="selected==='other'">
                    <!-- PARAM/MESSAGES/RADIO -->
                    <hr>
                    <a class="centered-section"> Show / hide </a>
                    <div v-if="state.processDone" class="show-hide">
                        <label v-if="state.params">
                          <i class="fa fa-cogs circle"></i>
                          <input type="checkbox" v-model="state.show_params">
                          <a class="check-font"> Parameters </a>
                        </label>
                        <label>
                          <i class="fa fa-gamepad circle"></i>
                          <input type="checkbox" v-model="state.show_radio">
                          <a class="check-font"> Radio Sticks </a>
                        </label>
                        <label v-if="state.textMessages">
                          <i class="fa fa-comment circle"></i>
                          <input type="checkbox" v-model="state.show_messages">
                          <a class="check-font"> Messages </a>
                        </label>
                    </div>
                </div>
            </b-collapse>
        </div>
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
            state: store
        }
    },
    methods: {
        setSelected (selected) {
            this.selected = selected
        }

    },
    created () {
        this.$eventHub.$on('set-selected', this.setSelected)
    },
    components: {PlotSetup, MessageMenu, Dropzone}
}
</script>
<style>

span.buildinfo {
    font-size: 70%;
    margin-left: 30px;
    display: block;
    opacity: 50%;
}

a.section {
    margin-left: 6px;
}

a.centered-section {
    text-align: center;
    display: block;
}

.col-lg-2 {
    padding: 0 !important;
}
/* NAV SIDE MENU */

    .nav-side-menu {
        overflow-x: hidden;
        padding: 0;
        background-color: rgb(29, 36, 52);
        background: linear-gradient(0deg, rgb(20, 25, 36) 51%, rgb(37, 47, 71) 100%);
        position: fixed !important;
        top: 0px;
        height: 100%;
        color: rgb(255, 255, 255);
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

    .nav-side-menu li a i {
        padding-left: 0;
        width: 20px;
        padding-right: 20px;
    }

    .nav-side-menu li:hover {
        border-left: 3px solid #01204191;
        background-color: rgba(52, 70, 100, 0.336);
        -webkit-transition: all 1s ease;
        -moz-transition: all 1s ease;
        -o-transition: all 1s ease;
        -ms-transition: all 1s ease;
        transition: all 1s ease;
    }

    i {
        margin: 10px;
    }

    /* SHOW / HIDE */

    .show-hide {
        text-align: center;
    }

    .circle {
        cursor: pointer;
        display: block;
        margin-left: 8px;
        background-color: rgba(47, 60, 83, 0.63);
        width: 52px;
        height: 52px;
        padding: 17px;
        border-radius: 50px;
    }

    .circle:hover {
        background-color: rgba(58, 71, 94, 0.63);
         box-shadow: 0px 0px 12px 0px rgba(24, 106, 173, 0.281);
    }

    .show-hide input[type=checkbox] {
        display: none;
        visibility: hidden;
    }

    .check-font {
        padding: 0 !important;
        font-size: 13px;
        color: rgb(146, 143, 143);
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
        background: rgb(30,37,53);
        background: linear-gradient(0deg, rgb(28, 42, 73) 51%, rgb(39, 51, 78) 100%);
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
        padding-left: 0px;
        line-height: 50px;
        margin-bottom: 0;
        color: rgb(54, 72, 114) !important;
        background-color: rgba(248, 248, 248, 0.918);
        display: block;
    }

    .brand a {
        text-decoration: none;
        color: rgb(54, 72, 114) !important;
    }

    .github img {
        float: left;
        max-height: 30px;
        margin-left: 8px;
        margin-top: 10px;
    }

    a:hover {
        text-decoration: none !important;
    }

    /* TABHOLDER */

    .tabholder {
        display: flex;
        flex-flow: row wrap;
        justify-content: space-evenly;
        overflow: hidden;
        padding: 12px 0px 12px 0px;
        cursor: pointer;
        font-size: 16px;
    }

    .tabholder a {
        background: rgb(41,51,75);
        float: left;
        padding: 2px 12px 2px 5px;
        border: 1px solid rgba(91, 100, 117, 0.76);
        border-radius: 30px;
    }

    a.selected {
        color: rgb(247, 248, 248) !important;
        box-shadow: 0px 0px 12px 0px rgba(125,125,125,0.55);
    }

    .tabholder a:hover {
        box-shadow: 0px 0px 12px 0px rgba(125,125,125,0.55);
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

    /* MEDIA QUERIES */

    @media (min-width: 575px) and (max-width: 992px) {
       a {
        padding: 2px 60px 2px 55px !important;
       }
    }
    
    @media only screen and (max-width: 992px) {
        .nav-side-menu {
            position: fixed;
            width: 100%;
            height: auto;
            max-height: 100%;
            z-index: 1002;
        }

        .nav-side-menu .toggle-btn {
            display: block;
            cursor: pointer;
            position: absolute;
            right: 10px;
            margin: 0;
            top: 5px;
            z-index: 10 !important;
            padding: 3px;
            background-color: rgba(248, 248, 248, 0.769);
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

        .col-lg-10 {
            max-width: 100%;
            height: 93%;
        }

        .col-md-9 {
            max-width: 100% !important;
        }
    }
    
    /* MIN */

    @media only screen and (min-width: 991px) and (max-width: 1439px) {
        .nav-side-menu {
            max-width: 27% !important;
        }

        .col-lg-10 {
            max-width: 73% !important;
        }

        main {
            height: 100%;
        }
    }

    @media only screen and (min-width: 1440px) and (max-width: 2000px) {
        .nav-side-menu {
        max-width: 20% !important;  
        }

        main {
            height: 100%;
        }

        .col-lg-10 {
            max-width: 80% !important;
        }
    }

    @media only screen and (min-width: 2000px) {
        .nav-side-menu {
            max-width: 15% !important;
        }
        
        main {
            height: 100%;
        }

        .col-lg-10 {
            max-width: 85% !important;
        }
    }
</style>
