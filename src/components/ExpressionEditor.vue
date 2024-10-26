<template>
  <div class="code-editor">
      <input class="code-input"
                :value="value"
                @input="updateValue($event.target.value)"
                @keydown="handleKeyDown"
                @blur="hideSuggestions"
                @focus="handleInput"
                ref="codeEditor"/>
      <div v-if="showSuggestions" class="suggestions-box" :style="suggestionsBoxStyle">
          <div v-for="(suggestion, index) in filteredSuggestions"
                :key="index"
                @click="applySuggestion(suggestion)"
                @mouseover="selectedIndex = index"
                class="suggestion-item"
                :class="{ selected: index === selectedIndex }">
              {{ suggestion }}
          </div>
      </div>
  </div>
</template>

<script>
export default {
    props: {
        value: String,
        suggestions: {
            type: Array,
            default: () => []
        }
    },
    data () {
        return {
            filteredSuggestions: [],
            showSuggestions: false,
            selectedIndex: 0,
            currentWord: '',
            cursorPosition: { top: 0, left: 0 }
        }
    },
    computed: {
        suggestionsBoxStyle () {
            return {
                top: `${this.cursorPosition.top}px`,
                left: `${this.cursorPosition.left}px`
            }
        }
    },
    mounted () {
        window.addEventListener('scroll', this.updateCursorPosition, true)
    },
    beforeDestroy () {
        window.removeEventListener('scroll', this.updateCursorPosition, true)
    },
    methods: {
        updateValue (value) {
            this.$emit('input', value)
            this.handleInput()
        },
        hideSuggestions () {
            setTimeout(() => {
                this.showSuggestions = false
            }, 100)
        },
        handleInput () {
            const cursorPosition = this.$refs.codeEditor.selectionStart
            const textBeforeCursor = this.value.slice(0, cursorPosition)

            if (this.shouldShowSuggestions(textBeforeCursor)) {
                const currentWord = this.getCurrentWord(textBeforeCursor)
                this.filteredSuggestions = this.suggestions.filter(s =>
                    s.toLowerCase().startsWith(currentWord.toLowerCase())
                )
                this.showSuggestions = this.filteredSuggestions.length > 0
                this.selectedIndex = 0
                this.updateCursorPosition()
            } else {
                this.showSuggestions = false
            }
        },
        shouldShowSuggestions (text) {
            const lastChar = text.slice(-1)
            const operators = ['+', '-', '*', '/', '=', '(', ',', ' ']
            return operators.includes(lastChar) || /\w/.test(lastChar)
        },
        getCurrentWord (text) {
            // eslint-disable-next-line no-useless-escape
            return text.split(/[\s\(\)\+\-\*\/\=,]+/).pop() || ''
        },
        handleKeyDown (e) {
            if (this.showSuggestions) {
                switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault()
                    this.selectedIndex = (this.selectedIndex + 1) % this.filteredSuggestions.length
                    break
                case 'ArrowUp':
                    e.preventDefault()
                    this.selectedIndex = (this.selectedIndex - 1 + this.filteredSuggestions.length) %
                     this.filteredSuggestions.length
                    break
                case 'Enter':
                case 'Tab':
                    e.preventDefault()
                    this.applySuggestion(this.filteredSuggestions[this.selectedIndex])
                    break
                case 'Escape':
                    this.showSuggestions = false
                    break
                }
            }
        },
        applySuggestion (suggestion) {
            const cursorPosition = this.$refs.codeEditor.selectionStart
            const textBeforeCursor = this.value.slice(0, cursorPosition)
            const textAfterCursor = this.value.slice(cursorPosition)
            const currentWord = this.getCurrentWord(textBeforeCursor)
            const lastChar = textBeforeCursor.slice(-1)
            const operators = ['+', '-', '*', '/', '=', '(', ',', ' ']

            let newValue
            if (operators.includes(lastChar)) {
                // If the last character is an operator or opening parenthesis, add the suggestion
                newValue = textBeforeCursor + suggestion + textAfterCursor
            } else {
                // Otherwise, replace the current word with the suggestion
                const textBeforeCurrentWord = textBeforeCursor.slice(0, -currentWord.length)
                newValue = textBeforeCurrentWord + suggestion + textAfterCursor
            }

            this.updateValue(newValue)

            this.$nextTick(() => {
                const newCursorPosition = cursorPosition + (suggestion.length - currentWord.length)
                this.$refs.codeEditor.selectionStart = this.$refs.codeEditor.selectionEnd = newCursorPosition
                this.$refs.codeEditor.focus()
            })

            this.showSuggestions = false
        },
        updateCursorPosition () {
            const input = this.$refs.codeEditor
            const inputRect = input.getBoundingClientRect()
            const textBeforeCursor = this.value.slice(0, input.selectionStart)

            // Create temporary element to measure text width
            const span = document.createElement('span')
            span.style.visibility = 'hidden'
            span.style.whiteSpace = 'pre'
            span.style.font = getComputedStyle(input).font
            span.textContent = textBeforeCursor || ' '
            document.body.appendChild(span)

            const textWidth = span.offsetWidth
            document.body.removeChild(span)

            this.cursorPosition = {
                top: inputRect.top + window.pageYOffset + inputRect.height,
                left: inputRect.left + window.pageXOffset + textWidth +
                    parseInt(getComputedStyle(input).paddingLeft)
            }
        }
    }
}
</script>

<style scoped>
        .code-editor {
            position: relative;
            color: black;
            display: inline-block;
        }
        .code-input {
            width: 100%;
            font-family: monospace;
            resize: none;
            display: inline-block;
            line-height: 15px;
            margin-bottom: 0;
            font-size: 13px;
            border: 1px solid grey;
            padding: 4.5px;
            border-radius: 20px;
        }
        .suggestions-box {
            text-align: left;
            position: fixed;
            background: white;
            border: 1px solid #ccc;
            border-radius: 4px;
            max-height: 150px;
            z-index: 1000;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .suggestion-item {
            cursor: pointer;
            line-height: 20px;

        }
        .suggestion-item.selected {
            background-color: #f0f0f0;
        }
    </style>
