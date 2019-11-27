<template>
    <div :id="getDivName()"
         v-bind:style="{width:  width + 'px', height: height + 'px', top: top + 'px', left: left + 'px' }">
        <div class="circle">
            <div class="stick" id="left"
                 v-bind:style="{'margin-left': leftStickLeft -3 + 'px', 'margin-top': leftStickTop -3 + 'px' }"></div>
        </div>
        <div class="circle">
            <div class="stick" id="right"
                 v-bind:style="{'margin-left': rightStickLeft -3 + 'px', 'margin-top': rightStickTop -3 + 'px' }">
            </div>
        </div>
    </div>
</template>

<script>
import {store} from '../Globals.js'
import {baseWidget} from './baseWidget'

class Interpolator {
    // This class holds all joystick positions and returns the interpolated position at an arbitraty time.
    constructor (x, y) {
        this.x = x
        this.y = y
        this.currentIndex = 0
    }

    at (point) {
        /*
            Returns x at closest y. TODO: interpolate properly.
            */
        while (this.x[this.currentIndex] < point && this.currentIndex < this.x.length - 2) {
            this.currentIndex += 1
        }
        while (this.x[this.currentIndex] > point && this.currentIndex > 1) {
            this.currentIndex -= 1
        }
        return this.y[Math.max(0, Math.min(this.currentIndex, this.y.length - 1))]
    }
}

export default {
    data () {
        return {
            state: store,
            name: 'inputViewer',
            throttle: 50,
            yaw: 50,
            pitch: 50,
            roll: 50,
            width: 294,
            height: 150,
            left: 500,
            top: 12,
            circleHeight: 40
        }
    },
    methods: {
        waitForMessage (fieldname) {
            this.$eventHub.$emit('loadType', fieldname.split('.')[0])
            let interval
            let _this = this
            let counter = 0
            return new Promise((resolve, reject) => {
                interval = setInterval(function () {
                    if (_this.state.messages.hasOwnProperty(fieldname.split('.')[0])) {
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
        setTime (time) {
            try {
                let sticks = this.interpolated.at(time)
                let reverses = [1, 1, 1, 1]
                if (this.state.params.get('RC1_REV') !== undefined) {
                    reverses = [
                        parseFloat(this.state.params.get('RC1_REV')),
                        parseFloat(this.state.params.get('RC2_REV')),
                        parseFloat(this.state.params.get('RC3_REV')),
                        parseFloat(this.state.params.get('RC4_REV'))]
                } else if (this.state.params.get('RC1_REVERSED') !== undefined) {
                    reverses = [
                        parseFloat(this.state.params.get('RC1_REVERSED')) ? -1 : 1,
                        parseFloat(this.state.params.get('RC2_REVERSED')) ? -1 : 1,
                        parseFloat(this.state.params.get('RC3_REVERSED')) ? -1 : 1,
                        parseFloat(this.state.params.get('RC4_REVERSED')) ? -1 : 1]
                }
                let trims = [1500, 1500, 1500, 1500]
                if (this.state.params.get('RC4_TRIM') !== undefined) {
                    trims = [
                        this.state.params.get('RC4_TRIM'),
                        this.state.params.get('RC3_TRIM'),
                        this.state.params.get('RC2_TRIM'),
                        this.state.params.get('RC1_TRIM')
                    ]
                }
                this.yaw = ((sticks[3] - trims[0]) * reverses[3] + 1500 - 1000) / 10
                this.throttle = ((sticks[2] - trims[1]) * reverses[2] + 1500 - 1000) / 10
                this.pitch = ((sticks[1] - trims[2]) * reverses[1] + 1500 - 1000) / 10
                this.roll = ((sticks[0] - trims[3]) * reverses[0] + 1500 - 1000) / 10
            } catch (e) {
                console.log(e)
            }
        },
        setup () {
            const _this = this

            this.waitForMessage('RC_CHANNELS.*').then(function () {
                let x = _this.state.messages['RC_CHANNELS'].time_boot_ms
                let y = []
                let msg = _this.state.messages['RC_CHANNELS']
                for (let i in msg.time_boot_ms) {
                    y.push([msg.chan1_raw[i], msg.chan2_raw[i], msg.chan3_raw[i], msg.chan4_raw[i]])
                }
                _this.interpolated = new Interpolator(x, y)
                _this.$eventHub.$on('cesium-time-changed', _this.setTime)
            })
            this.waitForMessage('RCIN.*').then(function () {
                let x = _this.state.messages['RCIN'].time_boot_ms
                let y = []

                let msg = _this.state.messages['RCIN']
                for (let i in msg.time_boot_ms) {
                    y.push([msg.C1[i], msg.C2[i], msg.C3[i], msg.C4[i]])
                }
                _this.interpolated = new Interpolator(x, y)
                _this.$eventHub.$on('cesium-time-changed', _this.setTime)
            })
        }
    },
    computed: {
        leftStickLeft: function () {
            return -12 + 0.01 * (this.yaw) * this.width / 2
        },
        leftStickTop () {
            return 22 + 0.02 * (100 - this.throttle) * this.circleHeight
        },
        rightStickLeft: function () {
            return -12 + (0.01 * this.roll) * (this.width / 2)
        },
        rightStickTop () {
            return 22 + 0.02 * (100 - this.pitch) * this.circleHeight
        }
    },
    name: 'TxInputs',
    mixins: [baseWidget],
    props: {
        'snappable': {type: Boolean, default: false},
        'fixedAspectRatio': {type: Boolean, default: false},
        'aspectRatio': {type: Number, default: 2}
    }
}
</script>

<style scoped>
    div #paneinputViewer {
        position: absolute;
        width: 100px;
        height: 100px;
        left: 20px;
        top: 20px;
        overflow: hidden;
        background: rgb(1, 160, 139);
        font-size: 10px;
        text-transform: uppercase;
        z-index: 10000;
        border-radius: 20px;
        border: 3px groove rgba(1, 133, 111, 0.541);
        box-shadow: inset 0px 0px 8px 6px rgba(0, 87, 72, 0.411);
    }

    div #paneinputViewer::before {
        content: '\2198';
        color: #fff;
        position: absolute;
        bottom: 0;
        right: 0;
        width: 20px;
        height: 20px;
        padding: 1px;
        padding-left: 5px;
        padding-bottom: 3px;
        background: rgba(0, 36, 27, 0.63);
        box-sizing: border-box;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        border: 1px outset rgba(107, 107, 107, 0.726);
        border-radius: 3px;
    }

    div.circle {
        border: double 4px rgba(2, 145, 121, 0.98);
        background: rgb(116,116,116);
        background: 
        radial-gradient(circle, rgba(24, 24, 24, 0.76) 0%, rgba(0,0,0,0.8886905103838411) 100%),
         linear-gradient(
            90deg,
            transparent 49.55%,
            darkgreen 49.75%,
            darkgreen 50.25%,
            transparent 50.25%
        ),
        linear-gradient(
            transparent 49.55%,
            darkgreen 49.75%,
            darkgreen 50.25%,
            transparent 50.25%
        );
        margin: 1px;
        border-radius: 50%;
        width: 48%;
        height: 98%;
        float: left;
        box-shadow: 0px 0px 14px -1px rgba(1, 82, 65, 0.61);
    }

/* STICK */

    div.stick {
        border-radius: 50%;
        width: 12px;
        height: 12px;
        background-color: rgb(221, 221, 221);
        border: 1px solid rgb(139, 139, 139);
        margin-left: 48%;
        display: inline-block;
        box-shadow: inset 0px 0px 4px 2px rgba(102, 102, 102, 0.877);
    }
    
</style>
