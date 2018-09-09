<template>
  <div v-if="hasMessages">

    <li  v-if="!state.map_on" @click="state.map_on=true">
      <a class="section" href="#">
        <i class="fas fa-eye fa-lg"></i> Show 3D View</a>
    </li>
    <li v-if="state.map_on" @click="state.map_on=false">
      <a class="section" href="#" >
        <i class="fas fa-eye-slash fa-lg"></i> Hide 3D View</a>
    </li>
    <li v-if="state.map_on">
      <a href="#" @click="$eventHub.$emit('change-camera')"><i class="fas fa-video "></i> Camera Mode </a>
    </li>
    <li v-if="state.plot_on" @click="state.plot_on=false" >
    <a class="section" href="#">
      <i class="fas fa-eye-slash fa-lg"></i> Hide Plot</a>
    </li>

    <li v-b-toggle="'messages'">
      <a class="section" href="#">
        <i class="fas fa-signature fa-lg"></i> Plot
        <i class="fas fa-caret-down"></i></a>
    </li>
    <b-collapse id="messages" >
    <template v-for="(message, key) in messages">
      <li class="type" v-bind:key="key">
        <div v-b-toggle="'type' + key" >
          <b-form-checkbox v-model="checkboxes[key].state"
                         :indeterminate="checkboxes[key].indeterminate"
                         @change="toggleType($event, key)">
        </b-form-checkbox>
          <a class="section" href="#">{{key}}
            <i class="expand fas fa-caret-down"></i></a>
        </div>
      </li>
      <b-collapse :id="'type' + key" >
      <template v-for="item in message">
        <li class="field">
          <a href="#">
            <b-form-checkbox v-model="checkboxes[key].fields[item]" @change="toggle($event, key, item)"> {{item}}</b-form-checkbox>
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
      messages: {}
    }
  },
  created () {
    this.$eventHub.$on('messages', this.handleMessages)
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
        for (let field of this.getMessageNumericField(this.state.messages[messageType][0])) {
          this.checkboxes[messageType].fields[field] = false
        }
      }
      this.messages = newMessages
    },
    getMessageNumericField (message) {
      let numberFields = []
      for (let field of message.fieldnames) {
        if (!isNaN(message[field])) {
          numberFields.push(field)
        }
      }
      return numberFields
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
      Vue.nextTick(function () {
        for (let messagekey of Object.keys(this.checkboxes)) {
          let message = this.checkboxes[messagekey]
          let allTrue = true
          let allFalse = true
          for (let fieldkey of Object.keys(message.fields)) {
            let field = message.fields[fieldkey]
            if (field) {
              allFalse = false
            } else {
              allTrue = false
            }
          }
          if (allTrue) {
            this.checkboxes[messagekey].state = true
            this.checkboxes[messagekey].indeterminate = false
          } else if (allFalse) {
            this.checkboxes[messagekey].state = false
            this.checkboxes[messagekey].indeterminate = false
          } else {
            this.checkboxes[messagekey].indeterminate = true
          }
        }
      }.bind(this))
    },
    toggleType (state, message) {
      for (let field of this.messages[message]) {
        this.checkboxes[message].fields[field] = state
      }
      if (state) {
        this.state.plot_on = true
      }
      Vue.nextTick(function () {
        for (let field of this.messages[message]) {
          this.checkboxes[message].fields[field] = state
          if (state) {
            this.$eventHub.$emit('addPlot', message + '.' + field)
          } else {
            this.$eventHub.$emit('hidePlot', message + '.' + field)
          }
        }
      }.bind(this))
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
      return Object.keys(this.messages).length > 0
    }
  }

}
</script>
<style scoped>
    i {
        margin: 10px;
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
