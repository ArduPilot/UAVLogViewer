<template>
    <div :id="getDivName()"
         v-bind:style="{width:  width + 'px', height: height + 'px', top: top + 'px', left: left + 'px' }">
        <div id="paneContent">
          <span style="float: right; margin: 3px; cursor: pointer;" @click="close()"> X </span>
            <ul>
                <li v-bind:key="msg[0]+msg[1]" v-for="msg in filteredData">
                    [{{timeFormatter(msg[0])}}]: {{ msg[2] }}
                </li>
            </ul>
        </div>
    </div>
</template>

<script>
import { store } from '../Globals.js'
import { baseWidget } from './baseWidget'

export default {
    name: 'MessageViewer',
    mixins: [baseWidget],
    created () {
        this.$eventHub.$on('cesium-time-changed', this.setTime)
        this.$eventHub.$on('hoveredTime', this.setTime)
    },
    data () {
        return {
            name: 'MessageViewer',
            filter: '',
            state: store,
            width: 220,
            height: 215,
            left: 310,
            top: 0,
            forceRecompute: 0,
            cursorTime: 0
        }
    },
    methods: {
        timeFormatter (milliseconds) {
            let outputString = ''
            const seconds = (milliseconds / 1000) % 60
            let minutes = Math.floor((milliseconds / 1000) / 60)
            const hours = Math.floor(minutes / 60)
            minutes = minutes % 60
            outputString = seconds.toFixed(1).padStart(4, '0')
            outputString = minutes.toFixed(0).padStart(2, '0') + ':' + outputString
            outputString = hours.toFixed(0).padStart(2, '0') + ':' + outputString
            return outputString
        },
        setTime (time) {
            this.cursorTime = time
        },
        waitForMessage (fieldname) {
            this.$eventHub.$emit('loadType', fieldname.split('.')[0])
            let interval
            const _this = this
            let counter = 0
            return new Promise((resolve, reject) => {
                interval = setInterval(function () {
                    if (_this.state.messages[fieldname.split('.')[0]]) {
                        clearInterval(interval)
                        counter += 1
                        resolve()
                    } else {
                        if (counter > 6) {
                            console.log('not resolving')
                            clearInterval(interval)
                            reject(new Error('Could not load messageType'))
                        }
                    }
                }, 2000)
            })
        },
        setup () {
        }
    },
    computed: {
        filteredData () {
            // this seems necessary to force a recomputation
            // eslint-disable-next-line
            let potato = this.forceRecompute
            return this.state.textMessages.filter(key => (key[0] < this.cursorTime))
        }
    },
    watch: {
        filteredData: function (data) {
            const container = this.$el.querySelector('#paneContent')
            container.scrollTop = container.scrollHeight
        }
    }
}
</script>

<style scoped>
    div #paneMessageViewer {
        min-width: 220px;
        min-height: 150px;
        position: absolute;
        background: rgba(253, 254, 255, 0.856);
        color: #141924;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        z-index: 10000;
        box-shadow: 9px 9px 3px -6px rgba(26, 26, 26, 0.699);
        border-radius: 5px;
        user-select: none;
    }

    div #paneMessageViewer::before {
        content: '\25e2';
        color: #ffffff;
        background-color: rgb(38, 53, 71);
        position: absolute;
        bottom: -1px;
        right: 0;
        width: 17px;
        height: 21px;
        padding: 2px 3px;
        border-radius: 10px 0px 1px 0px;
        box-sizing: border-box;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        cursor: se-resize;
    }

     div #paneMessageViewer::after {
        content: '\2725';
        color: #2E3F54;
        position: absolute;
        top: 0;
        left: 0;
        width: 18px;
        height: 17px;
        margin-top: -3px;
        padding: 0px 2px;
        box-sizing: border-box;
        align-items: center;
        justify-content: center;
        font-size: 17px;
         cursor: grab;
    }

    div#paneContent {
        height: 100%;
        overflow: auto;
        -webkit-user-select: none; /* Chrome all / Safari all */
        -moz-user-select: none; /* Firefox all */
        -ms-user-select: none; /* IE 10+ */
        user-select: none;
    }

    div#paneContent ul {
        list-style: none;
        line-height: 22px;
        padding: 16px;
        margin: 0;
    }

</style>
