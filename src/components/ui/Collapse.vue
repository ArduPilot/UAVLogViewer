<template>
    <div v-show="show"><slot /></div>
</template>

<script>
import { eventHub } from "../../eventHub.js";

// A panel that opens and closes when an element with v-collapse-toggle="name" is clicked.
// Several panels may share a name; they toggle together.
export default {
    name: "Collapse",
    props: {
        name: { type: String, required: true },
        visible: { type: Boolean, default: false },
        // re-apply `visible` whenever this changes (e.g. the filter text)
        syncKey: { type: [String, Number], default: null },
    },
    data() {
        return { show: this.visible };
    },
    watch: {
        visible(value) {
            this.show = value;
        },
        syncKey() {
            this.show = this.visible;
        },
    },
    created() {
        eventHub.$on("collapse-toggle", this.onToggle);
    },
    beforeDestroy() {
        eventHub.$off("collapse-toggle", this.onToggle);
    },
    methods: {
        onToggle(name) {
            if (name === this.name) {
                this.show = !this.show;
            }
        },
    },
};
</script>
