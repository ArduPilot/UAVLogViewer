<template>
    <div>
        <li class="type">
            <div v-b-toggle.plotsetupcontent>
                <a class="section"> Plots Setup
                    <i class="expand fas fa-caret-down"></i></a>
            </div>
        </li>
        <b-collapse class="menu-content collapse out" id="plotsetupcontent" visible>
            <ul class="colorpicker">

                <li :key="field.name" class="field plotsetup" v-for="field in state.fields">
                    <p class="plotname">{{field.name}}</p>
                    <select v-model.number="field.axis">
                        <option v-bind:key="'axisnumber'+axis" v-for="axis in state.allAxis">{{axis}}</option>
                    </select>
                    <select :style="{color: field.color}" v-model="field.color">
                        <option
                            v-bind:key="'axisColor'+color"
                            :style="{color: color}"
                            v-bind:value="color"
                            v-for="color in state.allColors">■
                        </option>
                    </select>
                    <a class="remove-button" @click="$eventHub.$emit('togglePlot', field.name)">
                        <i class="expand fas fa-trash" title="Remove data"></i>
                    </a>

                </li>
                <li v-if="state.fields.length === 0">  Please plot something first.</li>
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

    /* COLOR PICKER */

    ul.colorpicker {
        font-family: 'Montserrat', sans-serif;
    }

    ul.colorpicker li {
        cursor: default;
        font-size: 13px;
        padding: 5px;
    }

    ul.colorpicker li:hover {
        background-color: #2E2E2E;
        border-left: 3px solid #2E2E2E;
    }

    ul.colorpicker li a {
        cursor: pointer;
    }

    li.field {
        line-height: 20px;
        padding-left: 20px;
        font-size: 90%;
    }

    li.plotsetup {
        display: block;
    }

    i {
        margin: 5px;
        padding: 0;
    }

    p.plotname {
        display: inline-block;
        line-height: 15px;
        margin-bottom: 0;
        font-size: 13px;
        width: 60%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        direction: rtl;
    }

    select {
        display: inline;
        border-radius: 3px;
        border: 1px solid rgb(156, 156, 156);
        background-color: rgb(255, 255, 255);
        padding: 1px 2px;
        color: #838282;
    }

    select:focus {
        border: 1.5px solid #d47f00;
        outline: none;
    }

    select option {
        background-color: rgb(216, 215, 215);
    }

    select option:hover {
        background-color: #d47f00;
    }

    .fa-trash {
        margin: 1px;
        font-size: 10px;
    }

/* MEDIA QUERIES */

   @media (min-width: 1000px) and (max-width: 1440px) {
       p.plotname {
           width: 55%;
       }
   }

   @media (min-width: 2000px) {
       p.plotname {
           width: 75%;
       }       
   }

</style>
