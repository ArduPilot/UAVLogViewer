<template>
    <div class="collapse"><slot /></div>
</template>

<script>
import BsCollapse from "bootstrap/js/dist/collapse";
import { eventHub } from "@/shared/lib/eventHub.js";

// A panel that opens and closes when an element with v-collapse-toggle="name" is clicked.
// Several panels may share a name; they toggle together. Bootstrap's Collapse opens and closes
// it (with its height animation); this component keeps the state it should be in.
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
        show() {
            this.apply();
            eventHub.$emit("collapse-state", this.name, this.show);
        },
    },
    created() {
        eventHub.$on("collapse-toggle", this.onToggle);
    },
    mounted() {
        // open from the first render, without the animation
        this.$el.classList.toggle("show", this.show);
        this.collapse = new BsCollapse(this.$el, { toggle: false });
        // Bootstrap ignores show()/hide() while a transition runs: apply the state again after it
        this.$el.addEventListener("shown.bs.collapse", this.apply);
        this.$el.addEventListener("hidden.bs.collapse", this.apply);
        eventHub.$emit("collapse-state", this.name, this.show);
    },
    beforeUnmount() {
        eventHub.$off("collapse-toggle", this.onToggle);
        this.$el.removeEventListener("shown.bs.collapse", this.apply);
        this.$el.removeEventListener("hidden.bs.collapse", this.apply);
        const collapse = this.collapse;
        if (this.$el.classList.contains("collapsing")) {
            // Bootstrap still finishes the running transition (also once the element is out of
            // the page), and its last step needs the instance: dispose of it after that
            const dispose = () => collapse.dispose();
            this.$el.addEventListener("shown.bs.collapse", dispose, {
                once: true,
            });
            this.$el.addEventListener("hidden.bs.collapse", dispose, {
                once: true,
            });
        } else {
            collapse.dispose();
        }
    },
    methods: {
        onToggle(name) {
            if (name === this.name) {
                this.show = !this.show;
            }
        },
        apply() {
            const open = this.$el.classList.contains("show");
            if (this.show && !open) {
                this.collapse.show();
            } else if (!this.show && open) {
                this.collapse.hide();
            }
        },
    },
};
</script>
