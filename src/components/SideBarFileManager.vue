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
      state: store
    }
  },
  created () {

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
          console.log(e.loaded + ' / ' + e.total)
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
    process: function (file) {
      this.upload(file)
      let reader = new FileReader()
      reader.onload = function (e) {
        let data = reader.result
        worker.postMessage({action: 'parse', file: Buffer.from(data), isTlog: (file.name.indexOf('tlog') > 1)})
      }

      reader.readAsArrayBuffer(file)
    },
    upload (file) {
      this.transferMessage = 'Upload Done!'
      this.uploadpercentage = 0
      let formData = new FormData()
      formData.append('file', file)

      let request = new XMLHttpRequest()
      request.onload = function () {
        console.log(request)
        if (request.status >= 200 && request.status < 400) {
          this.uploadpercentage = 100
          this.url = request.responseText
        } else {
          alert('error! ' + request.status)
          console.log(request)
        }
      }.bind(this)
      request.upload.addEventListener('progress', function (e) {
        if (e.lengthComputable) {
          console.log(e.loaded + ' / ' + e.total)
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
      } else if (event.data.hasOwnProperty('messages')) {
        worker.terminate()
        this.state.messages = event.data.messages
        this.$eventHub.$emit('messages')
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


</style>
