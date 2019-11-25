<template>
    <div :id="getDivName()"
         v-bind:style="{width:  width + 'px', height: height + 'px', top: top + 'px', left: left + 'px' }">
        <div id="paneContent">
            <input id="filterbox" placeholder="Filter" v-model="filter">
            <ul id="params">
                <li v-for="param in filteredData" v-bind:key="param">
                    {{ param }} : <span style="float: right;">{{state.params.values[param]}}</span>
                </li>
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
            width: 220,
            height: 215,
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
        },
        setup () {
        }
    },
    computed: {
        filteredData () {
            // eslint-disable-next-line
            let potato = this.forceRecompute
            return Object.keys(this.state.params.values).filter(key => key.indexOf(this.filter.toUpperCase()) !== -1)
        }
    }
}
</script>

<style scoped>
    div #paneParamViewer {
        min-width: 220px;
        min-height: 150px;
        position: absolute;
        background: rgba(51, 49, 49, 0.938);
        color: rgba(255, 255, 255, 0.918);
        font-size: 11px;
        text-transform: uppercase;
        z-index: 10000;
        box-shadow: 9px 9px 3px -6px rgba(26, 26, 26, 0.699);
        border-radius: 1px;
    }

    div #paneParamViewer::before {
        content: '\2198';
        color: rgb(255, 140, 45);
        position: absolute;
        bottom: 0;
        right: 0;
        width: 20px;
        height: 20px;
        padding: 0px 5px;
        box-sizing: border-box;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        border-radius: 4px;
    }

    div#paneContent {
        height: 95%;
        overflow: auto;
        margin: 0;
    }

    input#filterbox {
        width: 95%;
        margin: 15px 0px 0px 10px;
        padding: 4px;
        background-color: rgba(255, 255, 255, 0.836);
        border: 1px solid rgb(133, 133, 133);
        border-radius: 3px;
    }

    input#filterbox:focus {
        outline: none;
        border: 1px solid rgba(194, 100, 19, 0.849);
    }

    ul#params {
        padding: 12px;
        list-style: none;
        line-height: 22px;
        -webkit-user-select: none; /* Chrome all / Safari all */
        -moz-user-select: none; /* Firefox all */
        -ms-user-select: none; /* IE 10+ */
        user-select: none;
    }

</style>
