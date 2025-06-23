<template>
  <div class="flight-chat-container">
    <!-- Header with aviation theme -->
    <header class="chat-header">
      <div class="header-content">
        <div class="avatar-section">
      <div class="avatar">
            <svg viewBox="0 0 24 24" fill="currentColor" class="plane-icon">
              <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
            </svg>
      </div>
      <div class="header-info">
            <h3 class="title">Flight Assistant</h3>
            <p class="subtitle">AI-Powered Log Analysis</p>
            <div class="status-indicator">
              <span class="status-dot"></span>
              <span class="status-text">Online</span>
            </div>
          </div>
        </div>
        <div class="header-actions">
          <button class="action-btn minimize-btn" @click="$emit('minimize')" title="Minimize">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M19 13H5v-2h14v2z"/>
            </svg>
          </button>
          <button class="action-btn close-btn" @click="$emit('close')" title="Close">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>
      </div>
    </header>

    <!-- Messages Area -->
    <div class="messages-container" ref="messagesContainer">
      <transition-group name="message-fade" tag="div" class="messages-wrapper">
        <!-- Welcome message -->
        <div v-if="messages.length === 0" class="welcome-message" key="welcome">
          <div class="welcome-icon">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>
            </svg>
          </div>
          <h3>Welcome to Flight Assistant</h3>
          <p>Attach your flight log using the paperclip icon below and ask me anything!</p>
        </div>

        <!-- Chat Messages -->
        <div
          v-for="(message, index) in messages"
          :key="message.timestamp.toISOString() + index"
          :class="['message', message.from]"
      >
          <div class="message-avatar">
            <div v-if="message.from === 'assistant'" class="bot-avatar">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
              </svg>
            </div>
            <div v-else class="user-avatar">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
              </svg>
            </div>
          </div>
          <div class="message-content">
            <div class="message-bubble">
              <div class="message-text" v-html="formatMessage(message.text)"></div>
              <div class="message-time">{{ formatTime(message.timestamp) }}</div>
            </div>
          </div>
        </div>

        <!-- Loading indicator -->
        <div v-if="isLoading" class="message assistant" key="loading">
          <div class="message-avatar">
            <div class="bot-avatar">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
              </svg>
            </div>
          </div>
          <div class="message-content">
            <div class="message-bubble">
              <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
        </div>
      </div>
      </transition-group>
    </div>

    <!-- Input Area -->
    <div class="input-area" @drop.prevent="handleFileDrop" @dragover.prevent @dragenter.prevent>
      <div v-if="attachedFile" class="attached-file-display">
        <div class="file-icon-wrapper">
          <svg viewBox="0 0 24 24" fill="currentColor" class="file-icon">
            <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z"/>
          </svg>
        </div>
        <div class="file-info">
          <span class="file-name" :title="attachedFile.name">{{ attachedFile.name }}</span>
          <div v-if="isUploading" class="progress-container">
            <div class="progress-bar" :style="{ width: uploadProgress + '%' }"></div>
          </div>
        </div>
        <button @click="removeFile" class="remove-file-btn" title="Remove file" :disabled="isLoading">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
          </svg>
        </button>
      </div>

<form class="input-container" @submit.prevent="sendMessage">
  <div class="input-wrapper">
    <input
      ref="fileInput"
      type="file"
      accept=".bin,.tlog,.ulg"
      @change="handleFileSelect"
      style="display: none"
    />
    <button
      @click="triggerFileUpload"
      class="action-btn attach-btn"
      title="Attach flight log"
      type="button"
    >
      <svg viewBox="0 0 24 24" fill="currentColor">
        <path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5c0-1.38 1.12-2.5 2.5-2.5s2.5 1.12 2.5 2.5v10.5c0 .55-.45 1-1 1s-1-.45-1-1V6H10v9.5c0 1.38 1.12 2.5 2.5 2.5s2.5-1.12 2.5-2.5V5c0-2.21-1.79-4-4-4S7 2.79 7 5v12.5c0 3.04 2.46 5.5 5.5 5.5s5.5-2.46 5.5-5.5V6h-1.5z"/>
      </svg>
    </button>

    <input
      v-model="draft"
      :placeholder="placeholderText"
      class="message-input"
      :disabled="isInputDisabled"
    />

    <div class="input-actions">
      <button
        :disabled="!canSend"
        class="action-btn send-btn"
        title="Send message"
        type="submit"
      >
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
        </svg>
      </button>
    </div>
  </div>
</form>
      
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
// No axios import needed here
// import axios from 'axios'

export default {
  name: 'FlightChatWidget',
  props: {
    messages: {
      type: Array,
      required: true,
      default: () => []
    },
    isLoading: {
      type: Boolean,
      default: false
    },
    isUploading: {
      type: Boolean,
      default: false
    },
    uploadProgress: {
      type: Number,
      default: 0
    },
    // This prop tells the widget if a log has been processed on the backend
    hasActiveLog: {
        type: Boolean,
        default: false
    }
  },
  data() {
    return {
      draft: '',
      attachedFile: null
    }
  },
  computed: {
    canSend() {
      // User can send if they type a message OR attach a file.
      return this.draft.trim() || this.attachedFile
    },
    isInputDisabled() {
        // Input is disabled if a file hasn't been processed yet AND no new file is attached.
        return !this.hasActiveLog && !this.attachedFile
    },
    placeholderText() {
      if (this.isInputDisabled) {
        return 'Attach a log file to begin...'
      }
      if (this.attachedFile) {
        return 'Add a message... (optional)'
      }
      return 'Ask a follow-up question...'
    }
  },
  methods: {
    sendMessage(event) {
      if (event) event.preventDefault();
      if (!this.canSend) return;

      // Emit one event with all the necessary info for the parent.
      this.$emit('send-request', {
          text: this.draft.trim(),
          file: this.attachedFile
      });

      // Clear the local state after sending.
      this.draft = '';
      this.attachedFile = null;
    },

    // All other methods like uploadFile, sendQuery, addMessage are REMOVED.
    // They will be handled by the parent component (Home.vue)

    triggerFileUpload(event) {
      if (event) event.preventDefault();
      this.$refs.fileInput.click()
    },

    handleFileSelect(event) {
      const file = event.target.files[0]
      if (file) {
        this.attachedFile = file
      }
      this.$refs.fileInput.value = ''
    },

    handleFileDrop(event) {
      const files = event.dataTransfer.files
      if (files.length > 0 && files[0].name.match(/\.(bin|tlog|ulg)$/i)) {
        this.attachedFile = files[0]
      } else {
        // Instead of adding a message directly, emit an event for the parent to handle.
        this.$emit('add-message', {
            from: 'assistant',
            text: 'Please drop a valid log file (.bin, .tlog, .ulg)',
            timestamp: new Date()
        });
      }
    },

    removeFile() {
      this.attachedFile = null;
    },

    formatMessage(text) {
      // This is a display utility, so it stays.
      if (typeof text !== 'string') {
        // If the message is not a string, display a generic error or string representation.
        return 'Received an invalid message format.';
      }
      return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>')
    },

    formatTime(timestamp) {
      if (!timestamp) return ''
      return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer
        if (container) {
          container.scrollTop = container.scrollHeight
        }
      })
    }
  },
  watch: {
    messages() {
      this.scrollToBottom()
    }
  },
  mounted() {
    this.scrollToBottom()
  }
}
</script>

<style scoped>
/* Main container with open animation and new background */
.flight-chat-container {
  position: fixed;
  bottom: 100px;
  right: 30px;
  width: 420px;
  height: 620px;
  background-color: #1a1c23; /* Deep space blue/black */
  background-image: radial-gradient(circle at top right, rgba(77, 95, 255, 0.1), transparent 40%),
                    radial-gradient(circle at bottom left, rgba(142, 84, 233, 0.1), transparent 50%);
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 1200;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #e0e0e0;
  font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
  transform-origin: bottom right;
  /* Animation properties */
  animation: open-chat 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes open-chat {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Header with a sleeker gradient */
.chat-header {
  background: linear-gradient(135deg, rgba(42, 42, 74, 0.5) 0%, rgba(58, 58, 90, 0.3) 100%);
  backdrop-filter: blur(10px);
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
}

/* Messages container with a darker, cleaner background */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background-color: transparent; /* Let the main background show through */
}

/* Animation for new messages */
.message-fade-enter-active {
  transition: all 0.4s ease-out;
}
.message-fade-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

/* Message bubbles with improved styling */
.message-bubble {
  background: #252832;
  border-radius: 18px;
  padding: 12px 16px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.message.user .message-bubble {
  background: linear-gradient(135deg, #4D5FFF 0%, #6B47DC 100%);
}

/* Input area with focus effects */
.input-area {
  padding: 15px 20px;
  background-color: rgba(30, 30, 47, 0.7);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  flex-shrink: 0;
}

.input-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  background: #1C1E26;
  border-radius: 25px;
  padding: 4px 4px 4px 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: box-shadow 0.3s ease;
}

.input-wrapper:focus-within {
  box-shadow: 0 0 0 2px rgba(77, 95, 255, 0.5);
}

/* Send button with new hover effect */
.send-btn {
  background: linear-gradient(135deg, #4D5FFF 0%, #8E54E9 100%);
  border-radius: 50%;
  width: 36px;
  height: 36px;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.send-btn:hover:not(:disabled) {
    transform: scale(1.1);
}

/* Keep the rest of the styles, just overriding the key ones */
@media (max-width: 480px) {
  .flight-chat-container {
    width: 100%;
    height: 100%;
    bottom: 0;
    right: 0;
    border-radius: 0;
  }
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.avatar-section {
  display: flex;
  align-items: center;
  gap: 15px;
}

.avatar {
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, #4D5FFF 0%, #8E54E9 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.plane-icon {
  width: 30px;
  height: 30px;
  color: white;
}

.header-info h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.header-info .subtitle {
  margin: 2px 0 0 0;
  font-size: 12px;
  opacity: 0.6;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 5px;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: #4ade80;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-size: 11px;
  opacity: 0.8;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 8px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  color: white;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.05);
}

.action-btn svg {
  width: 18px;
  height: 18px;
}

/* Welcome Message */
.welcome-message {
  text-align: center;
  color: white;
  padding: 40px 20px;
}

.welcome-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
  background: #252832;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.welcome-icon svg {
  width: 40px;
  height: 40px;
  color: #4D5FFF;
}

.welcome-message h3 {
  margin: 0 0 10px 0;
  font-size: 20px;
  font-weight: 600;
}

.welcome-message p {
  margin: 0;
  opacity: 0.6;
  line-height: 1.5;
}

/* Message Styles */
.message {
  display: flex;
  align-items: flex-end;
  margin-bottom: 20px; /* Added spacing between messages */
  position: relative;
}

.message:last-child {
    margin-bottom: 0;
}

.message.user {
  flex-direction: row-reverse;
  align-self: flex-end;
}

.message-avatar {
  flex-shrink: 0;
  margin-top: 4px;
}

.bot-avatar, .user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bot-avatar {
  background: linear-gradient(135deg, #4D5FFF 0%, #8E54E9 100%);
  color: white;
}

.user-avatar {
  background: #252832;
  color: white;
}

.bot-avatar svg, .user-avatar svg {
  width: 20px;
  height: 20px;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-text {
  color: white;
  font-size: 14px;
  line-height: 1.5;
  word-wrap: break-word;
}

.message-text strong {
  font-weight: 600;
}

.message-text em {
  font-style: italic;
}

.message-time {
  font-size: 11px;
  opacity: 0.6;
  color: white;
  margin-top: 4px;
}

.message.assistant .message-time { text-align: left; }
.message.user .message-time { text-align: right; }

/* Typing Indicator */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes typing {
  0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.attached-file-display {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #1C1E26;
  padding: 8px 12px;
  border-radius: 12px;
  margin-bottom: 10px;
  color: white;
  font-size: 13px;
  border: 1px solid rgba(255,255,255,0.1);
  position: relative;
  overflow: hidden;
}
.file-icon-wrapper {
  flex-shrink: 0;
  color: #a0a0e0;
}
.file-icon {
  width: 28px;
  height: 28px;
}

.file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  z-index: 1;
}

.file-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.progress-container {
  height: 4px;
  border-radius: 2px;
  background-color: rgba(77, 95, 255, 0.2);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(135deg, #4D5FFF 0%, #8E54E9 100%);
  transition: width 0.2s ease-in-out;
}

.remove-file-btn {
  background: none;
  border: none;
  color: white;
  opacity: 0.7;
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}

.remove-file-btn svg {
    width: 18px;
    height: 18px;
}
.remove-file-btn:hover {
  opacity: 1;
}

.remove-file-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.input-container {
  display: flex;
  align-items: center;
  gap: 10px;
}

.message-input {
  flex: 1;
  background: transparent;
  border: none;
  color: white;
  font-size: 14px;
  outline: none;
  padding: 8px;
}

.message-input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.message-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input-actions {
  display: flex;
  gap: 8px;
}

.attach-btn {
  background: transparent;
  color: rgba(255,255,255,0.6);
}
.attach-btn:hover {
  background: transparent;
  color: white;
}
</style>