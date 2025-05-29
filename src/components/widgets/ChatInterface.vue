<template>
    <div class="uav-chat-container">
        <div class="uav-chat-header">
            <div class="uav-chat-header__title">Chatbot</div>
            <button
                @click="closeChatWindow"
                type="button" id="chat-close-button"
                class="cesium-button cesium-toolbar-button uav-close-btn" title="Close 3D view">
                <svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
                    <line x1="12" y1="12" x2="28" y2="28" stroke="white" stroke-width="2" stroke-linecap="round" />
                    <line x1="28" y1="12" x2="12" y2="28" stroke="white" stroke-width="2" stroke-linecap="round" />
                </svg>
            </button>
        </div>
        <div class="uav-chat-messages">
            <div v-for="(msg, idx) in chatMessages" :key="idx" :class="`uav-chat-bubble-container ${msg.sender}`">
                <div :class="`uav-chat-bubble ${msg.sender}`">
                    <div class="fw-bold">{{ msg.sender }}:</div> {{ msg.text }}
                </div>
            </div>
        </div>
        <div
            id="agent-loader"
            v-show="isThinking"
            class="uav-chat-processing"
            >
            🤖 <span>Agent is thinking<span class="uav-chat-processing__dots"></span></span>
        </div>
        <form @submit.prevent="sendMessage" class="uav-chat-input">
            <input v-model="userInput" placeholder="Ask a question..." />
            <button class="uav-chat-btn" type="submit">Send</button>
        </form>
    </div>
</template>

<script>

import { store } from '../Globals'

export default {
    name: 'ChatInterface',
    data () {
        return {
            state: store,
            dataExtractors: null,
            chatMessages: [{ sender: 'bot', text: 'Hi! How can I help you?.' }],
            userInput: '',
            isThinking: false
        }
    },
    mounted () {
        if ('messages' in this.state) {
            this.establishKnowledgeBase()
        }
    },
    methods: {
        async closeChatWindow () {
            this.chatMessages = []
            try {
                await fetch('http://localhost:8000/chat-session-end', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: ''
                })
            } catch (err) {
                console.log('Error closing chat session: ', err)
            }
            this.$emit('closeChat')
        },
        async sendMessage () {
            if (!this.userInput.trim()) return
            this.chatMessages.push({ sender: 'you', text: this.userInput })

            const query = this.userInput
            this.userInput = ''
            this.isThinking = true

            try {
                const res = await fetch('http://localhost:8000/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: query })
                })
                const data = await res.json()
                this.chatMessages.push({ sender: 'bot', text: data.response })
                this.isThinking = false
            } catch (err) {
                this.chatMessages.push({ sender: 'bot', text: '⚠️ Error contacting chatbot API.' })
            }
        },
        async establishKnowledgeBase () {
            const knowledgeBase = JSON.stringify(this.state.messages)
            try {
                await fetch('http://localhost:8000/chat-knowledge', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: knowledgeBase })
                })
            } catch (err) {
                console.log('Error sending knowledge base data', err)
            }
        }
    }
}

</script>

<style scoped>
/* CSS for chat interface */

.uav-chat-container {
  width: 450px;
  height: 500px;
  display: flex;
  flex-direction: column;
  position: absolute;
  top: 50px;
  right: 10px;
  background: white;
  border: 1px solid #ccc;
  font-family: sans-serif;
  z-index: 999;
  box-shadow: 0 0 10px rgba(0,0,0,0.2);
}

.uav-chat-header {
  padding: 8px;
  background: #3d3a38;
  color: white;
  font-weight: bold;
  display: flex;
  justify-content: space-between;
}

.uav-chat-header__title {
    padding: 8px 0;
}

.uav-chat-messages {
  flex: 1;
  padding: 8px;
  overflow-y: auto;
  background: #f9f9f9;
}

.uav-chat-bubble-container {
    margin: 10px 0;
    position: relative;
    width: 100%;
    display: flex;
}

.uav-chat-bubble-container.bot {
    flex-flow: row;
}

.uav-chat-bubble-container.you {
    flex-flow: row-reverse;
}

.uav-chat-bubble {
    padding: 5px;
    color: white;
    border-radius: 5px;
    width: 80%;
}

.uav-chat-bubble.bot {
    background: #589de8;
}

.uav-chat-bubble.you {
    background: #77bd6b;
}

.uav-chat-input {
  display: flex;
  padding: 8px;
  border-top: 1px solid #ccc;
}

.uav-chat-input input {
  flex: 1;
  padding: 5px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.uav-chat-input button {
  margin-left: 5px;
  padding: 5px 10px;
}

.uav-chat-btn {
    background: #3d3a38;
    color: white;
    font-weight: 700;
    border: none;
}

.uav-chat-processing {
    margin-top: 8px;
    color: grey;
}

.uav-chat-processing > span {
    font-style: italic;
}

.uav-close-btn svg {
    stroke: white;
    stroke-width: 2px;
    width: 25px;
    height: 25px;
}

.uav-chat-processing__dots::after {
  content: '';
  display: inline-block;
  animation: dots 1.2s steps(3, end) infinite;
}

@keyframes dots {
  0%   { content: ''; }
  33%  { content: '.'; }
  66%  { content: '..'; }
  100% { content: '...'; }
}

/* Utility CSS */
.fw-bold {
    font-weight: 700;
}
</style>
