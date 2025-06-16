<template>
  <div class="chatbox" :class="{ minimized }">
    <div class="chatbox-header" @click="toggleMinimize">
      <span>💬 Chat</span>
      <button class="minimize-btn" aria-label="Minimize Chat">
  <span v-if="minimized">🔼</span>
  <span v-else>🔽</span>
</button>
    </div>
    <div class="chatbox-body" v-if="!minimized">
      <div class="chat-messages">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="chat-message"
        >
          <strong>{{ msg.sender }}:</strong> {{ msg.text }}
        </div>
      </div>
      <input
        type="text"
        v-model="newMessage"
        @keydown.enter="sendMessage"
        placeholder="Type a message..."
      />
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChatBox',
  data () {
    return {
      minimized: false,
      messages: [],
      newMessage: ''
    }
  },
  methods: {
    toggleMinimize () {
      this.minimized = !this.minimized
    },
    async sendMessage () {
      const message = this.newMessage.trim()
      if (!message) return

      this.messages.push({ sender: 'You', text: message })
      this.newMessage = ''

      try {
        const response = await fetch('http://localhost:8000/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ message })
        })

        const data = await response.json()
        this.messages.push({
          sender: 'Bot',
          text: data.reply || 'No response.'
        })
      } catch (error) {
        console.error('Chat API error:', error)
        this.messages.push({
          sender: 'Bot',
          text: 'Error: Could not connect to chat API.'
        })
      }
    }
  }
}
</script>

<style scoped>
.chatbox {
  position: fixed;
  bottom: 20px;
  left: 5px;
  width: 300px;
  border-radius: 12px;
  background: #1e293b; /* slate-800 */
  color: #f8fafc;       /* slate-50 */
  font-family: 'Segoe UI', sans-serif;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
  z-index: 9999;
  overflow: hidden;
  border: 1px solid #334155; /* slate-700 */
  transition: all 0.3s ease-in-out;
}

.chatbox-header {
  padding: 10px 14px;
  background: #0f172a; /* slate-900 */
  color: #e2e8f0;      /* slate-200 */
  font-weight: 600;
  font-size: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  border-bottom: 1px solid #334155;
}

.chatbox-body {
  padding: 12px 14px;
  background-color: #1e293b;
}

.chat-messages {
  max-height: 160px;
  overflow-y: auto;
  margin-bottom: 10px;
  padding-right: 6px;
}

.chat-message {
  margin-bottom: 6px;
  line-height: 1.4;
}

input[type='text'] {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #334155;
  border-radius: 8px;
  background: #0f172a;
  color: #f1f5f9;
  font-size: 14px;
  transition: border 0.2s;
}

input[type='text']:focus {
  outline: none;
  border-color: #3b82f6; /* blue-500 */
}

.minimized .chatbox-body {
  display: none;
}

.minimize-btn {
  background: transparent;
  border: none;
  color: #94a3b8; /* slate-400 */
  font-size: 18px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  transition: background 0.2s, color 0.2s;
}

.minimize-btn:hover {
  background: #334155; /* slate-700 */
  color: #f8fafc;       /* slate-50 */
}

</style>
