<template>
  <div class="chat-container">
    <div class="chat-header">
      <h3 class="chat-title">Flight Data Assistant</h3>
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
      <div v-for="(message, index) in messages" 
           :key="index"
           v-if="message.role === 'user' || message.content || message.isStreaming"
           :class="[
            'message',
            message.role === 'user' ? 'user-message' : 'assistant-message',
            { 
              'streaming': isStreaming && index === messages.length - 1,
              'processing': message.isProcessing
            }
          ]">
        <div class="message-content">
          <div 
            class="message-text" 
            v-html="renderMessageContent(message.content)"
          ></div>
          <span v-if="message.isStreaming" class="typing-cursor">|</span>
          <div class="message-time">{{ message.timestamp }}</div>
        </div>
      </div>

      <!-- Loading dots -->
      <div v-if="isProcessing && !isAnyMessageStreaming" class="loading-dots">
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
      </div>
    </div>
    <div class="chat-input">
      <input 
        v-model="newMessage" 
        @keyup.enter="sendMessage"
        :disabled="isProcessing || !isFileUploaded"
        :placeholder="isFileUploaded ? 'Type your message...' : 'Please upload a file first...'"
        class="message-input"
      />
      <button 
        @click="sendMessage" 
        :disabled="!newMessage.trim() || isProcessing || !isFileUploaded"
        :title="!isFileUploaded ? 'Please upload a file first' : ''"
      >
        Send
      </button>
    </div>
  </div>
</template>

<script>
import { marked } from 'marked';

export default {
  props: {
    sessionId: {
      type: String,
      default: null
    }
  },
  computed: {
    isAnyMessageStreaming() {
      return this.messages.some(msg => msg.isStreaming);
    }
  },
  data() {
    return {
      messages: [],
      newMessage: "",
      isProcessing: false,
      sessionId: null,
      isFileUploaded: false,  // Track if file is uploaded
      isStreaming: false,
      currentStreamingMessage: "",
      currentStreamingIndex: 0,
    };
  },
  methods: {
    renderMessageContent(content) {
      if (!content) return '';
      
      // First, render markdown to handle **bold** and other markdown
      let html = marked.parse(content);
      
      // Ensure line breaks are preserved
      html = html.replace(/\n/g, '<br>');
      
      return html;
    },
    
    async sendMessage() {
      if (this.newMessage.trim() === '') return
      
      // Add user message
      const userMessage = {
        role: 'user',
        content: this.newMessage,
        timestamp: new Date().toLocaleTimeString()
      }
      this.messages.push(userMessage);
      const userInput = this.newMessage;
      this.newMessage = '';
      
      this.isProcessing = true;
      this.scrollToBottom();
      
      // Call the backend API with the session ID
      try {
        this.isProcessing = true
        console.log("sessionId",this.sessionId);
        const response = await fetch('http://0.0.0.0:8000/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            session_id: this.sessionId,
            message: userInput
          })
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        const assistantMessage = {
          role: 'assistant',
          content: '',
          timestamp: new Date().toLocaleTimeString(),
          isStreaming: true
        };
        this.messages.push(assistantMessage);
        this.isProcessing = false;
        this.scrollToBottom();
        
        // Get the last message (which is our assistant's message)
        const lastMessageIndex = this.messages.length - 1;
        
        // Split the response into words
        const words = data.answer.split(' ');
        let currentText = '';
        
        // Add words one by one with a small delay
        for (let i = 0; i < words.length; i++) {
          // Add a space between words, but not before the first word
          currentText += (i > 0 ? ' ' : '') + words[i];
          
          // Update the message content
          this.$set(this.messages, lastMessageIndex, {
            ...this.messages[lastMessageIndex],
            content: currentText
          });
          
          // Scroll to bottom after each update
          this.scrollToBottom();
          
          // Small delay between words (adjust timing as needed)
          await new Promise(resolve => setTimeout(resolve, 100));
        }
        
      } catch (error) {
        console.error('Error sending message:', error);
        // Update the last message with the error
        const lastMessageIndex = this.messages.length - 1;
        this.$set(this.messages, lastMessageIndex, {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date().toLocaleTimeString(),
          isError: true
        });
      } finally {
        // Mark streaming as complete
        const lastMessageIndex = this.messages.length - 1;
        if (this.messages[lastMessageIndex]) {
          this.$set(this.messages, lastMessageIndex, {
            ...this.messages[lastMessageIndex],
            isStreaming: false
          });
        }
        this.isProcessing = false;
        this.scrollToBottom();
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
      this.isFileUploaded = !!newVal;
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
  height: calc(100vh - 150px); /* Full viewport height minus header and input */
  background-color: #2d3748;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
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

.chat-title {
  font-size: 1.1rem;
  margin: 0;
  font-weight: 500;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
  background-color: #1a202c;
  height: calc(100% - 110px); /* Adjust based on header and input height */
  position: relative;
  scroll-behavior: smooth;
}

.message {
  margin-bottom: 10px;
  max-width: 80%;
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 12px;
  line-height: 1.4;
}

.message-text {
  white-space: 0.95rem;
  line-height: 1.5;
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

.message.processing {
  opacity: 0.7;
  font-style: italic;
}

.message-text {
  font-size: 0.95rem;
  line-height: 1.5;
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

.typing-cursor {
  animation: blink 1s infinite;
}

@keyframes blink {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
  100% {
    opacity: 1;
  }
}

.loading-dots {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  padding: 10px 15px;
  margin: 2px 0;
  padding-left: 5px;
}

.dot {
  width: 8px;
  height: 8px;
  margin: 0 4px;
  background-color: #a0aec0;
  border-radius: 50%;
  display: inline-block;
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) {
  animation-delay: -0.32s;
}

.dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% { 
    transform: scale(0.6);
    opacity: 0.6;
  }
  40% { 
    transform: scale(1);
    opacity: 1;
  }
}

.message.assistant-message {
  position: relative;
  min-height: 30px;
}
</style>
