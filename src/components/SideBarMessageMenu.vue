<template>
    <div v-if="hasMessages">

        <!--<li v-if="state.plot_on" @click="state.plot_on=!state.plot_on">-->
        <!--<a class="section">-->
        <!--<i class="fas fa-eye-slash fa-lg"></i> Toggle Plot</a>-->
        <!--</li>-->
        <tree-menu
            v-if="Object.keys(availableMessagePresets).length > 0"
            :nodes="availableMessagePresets"
            :label="'Presets'"
            :level="0">

        </tree-menu>
        <li v-b-toggle="'messages'">
            <a class="section">
                Plot Individual Field
                <i class="fas fa-caret-down"></i></a>
        </li>

        <b-collapse id="messages">
            <li class="input-li">
                <input id="filterbox" placeholder=" Type here to filter..." v-model="filter">
            </li>
            <template v-for="(message, key) in messageTypesFiltered">
                <li class="type" v-bind:key="key">
                    <div v-b-toggle="'type' + key">
                        <a class="section">{{key}}
                            <i class="expand fas fa-caret-down"></i></a>
                    </div>
                </li>
                <b-collapse :id="'type' + key" v-bind:key="key+'1'">
                    <template v-for="item in message.complexFields">
                        <li @click="toggle(key, item.name)"
                            class="field"
                            v-bind:key="key+'.'+item.name"
                            v-if="isPlottable(key,item.name)
                                && item.name.toLowerCase().indexOf(filter.toLowerCase()) !== -1">
                            <a> {{item.name}}
                                <span v-if="item.units!=='?' && item.units!==''"> ({{item.units}})</span>
                            </a>

                            <a @click="$eventHub.$emit('togglePlot', field.name)" v-if="isPlotted(key,item.name)">
                                <i class="remove-icon fas fa-trash" title="Remove data"></i>
                            </a>
                        </li>
                    </template>
                </b-collapse>
            </template>
        </b-collapse>
    </div>
</template>
<script>
import {store} from './Globals.js'
import TreeMenu from './widgets/TreeMenu'
import fastXmlParser from 'fast-xml-parser'

export default {
    name: 'message-menu',
    components: {TreeMenu},
    data () {
        return {
            filter: '',
            checkboxes: {},
            state: store,
            messages: {},
            messageTypes: [],
            hiddenTypes: [
                'MISSION_CURRENT',
                'SYSTEM_TIME', 'HEARTBEAT', 'STATUSTEXT',
                'COMMAND_ACK', 'PARAM_VALUE', 'AUTOPILOT_VERSION',
                'TIMESYNC', 'MISSION_COUNT', 'MISSION_ITEM_INT',
                'MISSION_ITEM', 'MISSION_ITEM_REACHED', 'MISSION_ACK',
                'HOME_POSITION',
                'STRT',
                'ARM',
                'STAT',
                'FMT',
                'PARM',
                'MSG',
                'CMD',
                'MODE',
                'ORGN',
                'FMTU',
                'UNIT',
                'MULT'
            ],
            // TODO: lists are nor clear, use objects instead
            messagePresets: {
            },
            userPresets: {}
        }
    },
    created () {
        this.$eventHub.$on('messageTypes', this.handleMessageTypes)
        this.$eventHub.$on('presetsChanged', this.loadLocalPresets)
        this.messagePresets = this.loadXmlPresets()
        this.loadLocalPresets()
    },
    beforeDestroy () {
        this.$eventHub.$off('messageTypes')
    },
    methods: {
        loadXmlPresets () {
            // eslint-disable-next-line
            let contents = require('../assets/mavgraphs.xml')
            let graphs = {}
            let result = fastXmlParser.parse(contents.default, {ignoreAttributes: false})
            console.log(result)
            let igraphs = result['graphs']
            for (let graph of igraphs.graph) {
                let i = ''
                let name = graph['@_name']
                if (!Array.isArray(graph.expression)) {
                    graph.expression = [graph.expression]
                }
                for (const expression of graph.expression) {
                    let fields = []
                    for (let exp of expression.split(' ')) {
                        if (exp.indexOf(':') >= 0) {
                            exp = exp.replace(':2', '')
                            fields.push([exp, 1])
                        } else {
                            fields.push([exp, 0])
                        }
                    }
                    graphs[name + i] = fields
                    // workaround to avoid replacing a key
                    // TODO: implement this in a way that doesn't need this hack
                    i += ' '
                }
            }
            return graphs
        },
        loadLocalPresets () {
            let saved = window.localStorage.getItem('savedFields')
            if (saved !== null) {
                this.userPresets = JSON.parse(saved)
            }
        },
        handleMessageTypes (messageTypes) {
            if (this.$route.query.hasOwnProperty('plots')) {
                this.state.plot_on = true
            }
            let newMessages = {}
            // populate list of message types
            for (let messageType of Object.keys(messageTypes)) {
                this.$set(this.checkboxes, messageType, messageTypes[messageType].expressions.expressions)
                newMessages[messageType] = messageTypes[messageType]
            }
            // populate checkbox status
            for (let messageType of Object.keys(messageTypes)) {
                this.checkboxes[messageType] = {expressions: {}}
                // for (let field of this.getMessageNumericField(this.state.messages[messageType][0])) {
                for (let field of messageTypes[messageType].expressions) {
                    if (this.state.plot_on) {
                        this.checkboxes[messageType].expressions[field] =
                            this.$route.query.plots.indexOf(messageType + '.' + field) !== -1
                    } else {
                        this.checkboxes[messageType].expressions[field] = false
                    }
                }
            }
            this.messageTypes = newMessages
            this.state.messageTypes = newMessages
        },
        isPlotted (message, field) {
            let fullname = message + '.' + field
            for (let field of this.state.expressions) {
                if (field.name === fullname) {
                    return true
                }
            }
            return false
        },
        getMessageNumericField (message) {
            let numberFields = []
            if (message && message.hasOwnProperty('fieldnames')) {
                for (let field of message.fieldnames) {
                    if (!isNaN(message[field])) {
                        numberFields.push(field)
                    }
                }
            }
            return numberFields
        },
        toggle (message, item) {
            this.state.plot_on = true
            this.$nextTick(function () {
                this.$eventHub.$emit('togglePlot', message + '.' + item)
            })
        },
        isPlottable (msgtype, item) {
            return item !== 'TimeUS'
        }
    },
    computed: {
        hasMessages () {
            return Object.keys(this.messageTypes).length > 0
        },
        messageTypesFiltered () {
            let filtered = {}
            for (let key of Object.keys(this.messageTypes)) {
                if (this.hiddenTypes.indexOf(key) === -1) {
                    if (this.messageTypes[key].expressions
                        .filter(field => field.toLowerCase().indexOf(this.filter.toLowerCase()) !== -1).length > 0) {
                        filtered[key] = this.messageTypes[key]
                        // console.log('type' + key, document.getElementById('type' + key))
                        if (document.getElementById('type' + key) &&
                                document.getElementById('type' + key).style &&
                                document.getElementById('type' + key).style.display === 'none'
                        ) {
                            console.log(document.getElementById('type' + key).style.display)
                            this.$root.$emit('bv::toggle::collapse', 'type' + key)
                        }
                    }
                }
            }
            return filtered
        },
        availableMessagePresets () {
            let dict = {}
            let RE = /[A-Z][A-Z0-9_]+\b/g
            // do it for default messages
            for (const [key, value] of Object.entries(this.messagePresets)) {
                let missing = false
                let color = 0
                for (let field of value) {
                    // If all of the expressions match, add this and move on
                    if (field[0] === '') {
                        continue
                    }
                    for (let match of field[0].match(RE)) {
                        if (!(match in this.state.messageTypes)) {
                            missing = true
                            console.log(match + ' is missing!')
                        }
                    }
                    if (!missing) {
                        if (!(key in dict)) {
                            dict[key] = {messages: [[...field, color++]]}
                        } else {
                            dict[key].messages.push([...field, color++])
                        }
                    }
                }
                if (missing) {
                    delete dict[key]
                }
            }
            // And again for user presets
            for (const [key, value] of Object.entries(this.userPresets)) {
                let missing = false
                let color = 0
                for (let field of value) {
                    // If all of the expressions match, add this and move on
                    for (let match of field[0].match(RE)) {
                        if (!(match.split('.')[0] in this.state.messageTypes)) {
                            missing = true
                        }
                    }
                    if (!missing) {
                        if (!(key in dict)) {
                            dict[key] = {messages: [[...field, color++]]}
                        } else {
                            dict[key].messages.push([...field, color++])
                        }
                    }
                }
            }
            let newDict = {}
            for (const [key, value] of Object.entries(dict)) {
                let current = newDict
                let fields = key.split('/')
                let lastField = fields.pop()
                for (let field of fields) {
                    if (!(field in current)) {
                        console.log('overwriting ' + field)
                        current[field] = {}
                    }
                    current = current[field]
                }
                current[lastField] = value
            }
            return newDict
        }
    }
}
</script>
<style scoped>
    i {
        margin: 5px;
    }
    i.expand {
        float: right;
    }
    li > div {
        display: inline-block;
        width: 100%;
    }
    li.field {
        line-height: 25px;
        padding-left: 40px;
        font-size: 90%;
        display: inline-block;
        width: 100%;
    }
    li.type {
        line-height: 30px;
        padding-left: 10px;
        font-size: 85%;
    }
    input {
        margin: 12px 12px 15px 10px;
        border: 2px solid #ccc;
        -webkit-border-radius: 4px;
        -moz-border-radius: 4px;
        border-radius: 4px;
        background-color: rgba(255, 255, 255, 0.897);
        color: rgb(51, 51, 51);
        width: 92%;
    }
    input:focus {
        outline: none;
        border: 2px solid #135388;
    }
    .input-li:hover {
        background-color: rgba(30, 37, 54, 0.205);
        border-left: 3px solid rgba(24, 30, 44, 0.212);
    }
    ::placeholder { /* Chrome, Firefox, Opera, Safari 10.1+ */
        color: rgb(148, 147, 147);
        opacity: 1; /* Firefox */
    }
    :-ms-input-placeholder { /* Internet Explorer 10-11 */
        color: #2e2e2e;
    }
    ::-ms-input-placeholder { /* Microsoft Edge */
        color: #2e2e2e;
    }
    i.remove-icon {
        float: right;
    }

</style>
