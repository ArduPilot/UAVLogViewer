<template>
    <div :id="getDivName()" v-bind:style="{width:  width + 'px', height: height + 'px', top: top + 'px', left: left + 'px' }">
        <div class="circle">
            <div id="left" class="stick" v-bind:style="{'margin-left': leftStickLeft -3 + 'px', 'margin-top': leftStickTop -3 + 'px' }"></div>
            <div class="vertical-line"></div>
            <div class="horizontal-line"></div>
        </div>
        <div class="circle">
            <div id="right" class="stick" v-bind:style="{'margin-left': rightStickLeft -3 + 'px', 'margin-top': rightStickTop -3 + 'px' }"></div>
            <div class="vertical-line"></div>
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
            width: 264,
            height: 120,
            left: 500,
            top: 12,
            circleHeight: 50
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
                let reverses = [0, 0, 0, 0]
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
                this.yaw = ((sticks[3] - this.state.params.get('RC4_TRIM')) * reverses[3] + 1500 - 1000) / 10
                this.throttle = ((sticks[2] - this.state.params.get('RC3_TRIM')) * reverses[2] + 1500 - 1000) / 10
                this.pitch = ((sticks[1] - this.state.params.get('RC2_TRIM')) * reverses[1] + 1500 - 1000) / 10
                this.roll = ((sticks[0] - this.state.params.get('RC1_TRIM')) * reverses[0] + 1500 - 1000) / 10
            } catch (e) {
                console.log(e)
            }
        }

    },
    computed: {
        leftStickLeft: function () {
            return 0.01 * (this.yaw) * this.width / 2
        },
        leftStickTop () {
            return 0.02 * (100 - this.throttle) * this.circleHeight
        },
        rightStickLeft: function () {
            return (0.01 * this.roll) * (this.width / 2)
        },
        rightStickTop () {
            return 0.02 * (100 - this.pitch) * this.circleHeight
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
        background: rgba(255, 255, 255, 0.5);
        font-size: 10px;
        text-transform: uppercase;
        z-index: 10000;
        border-radius: 10px;
    }

    div #paneinputViewer::before {
        content: '\2198';
        color: #fff;
        position: absolute;
        bottom: 0;
        right: 0;
        width: 20px;
        height: 20px;
        padding: 2px;
        padding-left: 5px;
        padding-bottom: 3px;
        background: #000;
        box-sizing: border-box;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        border-radius: 5px;
    }

    div.circle {
        border: solid 1px black;
        border-radius: 20%;
        width:50%;
        height: 100%;
        float: left;
    }

    div.stick {
        border: solid 4px red;
        border-radius: 50%;
        width:6px;
        height: 6px;
        margin-left: 49%;
        display: inline-block;
    }

    div.vertical-line {
        position: absolute;
        margin-left: 25%;
        top: 0%;
        height: 100%;
        border-right: solid 1px black;
    }

    div.horizontal-line {
        position: absolute;
        top: 50%;
        width: 100%;
        height: 1%;
        border-top: solid 1px black;
    }
</style>
