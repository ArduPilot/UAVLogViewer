<template>
    <div :id="getDivName()"
         v-bind:style="{width:  width + 'px', height: height + 'px', top: top + 'px', left: left + 'px' }">
        <div id="paneContent">
            <span style="float: right; margin: 3px; cursor: pointer;" @click="close()"> X </span>
            <input id="filterbox" placeholder="Filter" v-model="filter">
            <button @click="saveParametersToFile">save</button>
            <b-form-checkbox
              v-if="haveDefaults"
              v-model="showdiff">
                Show only changed
            </b-form-checkbox>
            <table id="params">
                <tr>
                    <th>Param</th>
                    <th>Value</th>
                    <th v-if="haveDefaults">Default</th>
                </tr>
                <tr v-for="param in filteredData" v-bind:key="param">
                    <td>{{ param }}</td>
                    <template v-if="haveDefaults">
                      <td>{{ isDefaultParam(param) ? '→' : printParam(state.params.values[param])}}</td>
                      <td>{{ printParam(state.defaultParams[param]) }}</td>
                    </template>
                    <template v-else>
                      <td>{{printParam(state.params.values[param])}}</td>
                    </template>
                </tr>
          </table>
        </div>
    </div>
</template>

<script>
import { store } from '../Globals.js'
import { baseWidget } from './baseWidget'
import { saveAs } from 'file-saver'

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
            forceRecompute: 0,
            showdiff: false
        }
    },
    methods: {
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
        saveParametersToFile () {
            let parameterNameMaxSize = 0

            // Sort parameters alphabetically
            // We take advantage of sort to also calculate the parameter name maximum size
            const parameters = Object.entries(this.state.params.values).sort((first, second) => {
                parameterNameMaxSize = Math.max(parameterNameMaxSize, first[0].length)
                parameterNameMaxSize = Math.max(parameterNameMaxSize, second[0].length)

                if (first[0] < second[0]) {
                    return -1
                }
                if (first[0] > second[0]) {
                    return 1
                }
                return 0
            })

            let content = ''

            content += `# Parameters extracted from file ${this.state.file}\n`
            content += `# Date: ${new Date()}\n`

            const fileName = `${this.state.file}.params`

            for (const param of parameters) {
                // Calculate space between name and value to make it pretty
                const space = Array(parameterNameMaxSize - param[0].length + 2).join(' ')
                content += `${param[0]}${space}${param[1]}\n`
            }

            const file = new File([content], `${fileName}.txt`, { type: 'text/plain' })
            saveAs(file)
        },
        setup () {
        },
        printParam (param) {
            // prints number with just enough decimal places, up to 3, ommiting trailing zeroes
            return parseFloat(param).toFixed(Math.min(3, Math.max(0, 3 - Math.floor(param).toString().length)))
        },
        isDefaultParam (param) {
            return this.state.params.values[param] === this.state.defaultParams[param]
        }
    },
    computed: {
        haveDefaults () {
            return Object.keys(this.state.defaultParams).length > 0
        },
        filteredData () {
            // eslint-disable-next-line
            let potato = this.forceRecompute
            return Object.keys(this.state.params.values)
                .filter(
                    key => key.indexOf(this.filter.toUpperCase()) !== -1
                )
                .filter(
                    key => {
                        if (this.showdiff) {
                            return this.state.params.values[key] !== this.state.defaultParams[key]
                        } else {
                            return true
                        }
                    }
                )
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
