<template>
    <div>
        <div
            v-if="show"
            class="modal d-block"
            tabindex="-1"
            role="dialog"
            aria-modal="true"
            @click.self="$emit('cancel')"
            @keydown.esc="$emit('cancel')"
        >
            <div class="modal-dialog" role="document">
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
        <div v-if="show" class="modal-backdrop show"></div>
    </div>
</template>

<script>
// A dialog with Cancel/OK, shown while `show` is true. The parent decides what OK does and
// when to close it (Cancel, the close button, Escape and a click outside emit "cancel").
// Its element moves to the end of <body>, so no positioned ancestor can hide it.
export default {
    name: "Modal",
    props: {
        show: { type: Boolean, default: false },
        title: { type: String, default: "" },
    },
    emits: ["ok", "cancel"],
    mounted() {
        document.body.appendChild(this.$el);
    },
    beforeDestroy() {
        this.$el.remove();
    },
};
</script>
