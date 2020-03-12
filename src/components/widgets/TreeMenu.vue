<template>
    <div>
        <li v-b-toggle="label"  :style="{'margin-left': ''+level*15+'px'}">
            <a class="section">
                {{label}}
                <i class="fas fa-caret-down"></i></a>
        </li>
        <template v-if="nodes.length === undefined">
            <b-collapse :id="label">
                <template v-for="(newNode, nodeName) in nodes">
                    <tree-menu
                        v-if="newNode.length === undefined && newNode.messages === undefined"
                        :label="nodeName"
                        :nodes="newNode"
                        :level="level+1"
                        :name="name+nodeName+ '/'"
                        :key="newNode+nodeName">
                    </tree-menu>
                    <li :style="{'margin-left': ''+(level+1)*15+'px'}"
                        v-if="newNode.messages !== undefined && newNode.messages.length !== undefined"
                        class="type"
                        v-bind:key="nodeName">
                        <a
                            @click="openPreset(newNode.messages)"
                            class="section"
                        >
                            {{nodeName}}
                        </a>
                        <a @click="deletePreset(name+nodeName)" v-if="newNode.user">
                            <i class="remove-icon fas fa-trash" title="Delete preset"></i>
                        </a>

                    </li>

                </template>
            </b-collapse>
        </template>

    </div>
</template>

<script>
import {store} from '../Globals.js'

export default {
    props: {
        label: String,
        nodes: Object,
        level: Number,
        name: {
            type: String,
            default: ''
        }
    },
    name: 'tree-menu',
    data () {
        return {
            state: store
        }
    },
    methods: {
        deletePreset (preset) {
            let myStorage = window.localStorage
            let saved = myStorage.getItem('savedFields')
            if (saved === null) {
                return
            } else {
                saved = JSON.parse(saved)
            }
            delete saved[preset]
            myStorage.setItem('savedFields', JSON.stringify(saved))
            this.$eventHub.$emit('presetsChanged')
        },
        openPreset (preset) {
            this.$eventHub.$emit('clearPlot')
            this.state.plot_on = true
            this.$nextTick(function () {
                let msgs = []
                for (let msg of preset) {
                    msgs.push([msg[0], msg[1], msg[2]])
                }
                this.$eventHub.$emit('addPlots', msgs)
            })
        }
    }
}

</script>

<style scoped>

</style>
