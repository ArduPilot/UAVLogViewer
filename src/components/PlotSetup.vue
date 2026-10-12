<template>
    <div>
        <ul>
            <li class="type">
                <div v-collapse-toggle="'plotsetupcontent'">
                    <a class="section">
                        Plots Setup
                        <i class="expand fas fa-caret-down"></i>
                    </a>
                </div>
            </li>
        </ul>
        <Collapse name="plotsetupcontent" class="menu-content" visible>
            <ul class="colorpicker plot-wrapper">
                <template v-if="state.expressions.length">
                    <template v-for="(field, index) in state.expressions">
                        <li :key="'field' + index" class="field plotsetup">
                            <expression-editor
                                v-model="field.name"
                                :suggestions="completionOptions"
                            />
                            <select v-model.number="field.axis">
                                <option
                                    v-for="axis in state.allAxis"
                                    :key="'axisnumber' + axis"
                                    :value="axis"
                                >
                                    {{ axis }}
                                </option>
                            </select>
                            <select
                                v-model="field.color"
                                :style="{ color: field.color }"
                            >
                                <option
                                    v-for="color in state.allColors"
                                    :key="'axisColor' + color"
                                    :value="color"
                                    :style="{ color: color }"
                                >
                                    ■
                                </option>
                            </select>
                            <a
                                class="remove-button"
                                @click="
                                    $eventHub.$emit('togglePlot', field.name)
                                "
                            >
                                <i
                                    class="expand fas fa-trash"
                                    title="Remove data"
                                ></i>
                            </a>
                        </li>
                        <li
                            v-if="state.expressionErrors[index]"
                            :key="'field' + index + 'err'"
                            class="error"
                        >
                            <i
                                class="fas fa-exclamation-circle error"
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
                    <i class="fa fa-plus" aria-hidden="true"></i>Add Expression
                </button>
                <button
                    v-if="state.expressions.length > 0"
                    class="save-preset"
                    @click="openSaveModal"
                >
                    <i class="fa fa-check-circle" aria-hidden="true"></i>Save
                    Preset
                </button>
                <button
                    v-if="state.expressions.length > 0"
                    class="save-preset"
                    @click="clearExpressions(state)"
                >
                    <i class="fa fa-ban" aria-hidden="true"></i>
                    clear
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
} from "./Globals.js";
import ExpressionEditor from "./ExpressionEditor.vue";
import Collapse from "./ui/Collapse.vue";
import Modal from "./ui/Modal.vue";

export default {
    name: "PlotSetup",
    components: {
        ExpressionEditor,
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
            this.$nextTick(() => this.$refs.nameInput?.focus());
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
<style>
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
    display: block;
}

i {
    margin: 5px;
    padding: 0;
}

.plotname {
    display: inline-block;
    line-height: 15px;
    margin-bottom: 0;
    font-size: 13px;
    width: 100%;
    border: 1px solid grey;
    padding: 4.5px;
    border-radius: 20px;
}

.plotname:focus {
    background-color: rgb(241 248 255 / 96.6%);
    outline: none;
}

select {
    display: inline;
    border-radius: 5px;
    border: 1px solid rgb(156 156 156);
    background-color: rgb(255 255 255);
    padding: 2px 2.5px;
    color: #4a4a4a;
}

select:focus {
    border: 1.5px solid #d47f00;
    outline: none;
}

select option {
    background-color: rgb(216 215 215);
}

select option:hover {
    background-color: #d47f00;
}

.fa-trash {
    margin: 12px 5px 10px 1px !important;
    font-size: 10px;
    float: right;
}

.error {
    color: red;
}

/* BUTTONS */

.btns-wrapper {
    display: flex;
    flex-flow: row wrap;
    justify-content: space-evenly;
    margin: 10px;
}

/* SAVE PRESET BUTTON */

.save-preset {
    background-color: rgb(33 41 61);
    color: #fff;
    border-radius: 15px;
    padding: 0 10px 0 0;
    border: 1px solid rgb(91 100 117 / 76%);
    font-size: 13px;
}

.save-preset:hover {
    background-color: rgb(47 58 87);
    box-shadow: 0 0 12px 0 rgb(37 78 133 / 55%);
    transition: all 0.5s ease;
}

.save-preset:focus {
    outline: none;
}

/* ADD EXPRESSION BUTTON */

.add-expression {
    background-color: rgb(33 41 61);
    color: #fff;
    border-radius: 15px;
    padding: 0 10px 0 0;
    border: 1px solid rgb(91 100 117 / 76%);
    font-size: 13px;
}

.add-expression:hover {
    background-color: rgb(47 58 87);
    box-shadow: 0 0 12px 0 rgb(37 78 133 / 55%);
    transition: all 0.5s ease;
}

.add-expression:focus {
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
