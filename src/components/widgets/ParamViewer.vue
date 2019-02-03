<template>
    <div :id="getDivName()" v-bind:style="{width:  width + 'px', height: height + 'px', top: top + 'px', left: left + 'px' }">
        <div id="paneContent">
            <input id="filterbox" v-model="filter" placeholder="Filter">
            <ul>
                <li v-for="param in filteredData"> {{ param }} : <span style="float: right;">{{state.params.values[param]}}</span></li>
            </ul>
        </div>
    </div>
</template>

<script>
import {store} from '../Globals.js'
import {baseWidget} from './baseWidget'

export default {
    name: 'ParamViewer',
    mixins: [baseWidget],
    data () {
        return {
            name: 'ParamViewer',
            filter: '',
            state: store,
            throttle: 50,
            yaw: 50,
            pitch: 50,
            roll: 50,
            width: 264,
            height: 120,
            left: 780,
            top: 12,
            forceRecompute: 0
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
        }
    },
    computed: {
        filteredData () {
            let potato = this.forceRecompute
            return Object.keys(this.state.params.values).filter(key => key.indexOf(this.filter.toUpperCase()) !== -1)
        }
    },
}
</script>

<style scoped>
    div #paneParamViewer {
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

    div #paneParamViewer::before {
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
