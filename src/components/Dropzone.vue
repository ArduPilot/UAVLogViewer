<template>
    <div id="drop_zone" @dragover.prevent @drop="process">
        <p>Drag one or more files to this Drop Zone ...</p>
    </div>
</template>
<script>
/* eslint-disable no-undef */
let mavlink = require('mavlink_common_v1.0')
console.log(mavlink)
let mavlinkParser = new MAVLink()

mavlinkParser.on('message', function (message) {
  if (message.id !== -1) {
    /* if (message.name in app.messages) {
      app.messages[message.name].push(message)
    } else {
      app.messages[message.name] = [message]
      app.message_types = Object.keys(app.messages)
    } */
    console.log(message)
  }
})

export default {
  name: 'Dropzone',
  methods: {
    process: function (ev) {
      console.log('File(s) dropped')
      // Prevent default behavior (Prevent file from being opened)
      ev.preventDefault()
      if (ev.dataTransfer.items) {
        // Use DataTransferItemList interface to access the file(s)
        for (let i = 0; i < ev.dataTransfer.items.length; i++) {
          // If dropped items aren't files, reject them
          if (ev.dataTransfer.items[i].kind === 'file') {
            let file = ev.dataTransfer.items[i].getAsFile()
            console.log('... file[' + i + '].name = ' + file.name)
            console.log(file)
            let reader = new FileReader()
            reader.onload = function (e) {
              let data = reader.result
              let buffer = Buffer.from(data)
              console.log(buffer)
              mavlinkParser.pushBuffer(Buffer.from(data))
              mavlinkParser.parseBuffer()
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
    }
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
