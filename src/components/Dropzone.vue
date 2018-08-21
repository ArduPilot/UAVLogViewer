<template>
  <div>
    <li  v-if="!sampleLoaded">
      <a class="section" href="#" @click="onLoadSample"><i class="fas fa-play "></i> Open Sample </a>
    </li>
    <li  v-if="url">
      <a class="section" @click="share" href="#"><i class="fas fa-share-alt"></i> {{ shared ? 'Copied to clipboard!' : 'Share link'}}</a>
    </li>
    <div id="drop_zone" @dragover.prevent @drop="onDrop" @click="browse">
      <p>Drop *.tlog file here or click to browse</p>
      <input type="file" id="choosefile" style="opacity: 0;" @change="onChange">
    </div>
    <VProgress v-bind:percent="percentage"
               v-if="percentage > -1"
               v-bind:complete="'Processing done'"
    ></VProgress>
    <VProgress v-bind:percent="uploadpercentage"
               v-bind:complete="'Upload Done'"
               v-if="uploadpercentage > -1">
    </VProgress>
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
      percentage: -1,
      uploadpercentage: -1,
      sampleLoaded: false,
      shared: false,
      url: null
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
      this.sampleLoaded = true
      this.url = url
      let oReq = new XMLHttpRequest()
      oReq.open('GET', url, true)
      oReq.responseType = 'arraybuffer'

      oReq.onload = function (oEvent) {
        var arrayBuffer = oReq.response
        worker.postMessage({action: 'parse', file: arrayBuffer})
      }
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
        worker.postMessage({action: 'parse', file: Buffer.from(data)})
      }

      reader.readAsArrayBuffer(file)
    },
    upload (file) {
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
      request.onprogress = function (e) {
        if (e.lengthComputable) {
          console.log(e.loaded + ' / ' + e.total)
          this.uploadpercentage = 100 * e.loaded / e.total
        }
      }.bind(this)

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
      const el = document.createElement('textarea');
      el.value = window.location.host + '/#/v/' + this.url
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el)
      this.shared = true
    }
  },
  mounted () {
    worker.onmessage = function (event) {
      if (event.data.hasOwnProperty('percentage')) {
        this.percentage = event.data.percentage
      } else if (event.data.hasOwnProperty('messages')) {
        this.messages = event.data.messages
        this.$eventHub.$emit('messages', this.messages)
      }
    }.bind(this)
    if (this.$route.params.hasOwnProperty('id'))
    {
      this.onLoadSample(this.$route.params.id)
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
    .nav-side-menu li {
      padding-left: 0px;
      border-left: 3px solid #2e353d;
      border-bottom: 1px solid #23282e;
    }

    .nav-side-menu li a {
      text-decoration: none;
      color: #e1ffff;
    }

    .nav-side-menu li a i{
      padding-left: 0px;
      width: 20px;
      padding-right: 20px;
    }

    i {
      margin: 10px;
    }
</style>
