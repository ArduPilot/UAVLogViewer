<template>
  <div v-if="hasMessages">

    <li  v-if="!$parent.$parent.$parent.map_on" @click="$eventHub.$emit('show-map')">
      <a class="section" href="#">
        <i class="fas fa-eye fa-lg"></i> Show 3D View</a>
    </li>
    <li v-if="$parent.$parent.$parent.map_on" @click="$eventHub.$emit('hide-map')">
      <a class="section" href="#" >
        <i class="fas fa-eye-slash fa-lg"></i> Hide 3D View</a>
    </li>
    <li v-if="$parent.$parent.$parent.map_on">
      <a href="#" @click="$eventHub.$emit('change-camera')"><i class="fas fa-video "></i> Camera Mode </a>
    </li>
    <li v-if="$parent.$parent.$parent.plot_on" @click="hidePlots" >
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
      <li class="type">
        <b-form-checkbox v-model="checkboxes[key].state"
                         :indeterminate="checkboxes[key].indeterminate"
                         @change="toggleType($event, key)">
        </b-form-checkbox>
        <a v-b-toggle="'type' + message" class="section" href="#">{{key}}
          <i class="fas fa-caret-down"></i></a>
      </li>
      <b-collapse :id="'type' + message" >
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

export default {
  name: 'message-menu',
  data () {
    return {
      messages: {},
      checkboxes: {}
    }
  },
  created () {
    this.$eventHub.$on('messages', this.handleMessages)
  },
  beforeDestroy () {
    this.$eventHub.$off('messages')
  },
  methods: {
    handleMessages (messages) {
      let newMessages = {}
      // populate list of message types
      for (let messageType of Object.keys(messages)) {
        this.$set(this.checkboxes, messageType, this.getMessageNumericField(messages[messageType][0]))
        newMessages[messageType] = this.getMessageNumericField(messages[messageType][0])
      }

      // populate checkbox status
      for (let messageType of Object.keys(messages)) {
        this.checkboxes[messageType] = {state: false, indeterminate: false, fields: {}}
        for (let field of this.getMessageNumericField(messages[messageType][0])) {
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
        this.$eventHub.$emit('showPlot')
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
        this.$eventHub.$emit('showPlot')
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
      this.$eventHub.$emit('plotEmpty')
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

    .nav-side-menu ul,
    .nav-side-menu li {
        list-style: none;
        padding: 0px;
        margin: 0px;
        line-height: 35px;
        cursor: pointer;
        /*
          .collapsed{
             .arrow:before{
                       font-family: FontAwesome;
                       content: "\f053";
                       display: inline-block;
                       padding-left:10px;
                       padding-right: 10px;
                       vertical-align: middle;
                       float:right;
                  }
           }
      */
    }

    .nav-side-menu ul .sub-menu li.active a,
    .nav-side-menu li .sub-menu li.active a {
        color: #d19b3d;
    }

    .nav-side-menu ul .sub-menu li,
    .nav-side-menu li .sub-menu li {
        background-color: #181c20;
        border: none;
        line-height: 28px;
        border-bottom: 1px solid #23282e;
        margin-left: 0px;
    }

    .nav-side-menu ul .sub-menu li:hover,
    .nav-side-menu li .sub-menu li:hover {
        background-color: #020203;
    }

    .nav-side-menu ul .sub-menu li:before,
    .nav-side-menu li .sub-menu li:before {
        font-family: FontAwesome;
        content: "\f105";
        display: inline-block;
        padding-left: 10px;
        padding-right: 10px;
        vertical-align: middle;
    }

    .nav-side-menu li {
        padding-left: 0px;
        border-left: 3px solid #2e353d;
        border-bottom: 1px solid #23282e;
    }

    .nav-side-menu li a {
        text-decoration: none;
        color: #e1ffff;
    }

    .nav-side-menu li a i {
        padding-left: 0px;
        width: 20px;
        padding-right: 20px;
    }

    .nav-side-menu li:hover {
        border-left: 3px solid #d19b3d;
        background-color: #4f5b69;
        -webkit-transition: all 1s ease;
        -moz-transition: all 1s ease;
        -o-transition: all 1s ease;
        -ms-transition: all 1s ease;
        transition: all 1s ease;
    }

    @media (max-width: 767px) {

        main {
            height: 90%;
            margin-top: 50px;
        }
    }

    @media (min-width: 767px) {

        main {
            height: 100%;
        }
    }

    body {
        margin: 0px;
        padding: 0px;
    }

    i {
        margin: 10px;
    }

    ::-webkit-scrollbar {
        width: 12px;
        background-color: rgba(0, 0, 0, 0);
    }

    ::-webkit-scrollbar-thumb {
        border-radius: 5px;
        -webkit-box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.1);
        background-color: #1c437f;
    }
    li.field {
      line-height: 20px;
      padding-left: 40px;
      font-size: 90%;
    }

    li .field > a {

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
