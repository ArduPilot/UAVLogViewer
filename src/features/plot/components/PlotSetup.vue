<template>
    <div>
        <ul>
            <li class="type">
                <div v-collapse-toggle="'plotsetupcontent'">
                    <a class="section">
                        Plots Setup
                        <i
                            class="expand expand--closed fa-solid fa-caret-right"
                        ></i>
                        <i
                            class="expand expand--open fa-solid fa-caret-down"
                        ></i>
                    </a>
                </div>
            </li>
        </ul>
        <Collapse name="plotsetupcontent" class="menu-content" visible>
            <ul class="colorpicker plot-wrapper">
                <template v-if="state.expressions.length">
                    <template
                        v-for="(field, index) in state.expressions"
                        :key="'field' + index"
                    >
                        <li class="field plotsetup">
                            <expression-editor
                                v-model="field.name"
                                :suggestions="completionOptions"
                                class="expression-editor"
                            />
                            <button
                                type="button"
                                class="axis-toggle"
                                :aria-label="
                                    'Plot axis: ' +
                                    field.axis +
                                    '. Click to advance.'
                                "
                                title="Click to advance axis"
                                @click="advanceAxis(field)"
                            >
                                {{ field.axis }}
                            </button>
                            <color-picker
                                v-model="field.color"
                                :colors="state.allColors"
                                aria-label="Plot color"
                            />
                            <a
                                class="remove-button"
                                @click="
                                    $eventHub.$emit('togglePlot', field.name)
                                "
                            >
                                <i
                                    class="expand fa-solid fa-trash"
                                    title="Remove data"
                                ></i>
                            </a>
                        </li>
                        <li v-if="state.expressionErrors[index]" class="error">
                            <i
                                class="fa-solid fa-circle-exclamation error"
                                :title="state.expressionErrors[index]"
                            ></i>
                            {{ state.expressionErrors[index] }}
                        </li>
                    </template>
                </template>
                <li v-else>Please plot something first.</li>
            </ul>
            <!-- BUTTONS -->
            <div class="btns-wrapper">
                <button class="add-expression" @click="createNewExpression">
                    <i class="fa-solid fa-plus" aria-hidden="true"></i>Add
                    Expression
                </button>
                <button
                    v-if="state.expressions.length > 0"
                    class="save-preset"
                    @click="openSaveModal"
                >
                    <i class="fa-solid fa-circle-check" aria-hidden="true"></i
                    >Save Preset
                </button>
                <button
                    v-if="state.expressions.length > 0"
                    class="save-preset"
                    @click="clearExpressions(state)"
                >
                    <i class="fa-solid fa-ban" aria-hidden="true"></i>
                    Clear
                </button>
            </div>
        </Collapse>
        <!-- MODAL -->
        <Modal
            :show="saveModalOpen"
            @ok="handleOk"
            @cancel="saveModalOpen = false"
        >
            <form @submit.prevent="handleOk">
                <label for="name-input" class="form-label"
                    >New Preset Name</label
                >
                <input
                    id="name-input"
                    ref="nameInput"
                    v-model="name"
                    class="form-control"
                    placeholder="Attitude/OtherRoll"
                    required
                    autofocus
                />
            </form>
        </Modal>
    </div>
</template>
<script>
import {
    store,
    firstFreeAxis,
    firstFreeColor,
    clearExpressions,
} from "@/shared/stores/index.js";
import ExpressionEditor from "./ExpressionEditor.vue";
import ColorPicker from "./ColorPicker.vue";
import Collapse from "@/shared/ui/Collapse.vue";
import Modal from "@/shared/ui/Modal.vue";

export default {
    name: "PlotSetup",
    components: {
        ExpressionEditor,
        ColorPicker,
        Collapse,
        Modal,
    },
    data() {
        return {
            state: store,
            name: "",
            saveModalOpen: false,
        };
    },
    computed: {
        additionalCompletionItems() {
            const additionalCompletionItems = [
                "mag_heading_df(MAG[0],ATT)",
                "mag_heading(RAW_IMU,ATTITUDE)",
                "max(x,y)",
                "min(x,y)",
            ];
            for (const name of this.state.namedFloats) {
                additionalCompletionItems.push(
                    `named(NAMED_VALUE_FLOAT,"${name}")`,
                );
            }
            return additionalCompletionItems;
        },
        completionOptions() {
            const messageOptions = Object.keys(this.state.messageTypes).flatMap(
                (key) => {
                    const fields = this.state.messageTypes[key].expressions.map(
                        (field) => `${key}.${field}`,
                    );
                    return [key, ...fields];
                },
            );
            return [...this.additionalCompletionItems, ...messageOptions];
        },
    },
    methods: {
        clearExpressions,
        advanceAxis(field) {
            const axes = this.state.allAxis;
            const currentIndex = axes.indexOf(field.axis);
            field.axis = axes[(currentIndex + 1) % axes.length];
        },
        createNewExpression() {
            this.state.plotOn = true;
            this.$nextTick(() => {
                this.state.expressions.push({
                    name: "1+1",
                    color: firstFreeColor(this.state),
                    axis: firstFreeAxis(this.state),
                });
            });
        },
        savePreset(name) {
            const myStorage = globalThis.localStorage;
            const saved = JSON.parse(myStorage.getItem("savedFields")) || {};
            saved[name] = this.state.expressions.map((field) => [
                field.name,
                field.axis,
                field.color,
                field.function,
            ]);
            myStorage.setItem("savedFields", JSON.stringify(saved));
            this.$eventHub.$emit("presetsChanged");
        },

        openSaveModal() {
            this.name = "";
            this.saveModalOpen = true;
        },
        handleOk() {
            if (this.name.length > 0) {
                this.savePreset(this.name);
                this.saveModalOpen = false;
            }
        },
    },
};
</script>
<style scoped>
/* MAIN */
.plot-wrapper {
    min-height: 160px;
    overflow: hidden;
    overflow-y: scroll;
}

/* COLOR PICKER */

ul.colorpicker {
    font-family: Montserrat, sans-serif;
}

ul.colorpicker li {
    text-align: center;
    cursor: default;
    font-size: 13px;
    padding-top: 1px;
}

ul.colorpicker li:hover {
    background-color: #1e2536;
    border-left: 3px solid #1e2536;
}

ul.colorpicker li a {
    cursor: pointer;
}

li.field {
    line-height: 26px;
    padding-left: 20px;
    font-size: 90%;
}

li.plotsetup {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

li.plotsetup .expression-editor {
    flex: 1;
    min-width: 0;
}

li.plotsetup .axis-toggle,
li.plotsetup .remove-button {
    flex-shrink: 0;
}

li.plotsetup .remove-button {
    display: inline-flex;
    align-items: center;
}

/* Axis toggle -- cycles through state.allAxis on click */

.axis-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2rem;
    height: 2rem;
    padding: 0 0.75rem;
    border: 1px solid rgb(133 133 133);
    border-radius: 4px;
    background: #1a1e24;
    color: #fff;
    font-family: inherit;
    font-size: 0.8125rem;
    cursor: pointer;
    transition: background-color 0.15s ease;
}

.axis-toggle:hover {
    background: color-mix(in srgb, #1a1e24 92%, white);
}

.axis-toggle:focus-visible {
    box-shadow: inset 0 0 0 2px rgb(212 127 0 / 60%);
    outline: none;
}

.error {
    color: var(--bs-danger);
}

/* BUTTONS */

.btns-wrapper {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin: 0.625rem 1.25rem;
}

.add-expression,
.save-preset {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    height: 2rem;
    padding: 0 0.75rem;
    border: 1px solid rgb(91 100 117 / 76%);
    border-radius: 4px;
    background: #1a1e24;
    color: #fff;
    font-family: inherit;
    font-size: 0.8125rem;
    cursor: pointer;
    transition: background-color 0.15s ease;
}

.add-expression:hover,
.save-preset:hover {
    background: color-mix(in srgb, #1a1e24 92%, white);
}

.add-expression:focus-visible,
.save-preset:focus-visible {
    box-shadow: inset 0 0 0 2px rgb(212 127 0 / 60%);
    outline: none;
}

.add-expression i,
.save-preset i {
    margin: 0;
}

.expand--open {
    display: none;
}

.is-open .expand--closed {
    display: none;
}

.is-open .expand--open {
    display: inline;
}

li.error i {
    margin-right: 0.25rem;
}
</style>
