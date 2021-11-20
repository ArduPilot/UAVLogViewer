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
            left: 540,
            top: 0,
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

    div #paneParamViewer::before {
        content: '\25e2';
        color: #fff;
        background-color: rgb(38, 53, 71);
        position: absolute;
        bottom: 0;
        right: 0;
        width: 20px;
        height: 20px;
        padding: 2px 5px;
        box-sizing: border-box;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        border-radius: 10px 0px 1px 0px;
        cursor: se-resize;
    }

      div #paneParamViewer::after {
        content: '\2725';
        color: #141924;
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
        height: 95%;
        overflow: auto;
        margin: 0;
    }

    input#filterbox {
        width: 95%;
        margin: 23px 0px 0px 10px;
        padding: 4px;
        background-color: rgba(255, 255, 255, 0.836);
        border: 1px solid rgb(133, 133, 133);
        border-radius: 3px;
    }

    input#filterbox:focus {
        outline: none;
        border: 1px solid #162442;
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
