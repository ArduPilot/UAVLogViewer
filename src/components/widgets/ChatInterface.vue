<template>
    <div class="uav-chat-container">
        <div class="uav-chat-header">Chatbot</div>
        <div class="uav-chat-messages">
            <div v-for="(msg, idx) in chatMessages" :key="idx" :class="`uav-chat-bubble-container ${msg.sender}`">
                <div :class="`uav-chat-bubble ${msg.sender}`">
                    <div class="fw-bold">{{ msg.sender }}:</div> {{ msg.text }}
                </div>
            </div>
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
            userInput: ''
        }
    },
    mounted () {
        if ('messages' in this.state) {
            this.establishKnowledgeBase()
        }
    },
    methods: {
        async sendMessage () {
            if (!this.userInput.trim()) return
            this.chatMessages.push({ sender: 'you', text: this.userInput })

            const query = this.userInput
            this.userInput = ''

            try {
                const res = await fetch('http://localhost:8000/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: query })
                })
                const data = await res.json()
                this.chatMessages.push({ sender: 'bot', text: data.response })
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
  width: 300px;
  height: 400px;
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

/* Utility CSS */
.fw-bold {
    font-weight: 700;
}

</style>
