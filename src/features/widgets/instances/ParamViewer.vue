<template>
    <div
        :id="getDivName()"
        class="uav-widget"
        :style="{
            width: width + 'px',
            height: height + 'px',
            top: top + 'px',
            left: left + 'px',
        }"
    >
        <span class="uav-widget__move"></span>
        <span class="uav-widget__resize"></span>
        <span class="uav-widget__close" @click="close()"></span>
        <div class="uav-widget__content">
            <div class="filter-row">
                <label for="filterbox">Filter</label>
                <input id="filterbox" v-model="filter" placeholder="Filter" />
                <button @click="saveParametersToFile">save</button>
            </div>
            <div v-if="haveDefaults" class="param-check">
                <input
                    id="showdiff"
                    v-model="showdiff"
                    class="param-check__box"
                    type="checkbox"
                />
                <label class="param-check__label" for="showdiff">
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
import { store } from "@/shared/stores/index.js";
import { useWidget, widgetProps } from "@/features/widgets/core/useWidget.js";
import { downloadData } from "@/shared/lib/download.js";

export default {
    name: "ParamViewer",
    props: widgetProps,
    emits: ["close"],
    setup(props, { emit }) {
        return useWidget(props, emit, {
            name: "ParamViewer",
            width: 300,
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
                .filter((key) => key.includes(this.filter.toUpperCase()))
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
            let counter = 0;
            return new Promise((resolve, reject) => {
                interval = setInterval(() => {
                    if (this.state.messages[fieldname.split(".")[0]]) {
                        clearInterval(interval);
                        counter += 1;
                        resolve();
                    } else if (counter > 6) {
                        console.log("not resolving");
                        clearInterval(interval);
                        reject(new Error("Could not load messageType"));
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
                const space = new Array(
                    parameterNameMaxSize - param[0].length + 2,
                ).join(" ");
                content += `${param[0]}${space}${param[1]}\n`;
            }

            downloadData(content, `${fileName}.txt`, "text/plain");
        },
        printParam(param) {
            // prints number with just enough decimal places, up to 3, ommiting trailing zeroes
            return Number.parseFloat(param).toFixed(
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
#paneParamViewer {
    min-width: 300px;
}

.filter-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 0 0 10px;
}

.filter-row input#filterbox {
    flex: 1;
    min-width: 0;
}

input#filterbox {
    padding: 4px 8px;
    background-color: rgb(255 255 255 / 83.6%);
    border: 1px solid rgb(133 133 133);
    border-radius: 3px;
    box-sizing: border-box;
}

input#filterbox:focus {
    outline: none;
    border: 1px solid #162442;
}

button {
    padding: 0 10px;
    height: 26px;
    box-sizing: border-box;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background-color: #263547;
    color: #fff;
    border: none;
    border-radius: 3px;
    font-family: inherit;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    cursor: pointer;
    transition: background-color 0.15s ease;
}

button:hover {
    background-color: #3a4f6b;
}

button:active {
    background-color: #162442;
}

button:focus-visible {
    outline: 2px solid #162442;
    outline-offset: 2px;
}

.param-check {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 0 10px;
    padding: 0;
}

.param-check__box {
    appearance: none;
    margin: 0;
    padding: 0;
    flex: 0 0 16px;
    width: 16px;
    height: 16px;
    border: 2px solid #263547;
    border-radius: 3px;
    background-color: #fff;
    cursor: pointer;
    box-sizing: border-box;
    display: block;
}

.param-check__box:checked {
    background-color: #263547;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 12'%3E%3Cpath d='M3 6 L5 8 L9 4' stroke='white' stroke-width='2' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-size: 100% 100%;
    background-repeat: no-repeat;
}

.param-check__box:focus-visible {
    outline: 2px solid #162442;
    outline-offset: 1px;
}

.param-check__label {
    line-height: 1;
    text-box-trim: trim-both;
    text-box-edge: cap alphabetic;
}

table#params {
    padding: 0;
    line-height: 22px;
    user-select: none;
}
</style>
