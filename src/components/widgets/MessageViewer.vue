<template>
    <div :id="getDivName()"
         v-bind:style="{width:  width + 'px', height: height + 'px', top: top + 'px', left: left + 'px' }">
        <div id="paneContent">
            <ul>
                <li v-bind:key="msg[0]+msg[1]" v-for="msg in filteredData"> {{ msg[2] }}</li>
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
        this.$eventHub.$on('cesium-time-changed', this.setTime)
    },
    data () {
        return {
            name: 'MessageViewer',
            filter: '',
            state: store,
            width: 220,
            height: 215,
            left: 50,
            top: 12,
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
            let container = this.$el.querySelector('#paneContent')
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
        background: rgba(51, 49, 49, 0.938);
        color: rgba(255, 255, 255, 0.918);
        font-size: 11px;
        text-transform: uppercase;
        z-index: 10000;
        box-shadow: 9px 9px 3px -6px rgba(26, 26, 26, 0.699);
        border-radius: 1px;
    }

    div #paneMessageViewer::before {
        content: '\25e2';
        color: rgb(202, 99, 15);
        background-color: rgba(51, 49, 49, 0.938);
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
    }

     div #paneMessageViewer::after {
        content: '\2725';
        color: rgb(202, 99, 15);
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
