<template>
    <div v-if="hasMessages">

        <!--<li v-if="state.plot_on" @click="state.plot_on=!state.plot_on">-->
            <!--<a class="section">-->
                <!--<i class="fas fa-eye-slash fa-lg"></i> Toggle Plot</a>-->
        <!--</li>-->

        <li v-b-toggle="'messages'">
            <a class="section">
                <i class="fas fa-signature fa-lg"></i> Plot
                <i class="fas fa-caret-down"></i></a>
        </li>
        <b-collapse id="messages">
            <template v-for="(message, key) in messageTypesFiltered">
                <li class="type" v-bind:key="key">
                    <div v-b-toggle="'type' + key">
                        <a class="section">{{key}}
                            <i class="expand fas fa-caret-down"></i></a>
                    </div>
                </li>
                <b-collapse :id="'type' + key" v-bind:key="key+'1'">
                    <template v-for="item in message.complexFields">
                        <li class="field" v-bind:key="key+'.'+item.name" @click="toggle(key, item.name)">
                            <a v-if="isPlottable(key,item.name)"> {{item.name}}
                                ({{item.units}})</a>
                        </li>
                    </template>
                </b-collapse>
            </template>
        </b-collapse>
    </div>
</template>
<script>

import {store} from './Globals.js'

export default {
    name: 'message-menu',
    data () {
        return {
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
            ]
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
                    filtered[key] = this.messageTypes[key]
                }
            }
            return filtered
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
        line-height: 20px;
        padding-left: 40px;
        font-size: 90%;
    }

    li.type {
        line-height: 25px;
        padding-left: 30px;
        font-size: 90%;
    }
</style>
<style>
    .custom-control-label {
        margin-bottom: 0;
    }
</style>
