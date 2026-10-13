<template>
    <div class="modal fade" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">{{ title }}</h5>
                    <button
                        type="button"
                        class="btn-close"
                        aria-label="Close"
                        @click="$emit('cancel')"
                    ></button>
                </div>
                <div class="modal-body"><slot /></div>
                <div class="modal-footer">
                    <button
                        type="button"
                        class="btn btn-secondary"
                        @click="$emit('cancel')"
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        class="btn btn-primary"
                        @click="$emit('ok')"
                    >
                        OK
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import BsModal from "bootstrap/js/dist/modal";
import ScrollBarHelper from "bootstrap/js/dist/util/scrollbar";

// A dialog with Cancel/OK, shown while `show` is true. The parent decides what OK does and
// when to close it: Cancel, the close button, Escape and a click outside emit "cancel".
// Bootstrap's Modal shows it (backdrop, fade, focus kept inside, page scroll locked). Its
// element moves to the end of <body>, so no positioned ancestor can hide it.
export default {
    name: "Modal",
    props: {
        show: { type: Boolean, default: false },
        title: { type: String, default: "" },
    },
    emits: ["ok", "cancel"],
    watch: {
        show() {
            this.apply();
        },
    },
    mounted() {
        document.body.appendChild(this.$el);
        this.modal = new BsModal(this.$el);
        this.$el.addEventListener("hide.bs.modal", this.onHide);
        this.$el.addEventListener("shown.bs.modal", this.onShown);
        this.$el.addEventListener("hidden.bs.modal", this.apply);
        this.apply();
    },
    beforeDestroy() {
        const open = this.$el.classList.contains("show");
        this.modal.dispose();
        this.$el.remove();
        if (open) {
            // dispose() removes the backdrop but leaves the page scroll locked
            document.body.classList.remove("modal-open");
            new ScrollBarHelper().reset();
        }
    },
    methods: {
        // Bootstrap ignores show()/hide() while a transition runs: called again after each one
        apply() {
            const open = this.$el.classList.contains("show");
            if (this.show && !open) {
                this.modal.show();
            } else if (!this.show && open) {
                this.modal.hide();
            }
        },
        // Escape or a click outside: let the parent decide instead of closing here
        onHide(event) {
            if (this.show) {
                event.preventDefault();
                this.$emit("cancel");
            }
        },
        // autofocus has no effect in Bootstrap modals: focus the field once the dialog is shown
        onShown() {
            this.$el.querySelector("[autofocus]")?.focus();
            this.apply();
        },
    },
};
</script>
