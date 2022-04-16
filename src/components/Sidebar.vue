<template>
<!-- HEADER -->
    <div class="nav-side-menu col-lg-2">

        <h1 class="brand">
            <a class="github" href="https://github.com/ardupilot/uavlogviewer">
            <img :src="require('../assets/GitHub-Mark-64px.png')"/>
            </a>
            <a href="/"><b>UAV</b> Log Viewer<i class="fas fa-plane"></i></a><a class="github" href="https://ardupilot.org/copter/docs/common-uavlogviewer.html"><img :src="require('../assets/wiki.svg')"/></a></h1>
        <!-- TABHOLDER -->
        <i class="fa fa-bars fa-2x toggle-btn" v-b-toggle.menucontent></i>
        <b-collapse class="menu-content collapse out" id="menucontent" visible>
            <span v-if="state.file" class="filename">Current file: {{state.file}}</span>
            <div class="tabholder">
                <!-- Home -->
                <a :class="selected === 'home' ? 'selected' : ''" @click="selected='home'" v-if="!state.processDone">
                <i class="fas fa-home"></i>Home</a>
                <!-- Plot -->
                <a :class="selected === 'plot' ? 'selected' : ''" @click="selected='plot'"
                   v-if="state.processDone"> <i class="fas fa-chart-line"></i>Plot</a>
                <!-- 3D -->
                <a :class="selected ==='3d' ? 'selected' : ''" @click="selected='3d'"
                   v-if="state.mapAvailable && state.showMap">  <i class="fas fa-cube"></i> 3D </a>
                <a :class="selected ==='3d' ? 'selected' : ''" @click="state.showMap=trueselected='3d'"
                   v-if="state.mapAvailable && !state.showMap">3D</a>
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
                <div v-if="selected==='3d' && state.mapAvailable">
                    <!--<li v-if="!state.mapAvailable" @click="state.mapAvailable=true">-->
                    <!--<a class="section">-->
                    <!--<i class="fas fa-eye fa-lg"></i> Show 3D View</a>-->
                    <!--</li>-->
                    <!--<li v-if="state.mapAvailable" @click="state.mapAvailable=false">-->
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
                    <!-- ALTITUDE OFFSET -->
                    <div>
                        <label><i class="fa fa-arrows-v" aria-hidden="true"></i> Altitude Offset (m)
                            <input max="3000" min="-1000" step="0.01" type="range"
                            class="custom-range" v-model="state.heightOffset">
                            <input class="wingspan-text" size="5" type="number" v-model="state.heightOffset">
                        </label>
                    </div>
                    <!-- Trajectory Source -->
                    <div>
                        <label><i class="fas fa-map"></i> Trajectory Source</label>
                        <select class="cesium-button" v-model="state.trajectorySource">
                            <!-- eslint-disable-next-line vue/no-v-html vue/no-unused-vars -->
                            <option v-for="item in state.trajectorySources" :key="item">
                                {{item}}
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
                          <input type="checkbox" v-model="state.showParams">
                          <a class="check-font"> Parameters </a>
                        </label>
                        <label>
                          <i class="fa fa-gamepad circle"></i>
                          <input type="checkbox" v-model="state.showRadio">
                          <a class="check-font"> Radio Sticks </a>
                        </label>
                        <label v-if="state.textMessages">
                          <i class="fa fa-comment circle"></i>
                          <input type="checkbox" v-model="state.showMessages">
                          <a class="check-font"> Messages </a>
                        </label>
                        <label>
                          <i class="fa fa-plane-departure circle"></i>
                          <input type="checkbox" v-model="state.showAttitude">
                          <a class="check-font"> Attitude </a>
                        </label>
                        <label v-if="!recording" v-on:click="startCapture">
                            <i class="fa fa-play circle"></i>
                            <a class="check-font"> Record </a>
                        </label>
                        <label v-if="recording" v-on:click="stopCapture">
                            <i class="fa fa-stop circle"></i>
                            <a class="check-font"> End Rec </a>
                        </label>
                        <label  v-if="this.chunks" v-on:click="download">
                            <i class="fa fa-download circle"></i>
                            <a class="check-font download-text" v-bind:href="downloadURL"
                               v-bind:download="fileName" ref="downloadFile"> Download </a>
                        </label>
                        <label v-if="state.logType==='tlog'" v-on:click="downloadTrimmed">
                            <i
                            class="fa fa-download circle"
                            title="Download a log with starting and end time matching the current views">
                            </i>
                            <a class="check-font"> Trimmed log </a>
                        </label>
                        <label>
                            <i
                            class="fa fa-microchip circle"
                            title="Show a widget with the detected sensors">
                            </i>
                            <input type="checkbox" v-model="state.showDeviceIDs">
                            <a class="check-font">  Sensors </a>
                        </label>
                    </div>
                    <div v-if="state.files" class="show-hide">
                        <ul class="files-list">
                        <span class="files-header">Files:</span>
                        <li
                            v-for="filename in Object.keys(state.files)"
                            :key="filename"
                            href="#"
                            @click="downloadFile(filename)"
                        >
                                <i class="fa fa-file-download"></i>
                            {{ filename }}
                        </li>
                        </ul>
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
            state: store,
            chunks: false,
            blob: null,
            recording: false,
            recorder: null,
            stream: null,
            downloadURL: '',
            fileName: 'video.mp4'
        }
    },
    methods: {
        setSelected (selected) {
            this.selected = selected
        },

        startCapture (displayMediaOptions) {
            navigator.mediaDevices.getDisplayMedia({video: { mediaSource: 'screen' }})
                .then((stream) => {
                    this.record(stream)
                })
                .catch(err => { console.error('Error:' + err); return null })
        },

        stopCapture () {
            this.recorder.stop()
            this.stream.getTracks().forEach(track => track.stop())

        },

        record (stream) {
            const recorder = new MediaRecorder(stream)
            const chunks = []
            recorder.ondataavailable = e => chunks.push(e.data)

            this.stream = stream
            this.recorder = recorder
            this.recorder.start()

            this.recording = true

            recorder.onstop = e => {
                const completeBlob = new Blob(chunks, { type: chunks[0].type })
                this.chunks = true
                this.blob = completeBlob
                this.recording = false
            }
        },

        download () {
            this.$refs.downloadFile.click()
        },
        downloadTrimmed () {
            this.$eventHub.$emit('trimFile')
        },

        createDownloadURL (data, fileName) {
            const a = document.createElement('a')
            a.href = data
            a.download = fileName
            document.body.appendChild(a)
            a.style.display = 'none'
            a.click()
            a.remove()
        },

        downloadBlob (data, fileName, mimeType) {
            const blob = new Blob([data], {
                type: mimeType
            })
            const url = window.URL.createObjectURL(blob)
            this.createDownloadURL(url, fileName)
            setTimeout(() => window.URL.revokeObjectURL(url), 1000)
        },

        downloadFile (filename) {
            this.downloadBlob(this.state.files[filename], filename, 'application/octet-stream')
        }
    },
    created () {
        this.$eventHub.$on('set-selected', this.setSelected)
    },
    watch: {
        blob () {
            this.downloadURL = URL.createObjectURL(this.blob)
        }
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
        margin: 8px;
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
        background: rgb(60, 75, 112);
        background: linear-gradient(0deg, rgb(67, 95, 155) 51%, rgb(61, 79, 121) 100%);
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
        padding: 0px 0px 12px 0px;
        cursor: pointer;
        font-size: 16px;
    }

    .tabholder a {
        background: rgb(41,51,75);
        float: left;
        padding: 2px 9px 2px 9px;
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

    .filename {
        display: block;
        text-align: center;
        opacity: 0.8;
        margin: 6px;
    }

    .download-text {
        color: #fff;
        text-decoration: none;
    }
    .download-text:hover {
        text-decoration: none;
        color: #fff;
    }
    ul.files-list {
        margin: 40px;
        border: solid 1px gray;
        border-radius: 15px;
        text-align: left;
        padding-left: 10px;
        cursor: default;
    }

    .files-list li {
        border-left: none;
    }
    .files-header {
        border-left: none;
        margin-left: 40%;

    }
</style>
