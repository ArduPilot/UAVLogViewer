<template>
    <div :id="getDivName()"
         v-bind:style="{width:  width + 'px', height: height + 'px', top: top + 'px', left: left + 'px' }">
        <div id="paneContent">
            {{ solutionValue }} {{ closestIndex }}
          <span style="float: right; margin: 3px; cursor: pointer;" @click="close()"> X </span>
          <table>
            <thead>
            <tr>
                <th>Property</th>
                <th>Value</th>
            </tr>
            </thead>
            <tbody>
            <tr v-for="(value, key) in decodedSolution" :key="key">
                <td>{{ key }}</td>
                <td>{{ value }}</td>
            </tr>
            </tbody>
          </table>
        </div>
    </div>
</template>

<script>
import { store } from '../Globals.js'
import { baseWidget } from './baseWidget'

export default {
    name: 'EkfHelperViewer',
    mixins: [baseWidget],
    created () {
        this.$eventHub.$on('cesium-time-changed', this.setTime)
        this.$eventHub.$on('hoveredTime', this.setTime)
    },
    data () {
        return {
            name: 'EkfHelperViewer',
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
            this.waitForMessage('EKF4.SS')
        }
    },
    computed: {
        closestIndex () {
            const messages = this.state.messages['XKF4[0]']
            console.log(messages)
            if (!messages) {
                return 0
            }
            for (const index in messages.time_boot_ms) {
                if (messages.time_boot_ms[index] > this.cursorTime) {
                    return index
                }
            }
            console.log(messages.time_boot_ms[messages.time_boot_ms.length - 1])
            return 0
        },
        solutionValue () {
            const messages = this.state.messages['XKF4[0]']
            if (!this.closestIndex || !messages) {
                return 0
            }
            return messages.SS[this.closestIndex]
        },
        decodedSolution () {
            const solution = this.solutionValue
            return {
                attitude: !!(solution & (1 << 0)),
                horizVel: !!(solution & (1 << 1)),
                vertVel: !!(solution & (1 << 2)),
                horizPosRel: !!(solution & (1 << 3)),
                horizPosAbs: !!(solution & (1 << 4)),
                vertPos: !!(solution & (1 << 5)),
                terrainAlt: !!(solution & (1 << 6)),
                constPosMode: !!(solution & (1 << 7)),
                predHorizPosRel: !!(solution & (1 << 8)),
                predHorizPosAbs: !!(solution & (1 << 9)),
                takeoffDetected: !!(solution & (1 << 10)),
                takeoff: !!(solution & (1 << 11)),
                touchdown: !!(solution & (1 << 12)),
                usingGps: !!(solution & (1 << 13)),
                gpsGlitching: !!(solution & (1 << 14)),
                gpsQualityGood: !!(solution & (1 << 15)),
                initialized: !!(solution & (1 << 16)),
                rejectingAirspeed: !!(solution & (1 << 17)),
                deadReckoning: !!(solution & (1 << 18))
            }
        }
    }
}
</script>

<style scoped>
    div #paneEkfHelperViewer {
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

    div #paneEkfHelperViewer::before {
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

     div #paneEkfHelperViewer::after {
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
        margin: 20px;
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
