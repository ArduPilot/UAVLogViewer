<template>
    <div class="color-picker">
        <button
            type="button"
            class="color-picker-trigger"
            :aria-expanded="open"
            :aria-label="'Color: ' + modelValue"
            v-bind="$attrs"
            @click="toggle"
        >
            <span
                class="color-picker-swatch"
                :style="{ backgroundColor: modelValue }"
            ></span>
        </button>
        <div v-if="open" class="color-picker-panel">
            <div class="color-picker-grid">
                <button
                    v-for="color in colors"
                    :key="color"
                    type="button"
                    class="color-picker-item"
                    :class="{ selected: color === modelValue }"
                    :aria-label="color"
                    @click="selectColor(color)"
                >
                    <span
                        class="color-picker-swatch color-picker-swatch-lg"
                        :style="{ backgroundColor: color }"
                    ></span>
                </button>
            </div>
            <div class="color-picker-custom">
                <label>
                    <i class="fa-solid fa-palette" aria-hidden="true"></i>
                    <span>Custom...</span>
                    <input
                        type="color"
                        :value="modelValue"
                        @input="handleCustom"
                    />
                </label>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: "ColorPicker",
    inheritAttrs: false,
    props: {
        modelValue: { type: String, default: "" },
        colors: { type: Array, default: () => [] },
    },
    emits: ["update:modelValue"],
    data() {
        return {
            open: false,
        };
    },
    mounted() {
        document.addEventListener("mousedown", this.handleClickOutside);
        document.addEventListener("keydown", this.handleEscape);
    },
    beforeUnmount() {
        document.removeEventListener("mousedown", this.handleClickOutside);
        document.removeEventListener("keydown", this.handleEscape);
    },
    methods: {
        toggle() {
            this.open = !this.open;
        },
        close() {
            this.open = false;
        },
        selectColor(color) {
            this.$emit("update:modelValue", color);
            this.close();
        },
        handleCustom(event) {
            this.$emit("update:modelValue", event.target.value);
            this.close();
        },
        handleClickOutside(event) {
            if (this.$el && !this.$el.contains(event.target)) {
                this.close();
            }
        },
        handleEscape(event) {
            if (event.key === "Escape" && this.open) {
                this.close();
            }
        },
    },
};
</script>

<style scoped>
.color-picker {
    position: relative;
    flex-shrink: 0;
}

.color-picker-trigger {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem; /* 32px -- matches selects and buttons */
    height: 2rem; /* 32px */
    padding: 0;
    border: 1px solid rgb(91 100 117 / 76%); /* sidebar-standard divider */
    border-radius: 4px; /* user-specified app radius */
    background: #1a1e24; /* user-specified dark surface */
    cursor: pointer;
}

.color-picker-trigger:hover {
    border-color: #a0a8b8;
}

.color-picker-trigger:focus-visible {
    box-shadow: inset 0 0 0 2px rgb(212 127 0 / 60%);
    outline: none;
}

.color-picker-swatch {
    display: block;
    width: 0.75rem; /* 12px -- closed-box swatch */
    height: 0.75rem;
    border-radius: 2px; /* 2px -- small square chip */
}

.color-picker-swatch-lg {
    width: 1rem; /* 16px -- dropdown cell swatch */
    height: 1rem;
}

.color-picker-panel {
    position: absolute;
    top: calc(100% + 0.25rem); /* 4px -- gap from trigger */
    right: 0;
    z-index: 1000;
    background: #1a1e24;
    border: 1px solid rgb(91 100 117 / 76%);
    border-radius: 4px;
    box-shadow: 0 2px 10px rgb(0 0 0 / 10%);
}

.color-picker-grid {
    display: grid;
    grid-template-columns: repeat(3, auto);
    gap: 0.5rem;
    padding: 0.5rem;
}

.color-picker-item {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 1.5rem; /* 24px cell: 16px swatch + 4px padding each side */
    height: 1.5rem;
    padding: 0;
    border: 0;
    border-radius: 2px;
    background: transparent;
    cursor: pointer;
}

.color-picker-item:hover,
.color-picker-item.selected {
    background: color-mix(in srgb, #1a1e24 92%, white);
}

.color-picker-item:focus-visible {
    box-shadow: inset 0 0 0 2px rgb(212 127 0 / 60%);
    outline: none;
}

.color-picker-custom {
    padding: 0.5rem;
    border-top: 1px solid rgb(91 100 117 / 76%);
}

.color-picker-custom label {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.25rem 0.5rem;
    border-radius: 2px;
    color: #fff;
    font-size: 0.8125rem;
    cursor: pointer;
}

.color-picker-custom label:hover {
    background: color-mix(in srgb, #1a1e24 92%, white);
}

.color-picker-custom input[type="color"] {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
}
</style>
