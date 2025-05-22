<template>
  <div class="chat-container">
    <div v-for="(msg, idx) in messages" :key="idx">
      {{ msg.content }}
    </div>
    <input v-model="input" @keyup.enter="sendMessage">
  </div>
</template>

<script>
export default {
  data() {
    return {
      ws: null,
      input: '',
      messages: []
    }
  },
  mounted() {
    this.ws = new WebSocket('ws://localhost:8000/ws/chat')
    this.ws.onmessage = (event) => {
      this.messages.push(JSON.parse(event.data))
    }
  },
  methods: {
    sendMessage() {
      this.ws.send(JSON.stringify({
        message: this.input,
        session_id: this.$route.params.logId
      }))
      this.input = ''
    }
  }
}
</script>