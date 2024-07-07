<template>
  <div class="code-editor">
      <input class="code-input"
                :value="value"
                @input="updateValue($event.target.value)"
                @keydown="handleKeyDown"
                @scroll="handleScroll"
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
            cursorPosition: { top: 0, left: 0 },
            scrollTop: 0
        }
    },
    computed: {
        suggestionsBoxStyle () {
            return {
                top: `${this.cursorPosition.top - this.scrollTop + 20}px`,
                left: `${this.cursorPosition.left}px`
            }
        }
    },
    methods: {
        updateValue (value) {
            this.$emit('input', value)
            this.handleInput()
        },
        handleInput () {
            const cursorPosition = this.$refs.codeEditor.selectionStart
            const textBeforeCursor = this.value.slice(0, cursorPosition)
            const words = textBeforeCursor.split(/\s+/)
            this.currentWord = words[words.length - 1]

            if (this.currentWord.length > 0) {
                this.filteredSuggestions = this.suggestions.filter(s =>
                    s.toLowerCase().startsWith(this.currentWord.toLowerCase())
                )
                this.showSuggestions = this.filteredSuggestions.length > 0
                this.selectedIndex = 0
                this.updateCursorPosition()
            } else {
                this.showSuggestions = false
            }
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
            const lastSpaceIndex = textBeforeCursor.lastIndexOf(' ')
            const newTextBeforeCursor = textBeforeCursor.slice(0, lastSpaceIndex + 1) + suggestion

            const newValue = newTextBeforeCursor + textAfterCursor
            this.updateValue(newValue)

            this.$nextTick(() => {
                this.$refs.codeEditor.selectionStart = this.$refs.codeEditor.selectionEnd = newTextBeforeCursor.length
                this.$refs.codeEditor.focus()
            })

            this.showSuggestions = false
        },
        updateCursorPosition () {
            const textarea = this.$refs.codeEditor
            const cursorPosition = textarea.selectionStart
            const textBeforeCursor = this.value.slice(0, cursorPosition)
            // const lines = textBeforeCursor.split('\n')
            // const currentLine = lines.length
            // const currentLineText = lines[lines.length - 1]

            const temp = document.createElement('div')
            temp.style.position = 'absolute'
            temp.style.top = '-9999px'
            temp.style.left = '-9999px'
            temp.style.width = textarea.clientWidth + 'px'
            temp.style.height = 'auto'
            temp.style.whiteSpace = 'pre-wrap'
            temp.style.wordWrap = 'break-word'
            temp.style.font = window.getComputedStyle(textarea).font
            temp.textContent = textBeforeCursor + '\n'
            document.body.appendChild(temp)

            const { lineHeight } = window.getComputedStyle(textarea)
            // const textareaRect = textarea.getBoundingClientRect()
            this.cursorPosition = {
                top: temp.clientHeight - parseFloat(lineHeight) + textarea.offsetTop,
                left: textarea.offsetLeft + 10
            }

            document.body.removeChild(temp)
        },
        handleScroll () {
            this.scrollTop = this.$refs.codeEditor.scrollTop
            if (this.showSuggestions) {
                this.updateCursorPosition()
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
            position: absolute;
            background: white;
            border: 1px solid #ccc;
            border-radius: 4px;
            max-height: 150px;
            overflow-y: auto;
            z-index: 1000;
            width: 200px;
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
