<template>
    <!-- HEADER -->
    <div class="nav-side-menu col-lg-2">
        <h1 class="brand">
            <a class="github" href="https://github.com/ardupilot/uavlogviewer">
                <img :src="githubIcon" />
            </a>
            <a href="/"><b>UAV</b> Log Viewer<i class="fas fa-plane"></i></a
            ><a
                class="github"
                href="https://ardupilot.org/copter/docs/common-uavlogviewer.html"
                ><img :src="wikiIcon"
            /></a>
        </h1>
        <!-- TABHOLDER -->
        <i
            v-collapse-toggle="'menucontent'"
            class="fa fa-bars fa-2x toggle-btn"
        ></i>
        <Collapse name="menucontent" class="menu-content" visible>
            <span v-if="state.file" class="filename"
                >Current file: {{ state.file }}</span
            >
            <div class="tabholder">
                <!-- Home -->
                <a
                    v-if="!state.processDone"
                    :class="selected === 'home' ? 'selected' : ''"
                    @click="selected = 'home'"
                >
                    <i class="fas fa-home"></i>Home</a
                >
                <!-- Plot -->
                <a
                    v-if="state.processDone"
                    :class="selected === 'plot' ? 'selected' : ''"
                    @click="selected = 'plot'"
                >
                    <i class="fas fa-chart-line"></i>Plot</a
                >
                <!-- 3D: reopens the 3D view after its close button -->
                <a
                    v-if="state.mapAvailable && !state.showMap"
                    title="Show the 3D view"
                    @click="state.showMap = true"
                >
                    <i class="fas fa-cube"></i>3D</a
                >
                <!-- more -->
                <a
                    v-if="state.processDone"
                    :class="selected === 'other' ? 'selected' : ''"
                    @click="selected = 'other'"
                >
                    <i class="fas fa-ellipsis-v"></i>
                </a>
            </div>
        </Collapse>
        <!-- TOGGLE MENU -->
        <div class="menu-list">
            <Collapse name="menucontent" class="menu-content" visible>
                <div :style="{ display: selected === 'plot' ? '' : 'none' }">
                    <plotSetup />
                    <message-menu />
                </div>
                <div v-if="selected === 'home'">
                    <Dropzone />
                    <span class="buildinfo">Commit {{ state.commit }}</span>
                    <span class="buildinfo">Built {{ state.buildDate }}</span>
                </div>
                <div v-if="selected === 'other'">
                    <!-- PARAM/MESSAGES/RADIO -->
                    <hr />
                    <a class="centered-section"> Show / hide </a>
                    <div v-if="state.processDone" class="show-hide">
                        <label v-if="state.params">
                            <i class="fa fa-cogs circle"></i>
                            <input v-model="state.showParams" type="checkbox" />
                            <a class="check-font"> Parameters </a>
                        </label>
                        <label>
                            <i class="fa fa-gamepad circle"></i>
                            <input v-model="state.showRadio" type="checkbox" />
                            <a class="check-font"> Radio Sticks </a>
                        </label>
                        <label>
                            <i class="fa fa-compass circle"></i>
                            <input v-model="state.showMagfit" type="checkbox" />
                            <a class="check-font"> Mag Fit Tool </a>
                        </label>
                        <label>
                            <i class="fa fa-compass circle"></i>
                            <input
                                v-model="state.showEkfHelper"
                                type="checkbox"
                            />
                            <a class="check-font"> EKF helper </a>
                        </label>
                        <label v-if="state.textMessages">
                            <i class="fa fa-comment circle"></i>
                            <input
                                v-model="state.showMessages"
                                type="checkbox"
                            />
                            <a class="check-font"> Messages </a>
                        </label>
                        <label>
                            <i class="fa fa-plane-departure circle"></i>
                            <input
                                v-model="state.showAttitude"
                                type="checkbox"
                            />
                            <a class="check-font"> Attitude </a>
                        </label>
                        <label v-if="!recording" @click="startCapture">
                            <i class="fa fa-play circle"></i>
                            <a class="check-font"> Record </a>
                        </label>
                        <label v-if="recording" @click="stopCapture">
                            <i class="fa fa-stop circle"></i>
                            <a class="check-font"> End Rec </a>
                        </label>
                        <label v-if="chunks" @click="download">
                            <i class="fa fa-download circle"></i>
                            <a
                                ref="downloadFile"
                                class="check-font download-text"
                                :href="downloadURL"
                                :download="fileName"
                            >
                                Download
                            </a>
                        </label>
                        <label
                            v-if="state.logType === 'tlog'"
                            @click="downloadTrimmed"
                        >
                            <i
                                class="fa fa-download circle"
                                title="Download a log with starting and end time matching the current views"
                            >
                            </i>
                            <a class="check-font"> Trimmed log </a>
                        </label>
                        <label>
                            <i
                                class="fa fa-microchip circle"
                                title="Show a widget with the detected sensors"
                            >
                            </i>
                            <input
                                v-model="state.showDeviceIDs"
                                type="checkbox"
                            />
                            <a class="check-font"> Sensors </a>
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
                    <div>
                        <label><i class="fas fa-gamepad"></i> Radio Mode</label>
                        <select v-model="state.radioMode" class="cesium-button">
                            <option value="1">1</option>
                            <option value="2">2</option>
                        </select>
                    </div>
                </div>
            </Collapse>
        </div>
    </div>
</template>
<script>
import Dropzone from "./SideBarFileManager.vue";
import MessageMenu from "./SideBarMessageMenu.vue";
import { store } from "./Globals.js";
import { downloadData } from "../tools/download.js";
import PlotSetup from "./PlotSetup.vue";
import Collapse from "./ui/Collapse.vue";
import githubIcon from "../assets/GitHub-Mark-64px.png";
import wikiIcon from "../assets/wiki.svg";

export default {
    name: "Sidebar",
    components: { PlotSetup, MessageMenu, Dropzone, Collapse },
    data() {
        return {
            githubIcon,
            wikiIcon,
            selected: "home",
            state: store,
            chunks: false,
            blob: null,
            recording: false,
            recorder: null,
            stream: null,
            downloadURL: "",
            fileName: "video.mp4",
        };
    },
    watch: {
        blob() {
            this.downloadURL = URL.createObjectURL(this.blob);
        },
    },
    created() {
        this.$eventHub.$on("set-selected", this.setSelected);
    },
    beforeDestroy() {
        this.$eventHub.$off("set-selected", this.setSelected);
    },
    methods: {
        setSelected(selected) {
            this.selected = selected;
        },

        startCapture() {
            navigator.mediaDevices
                .getDisplayMedia({ video: { mediaSource: "screen" } })
                .then((stream) => {
                    this.record(stream);
                })
                .catch((err) => {
                    console.error("Error:" + err);
                    return null;
                });
        },

        stopCapture() {
            this.recorder.stop();
            this.stream.getTracks().forEach((track) => track.stop());
        },

        record(stream) {
            const recorder = new MediaRecorder(stream);
            const chunks = [];
            recorder.ondataavailable = (e) => chunks.push(e.data);

            this.stream = stream;
            this.recorder = recorder;
            this.recorder.start();

            this.recording = true;

            recorder.onstop = () => {
                const completeBlob = new Blob(chunks, { type: chunks[0].type });
                this.chunks = true;
                this.blob = completeBlob;
                this.recording = false;
            };
        },

        download() {
            this.$refs.downloadFile.click();
        },
        downloadTrimmed() {
            this.$eventHub.$emit("trimFile");
        },

        downloadFile(filename) {
            downloadData(this.state.files[filename], filename);
        },
    },
};
</script>
<style scoped>
@media (min-width: 575px) and (max-width: 992px) {
    a {
        padding: 2px 60px 2px 55px;
    }
}
</style>

<style>
span.buildinfo {
    font-size: 70%;
    margin-left: 30px;
    display: block;
    opacity: 0.5;
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
    background: linear-gradient(0deg, rgb(20 25 36) 51%, rgb(37 47 71) 100%);
    position: fixed !important;
    top: 0;
    height: 100%;
    color: rgb(255 255 255);
}

.nav-side-menu .toggle-btn {
    display: none;
}

/* UL/LI */

.nav-side-menu ul,
.nav-side-menu li {
    list-style: none;
    padding: 0;
    margin: 0;
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
    margin-left: 0;
}

.nav-side-menu ul .sub-menu li:hover,
.nav-side-menu li .sub-menu li:hover {
    background-color: #020203;
}

.nav-side-menu ul .sub-menu li::before,
.nav-side-menu li .sub-menu li::before {
    content: "\f105";
    display: inline-block;
    padding-left: 10px;
    padding-right: 10px;
    vertical-align: middle;
}

.nav-side-menu li {
    padding-left: 0;
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
    background-color: rgb(52 70 100 / 33.6%);
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
    background-color: rgb(47 60 83 / 63%);
    width: 52px;
    height: 52px;
    padding: 17px;
    border-radius: 50px;
}

.circle:hover {
    background-color: rgb(58 71 94 / 63%);
    box-shadow: 0 0 12px 0 rgb(24 106 173 / 28.1%);
}

.show-hide input[type="checkbox"] {
    display: none;
    visibility: hidden;
}

.check-font {
    padding: 0 !important;
    font-size: 13px;
    color: rgb(146 143 143);
}

/* SCROLLBAR */

::-webkit-scrollbar {
    width: 12px;
    background-color: rgb(0 0 0 / 0%);
}

::-webkit-scrollbar-thumb {
    border-radius: 5px;
    box-shadow: inset 0 0 6px rgb(0 0 0 / 10%);
    background: rgb(60 75 112);
    background: linear-gradient(0deg, rgb(67 95 155) 51%, rgb(61 79 121) 100%);
}

/* BRAND */

.fa-plane {
    margin: 8px;
    font-size: 18px;
}

.brand {
    text-align: center;
    font-size: 22px;
    padding-left: 0;
    line-height: 50px;
    margin-bottom: 0;
    color: rgb(54 72 114) !important;
    background-color: rgb(248 248 248 / 91.8%);
    display: block;
}

.brand a {
    text-decoration: none;
    color: rgb(54 72 114) !important;
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
    padding: 0 0 12px;
    cursor: pointer;
    font-size: 16px;
}

.tabholder a {
    background: rgb(41 51 75);
    float: left;
    padding: 2px 9px;
    border: 1px solid rgb(91 100 117 / 76%);
    border-radius: 30px;
}

a.selected {
    color: rgb(247 248 248) !important;
    box-shadow: 0 0 12px 0 rgb(125 125 125 / 55%);
}

.tabholder a:hover {
    box-shadow: 0 0 12px 0 rgb(125 125 125 / 55%);
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
    background-color: rgb(175 177 175);
}

/* MEDIA QUERIES */

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
        background-color: rgb(248 248 248 / 76.9%);
        color: rgb(58 58 58);
        height: auto;
        width: 40px;
        text-align: center;
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
        width: 27% !important;
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
        width: 20% !important;
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
        width: 15% !important;
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
