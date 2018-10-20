<template>
  <div>
    <li  v-if="!sampleLoaded">
      <a class="section" href="#" @click="onLoadSample('sample')"><i class="fas fa-play "></i> Open Sample </a>
    </li>
    <li  v-if="url">
      <a class="section" @click="share" href="#"><i class="fas fa-share-alt"></i> {{ shared ? 'Copied to clipboard!' : 'Share link'}}</a>
    </li>
    <li  v-if="url">
      <a class="section" target="_blank" :href="'/uploaded/' + url"><i class="fas fa-download"></i> Download</a>
    </li>
    <div id="drop_zone" v-if="uploadpercentage===-1" @dragover.prevent @drop="onDrop" @click="browse">
      <p>Drop *.tlog file here or click to browse</p>
      <input type="file" id="choosefile" style="opacity: 0;" @change="onChange">
    </div>
    <b-form-checkbox class="uploadCheckbox" v-if="file!=null && !uploadStarted" @change="uploadFile()"> Upload
    </b-form-checkbox>
    <VProgress v-bind:percent="uploadpercentage"
               v-bind:complete="transferMessage"
               v-if="uploadpercentage > -1">
    </VProgress>
    <VProgress v-bind:percent="state.processPercentage"
               v-if="state.processPercentage > -1"
               v-bind:complete="state.processStatus"
    ></VProgress>
  </div>
</template>
<script>
import VProgress from './SideBarFileManagerProgressBar'
import Worker from '../tools/parsers/parser.worker.js'
import {store} from './Globals'

require('mavlink_common_v1.0')

const worker = new Worker()

worker.addEventListener('message', function (event) {})

export default {
    name: 'Dropzone',
    data: function () {
        return {
            mavlinkParser: new MAVLink(),
            uploadpercentage: -1,
            sampleLoaded: false,
            shared: false,
            url: null,
            transferMessage: '',
            state: store,
            file: null,
            uploadStarted: false
        }
    },
    created () {
        this.$eventHub.$on('loadType', this.loadType)
    },
    beforeDestroy () {
        this.$eventHub.$off('open-sample')
    },
    methods: {
        onLoadSample (file) {
            let url
            if (file === 'sample') {
                url = require('../assets/vtol.tlog')
            } else {
                url = ('/uploaded/' + file)
            }
            this.transferMessage = 'Download Done'
            this.sampleLoaded = true
            this.url = url
            let oReq = new XMLHttpRequest()
            oReq.open('GET', url, true)
            oReq.responseType = 'arraybuffer'

            oReq.onload = function (oEvent) {
                var arrayBuffer = oReq.response
                worker.postMessage({action: 'parse', file: arrayBuffer, isTlog: (url.indexOf('.tlog') > -1)})
            }
            oReq.addEventListener('progress', function (e) {
                if (e.lengthComputable) {
                    this.uploadpercentage = 100 * e.loaded / e.total
                }
            }.bind(this)
                , false)

            oReq.send()
        },
        onChange (ev) {
            let fileinput = document.getElementById('choosefile')
            this.process(fileinput.files[0])
        },
        onDrop (ev) {
            // Prevent default behavior (Prevent file from being opened)
            ev.preventDefault()
            if (ev.dataTransfer.items) {
                // Use DataTransferItemList interface to access the file(s)
                for (let i = 0; i < ev.dataTransfer.items.length; i++) {
                    // If dropped items aren't files, reject them
                    if (ev.dataTransfer.items[i].kind === 'file') {
                        let file = ev.dataTransfer.items[i].getAsFile()
                        this.process(file)
                    }
                }
            } else {
                // Use DataTransfer interface to access the file(s)
                for (let i = 0; i < ev.dataTransfer.files.length; i++) {
                    console.log('... file[' + i + '].name = ' + ev.dataTransfer.files[i].name)
                    console.log(ev.dataTransfer.files[i])
                }
            }
        },
        loadType: function (type) {
            console.log("asking worker")
            worker.postMessage({
                action: 'loadType',
                type: type
            })
        },
        process: function (file) {
            this.file = file
            let reader = new FileReader()
            reader.onload = function (e) {
                let data = reader.result
                worker.postMessage({action: 'parse',
                    file: Buffer.from(data),
                    isTlog: (file.name.indexOf('tlog') > 1)})
            }

            reader.readAsArrayBuffer(file)
        },
        uploadFile () {
            this.uploadStarted = true
            this.transferMessage = 'Upload Done!'
            this.uploadpercentage = 0
            let formData = new FormData()
            formData.append('file', this.file)

            let request = new XMLHttpRequest()
            request.onload = function () {
                if (request.status >= 200 && request.status < 400) {
                    this.uploadpercentage = 100
                    this.url = request.responseText
                } else {
                    alert('error! ' + request.status)
                    this.uploadpercentage = 100
                    this.transferMessage = 'Error Uploading'
                    console.log(request)
                }
            }.bind(this)
            request.upload.addEventListener('progress', function (e) {
                if (e.lengthComputable) {
                    this.uploadpercentage = 100 * e.loaded / e.total
                }
            }.bind(this)
                , false)
            request.open('POST', '/upload')
            request.send(formData)
        },
        fixData (message) {
            if (message.name === 'GLOBAL_POSITION_INT') {
                message.lat = message.lat / 10000000
                message.lon = message.lon / 10000000
                message.relative_alt = message.relative_alt / 1000
            }
            return message
        },
        browse () {
            document.getElementById('choosefile').click()
        },
        share () {
            const el = document.createElement('textarea')
            el.value = window.location.host + '/#/v/' + this.url
            document.body.appendChild(el)
            el.select()
            document.execCommand('copy')
            document.body.removeChild(el)
            this.shared = true
        }
    },
    mounted () {
        worker.onmessage = function (event) {
            if (event.data.hasOwnProperty('percentage')) {
                this.state.processPercentage = event.data.percentage
            } else if (event.data.hasOwnProperty('availableMessages')) {
                console.log(event.data.availableMessages)
                this.$eventHub.$emit('messageTypes', event.data.availableMessages)
            } else if (event.data.hasOwnProperty('messages')) {
                this.state.messages = event.data.messages
                this.$eventHub.$emit('messages')
            } else if (event.data.hasOwnProperty('messageType')) {
                this.state.messages[event.data.messageType] = event.data.messageList
                this.$eventHub.$emit('messages')
            } else if (event.data.hasOwnProperty('done')) {
                worker.terminate()
            }
        }.bind(this)
        if (this.$route.params.hasOwnProperty('id')) {
            this.onLoadSample(this.$route.params.id)
        }
    },
    components: {
        VProgress
    }
}
</script>
<style scoped>
    /*
     * Navbar
     */

    #drop_zone {
      padding-top: 25px;
      padding-left: 10px;
      border: 1px solid dimgrey;
      width:  auto;
      height: 100px;
      margin: 20px;
      border-radius: 10px;
      cursor: default;
      background-color: rgba(0,0,0,0.0);
    }
    #drop_zone:hover {
      background-color: rgba(0,0,0,0.05);
    }

    .uploadCheckbox {
      margin-left: 20px;
    }

</style>
