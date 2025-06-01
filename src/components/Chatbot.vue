/* eslint-disable */
<template>
  <div class="chatbot">
    <h2>Flight Log Chatbot</h2>
    <div v-if="!sessionId">
      <label class="upload-label">Upload .bin flight log:</label>
      <input type="file" accept=".bin" @change="onFileChange" />
    </div>
    <div v-else>
      <div class="messages">
        <div v-for="(m, idx) in messages" :key="idx" :class="m.role">
          <strong>{{ m.role === 'user' ? 'You' : 'Bot' }}:</strong> {{ m.content }}
        </div>
      </div>
      <div class="input-area">
        <input
          v-model="userInput"
          @keyup.enter="sendMessage"
          placeholder="Type a question..."
        />
        <button @click="sendMessage">Send</button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'Chatbot',
  data() {
    return {
      sessionId: null,
      messages: [],
      userInput: ''
    }
  },
  methods: {
    async onFileChange(e) {
      const file = e.target.files[0]
      if (!file) return
      const form = new FormData()
      form.append('file', file)
      try {
        const res = await axios.post('/api/upload-log', form, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        this.sessionId = res.data.sessionId
      } catch (err) {
        console.error(err)
        alert('Failed to upload log file.')
      }
    },
    async sendMessage() {
      const content = this.userInput.trim()
      if (!content) return
      this.messages.push({ role: 'user', content })
      this.userInput = ''
      try {
        const res = await axios.post('/api/chat', {
          sessionId: this.sessionId,
          message: content
        })
        this.messages.push({ role: 'bot', content: res.data.reply })
      } catch (err) {
        console.error(err)
        this.messages.push({ role: 'bot', content: 'Error getting response.' })
      }
    }
  }
}
</script>

<style scoped>
.chatbot {
  max-width: 600px;
  margin: 2rem auto;
  padding: 1rem;
  border: 1px solid #ccc;
  border-radius: 0.5rem;
  background: #fff;
}
.upload-label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
}
.messages {
  height: 400px;
  overflow-y: auto;
  margin-bottom: 1rem;
  padding: 0.5rem;
  background: #f9f9f9;
  border-radius: 0.25rem;
}
.user {
  text-align: right;
  margin: 0.5rem 0;
}
.bot {
  text-align: left;
  margin: 0.5rem 0;
}
.input-area {
  display: flex;
}
.input-area input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 0.25rem;
}
.input-area button {
  padding: 0.5rem 1rem;
  margin-left: 0.5rem;
  border: none;
  background: #007bff;
  color: #fff;
  border-radius: 0.25rem;
  cursor: pointer;
}
.input-area button:hover {
  background: #0056b3;
}
</style>
