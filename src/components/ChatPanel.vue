<template>
    <div class="chat-panel">
        <div class="controls">
            <textarea v-model="summaryText" placeholder="Paste summary JSON (temporary)" rows="6"></textarea>
            <button @click="onBootstrap" :disabled="bootstrapping">
                {{ sessionId ? 'Re-bootstrap' : 'Bootstrap' }}
            </button>
        </div>
        <div class="chat">
            <div class="messages">
                <div v-for="(m,i) in messages" :key="i" class="msg">{{ m }}</div>
            </div>
            <div class="input">
                <input v-model="input" @keyup.enter="onSend" placeholder="Ask about the flight..." />
                <button @click="onSend" :disabled="!sessionId">Send</button>
            </div>
        </div>
    </div>
</template>

<script>
import { bootstrapSession, chatSSE } from '../services/chat'
import { buildSummaryFromState } from '../services/summary'
import { store } from './Globals.js'

export default {
    name: 'ChatPanel',
    data () {
        return {
            summaryText: '',
            input: '',
            messages: [],
            bootstrapping: false,
            stopStream: null,
            store
        }
    },
    computed: {
        sessionId () {
            return this.store.chatSessionId
        }
    },
    methods: {
        async onBootstrap () {
            try {
                this.bootstrapping = true
                const summary = this.summaryText
                    ? JSON.parse(this.summaryText)
                    : buildSummaryFromState(this.store)
                const res = await bootstrapSession(summary)
                this.store.chatSessionId = res.session_id
                this.messages.push(`Session bootstrapped: ${this.store.chatSessionId}`)
            } catch (e) {
                this.messages.push('Bootstrap failed')
            } finally {
                this.bootstrapping = false
            }
        },
        onSend () {
            if (!this.store.chatSessionId || !this.input) return
            const text = this.input
            this.input = ''
            this.messages.push(`You: ${text}`)
            if (this.stopStream) this.stopStream()
            this.stopStream = chatSSE({
                sessionId: this.store.chatSessionId,
                message: text,
                onEvent: this.handleEvent
            })
        },
        handleEvent ({ event, data }) {
            if (event === 'message' && data && data.content) {
                this.messages.push(`Agent: ${data.content}`)
            } else if (event === 'tool_result') {
                this.messages.push(`Tool: ${data.name} -> ${JSON.stringify(data.result)}`)
            } else if (event === 'error') {
                this.messages.push(`Error: ${data.message}`)
            }
        }
    }
}
</script>

<style scoped>
.chat-panel { display: flex; gap: 12px; }
.controls { width: 30%; display: flex; flex-direction: column; gap: 8px; }
.chat { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.messages { flex: 1; overflow: auto; background: #111; color: #eee; padding: 8px; border-radius: 6px; }
.msg { margin: 4px 0; }
.input { display: flex; gap: 8px; }
textarea { width: 100%; font-family: monospace; }
input { flex: 1; }
</style>
