<!-- eslint-disable -->
<template>
  <div v-if="isVisible" class="chatbot-overlay" @click.self="closeChatbot">
    <div class="chatbot-popup">
      <div class="chatbot-header">
        <h3><i class="fas fa-robot"></i> Flight Log Assistant</h3>
        <button class="close-btn" @click="closeChatbot">
          <i class="fas fa-times"></i>
        </button>
      </div>
      
      <div class="chatbot-content">
        <div class="messages" ref="messagesContainer">
          <div v-for="(m, idx) in messages" :key="idx" :class="['message', m.role]">
            <div class="message-content">
              <strong>{{ m.role === 'user' ? 'You' : 'Assistant' }}:</strong>
              <div v-if="m.role === 'user'" class="user-message">
                <p>{{ m.content }}</p>
              </div>
              <div v-else class="bot-message" v-html="renderMarkdown(m.content)"></div>
            </div>
          </div>
          <div v-if="isTyping" class="message bot typing">
            <div class="message-content">
              <strong>Assistant:</strong>
              <div class="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="input-section">
          <div class="input-area">
            <input
              v-model="userInput"
              @keyup.enter="sendMessage"
              placeholder="Ask me anything about UAV flight logs..."
              :disabled="isTyping"
            />
            <button @click="sendMessage" :disabled="isTyping || !userInput.trim()">
              <i class="fas fa-paper-plane"></i>
            </button>
          </div>
          
          <div class="session-info">
            <small v-if="hasUploadedFile">
              <i class="fas fa-file-alt"></i> Analyzing: {{ state.file }}
            </small>
            <small v-else>
              <i class="fas fa-info-circle"></i> Ready to chat! Upload a flight log for detailed analysis.
            </small>
            <button class="new-session-btn" @click="resetSession">
              <i class="fas fa-refresh"></i> New Session
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { store } from './Globals'
import { marked } from 'marked'

// Configure marked for better security and styling
marked.setOptions({
    breaks: true,
    gfm: true,
    headerIds: false,
    mangle: false
})

export default {
    name: 'ChatbotSidebar',
    props: {
        isVisible: {
            type: Boolean,
            default: false
        }
    },
    data () {
        return {
            state: store,
            messages: [
                {
                    role: 'bot',
                    content: 'Hello! I\'m your UAV flight log assistant. I can help you with questions about ' +
                             'flight logs, telemetry data, troubleshooting, and UAV operations. ' +
                             'What would you like to know?'
                }
            ],
            userInput: '',
            isTyping: false
        }
    },
    computed: {
        sessionId () {
            // Use the session ID from uploaded file if available, otherwise generate one
            return this.state.chatbotSessionId || this.generateSessionId()
        },
        hasUploadedFile () {
            return this.state.chatbotSessionId !== null
        }
    },
    watch: {
        'state.chatbotSessionId' (newSessionId, oldSessionId) {
            if (newSessionId && newSessionId !== oldSessionId) {
                // New file uploaded, update welcome message
                this.messages = [
                    {
                        role: 'bot',
                        content: `Hello! I've loaded your flight log "${this.state.file}" and I'm ready to ` +
                                'analyze it. I can help you understand your flight data, identify issues, ' +
                                'analyze performance, and answer questions about your flight. ' +
                                'What would you like to know about this flight?'
                    }
                ]
            }
        }
    },
    methods: {
        generateSessionId () {
            return Date.now().toString() + Math.random().toString(36).substr(2, 9)
        },

        closeChatbot () {
            this.$emit('close')
        },

        async sendMessage () {
            const content = this.userInput.trim()
            if (!content || this.isTyping) return

            this.messages.push({ role: 'user', content })
            this.userInput = ''
            this.isTyping = true

            // Scroll to bottom
            this.$nextTick(() => {
                this.scrollToBottom()
            })

            try {
                const res = await axios.post('/api/chat', {
                    sessionId: this.sessionId,
                    message: content
                })
                this.messages.push({ role: 'bot', content: res.data.reply })
            } catch (err) {
                console.error(err)
                this.messages.push({
                    role: 'bot',
                    content: 'Sorry, I encountered an error while processing your request. Please try again.'
                })
            } finally {
                this.isTyping = false
                this.$nextTick(() => {
                    this.scrollToBottom()
                })
            }
        },

        resetSession () {
            // Clear the chatbot session but keep file session if available
            this.state.chatbotSessionId = null
            this.messages = [
                {
                    role: 'bot',
                    content: 'Hello! I\'m your UAV flight log assistant. I can help you with questions about ' +
                             'flight logs, telemetry data, troubleshooting, and UAV operations. ' +
                             'What would you like to know?'
                }
            ]
            this.userInput = ''
            this.isTyping = false
        },

        scrollToBottom () {
            if (this.$refs.messagesContainer) {
                this.$refs.messagesContainer.scrollTo({
                    top: this.$refs.messagesContainer.scrollHeight,
                    behavior: 'smooth'
                })
            }
        },

        renderMarkdown (content) {
            try {
                return marked.parse(content)
            } catch (error) {
                console.error('Markdown parsing error:', error)
                return content // Fallback to plain text
            }
        }
    }
}
</script>

<style scoped>
.chatbot-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chatbot-popup {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  height: 85vh;
  max-height: 700px;
  min-height: 400px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chatbot-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chatbot-header h3 {
  margin: 0;
  font-size: 1.2rem;
}

.close-btn {
  background: none;
  border: none;
  color: white;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  transition: background 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.chatbot-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0; /* Important for flex children to shrink */
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  margin: 1rem;
  margin-bottom: 0;
  border: 1px solid #e9ecef;
  min-height: 0; /* Important for scrolling */
  scroll-behavior: smooth;
}

.input-section {
  flex-shrink: 0; /* Prevent input section from shrinking */
  padding: 1rem;
  border-top: 1px solid #e9ecef;
  background: white;
}

.message {
  margin: 0.75rem 0;
}

.message.user {
  text-align: right;
}

.message.bot {
  text-align: left;
}

.message-content {
  display: inline-block;
  max-width: 80%;
  padding: 0.75rem;
  border-radius: 12px;
  word-wrap: break-word;
}

.message.user .message-content {
  background: #667eea;
  color: white;
  border-bottom-right-radius: 4px;
}

.message.bot .message-content {
  background: white;
  border: 1px solid #e9ecef;
  border-bottom-left-radius: 4px;
}

.message-content strong {
  display: block;
  margin-bottom: 0.25rem;
  font-size: 0.85rem;
  opacity: 0.8;
}

.message-content p {
  margin: 0;
  line-height: 1.4;
}

.typing-indicator {
  display: flex;
  gap: 0.25rem;
  margin-top: 0.25rem;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #667eea;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-10px);
  }
}

.input-area {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.input-area input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 0.9rem;
}

.input-area input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.input-area button {
  padding: 0.75rem 1rem;
  border: none;
  background: #667eea;
  color: white;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.input-area button:hover:not(:disabled) {
  background: #5a6fd8;
}

.input-area button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.session-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 0.8rem;
  color: #666;
}

.new-session-btn {
  background: #6c757d;
  color: white;
  border: none;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: background 0.2s;
}

.new-session-btn:hover {
  background: #5a6268;
}

/* Mobile responsiveness */
@media (max-width: 768px) {
  .chatbot-popup {
    width: 95%;
    height: 95vh;
    max-height: none;
    margin: 0;
    border-radius: 8px;
  }

  .message-content {
    max-width: 90%;
  }

  .messages {
    margin: 0.5rem;
    padding: 0.75rem;
  }

  .input-section {
    padding: 0.75rem;
  }
}

@media (max-width: 480px) {
  .chatbot-popup {
    width: 100%;
    height: 100vh;
    border-radius: 0;
  }

  .chatbot-header h3 {
    font-size: 1rem;
  }
}

/* Markdown content styling */
.bot-message {
  line-height: 1.6;
}

.bot-message h1,
.bot-message h2,
.bot-message h3,
.bot-message h4,
.bot-message h5,
.bot-message h6 {
  margin: 0.5rem 0 0.25rem 0;
  color: #2c3e50;
  font-weight: 600;
}

.bot-message h1 { font-size: 1.4rem; }
.bot-message h2 { font-size: 1.2rem; }
.bot-message h3 { font-size: 1.1rem; }
.bot-message h4 { font-size: 1rem; }

.bot-message p {
  margin: 0.5rem 0;
}

.bot-message ul,
.bot-message ol {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.bot-message li {
  margin: 0.25rem 0;
}

.bot-message strong {
  color: #2c3e50;
  font-weight: 600;
}

.bot-message em {
  color: #666;
  font-style: italic;
}

.bot-message code {
  background: #f1f3f4;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.85rem;
  color: #d73e48;
}

.bot-message pre {
  background: #f8f9fa;
  padding: 0.75rem;
  border-radius: 6px;
  overflow-x: auto;
  border-left: 4px solid #667eea;
  margin: 0.5rem 0;
}

.bot-message pre code {
  background: none;
  padding: 0;
  color: #333;
}

.bot-message blockquote {
  border-left: 4px solid #ddd;
  margin: 0.5rem 0;
  padding-left: 1rem;
  color: #666;
  font-style: italic;
}

.bot-message table {
  border-collapse: collapse;
  width: 100%;
  margin: 0.5rem 0;
}

.bot-message th,
.bot-message td {
  border: 1px solid #ddd;
  padding: 0.5rem;
  text-align: left;
}

.bot-message th {
  background: #f8f9fa;
  font-weight: 600;
}

.user-message {
  line-height: 1.5;
}

.user-message p {
  margin: 0;
}
</style>
