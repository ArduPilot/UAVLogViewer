<template>
    <div :id="getDivName()" v-bind:style="{width:  width + 'px', height: height + 'px', top: top + 'px', left: left + 'px' }">
        <div id="paneContent">
            <ul>
                <li v-for="msg in filteredData"> {{ msg[2] }}</li>
            </ul>
        </div>
    </div>
</template>

<script>
import {store} from '../Globals.js'
import {baseWidget} from './baseWidget'

export default {
    name: 'MessageViewer',
    mixins: [baseWidget],
    created () {
        this.$eventHub.$on('hoveredTime', this.setTime)
    },
    data () {
        return {
            name: 'MessageViewer',
            filter: '',
            state: store,
            width: 264,
            height: 120,
            left: 780,
            top: 132,
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
        }
    },
    computed: {
        filteredData () {
            let potato = this.forceRecompute
            return this.state.textMessages.filter(key => (key[0] < this.cursorTime))
        }
    }
}
</script>

<style scoped>
    div #paneMessageViewer {
        position: absolute;
        width: 100px;
        height: 100px;
        left: 20px;
        top: 20px;
        background: rgba(255, 255, 255, 0.5);
        font-size: 10px;
        text-transform: uppercase;
        z-index: 10000;
        border-radius: 10px;
    }

    div #paneMessageViewer::before {
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

    div#paneContent {
        width:90%;height: 90%; overflow: auto;
    }

    input#filterbox {
        margin-left: 30px;
        background-color: rgba(255,255,255,0.5);
        border: 1px solid black;
        border-radius: 5px;
    }

</style>
