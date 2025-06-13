<template>
  <div>
    <!-- Toggle button -->
    <button
      class="chat-toggle btn btn-primary"
      @click="toggle"
      title="Open/Close Chat"
    >💬 Chat</button>

    <!-- Floating panel -->
    <transition name="fade">
      <div v-if="open" class="chat-wrapper card shadow">
        <div class="card-body p-2 chat-history" ref="scrollArea">
          <div v-for="(msg, idx) in state.chatMessages" :key="idx" :class="['chat-msg', msg.sender]">
            <span v-html="renderMarkdown(msg.text)" />
          </div>
          <div v-if="loading" class="chat-msg bot"><em>...</em></div>
        </div>
        <div class="input-group p-2" v-if="state.backendReady">
          <input
            type="text"
            class="form-control"
            v-model.trim="input"
            @keyup.enter="send"
            :disabled="loading"
            placeholder="Type a question…"
          />
          <div class="input-group-append">
            <button
              class="btn btn-success"
              :disabled="loading || !input"
              @click="send"
            >Send</button>
          </div>
        </div>
        <div v-else class="p-2 text-center text-muted small">
          <em>Backend is still processing the log… Chat will be enabled once ready.</em>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
/* eslint-disable indent, no-trailing-spaces, eol-last */
import { store } from './Globals'
import { sendChat } from '../libs/chatApi'
import { marked } from 'marked'

export default {
  name: 'ChatPanel',
  data () {
    return {
      state: store,
      open: false,
      input: '',
      loading: false
    }
  },
  methods: {
    toggle () {
      this.open = !this.open
      this.$nextTick(() => {
        this.scrollToBottom()
      })
    },
    async send () {
      if (!this.input) return
      if (!this.state.sessionId) {
        alert('Please upload a log file first.')
        return
      }
      const text = this.input
      this.input = ''
      // push user message immediately
      this.state.chatMessages.push({ sender: 'user', text, ts: Date.now() })
      this.loading = true
      try {
        const resp = await sendChat({
          sessionId: this.state.sessionId,
          message: text,
          conversationId: this.state.conversationId
        })
        this.state.conversationId = resp.conversation_id || this.state.conversationId
        this.state.chatMessages.push({ sender: 'bot', text: resp.response, ts: Date.now() })
      } catch (err) {
        console.error(err)
        this.state.chatMessages.push({ sender: 'bot', text: `(Error) ${err.message}`, ts: Date.now() })
      } finally {
        this.loading = false
        this.$nextTick(this.scrollToBottom)
      }
    },
    scrollToBottom () {
      const el = this.$refs.scrollArea
      if (el) el.scrollTop = el.scrollHeight
    },
    renderMarkdown (text) {
      try {
        return marked.parse(text)
      } catch (e) {
        return text
      }
    }
  },
  watch: {
    'state.chatMessages': {
      handler () {
        this.$nextTick(this.scrollToBottom)
      },
      deep: true
    }
  }
}
</script>

<style scoped>
.chat-toggle {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 999;
}
.chat-wrapper {
  position: fixed;
  bottom: 70px;
  right: 20px;
  width: 300px;
  max-height: 60vh;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 6px;
  z-index: 998;
}
.chat-history {
  overflow-y: auto;
  flex: 1;
  font-size: 0.9em;
}
.chat-msg {
  margin-bottom: 6px;
}
.chat-msg.user {
  text-align: right;
  color: #0b5ed7;
}
.chat-msg.bot {
  text-align: left;
  color: #212529;
}
.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter, .fade-leave-to { opacity: 0; }
</style> 