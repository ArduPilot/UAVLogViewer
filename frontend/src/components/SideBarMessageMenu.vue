<template>
    <div v-if="hasMessages">

        <!--<li v-if="state.plotOn" @click="state.plotOn=!state.plotOn">-->
        <!--<a class="section">-->
        <!--<i class="fas fa-eye-slash fa-lg"></i> Toggle Plot</a>-->
        <!--</li>-->
        <tree-menu
            v-if="Object.keys(availableMessagePresets).length > 0"
            :nodes="availableMessagePresets"
            :label="'Presets'"
            :clean-name="'Presets'"
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
            <template v-for="key of Object.keys(this.messageTypesFiltered).sort()">
                <li class="type" v-bind:key="key">
                    <div
                        v-b-toggle="'type' + key"
                        :title="messageDocs[key.split('[')[0]] ? messageDocs[key.split('[')[0]].doc : ''"
                    >
                        <a class="section">{{key}} <span v-if="messageTypes[key].isArray">{{"[...]"}}</span>
                            <i class="expand fas fa-caret-down"></i></a>
                    </div>
                </li>
                <b-collapse :id="'type' + key" v-bind:key="key+'1'">
                    <template v-for="item in messageTypes[key].complexFields">
                        <li @click="toggle(key, item.name)"
                            class="field"
                            :title="messageDocs[key] ? messageDocs[key][item.name] : ''"
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
import { store } from './Globals.js'
import TreeMenu from './widgets/TreeMenu.vue'
import fastXmlParser from 'fast-xml-parser'

export default {
    name: 'message-menu',
    components: { TreeMenu },
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
            userPresets: {},
            messageDocs: {}
        }
    },
    created () {
        this.$eventHub.$on('messageTypes', this.handleMessageTypes)
        this.$eventHub.$on('presetsChanged', this.loadLocalPresets)
        this.messagePresets = this.loadXmlPresets()
        this.messageDocs = this.loadXmlDocs()
        this.loadLocalPresets()
    },
    beforeDestroy () {
        this.$eventHub.$off('messageTypes')
    },
    methods: {
        loadXmlPresets () {
            // eslint-disable-next-line
            const graphs = {}
            const files = [
                require('../assets/mavgraphs.xml'),
                require('../assets/mavgraphs2.xml'),
                require('../assets/ekfGraphs.xml'),
                require('../assets/ekf3Graphs.xml')
            ]
            for (const contents of files) {
                const result = fastXmlParser.parse(contents.default, { ignoreAttributes: false })
                const igraphs = result.graphs
                for (const graph of igraphs.graph) {
                    let i = ''
                    const name = graph['@_name']
                    if (!Array.isArray(graph.expression)) {
                        graph.expression = [graph.expression]
                    }
                    for (const expression of graph.expression) {
                        const fields = []
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
            }
            return graphs
        },
        loadLocalPresets () {
            const saved = window.localStorage.getItem('savedFields')
            if (saved !== null) {
                this.userPresets = JSON.parse(saved)
                for (const preset in this.userPresets) {
                    for (const message in this.userPresets[preset]) {
                        // Field 3 means it is a user preset and can be deleted
                        this.userPresets[preset][message][3] = 1
                    }
                }
            }
        },
        loadXmlDocs () {
            const logDocs = {}
            const files = [
                require('../assets/logmetadata/plane.xml'),
                require('../assets/logmetadata/copter.xml'),
                require('../assets/logmetadata/tracker.xml'),
                require('../assets/logmetadata/rover.xml')
            ]
            for (const contents of files) {
                const result = fastXmlParser.parse(contents.default, { ignoreAttributes: false })
                const igraphs = result.loggermessagefile
                for (const graph of igraphs.logformat) {
                    logDocs[graph['@_name']] = { doc: graph.description }
                    for (const field of graph.fields.field) {
                        logDocs[graph['@_name']][field['@_name']] = field.description
                    }
                }
            }
            return logDocs
        },
        handleMessageTypes (messageTypes) {
            if (this.$route.query.plots) {
                this.state.plotOn = true
            }
            const newMessages = {}
            // populate list of message types
            for (const messageType of Object.keys(messageTypes)) {
                if (messageTypes[messageType].instances !== undefined) {
                    continue
                }
                this.$set(this.checkboxes, messageType, messageTypes[messageType].expressions.expressions)
                newMessages[messageType] = messageTypes[messageType]
            }
            // populate checkbox status
            for (const messageType of Object.keys(messageTypes)) {
                if (messageTypes[messageType].instances !== undefined) {
                    continue
                }
                this.checkboxes[messageType] = { expressions: {} }
                // for (let field of this.getMessageNumericField(this.state.messages[messageType][0])) {
                for (const field of messageTypes[messageType].expressions) {
                    if (this.state.plotOn) {
                        this.checkboxes[messageType].expressions[field] =
                            this.$route.query?.plots?.indexOf(messageType + '.' + field) !== -1
                    } else {
                        this.checkboxes[messageType].expressions[field] = false
                    }
                }
            }
            this.messageTypes = newMessages
            this.$set(this.state, 'messageTypes', newMessages)
        },
        isPlotted (message, field) {
            const fullname = message + '.' + field
            for (const field of this.state.expressions) {
                if (field.name === fullname) {
                    return true
                }
            }
            return false
        },
        getMessageNumericField (message) {
            const numberFields = []
            if (message && message.fieldnames) {
                for (const field of message.fieldnames) {
                    if (!isNaN(message[field])) {
                        numberFields.push(field)
                    }
                }
            }
            return numberFields
        },
        toggle (message, item) {
            this.state.plotOn = true
            this.$nextTick(function () {
                this.$eventHub.$emit('togglePlot', message + '.' + item)
            })
        },
        isPlottable (msgtype, item) {
            return item !== 'TimeUS'
        },
        collapse (name) {
            if (document.getElementById(name) &&
                document.getElementById(name).style &&
                document.getElementById(name).style.display !== 'none') {
                this.$root.$emit('bv::toggle::collapse', name)
            }
        },
        expand (name) {
            if (document.getElementById(name) &&
                document.getElementById(name).style &&
                document.getElementById(name).style.display === 'none') {
                this.$root.$emit('bv::toggle::collapse', name)
            }
        },
        findMessagesInExpression (expression) {
            // delete all expressions after dots (and dots)
            const toDelete = /\.[A-Za-z-0-9_]+/g
            const name = expression.replace(toDelete, '')
            const RE = /[A-Z][A-Z0-9_]+(\[0-9\])?/g
            const fields = name.match(RE)
            if (fields === null) {
                return []
            }
            return fields
        },
        isAvailable (msg) {
            const msgRe = /[A-Z][A-Z0-9_]+(\[[0-9]\])?(\.[a-zA-Z0-9_]+)?/g
            const match = msg[0].match(msgRe)
            if (!match) {
                return true
            }
            const msgName = match[0].split('.')[0]
            if (!this.messageTypes[msgName]) {
                return false
            }
            const fieldName = match[0].split('.')[1]
            if (fieldName === undefined) {
                return true
            }
            if (!this.messageTypes[msgName].complexFields[fieldName]) {
                console.log('missing field ' + msgName + '.' + fieldName)
                return false
            }
            return true
        }
    },
    computed: {
        hasMessages () {
            return Object.keys(this.messageTypes).length > 0
        },
        messageTypesFiltered () {
            const filtered = {}
            for (const key of Object.keys(this.messageTypes)) {
                if (this.hiddenTypes.indexOf(key) === -1) {
                    if (this.filter === '') {
                        this.collapse('type' + key)
                        filtered[key] = this.messageTypes[key]
                        continue
                    }
                    if (this.messageTypes[key].expressions
                        .filter(field => field.toLowerCase().indexOf(this.filter.toLowerCase()) !== -1).length > 0) {
                        filtered[key] = this.messageTypes[key]
                        // console.log('type' + key, document.getElementById('type' + key))
                        this.expand('type' + key)
                    } else {
                        this.collapse('type' + key)
                    }
                }
            }
            return filtered
        },
        availableMessagePresets () {
            const dict = {}
            // do it for default messages
            for (const [key, value] of Object.entries(this.messagePresets)) {
                let missing = false
                let color = 0
                for (const field of value) {
                    // If all of the expressions match, add this and move on
                    if (field[0] === '') {
                        continue
                    }
                    missing = missing || !this.isAvailable(field)
                    if (!missing) {
                        if (!(key in dict)) {
                            dict[key] = { messages: [[...field, color++]] }
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
                for (const field of value) {
                    // If all of the expressions match, add this and move on
                    missing = missing || !this.isAvailable(field)
                    if (!missing) {
                        if (!(key in dict)) {
                            dict[key] = { messages: [[...field, color++]] }
                        } else {
                            dict[key].messages.push([...field, color++])
                        }
                    }
                }
            }
            const newDict = {}
            for (const [key, value] of Object.entries(dict)) {
                let current = newDict
                const fields = key.trim().split('/')
                const lastField = fields.pop()
                for (const field of fields) {
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
        line-height: 29px;
        padding-left: 40px;
        font-size: 90%;
        display: inline-block;
        vertical-align: middle;
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

    @media (min-width: 575px) and (max-width: 992px) {
       a {
        padding: 2px 60px 2px 55px !important;
       }
    }

</style>
