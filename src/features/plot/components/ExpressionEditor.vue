<template>
    <div class="code-editor">
        <label for="expression-editor" class="visually-hidden"
            >Expression</label
        >
        <input
            id="expression-editor"
            ref="codeEditor"
            class="code-input"
            :value="modelValue"
            @input="updateValue($event.target.value)"
            @keydown="handleKeyDown"
            @blur="hideSuggestions"
            @focus="handleInput"
        />
        <div
            v-if="showSuggestions"
            class="suggestions-box"
            :style="suggestionsBoxStyle"
        >
            <div
                v-for="(suggestion, index) in filteredSuggestions"
                :key="index"
                class="suggestion-item"
                :class="{ selected: index === selectedIndex }"
                @click="applySuggestion(suggestion)"
                @mouseover="selectedIndex = index"
            >
                {{ suggestion }}
            </div>
        </div>
    </div>
</template>

<script>
export default {
    props: {
        modelValue: { type: String, default: "" },
        suggestions: {
            type: Array,
            default: () => [],
        },
    },
    emits: ["update:modelValue"],
    data() {
        return {
            filteredSuggestions: [],
            showSuggestions: false,
            selectedIndex: 0,
            currentWord: "",
            cursorPosition: { top: 0, left: 0 },
        };
    },
    computed: {
        suggestionsBoxStyle() {
            return {
                top: `${this.cursorPosition.top}px`,
                left: `${this.cursorPosition.left}px`,
            };
        },
    },
    mounted() {
        window.addEventListener("scroll", this.updateCursorPosition, true);
    },
    beforeUnmount() {
        window.removeEventListener("scroll", this.updateCursorPosition, true);
    },
    methods: {
        updateValue(value) {
            this.$emit("update:modelValue", value);
            this.handleInput();
        },
        hideSuggestions() {
            setTimeout(() => {
                this.showSuggestions = false;
            }, 100);
        },
        handleInput() {
            const cursorPosition = this.$refs.codeEditor.selectionStart;
            const textBeforeCursor = this.modelValue.slice(0, cursorPosition);

            if (this.shouldShowSuggestions(textBeforeCursor)) {
                const currentWord = this.getCurrentWord(textBeforeCursor);
                this.filteredSuggestions = this.suggestions.filter((s) =>
                    s.toLowerCase().startsWith(currentWord.toLowerCase()),
                );
                this.showSuggestions = this.filteredSuggestions.length > 0;
                this.selectedIndex = 0;
                this.updateCursorPosition();
            } else {
                this.showSuggestions = false;
            }
        },
        shouldShowSuggestions(text) {
            const lastChar = text.slice(-1);
            const operators = ["+", "-", "*", "/", "=", "(", ",", " "];
            return operators.includes(lastChar) || /\w/.test(lastChar);
        },
        getCurrentWord(text) {
            return text.split(/[\s()+\-*/=,]+/).pop() || "";
        },
        handleKeyDown(e) {
            if (this.showSuggestions) {
                switch (e.key) {
                    case "ArrowDown":
                        e.preventDefault();
                        this.selectedIndex =
                            (this.selectedIndex + 1) %
                            this.filteredSuggestions.length;
                        break;
                    case "ArrowUp":
                        e.preventDefault();
                        this.selectedIndex =
                            (this.selectedIndex -
                                1 +
                                this.filteredSuggestions.length) %
                            this.filteredSuggestions.length;
                        break;
                    case "Enter":
                    case "Tab":
                        e.preventDefault();
                        this.applySuggestion(
                            this.filteredSuggestions[this.selectedIndex],
                        );
                        break;
                    case "Escape":
                        this.showSuggestions = false;
                        break;
                }
            }
        },
        applySuggestion(suggestion) {
            const cursorPosition = this.$refs.codeEditor.selectionStart;
            const textBeforeCursor = this.modelValue.slice(0, cursorPosition);
            const textAfterCursor = this.modelValue.slice(cursorPosition);
            const currentWord = this.getCurrentWord(textBeforeCursor);
            const lastChar = textBeforeCursor.slice(-1);
            const operators = ["+", "-", "*", "/", "=", "(", ",", " "];

            let newValue;
            if (operators.includes(lastChar)) {
                // If the last character is an operator or opening parenthesis, add the suggestion
                newValue = textBeforeCursor + suggestion + textAfterCursor;
            } else {
                // Otherwise, replace the current word with the suggestion
                const textBeforeCurrentWord = textBeforeCursor.slice(
                    0,
                    -currentWord.length,
                );
                newValue = textBeforeCurrentWord + suggestion + textAfterCursor;
            }

            this.updateValue(newValue);

            this.$nextTick(() => {
                const newCursorPosition =
                    cursorPosition + (suggestion.length - currentWord.length);
                this.$refs.codeEditor.selectionStart =
                    this.$refs.codeEditor.selectionEnd = newCursorPosition;
                this.$refs.codeEditor.focus();
            });

            this.showSuggestions = false;
        },
        updateCursorPosition() {
            const input = this.$refs.codeEditor;
            const inputRect = input.getBoundingClientRect();
            const textBeforeCursor = this.modelValue.slice(
                0,
                input.selectionStart,
            );

            // Create temporary element to measure text width
            const span = document.createElement("span");
            span.style.visibility = "hidden";
            span.style.whiteSpace = "pre";
            span.style.font = getComputedStyle(input).font;
            span.textContent = textBeforeCursor || " ";
            document.body.appendChild(span);

            const textWidth = span.offsetWidth;
            span.remove();

            this.cursorPosition = {
                top: inputRect.top + window.pageYOffset + inputRect.height,
                left:
                    inputRect.left +
                    window.pageXOffset +
                    textWidth +
                    Number.parseInt(getComputedStyle(input).paddingLeft),
            };
        },
    },
};
</script>

<style scoped>
.code-editor {
    position: relative;
    display: inline-block;
}

.code-input {
    box-sizing: border-box;
    width: 100%;
    height: 2rem;
    padding: 0 0.75rem;
    border: 1px solid rgb(133 133 133);
    border-radius: 4px;
    background-color: #fff;
    color: #141924;
    caret-color: #141924;
    font-family: monospace;
    font-size: 0.8125rem;
}

.code-input::placeholder {
    color: #a0a8b8;
}

.code-input:focus-visible {
    border-color: #d47f00;
    box-shadow: 0 0 4px 0 rgb(212 127 0 / 40%);
    outline: none;
}

.suggestions-box {
    position: fixed;
    text-align: left;
    max-height: 10rem;
    overflow-y: auto;
    background: #fff;
    border: 1px solid rgb(133 133 133);
    border-radius: 4px;
    color: #141924;
    z-index: 1000;
    box-shadow: 0 2px 10px rgb(0 0 0 / 10%);
}

.suggestion-item {
    padding: 0.25rem 0.5rem;
    line-height: 1.25rem;
    cursor: pointer;
}

.suggestion-item.selected {
    background: color-mix(in srgb, #fff 92%, black);
}
</style>
