<template>
    <div
        :id="getDivName()"
        :style="{
            width: width + 'px',
            height: height + 'px',
            top: top + 'px',
            left: left + 'px',
        }"
    >
        <div id="paneContent">
            <span
                style="float: right; margin: 3px; cursor: pointer"
                @click="close()"
            >
                X
            </span>
            <input id="filterbox" v-model="filter" placeholder="Filter" />
            <button @click="saveParametersToFile">save</button>
            <div v-if="haveDefaults" class="form-check">
                <input
                    id="showdiff"
                    v-model="showdiff"
                    class="form-check-input"
                    type="checkbox"
                />
                <label class="form-check-label" for="showdiff">
                    Show only changed
                </label>
            </div>
            <table id="params">
                <thead>
                    <tr>
                        <th>Param</th>
                        <th>Value</th>
                        <th v-if="haveDefaults">Default</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="param in filteredData" :key="param">
                        <td>{{ param }}</td>
                        <template v-if="haveDefaults">
                            <td>
                                {{
                                    isDefaultParam(param)
                                        ? "→"
                                        : printParam(paramValue(param))
                                }}
                            </td>
                            <td>
                                {{ printParam(state.defaultParams[param]) }}
                            </td>
                        </template>
                        <template v-else>
                            <td>{{ printParam(paramValue(param)) }}</td>
                        </template>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<script>
import { store } from "../Globals.js";
import { useWidget, widgetProps } from "./useWidget.js";
import { downloadData } from "../../tools/download.js";

export default {
    name: "ParamViewer",
    props: widgetProps,
    emits: ["close"],
    setup(props, { emit }) {
        return useWidget(props, emit, {
            name: "ParamViewer",
            width: 220,
            height: 215,
            left: 540,
            top: 0,
        });
    },
    data() {
        return {
            filter: "",
            state: store,
            throttle: 50,
            yaw: 50,
            pitch: 50,
            roll: 50,
            showdiff: false,
        };
    },
    computed: {
        haveDefaults() {
            return Object.keys(this.state.defaultParams).length > 0;
        },
        filteredData() {
            this.dependOnParams();
            return Object.keys(this.state.params?.values ?? {})
                .filter((key) => key.indexOf(this.filter.toUpperCase()) !== -1)
                .filter((key) => {
                    if (this.showdiff) {
                        return (
                            this.state.params.values[key] !==
                            this.state.defaultParams[key]
                        );
                    } else {
                        return true;
                    }
                });
        },
    },
    methods: {
        waitForMessage(fieldname) {
            this.$eventHub.$emit("loadType", fieldname.split(".")[0]);
            let interval;
            const _this = this;
            let counter = 0;
            return new Promise((resolve, reject) => {
                interval = setInterval(function () {
                    if (_this.state.messages[fieldname.split(".")[0]]) {
                        clearInterval(interval);
                        counter += 1;
                        resolve();
                    } else {
                        if (counter > 6) {
                            console.log("not resolving");
                            clearInterval(interval);
                            reject(new Error("Could not load messageType"));
                        }
                    }
                }, 2000);
            });
        },
        saveParametersToFile() {
            let parameterNameMaxSize = 0;

            // Sort parameters alphabetically
            // We take advantage of sort to also calculate the parameter name maximum size
            const parameters = Object.entries(
                this.state.params?.values ?? {},
            ).sort((first, second) => {
                parameterNameMaxSize = Math.max(
                    parameterNameMaxSize,
                    first[0].length,
                );
                parameterNameMaxSize = Math.max(
                    parameterNameMaxSize,
                    second[0].length,
                );

                if (first[0] < second[0]) {
                    return -1;
                }
                if (first[0] > second[0]) {
                    return 1;
                }
                return 0;
            });

            let content = "";

            content += `# Parameters extracted from file ${this.state.file}\n`;
            content += `# Date: ${new Date()}\n`;

            const fileName = `${this.state.file}.params`;

            for (const param of parameters) {
                // Calculate space between name and value to make it pretty
                const space = Array(
                    parameterNameMaxSize - param[0].length + 2,
                ).join(" ");
                content += `${param[0]}${space}${param[1]}\n`;
            }

            downloadData(content, `${fileName}.txt`, "text/plain");
        },
        printParam(param) {
            // prints number with just enough decimal places, up to 3, ommiting trailing zeroes
            return parseFloat(param).toFixed(
                Math.min(
                    3,
                    Math.max(0, 3 - Math.floor(param).toString().length),
                ),
            );
        },
        // undefined while the next log loads (resetLogState clears params)
        paramValue(param) {
            return this.state.params?.values[param];
        },
        isDefaultParam(param) {
            return this.paramValue(param) === this.state.defaultParams[param];
        },
    },
};
</script>

<style scoped>
div #paneParamViewer {
    min-width: 220px;
    min-height: 150px;
    position: absolute;
    background: rgb(253 254 255 / 85.6%);
    color: #141924;
    font-size: 11px;
    font-weight: 600;
    z-index: 10000;
    box-shadow: 9px 9px 3px -6px rgb(26 26 26 / 69.9%);
    border-radius: 5px;
    user-select: none;
}

div #paneParamViewer::before {
    content: "\25e2";
    color: #fff;
    background-color: rgb(38 53 71);
    position: absolute;
    bottom: 0;
    right: 0;
    width: 20px;
    height: 20px;
    padding: 2px 5px;
    box-sizing: border-box;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    border-radius: 10px 0 1px;
    cursor: se-resize;
}

div #paneParamViewer::after {
    content: "\2725";
    color: #141924;
    position: absolute;
    top: 0;
    left: 0;
    width: 18px;
    height: 17px;
    margin-top: -3px;
    padding: 0 2px;
    box-sizing: border-box;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    cursor: grab;
}

div#paneContent {
    /* ends above the resize handle in the bottom-right corner */
    height: calc(100% - 22px);
    overflow: auto;
    margin: 0;
}

input#filterbox {
    margin: 23px 0 0 10px;
    padding: 4px;
    background-color: rgb(255 255 255 / 83.6%);
    border: 1px solid rgb(133 133 133);
    border-radius: 3px;
}

input#filterbox:focus {
    outline: none;
    border: 1px solid #162442;
}

ul#params {
    padding: 12px;
    list-style: none;
    line-height: 22px;
    user-select: none;
}
</style>
