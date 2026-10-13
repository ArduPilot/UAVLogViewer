<template>
    <div v-if="hasMessages">
        <!--<li v-if="state.plotOn" @click="state.plotOn=!state.plotOn">-->
        <!--<a class="section">-->
        <!--<i class="fas fa-eye-slash fa-lg"></i> Toggle Plot</a>-->
        <!--</li>-->
        <tree-menu
            v-if="Object.keys(availableMessagePresets).length > 0"
            :nodes="availableMessagePresets"
            :label="'Presets'"
            :clean-name="'Presets'"
            :level="0"
        >
        </tree-menu>
        <ul>
            <li v-collapse-toggle="'messages'">
                <a class="section">
                    Plot Individual Field
                    <i class="fas fa-caret-down"></i
                ></a>
            </li>
        </ul>

        <Collapse name="messages">
            <ul>
                <li class="input-li">
                    <input
                        id="filterbox"
                        v-model="filter"
                        placeholder=" Type here to filter..."
                    />
                </li>
            </ul>
            <template v-for="key of Object.keys(messageTypesFiltered).sort()">
                <ul :key="key">
                    <li class="type">
                        <div
                            v-collapse-toggle="'type' + key"
                            :title="
                                messageDocs[key.split('[')[0]]
                                    ? messageDocs[key.split('[')[0]].doc
                                    : ''
                            "
                        >
                            <a class="section"
                                >{{ key }}
                                <span v-if="messageTypes[key].isArray">{{
                                    "[...]"
                                }}</span>
                                <i class="expand fas fa-caret-down"></i>
                                <span class="description">
                                    {{
                                        messageDocs[key.split("[")[0]]
                                            ? messageDocs[key.split("[")[0]].doc
                                            : ""
                                    }}
                                </span>
                            </a>
                        </div>
                    </li>
                </ul>
                <Collapse
                    :key="key + '1'"
                    :name="'type' + key"
                    :visible="filter !== ''"
                    :sync-key="filter"
                >
                    <template v-for="item in messageTypes[key].complexFields">
                        <li
                            v-if="
                                isPlottable(key, item.name) &&
                                item.name
                                    .toLowerCase()
                                    .includes(filter.toLowerCase())
                            "
                            :key="key + '.' + item.name"
                            class="field"
                            :title="fieldDoc(key, item.name)"
                            @click="toggle(key, item.name)"
                        >
                            <a>
                                {{ item.name }}
                                <span
                                    v-if="
                                        item.units !== '?' && item.units !== ''
                                    "
                                >
                                    ({{ item.units }})</span
                                >
                            </a>
                            <span class="description">
                                {{ fieldDoc(key, item.name) }}
                            </span>

                            <!-- clicking anywhere on the item (also this icon) toggles the plot -->
                            <a v-if="isPlotted(key, item.name)">
                                <i
                                    class="remove-icon fas fa-trash"
                                    title="Remove data"
                                ></i>
                            </a>
                        </li>
                    </template>
                </Collapse>
            </template>
        </Collapse>
    </div>
</template>
<script>
import { store } from "./Globals.js";
import TreeMenu from "./widgets/TreeMenu.vue";
import Collapse from "./ui/Collapse.vue";
import fastXmlParser from "fast-xml-parser";
import mavgraphs from "../assets/mavgraphs.xml?raw";
import mavgraphs2 from "../assets/mavgraphs2.xml?raw";
import ekfGraphs from "../assets/ekfGraphs.xml?raw";
import ekf3Graphs from "../assets/ekf3Graphs.xml?raw";
import planeDocs from "../assets/logmetadata/plane.xml?raw";
import copterDocs from "../assets/logmetadata/copter.xml?raw";
import trackerDocs from "../assets/logmetadata/tracker.xml?raw";
import roverDocs from "../assets/logmetadata/rover.xml?raw";
import subDocs from "../assets/logmetadata/sub.xml?raw";

// "MSG.field:2" goes on the second axis
function presetFields(expression) {
    return expression
        .split(" ")
        .map((exp) =>
            exp.includes(":") ? [exp.replace(":2", ""), 1] : [exp, 0],
        );
}

// presets keyed "Folder/Sub/Name" as nested objects, for the tree menu
function presetTree(presets) {
    const tree = {};
    for (const [key, value] of Object.entries(presets)) {
        let current = tree;
        const fields = key.trim().split("/");
        const lastField = fields.pop();
        for (const field of fields) {
            if (!(field in current)) {
                console.log("overwriting " + field);
                current[field] = {};
            }
            current = current[field];
        }
        current[lastField] = value;
    }
    return tree;
}

export default {
    name: "MessageMenu",
    components: { TreeMenu, Collapse },
    data() {
        return {
            filter: "",
            checkboxes: {},
            state: store,
            messages: {},
            messageTypes: [],
            hiddenTypes: [
                "MISSION_CURRENT",
                "SYSTEM_TIME",
                "HEARTBEAT",
                "STATUSTEXT",
                "COMMAND_ACK",
                "PARAM_VALUE",
                "AUTOPILOT_VERSION",
                "TIMESYNC",
                "MISSION_COUNT",
                "MISSION_ITEM_INT",
                "MISSION_ITEM",
                "MISSION_ITEM_REACHED",
                "MISSION_ACK",
                "HOME_POSITION",
                "STRT",
                "FMT",
                "PARM",
                "MSG",
                "FMTU",
                "UNIT",
                "MULT",
            ],
            // Preset fields are positional arrays (https://github.com/igoutta/UAVLogViewer/issues/4)
            messagePresets: {},
            userPresets: {},
            messageDocs: {},
        };
    },
    computed: {
        hasMessages() {
            return Object.keys(this.messageTypes).length > 0;
        },
        messageTypesFiltered() {
            const filtered = {};
            // the matching types' panels open while a filter is typed (Collapse :visible)
            const filter = this.filter.toLowerCase();
            for (const key of Object.keys(this.messageTypes)) {
                const matches =
                    filter === "" ||
                    this.messageTypes[key].expressions.some((field) =>
                        field.toLowerCase().includes(filter),
                    );
                if (!this.hiddenTypes.includes(key) && matches) {
                    filtered[key] = this.messageTypes[key];
                }
            }
            return filtered;
        },
        availableMessagePresets() {
            const dict = {};
            // built-in presets only when the log has all of their fields
            for (const [key, value] of Object.entries(this.messagePresets)) {
                const fields = value.filter((field) => field[0] !== "");
                if (!this.addPresetFields(dict, key, fields)) {
                    delete dict[key];
                }
            }
            // user presets keep the fields before the first one the log doesn't have
            for (const [key, value] of Object.entries(this.userPresets)) {
                this.addPresetFields(dict, key, value);
            }
            return presetTree(dict);
        },
    },
    created() {
        this.$eventHub.$on("messageTypes", this.handleMessageTypes);
        this.$eventHub.$on("presetsChanged", this.loadLocalPresets);
        this.messagePresets = this.loadXmlPresets();
        this.messageDocs = this.loadXmlDocs();
        this.loadLocalPresets();
    },
    beforeDestroy() {
        this.$eventHub.$off("messageTypes", this.handleMessageTypes);
        this.$eventHub.$off("presetsChanged", this.loadLocalPresets);
    },
    methods: {
        // adds the fields (each with a color index) to dict[key] up to the first one
        // the log doesn't have; false if there was such a field
        addPresetFields(dict, key, fields) {
            let color = 0;
            for (const field of fields) {
                if (!this.isAvailable(field)) {
                    return false;
                }
                dict[key] ??= { messages: [] };
                dict[key].messages.push([...field, color++]);
            }
            return true;
        },
        loadXmlPresets() {
            const graphs = {};
            const files = [mavgraphs, mavgraphs2, ekfGraphs, ekf3Graphs];
            for (const contents of files) {
                const result = fastXmlParser.parse(contents, {
                    ignoreAttributes: false,
                });
                for (const graph of result.graphs.graph) {
                    const name = graph["@_name"];
                    const expressions = Array.isArray(graph.expression)
                        ? graph.expression
                        : [graph.expression];
                    // graphs with several expressions share a name: pad it so each keeps its own key
                    expressions.forEach((expression, i) => {
                        graphs[name + " ".repeat(i)] = presetFields(expression);
                    });
                }
            }
            return graphs;
        },
        loadLocalPresets() {
            const saved = globalThis.localStorage.getItem("savedFields");
            if (saved !== null) {
                this.userPresets = JSON.parse(saved);
                for (const preset in this.userPresets) {
                    for (const message in this.userPresets[preset]) {
                        // Field 3 means it is a user preset and can be deleted
                        this.userPresets[preset][message][3] = 1;
                    }
                }
            }
        },
        loadXmlDocs() {
            const logDocs = {};
            const files = [
                planeDocs,
                copterDocs,
                trackerDocs,
                roverDocs,
                subDocs,
            ];
            for (const contents of files) {
                const result = fastXmlParser.parse(contents, {
                    ignoreAttributes: false,
                });
                const igraphs = result.loggermessagefile;
                for (const graph of igraphs.logformat) {
                    logDocs[graph["@_name"]] = { doc: graph.description };
                    if (!Array.isArray(graph.fields.field)) {
                        continue;
                    }
                    for (const field of graph.fields.field) {
                        logDocs[graph["@_name"]][field["@_name"]] =
                            field.description;
                    }
                }
            }
            return logDocs;
        },
        handleMessageTypes(messageTypes) {
            if (this.$route.query.plots) {
                this.state.plotOn = true;
            }
            const newMessages = {};
            // populate list of message types
            for (const messageType of Object.keys(messageTypes)) {
                if (messageTypes[messageType].instances !== undefined) {
                    continue;
                }
                this.$set(
                    this.checkboxes,
                    messageType,
                    messageTypes[messageType].expressions.expressions,
                );
                newMessages[messageType] = messageTypes[messageType];
            }
            // populate checkbox status
            for (const messageType of Object.keys(messageTypes)) {
                if (messageTypes[messageType].instances !== undefined) {
                    continue;
                }
                this.checkboxes[messageType] = { expressions: {} };
                // for (let field of this.getMessageNumericField(this.state.messages[messageType][0])) {
                for (const field of messageTypes[messageType].expressions) {
                    if (this.state.plotOn) {
                        this.checkboxes[messageType].expressions[field] =
                            this.$route.query?.plots?.indexOf(
                                messageType + "." + field,
                            ) !== -1;
                    } else {
                        this.checkboxes[messageType].expressions[field] = false;
                    }
                }
            }
            this.messageTypes = newMessages;
            this.$set(this.state, "messageTypes", newMessages);
        },
        fieldDoc(msgtype, field) {
            // Message types can carry an instance suffix (e.g. GPYW[1]) which the
            // metadata is not keyed by, so strip it before looking the docs up.
            const docs = this.messageDocs[msgtype.split("[")[0]];
            return docs ? docs[field.split("[")[0]] || "" : "";
        },
        isPlotted(message, field) {
            const fullname = message + "." + field;
            for (const field of this.state.expressions) {
                if (field.name === fullname) {
                    return true;
                }
            }
            return false;
        },
        getMessageNumericField(message) {
            const numberFields = [];
            if (message && message.fieldnames) {
                for (const field of message.fieldnames) {
                    if (!Number.isNaN(Number(message[field]))) {
                        numberFields.push(field);
                    }
                }
            }
            return numberFields;
        },
        toggle(message, item) {
            this.state.plotOn = true;
            this.$nextTick(function () {
                this.$eventHub.$emit("togglePlot", message + "." + item);
            });
        },
        isPlottable(msgtype, item) {
            return item !== "TimeUS";
        },
        findMessagesInExpression(expression) {
            // delete all expressions after dots (and dots)
            const toDelete = /\.[A-Za-z-0-9_]+/g;
            const name = expression.replace(toDelete, "");
            const RE = /[A-Z][A-Z0-9_]+(\[0-9\])?/g;
            const fields = name.match(RE);
            if (fields === null) {
                return [];
            }
            return fields;
        },
        isAvailable(msg) {
            const msgRe = /[A-Z][A-Z0-9_]+(\[\d\])?(\.\w+)?/g;
            const match = msg[0].match(msgRe);
            if (!match) {
                return true;
            }
            const msgName = match[0].split(".")[0];
            if (!this.messageTypes[msgName]) {
                return false;
            }
            const fieldName = match[0].split(".")[1];
            if (fieldName === undefined) {
                return true;
            }
            if (!this.messageTypes[msgName].complexFields[fieldName]) {
                console.log("missing field " + msgName + "." + fieldName);
                return false;
            }
            return true;
        },
    },
};
</script>
<style scoped>
i {
    margin: 5px;
}

i.expand {
    float: right;
}

li > div {
    display: inline-block;
    width: 100%;
}

li.field {
    line-height: 29px;
    padding-left: 40px;
    font-size: 90%;
    display: inline-block;
    vertical-align: middle;
    width: 100%;
}

li.type {
    line-height: 30px;
    padding-left: 10px;
    font-size: 85%;
}

input {
    margin: 12px 12px 15px 10px;
    border: 2px solid #ccc;
    border-radius: 4px;
    background-color: rgb(255 255 255 / 89.7%);
    color: rgb(51 51 51);
    width: 92%;
}

input:focus {
    outline: none;
    border: 2px solid #135388;
}

.input-li:hover {
    background-color: rgb(30 37 54 / 20.5%);
    border-left: 3px solid rgb(24 30 44 / 21.2%);
}

::placeholder {
    /* Chrome, Firefox, Opera, Safari 10.1+ */
    color: rgb(148 147 147);
    opacity: 1; /* Firefox */
}

i.remove-icon {
    float: right;
}

@media (min-width: 575px) and (max-width: 992px) {
    a {
        padding: 2px 60px 2px 55px !important;
    }
}

span.description {
    opacity: 0.7;
    font-size: 80%;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    display: inline-block;
    max-width: 180px;
    vertical-align: top;
}
</style>
