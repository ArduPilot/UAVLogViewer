<template>
  <div v-if="hasMessages">

    <li  v-if="!state.map_on" @click="state.map_on=true">
      <a class="section" >
        <i class="fas fa-eye fa-lg"></i> Show 3D View</a>
    </li>
    <li v-if="state.map_on" @click="state.map_on=false">
      <a class="section"  >
        <i class="fas fa-eye-slash fa-lg"></i> Hide 3D View</a>
    </li>
    <li v-if="state.plot_on" @click="state.plot_on=false" >
    <a class="section" >
      <i class="fas fa-eye-slash fa-lg"></i> Hide Plot</a>
    </li>

    <li v-b-toggle="'messages'">
      <a class="section" >
        <i class="fas fa-signature fa-lg"></i> Plot
        <i class="fas fa-caret-down"></i></a>
    </li>
    <b-collapse id="messages" >
    <template v-for="(message, key) in messageTypes">
      <li class="type" v-bind:key="key">
        <div v-b-toggle="'type' + key" >
          <a class="section" >{{key}}
            <i class="expand fas fa-caret-down"></i></a>
        </div>
      </li>
      <b-collapse :id="'type' + key" v-bind:key="key+'1'">
      <template v-for="item in message.complexFields">
        <li class="field" v-bind:key="key+'.'+item.name">
          <a >
            <b-form-checkbox v-if="isPlottable(key,item.name)" v-model="checkboxes[key].fields[item.name]" @change="toggle($event, key, item.name)"> {{item.name}} ({{item.units}})</b-form-checkbox>
          </a>
        </li>
        </template>
      </b-collapse>
    </template>
    </b-collapse>
  </div>
</template>
<script>

import Vue from 'vue'
import {store} from './Globals.js'

export default {
    name: 'message-menu',
    data () {
        return {
            checkboxes: {},
            state: store,
            messages: {},
            messageTypes: []
        }
    },
    created () {
        this.$eventHub.$on('messageTypes', this.handleMessageTypes)
    },
    beforeDestroy () {
        this.$eventHub.$off('messages')
    },
    methods: {
        handleMessages () {
            let newMessages = {}
            // populate list of message types
            for (let messageType of Object.keys(this.state.messages)) {
                this.$set(this.checkboxes, messageType, this.getMessageNumericField(this.state.messages[messageType][0]))
                newMessages[messageType] = this.getMessageNumericField(this.state.messages[messageType][0])
            }

            // populate checkbox status
            for (let messageType of Object.keys(this.state.messages)) {
                this.checkboxes[messageType] = {state: false, indeterminate: false, fields: {}}
                for (let field of this.getMessageNumericField(this.state.messages[messageType].fields[0])) {
                    this.checkboxes[messageType].fields[field] = false
                }
            }
            this.messages = newMessages
        },
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
                        }
                        else {
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
        updateType (type) {
            if (Object.keys(this.messages).indexOf(type) < 0) {
                this.$eventHub.$emit('loadType', type)
            }
        },
        toggle (state, message, item) {
            if (state) {
                this.state.plot_on = true
                Vue.nextTick(function () {
                    this.$eventHub.$emit('addPlot', message + '.' + item)
                }.bind(this))
            } else {
                this.$eventHub.$emit('hidePlot', message + '.' + item)
            }
        },

        isPlottable(msgtype, item) {
            if ( item === 'TimeUS') {
                return false
            }
            return true
        },

        hidePlots () {
            for (let message of Object.keys(this.checkboxes)) {
                this.checkboxes[message].state = false
                this.checkboxes[message].indeterminate = false
                for (let field of Object.keys(this.checkboxes[message].fields)) {
                    this.checkboxes[message].fields[field] = false
                }
            }
            this.state.plot_on = false
        }
    },
    computed: {
        hasMessages () {
            return Object.keys(this.messageTypes).length > 0
        }
    }

}
</script>
<style scoped>
    i {
        margin: 10px;
    }
    i.expand {
      float:right;
    }

    li>div {
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
    margin-bottom: 8px
  }
</style>
