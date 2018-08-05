<template>
    <div id="drop_zone" @dragover.prevent @drop="process">
        <p>Drag one or more files to this Drop Zone ...</p>
    </div>
</template>
<script>
require('mavlink_common_v1.0')

export default {
  name: 'Dropzone',
  data: function () {
    return {
      mavlinkParser: new MAVLink(),
      messages: {}
    }
  },
  methods: {
    process: function (ev) {
      console.log('File(s) dropped')
      let _this = this
      // Prevent default behavior (Prevent file from being opened)
      ev.preventDefault()
      if (ev.dataTransfer.items) {
        // Use DataTransferItemList interface to access the file(s)
        for (let i = 0; i < ev.dataTransfer.items.length; i++) {
          // If dropped items aren't files, reject them
          if (ev.dataTransfer.items[i].kind === 'file') {
            let file = ev.dataTransfer.items[i].getAsFile()
            console.log('... file[' + i + '].name = ' + file.name)
            let reader = new FileReader()
            reader.onload = function (e) {
              let data = reader.result
              _this.mavlinkParser.pushBuffer(Buffer.from(data))
              _this.mavlinkParser.parseBuffer()
              _this.$emit('messages', _this.messages)
            }
            reader.readAsArrayBuffer(file)
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
    fixData (message) {
      if (message.name === 'GLOBAL_POSITION_INT') {
        message.lat = message.lat / 10000000
        message.lon = message.lon / 10000000
        message.relative_alt = message.relative_alt / 1000
      }
      return message
    }
  },
  mounted () {
    let _this = this
    this.mavlinkParser.on('message', function (message) {
      if (message.id !== -1) {
        if (message.name in _this.messages) {
          _this.messages[message.name].push(_this.fixData(message))
        } else {
          _this.messages[message.name] = [_this.fixData(message)]
        }
      }
    })
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
      border: 1px solid blue;
      width:  200px;
      height: 100px;
      margin: auto;
    }
</style>
