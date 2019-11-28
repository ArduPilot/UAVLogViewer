<template>
    <div>
        <li class="type">
            <div v-b-toggle.plotsetupcontent>
                <a class="section">Plots Setup
                    <i class="expand fas fa-caret-down"></i></a>
            </div>
        </li>
        <b-collapse class="menu-content collapse out" id="plotsetupcontent" visible>
            <ul class="colorpicker">

                <li :key="field.name" class="field plotsetup" v-for="field in state.fields">
                    <span class="plotname">{{field.name}}</span>
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

    /* COLOR PICKER */

    ul.colorpicker {
        font-family: 'Montserrat', sans-serif;
    }

    ul.colorpicker li {
        cursor: default;
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
    span.plotname {
        white-space: nowrap;
        overflow: hidden;
        direction: rtl;
        display: block;
    }

</style>
