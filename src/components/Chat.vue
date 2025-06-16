<template>
  <div class="chat-container">
    <div class="chat-header">
      <h3>Flight Data Assistant</h3>
    </div>
    <div class="chat-messages" ref="messagesContainer">
      <!-- Initial welcome message -->
      <div class="message assistant-message">
        <div class="message-content">
          <div class="message-text">Hi, I'm your Flight Data Assistant. Please upload a file and I can help you analyze it!</div>
          <div class="message-time">Just now</div>
        </div>
      </div>
      
      <!-- Dynamic messages -->
      <div v-for="(message, index) in messages" :key="index" 
           :class="['message', message.role === 'user' ? 'user-message' : 'assistant-message']">
        <div class="message-content">
          <div class="message-text">{{ message.content }}</div>
          <div class="message-time">{{ message.timestamp }}</div>
        </div>
      </div>
    </div>
    <div class="chat-input">
      <input 
        v-model="newMessage" 
        @keypress.enter.prevent="sendMessage"
        placeholder="Type your message..."
        class="message-input"
      />
      <button @click="sendMessage" class="send-button">
        <i class="fas fa-paper-plane"></i>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    sessionId: {
      type: String,
      default: null
    }
  },
  data() {
    return {
      messages: [],
      newMessage: ''
    }
  },
  methods: {
    async sendMessage() {
      if (this.newMessage.trim() === '') return
      
      // Add user message
      const userMessage = {
        role: 'user',
        content: this.newMessage,
        timestamp: new Date().toLocaleTimeString()
      }
      this.messages.push(userMessage)
      this.newMessage = ''
      
      // Call the backend API with the session ID
      try {
        const response = await fetch('http://0.0.0.0:8000/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            session_id: this.sessionId,
            message: userMessage.content
          })
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Add assistant's response to the chat
        this.addMessage({
          role: 'assistant',
          content: data.message,
          timestamp: new Date().toLocaleTimeString()
        });
      } catch (error) {
        console.error('Error sending message:', error);
        this.addMessage({
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date().toLocaleTimeString()
        });
      }
    },
    addMessage(message) {
      this.messages.push(message);
      this.scrollToBottom();
    },
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer;
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      });
    }
  },
  watch: {
    sessionId(newVal) {
      if (newVal) {
        // If we have a new session ID, we might want to load any previous messages
        // or do other session-specific initialization here
        console.log('New session ID:', newVal);
      }
    }
  },
  mounted() {
    this.scrollToBottom();
  }
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 400px;
  max-height: 100%;
  background-color: #2d3748;
  border-radius: 8px;
  overflow: hidden;
  margin-top: 10px;
}

.chat-header {
  background-color: #2d3748;
  color: white;
  padding: 10px 15px;
  font-size: 14px;
  font-weight: bold;
  border-bottom: 1px solid #4a5568;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  background-color: #1a202c;
}

.message {
  margin-bottom: 10px;
  max-width: 80%;
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 12px;
  line-height: 1.4;
}

.user-message {
  margin-left: auto;
  background-color: #4299e1;
  color: white;
  border-bottom-right-radius: 4px;
}

.assistant-message {
  margin-right: auto;
  background-color: #4a5568;
  color: white;
  border-bottom-left-radius: 4px;
}

.message-content {
  display: flex;
  flex-direction: column;
}

.message-time {
  font-size: 10px;
  opacity: 0.8;
  margin-top: 2px;
  text-align: right;
}

.chat-input {
  display: flex;
  padding: 8px;
  background-color: #2d3748;
  border-top: 1px solid #4a5568;
}

.message-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #4a5568;
  border-radius: 4px;
  background-color: #1a202c;
  color: white;
  font-size: 12px;
  outline: none;
}

.send-button {
  background-color: #4299e1;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0 12px;
  margin-left: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.send-button:hover {
  background-color: #3182ce;
}

.send-button i {
  font-size: 14px;
}
</style>
