<template>
    <div >
        <li class="type">
            <div v-b-toggle.plotsetupcontent>
                <a class="section"> <i data-v-03de825a="" class="fas fa-wrench fa-lg"></i>Plots Setup
                    <i class="expand fas fa-caret-down"></i></a>
            </div>
        </li>
        <b-collapse id="plotsetupcontent" visible class="menu-content collapse out">
            <ul class="colorpicker">

                <li class="field" v-for="(field, index) in state.fields" :key="field">
                    {{field}} <i :style="{color: state.axis[state.fieldAxis[index+1]]}" class="fas fa-square"></i>
                    <select v-model="state.fieldAxis[index+1]" :style="{color: state.axis[state.fieldAxis[index+1]]}">
                        <option  v-for="(color, colorIndex) in state.axis" :style="{color: color}" v-bind:value="colorIndex">{{colorIndex}}
                        </option>
                    </select>
                    <a @click="$eventHub.$emit('togglePlot', field)">
                        <i class="expand fas fa-times" title="Remove data"></i>
                    </a>

                </li>
                <li v-if="state.fields.length === 0"> Please plot something first.</li>
            </ul>

        </b-collapse>
    </div>
</template>
<script>

import {store} from './Globals.js'

export default {
    name: 'plotSetup',
    data () {
        return {
            state: store
        }
    }
}
</script>
<style>

    .nav-side-menu ul,
    .nav-side-menu li {
        list-style: none;
        padding: 0;
        margin: 0;
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
        padding-left: 10px;
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

    .tabholder a {
        border-top: 1px solid white;
        border-left: 1px solid white;
        border-right: 1px solid white;
        border-radius: 3px;
        padding-left: 5px;
        padding-right: 5px;
        font-weight: bold;
        background-color: #2E353D;
    }

    .tabholder a:hover {
        background-color: #4f5b69;
        -webkit-transition: all 1s ease;
        -moz-transition: all 1s ease;
        -o-transition: all 1s ease;
        -ms-transition: all 1s ease;
        transition: all 1s ease;
    }

    ul.colorpicker {
        font-family: 'FontAwesome';
    }

    ul.colorpicker li {
        cursor: default;
    }

    ul.colorpicker li a{
        cursor: pointer;
    }

    li.field {
        line-height: 20px;
        padding-left: 40px;
        font-size: 90%;
    }

    i {
        margin: 5px;
        padding: 0;
    }
</style>
