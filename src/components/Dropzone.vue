<template>
  <div>
    <div id="drop_zone" @dragover.prevent @drop="onDrop" @click="browse">
        <p>Drop *.tlog file here or click to browse</p>
      <input type="file" id="choosefile" style="opacity: 0;" @change="onChange">
    </div>
    <VProgress v-bind:percent="percentage" v-if="percentage < 100"></VProgress>
  </div>
</template>
<script>
import VProgress from './VProgress'
import Worker from '../tools/parsers/parser.worker.js'
require('mavlink_common_v1.0')

const worker = new Worker()

worker.addEventListener('message', function (event) {})

export default {
  name: 'Dropzone',
  data: function () {
    return {
      mavlinkParser: new MAVLink(),
      messages: {},
      percentage: 100,
      totalSize: null
    }
  },
  created () {
    this.$eventHub.$on("open-sample", this.onLoadSample)
  },
  beforeDestroy () {
    this.$eventHub.$off("open-sample")
  },
  methods: {
    onLoadSample () {
      let url = require('../assets/vtol.tlog')
      let oReq = new XMLHttpRequest()
      oReq.open('GET', url, true)
      oReq.responseType = 'arraybuffer'

      oReq.onload = function (oEvent) {
        var arrayBuffer = oReq.response
        worker.postMessage({action: 'parse', file: arrayBuffer})
      }
      oReq.send();
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
      let reader = new FileReader()
      reader.onload = function (e) {
        let data = reader.result
        worker.postMessage({action: 'parse', file: Buffer.from(data)})
      }
      reader.readAsArrayBuffer(file)
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
    }
  },
  mounted () {
    let _this = this
    worker.onmessage = function (event) {
      if (event.data.hasOwnProperty('percentage')) {
        _this.percentage = event.data.percentage
      } else if (event.data.hasOwnProperty('messages')) {
        _this.messages = event.data.messages
        _this.$emit('messages')
      }
    }
  },
  components: {
    VProgress
  }
}
</script>
<style scoped>
    body {
        font-size: .875rem;
    }

    /*
     * Sidebar
     */

    @supports ((position: -webkit-sticky) or (position: sticky)) {
    }

    /*
     * Content
     */

    [role="main"] {
        padding-top: 48px; /* Space for fixed navbar */
    }

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
