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
            <button class="save-preset" v-if="state.fields.length > 0" v-b-modal.modal-prevent-closing>
            <i class="fa fa-check-circle" aria-hidden="true"></i>Save Preset</button>
        </b-collapse>
        <b-modal
            id="modal-prevent-closing"
            ref="modal"
            @show="resetModal"
            @hidden="resetModal"
            @ok="handleOk"
        >
            <form ref="form" @submit.stop.prevent="handleOk">
                <b-form-group
                    label="New Preset Name"
                    label-for="name-input"
                >
                    <b-form-input
                        id="name-input"
                        v-model="name"
                        placeholder="Attitude/OtherRoll"
                        required
                    ></b-form-input>
                </b-form-group>
            </form>
        </b-modal>
    </div>
</template>
<script>
import {store} from './Globals.js'

export default {
    name: 'plotSetup',
    data () {
        return {
            state: store,
            name: ''
        }
    },
    methods: {
        savePreset (name) {
            let myStorage = window.localStorage
            let saved = myStorage.getItem('savedFields')
            if (saved === null) {
                saved = {}
            } else {
                saved = JSON.parse(saved)
            }
            saved[name] = []
            for (let field of this.state.fields) {
                saved[name].push([field.name, field.axis, field.color, field.function])
            }
            myStorage.setItem('savedFields', JSON.stringify(saved))
            this.$eventHub.$emit('presetsChanged')
        },

        resetModal () {
            this.name = ''
        },
        handleOk (bvModalEvt) {
            // Prevent modal from closing
            bvModalEvt.preventDefault()

            if (this.name.lenght > 0) {
                return
            }
            this.savePreset(this.name)

            // Hide the modal manually
            this.$nextTick(() => {
                this.$refs.modal.hide()
            })
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
        background-color: #1E2536;
        border-left: 3px solid #1E2536;
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

/* SAVE PRESET BUTTON */

    .save-preset {
        background-color:rgb(33, 41, 61);
        color: #fff;
        border-radius: 15px;
        padding: 0px 10px 0px 0px;
        border: 1px solid rgba(91, 100, 117, 0.76);
        margin-left: 32%;
        font-size: 13px;
    }

    .save-preset:hover {
        background-color: rgb(47, 58, 87);
        box-shadow: 0px 0px 12px 0px rgba(37, 78, 133, 0.55);
        transition: all 0.5s ease;
    }

    .save-preset:focus {
        outline: none;
    }

/* MEDIA QUERIES */

   @media (min-width: 1000px) and (max-width: 1440px) {
       p.plotname {
           width: 55%;
       }
   }

   @media (min-width: 2000px) {
       p.plotname {
           width: 60%;
       }
   }

</style>
