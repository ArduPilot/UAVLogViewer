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
            <li>
                <input id="filterbox" placeholder="Type here to filter..." v-model="filter">
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
                        <li @click="toggle(key, item.name)" class="field"
                            v-bind:key="key+'.'+item.name" v-if="isPlottable(key,item.name) && item.name.indexOf(filter) !== -1">
                            <a> {{item.name}}
                                <span v-if="item.units!=='?' && item.units!==''"> ({{item.units}})</span>
                            </a>

                            <a @click="$eventHub.$emit('togglePlot', field.name)" v-if="isPlotted(key,item.name)">
                                <i class="remove-icon fas fa-times" title="Remove data"></i>
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
            messagePresets: {
                'Attitude/Attitude Control': [
                    'NAV_CONTROLLER_OUTPUT.nav_roll',
                    'NAV_CONTROLLER_OUTPUT.nav_pitch',
                    'ATTITUDE.roll',
                    'ATTITUDE.pitch'
                ],
                'Attitude/Roll and Pitch': [
                    'ATT.Roll',
                    'ATT.Pitch'
                ],
                'Servos/Servos 1-4': [
                    'SERVO_OUTPUT_RAW.servo1_raw',
                    'SERVO_OUTPUT_RAW.servo2_raw',
                    'SERVO_OUTPUT_RAW.servo3_raw',
                    'SERVO_OUTPUT_RAW.servo4_raw'
                ],
                'Sensors/Accelerometer/Vibration': [
                    'VIBRATION.vibration_x',
                    'VIBRATION.vibration_y',
                    'VIBRATION.vibration_z'
                ]
            }
        }
    },
    created () {
        this.$eventHub.$on('messageTypes', this.handleMessageTypes)
    },
    beforeDestroy () {
        this.$eventHub.$off('messageTypes')
    },
    methods: {
        handleMessageTypes (messageTypes) {
            if (this.$route.query.hasOwnProperty('plots')) {
                this.state.plot_on = true
            }

            let newMessages = {}
            // populate list of message types
            for (let messageType of Object.keys(messageTypes)) {
                this.$set(this.checkboxes, messageType, messageTypes[messageType].fields.fields)
                newMessages[messageType] = messageTypes[messageType]
            }

            // populate checkbox status
            for (let messageType of Object.keys(messageTypes)) {
                this.checkboxes[messageType] = {fields: {}}
                // for (let field of this.getMessageNumericField(this.state.messages[messageType][0])) {
                for (let field of messageTypes[messageType].fields) {
                    if (this.state.plot_on) {
                        if (this.$route.query.plots.indexOf(messageType + '.' + field) !== -1) {
                            this.checkboxes[messageType].fields[field] = true
                            // this.checkboxes[messageType].indeterminate = true
                        } else {
                            this.checkboxes[messageType].fields[field] = false
                        }
                    } else {
                        this.checkboxes[messageType].fields[field] = false
                    }
                }
            }
            this.messageTypes = newMessages
            this.state.messageTypes = newMessages
        },
        isPlotted (message, field) {
            let fullname = message + '.' + field
            for (let field of this.state.fields) {
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
                    if (this.messageTypes[key].fields.filter(field => field.indexOf(this.filter) !== -1).length > 0) {
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
            for (const [key, value] of Object.entries(this.messagePresets)) {
                for (let field of value) {
                    // If any of the fields match, add this and move on
                    if (field.split('.')[0] in this.state.messageTypes) {
                        if (!(key in dict)) {
                            dict[key] = [field]
                        } else {
                            dict[key].push(field)
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
        },
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
        line-height: 20px;
        padding-left: 40px;
        font-size: 90%;
        display: inline-block;
        width: 100%;
    }

    li.type {
        line-height: 25px;
        padding-left: 30px;
        font-size: 90%;
    }

    input {
        margin-left: 30px;
        margin-right: 30px;
        -webkit-border-radius: 10px;
        -moz-border-radius: 10px;
        border-radius: 10px;
        background-color: #4f5b69;
        color: white;
        width: 85%;
    }

    ::placeholder { /* Chrome, Firefox, Opera, Safari 10.1+ */
        color: #AAAAAA;
        opacity: 1; /* Firefox */
    }

    :-ms-input-placeholder { /* Internet Explorer 10-11 */
        color: gainsboro;
    }

    ::-ms-input-placeholder { /* Microsoft Edge */
        color: gainsboro;
    }

    i.remove-icon {
        float: right;
    }
</style>
<style>
    .custom-control-label {
        margin-bottom: 0;
    }
</style>
