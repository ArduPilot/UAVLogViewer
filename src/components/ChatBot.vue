<template>
    <div class="chatbot-panel">
        <div class="chatbot-header"><span>ChatBot</span></div>
        <div class="chatbot-body" ref="body">
            <div v-for="(msg, i) in messages" :key="i" :class="['chat-message', msg.role]">
                <span class="role">{{ msg.role === 'user' ? 'You' : 'Bot' }}:</span>
                <span class="content">{{ msg.content }}</span>
            </div>
            <div v-if="loading" class="chat-message assistant">
                <span class="role">Bot:</span>
                <span class="content">Thinking...</span>
            </div>
        </div>
        <div class="chatbot-input">
            <input v-model="input" @keyup.enter="send" :disabled="loading" placeholder="Ask about the flight log..." />
            <button @click="send" :disabled="loading || !input.trim()">Send</button>
        </div>
    </div>
</template>

<script>
/* eslint-disable space-before-function-paren */
export default {
    name: 'ChatBot',
    data() {
        return {
            messages: [
                {
                    role: 'assistant',
                    content: 'Hello! You can ask anything about the UAV flight log.'
                }
            ],
            input: '',
            loading: false
        }
    },
    methods: {
        async send() {
            if (!this.input.trim()) return
            const question = this.input
            this.messages.push({ role: 'user', content: question })
            this.input = ''
            this.loading = true
            this.scrollToBottom()
            try {
                const res = await fetch('http://localhost:5001/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question })
                })
                const data = await res.json()
                this.messages.push({
                    role: 'assistant',
                    content: data.answer || '[No answer from backend.]'
                })
            } catch (err) {
                this.messages.push({
                    role: 'assistant',
                    content: 'Sorry, I could not contact backend.'
                })
            }
            this.loading = false
            this.scrollToBottom()
        },
        scrollToBottom() {
            this.$nextTick(() => {
                const el = this.$refs.body
                if (el) el.scrollTop = el.scrollHeight
            })
        }
    }
}
</script>

<style scoped>
/* All your same chatbot styles, unchanged */
.chatbot-panel {
    background: #23243a;
    color: #fff;
    border-radius: 8px;
    margin-top: 24px;
    padding: 8px 0 0 0;
    display: flex;
    flex-direction: column;
    width: 100%;
    min-height: 320px;
    box-shadow: none;
}

.chatbot-header {
    display: flex;
    background: none;
    padding: 0 0 8px 20px;
    font-size: 30px;
    font-weight: 700;
    justify-content: center;
}

.chatbot-body {
    flex: 1;
    overflow-y: auto;
    padding: 10px 16px;
    background: #23243a;
    min-height: 200px;
    max-height: 320px;
}

.chat-message {
    margin-bottom: 10px;
    display: flex;
    align-items: flex-start;
}

.chat-message.user .role {
    color: #50d3a4;
    font-weight: bold;
    margin-right: 6px;
}

.chat-message.assistant .role {
    color: #88aaff;
    font-weight: bold;
    margin-right: 6px;
}

.chatbot-input {
    padding: 10px 16px 10px 16px;
    background: #23243a;
    display: flex;
    gap: 8px;
    border-bottom-left-radius: 8px;
    border-bottom-right-radius: 8px;
}

.chatbot-input input {
    flex: 1;
    padding: 6px 10px;
    border: none;
    border-radius: 6px;
    outline: none;
    font-size: 15px;
}

.chatbot-input button {
    padding: 6px 15px;
    background: #ffe92e;
    color: #222;
    border: none;
    border-radius: 6px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
}

.chatbot-input button[disabled] {
    background: #bbbbbb;
    cursor: not-allowed;
}
</style>
