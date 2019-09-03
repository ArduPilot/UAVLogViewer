<template>
    <div>
        <li v-b-toggle="label"  :style="{'margin-left': ''+level*10+'px'}">
            <a class="section">
                {{label}}
                <i class="fas fa-caret-down"></i></a>
        </li>
        <template v-if="nodes.length === undefined">
            <b-collapse :id="label">
                <template v-for="(newNode, nodeName) in nodes">
                    <tree-menu
                        v-if="newNode.length === undefined"
                        :label="nodeName"
                        :nodes="newNode"
                        :level="level+1">
                    </tree-menu>
                    <li v-if="newNode.length !== undefined"
                        class="type"
                        v-bind:key="nodeName">
                        <a :style="{'margin-left': ''+(level+3)*10+'px'}"  @click="openPreset(newNode)" class="section">{{nodeName}}
                        </a>

                    </li>

                </template>
            </b-collapse>
        </template>

    </div>
</template>

<script>
import {store} from '../Globals.js'
import TreeMenu from './TreeMenu.vue'
export default {
    props: {
        label: String,
        nodes: Object,
        level: Number
    },
    name: 'tree-menu',
    data () {
        return {
            state: store
        }
    },
    methods: {
        openPreset (preset) {
            this.$eventHub.$emit('clearPlot')
            this.state.plot_on = true
            this.$nextTick(function () {
                for (let msg of preset) {
                    this.$eventHub.$emit('togglePlot', msg)
                }
            })
        }
    }
}

</script>

<style scoped>

</style>
