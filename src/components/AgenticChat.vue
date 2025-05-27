<template>
    <div class="agentic-chat-container">
        <!-- Header -->
        <div class="chat-header">
            <div class="header-content">
                <h3><i class="fas fa-robot"></i> UAV Agentic Analysis</h3>
                <div class="connection-status" v-if="hasUploadedFile">
                    <span v-if="websocket && websocket.readyState === 1" class="status-indicator ws-connected">
                        <i class="fas fa-bolt"></i> Live
                    </span>
                    <span v-else class="status-indicator ws-disconnected">
                        <i class="fas fa-wifi"></i> Standard
                    </span>
                </div>
            </div>
            <div class="session-info" v-if="sessionId">
                <small class="text-muted">Session: {{ sessionId.substring(0, 8) }}...</small>
            </div>
        </div>

        <!-- File Upload Section -->
        <div class="upload-section" v-if="!hasUploadedFile">
            <div class="upload-card">
                <h5><i class="fas fa-upload"></i> Upload MAVLink Log</h5>
                <p class="text-muted">Upload a MAVLink log file to start analyzing your flight data</p>

                <div class="upload-dropzone"
                     @drop="handleDrop"
                     @dragover.prevent
                     @dragenter.prevent
                     :class="{ 'drag-over': isDragOver }"
                     @dragenter="isDragOver = true"
                     @dragleave="isDragOver = false">

                    <input type="file"
                           ref="fileInput"
                           @change="handleFileSelect"
                           accept=".bin,.log,.tlog,.ulg,.ulog"
                           style="display: none;">

                    <div class="upload-content">
                        <i class="fas fa-cloud-upload-alt fa-3x text-primary"></i>
                        <p class="mt-3">
                            <strong>Drop your log file here</strong><br>
                            or <a href="#" @click="$refs.fileInput.click()" class="text-primary">browse files</a>
                        </p>
                        <small class="text-muted">Supports .bin, .log, .tlog, .ulg, and .ulog formats</small>
                    </div>
                </div>

                <div v-if="uploadProgress > 0" class="upload-progress mt-3">
                    <b-progress :value="uploadProgress" :max="100" show-progress animated></b-progress>
                </div>

                <div v-if="uploadError" class="alert alert-danger mt-3">
                    <i class="fas fa-exclamation-triangle"></i> {{ uploadError }}
                </div>
            </div>
        </div>

        <!-- Chat Interface -->
        <div class="chat-interface" v-if="hasUploadedFile">
            <!-- Chat Messages -->
            <div class="chat-messages" ref="chatMessages">
                <div v-for="message in messages" :key="message.id" class="message-wrapper">

                    <!-- User Message -->
                    <div v-if="message.role === 'user'" class="message user-message">
                        <div class="message-content">
                            <div class="message-text">{{ message.content }}</div>
                            <div class="message-time">{{ formatTime(message.timestamp) }}</div>
                        </div>
                        <div class="message-avatar">
                            <i class="fas fa-user"></i>
                        </div>
                    </div>

                    <!-- Assistant Message -->
                    <div v-if="message.role === 'assistant'" class="message assistant-message">
                        <div class="message-avatar">
                            <i class="fas fa-robot"></i>
                        </div>
                        <div class="message-content">
                            <div class="message-text" v-html="formatResponse(message.content)"></div>
                            <div v-if="message.isStreaming" class="streaming-cursor">▊</div>

                            <!-- Analysis Data -->
                            <div v-if="message.analysis" class="analysis-section mt-3">
                                <h6><i class="fas fa-chart-line"></i> Analysis Results</h6>
                                <div class="analysis-cards">
                                    <div v-for="(value, key) in message.analysis" :key="key" class="analysis-card">
                                        <strong>{{ formatAnalysisKey(key) }}:</strong>
                                        <span v-if="typeof value === 'object'">
                                            <pre class="analysis-json">{{ JSON.stringify(value, null, 2) }}</pre>
                                        </span>
                                        <span v-else>{{ value }}</span>
                                    </div>
                                </div>
                            </div>

                            <div class="message-time">{{ formatTime(message.timestamp) }}</div>
                        </div>
                    </div>

                    <!-- System Message -->
                    <div v-if="message.role === 'system'" class="message system-message">
                        <div class="system-content">
                            <i class="fas fa-info-circle"></i>
                            {{ message.content }}
                        </div>
                    </div>
                </div>

                <!-- Typing Indicator -->
                <div v-if="isTyping" class="message assistant-message typing">
                    <div class="message-avatar">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div class="message-content">
                        <div class="typing-indicator">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Chat Input -->
            <div class="chat-input-section">
                <div class="input-group">
                    <input type="text"
                           class="form-control"
                           v-model="currentMessage"
                           @keyup.enter="sendMessage"
                           :disabled="isTyping"
                           placeholder="Ask about your flight data... (e.g., 'What was the max altitude?')">
                    <div class="input-group-append">
                        <button class="btn btn-primary"
                                @click="sendMessage"
                                :disabled="!currentMessage.trim() || isTyping">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </div>
                </div>

                <!-- Quick Questions -->
                <div class="quick-questions mt-2">
                    <small class="text-muted">Quick questions:</small>
                    <div class="quick-question-buttons">
                        <button v-for="question in quickQuestions"
                                :key="question"
                                class="btn btn-sm btn-outline-secondary mr-1 mb-1"
                                @click="askQuickQuestion(question)"
                                :disabled="isTyping">
                            {{ question }}
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Session Actions -->
        <div class="session-actions" v-if="hasUploadedFile">
            <div class="session-info-actions">
                <small class="text-muted">
                    {{ messages.length }} message{{ messages.length !== 1 ? 's' : '' }}
                </small>
            </div>

            <div class="action-buttons">
                <div class="download-section">
                    <div class="input-group input-group-sm">
                        <div class="input-group-prepend">
                            <button class="btn btn-outline-primary"
                                    @click="downloadChat"
                                    :disabled="messages.length === 0">
                                <i class="fas fa-download"></i> Download
                            </button>
                        </div>
                        <select class="form-control" v-model="downloadFormat">
                            <option value="txt">Text (.txt)</option>
                            <option value="json">JSON (.json)</option>
                            <option value="csv">CSV (.csv)</option>
                        </select>
                    </div>
                </div>
                <button class="btn btn-outline-secondary btn-sm ml-2" @click="clearChat">
                    <i class="fas fa-trash"></i> Clear Chat
                </button>
                <button class="btn btn-outline-danger btn-sm ml-2" @click="endSession">
                    <i class="fas fa-sign-out-alt"></i> End Session
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import axios from 'axios'
import { config } from '@/config'

export default {
    name: 'AgenticChat',
    data () {
        return {
            sessionId: null,
            hasUploadedFile: false,
            messages: [],
            currentMessage: '',
            isTyping: false,
            isDragOver: false,
            uploadProgress: 0,
            uploadError: null,
            backendUrl: config.backendUrl,
            downloadFormat: 'txt',
            websocket: null,
            useWebSocket: true,
            streamingMessage: null,
            quickQuestions: [
                'What was the max altitude?',
                'How long did the flight last?',
                'Any GPS issues?',
                'RC signal dropouts?',
                'Flight summary',
                'Any anomalies?'
            ]
        }
    },
    mounted () {
        this.addSystemMessage('Welcome! Upload a MAVLink log file to start analyzing your flight data.')
    },
    beforeDestroy () {
        this.disconnectWebSocket()
    },
    methods: {
        handleDrop (event) {
            event.preventDefault()
            this.isDragOver = false
            const files = event.dataTransfer.files
            if (files.length > 0) {
                this.uploadFile(files[0])
            }
        },

        handleFileSelect (event) {
            const file = event.target.files[0]
            if (file) {
                this.uploadFile(file)
            }
        },

        async uploadFile (file) {
            this.uploadError = null
            this.uploadProgress = 0

            // Validate file type
            const validExtensions = ['.bin', '.log', '.tlog', '.ulg', '.ulog']
            const fileExtension = '.' + file.name.split('.').pop().toLowerCase()
            if (!validExtensions.includes(fileExtension)) {
                this.uploadError = 'Invalid file type. Please upload a .bin, .log, .tlog, .ulg, or .ulog file.'
                return
            }

            const formData = new FormData()
            formData.append('file', file)

            try {
                this.uploadProgress = 10

                const response = await axios.post(`${this.backendUrl}/upload`, formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                        ...(this.sessionId && { 'X-Session-ID': this.sessionId })
                    },
                    onUploadProgress: (progressEvent) => {
                        const progress = Math.round((progressEvent.loaded * 90) / progressEvent.total) + 10
                        this.uploadProgress = progress
                    }
                })

                this.sessionId = response.data.session_id || response.headers['x-session-id']
                this.hasUploadedFile = true
                this.uploadProgress = 100

                const message = `File "${file.name}" uploaded successfully! ` +
                    'You can now ask questions about your flight data.'
                this.addSystemMessage(message)

                // Clear the file input
                this.$refs.fileInput.value = ''

                // Establish WebSocket connection after successful upload
                this.$nextTick(() => {
                    this.connectWebSocket()
                })
            } catch (error) {
                console.error('Upload error:', error)
                const errorDetail = error.response?.data?.detail ||
                    'Failed to upload file. Please try again.'
                this.uploadError = errorDetail
                this.uploadProgress = 0
            }
        },

        async sendMessage () {
            if (!this.currentMessage.trim() || this.isTyping) return

            const userMessage = this.currentMessage.trim()
            this.currentMessage = ''

            // Add user message
            this.addMessage('user', userMessage)

            // Try WebSocket first, fallback to HTTP
            if (this.useWebSocket && this.sessionId) {
                console.log('Attempting WebSocket message send...')
                const wsSuccess = await this.sendMessageWebSocket(userMessage)
                if (wsSuccess) {
                    console.log('Message sent via WebSocket successfully')
                    return
                }
                // If WebSocket fails, fall back to HTTP
                console.log('WebSocket failed, falling back to HTTP')
            } else {
                console.log('WebSocket disabled or no session, using HTTP')
            }

            // HTTP fallback
            this.isTyping = true
            this.scrollToBottom()

            try {
                console.log('Sending HTTP chat request:', {
                    url: `${this.backendUrl}/chat`,
                    message: userMessage,
                    sessionId: this.sessionId
                })

                const requestData = {
                    message: userMessage
                }
                if (this.sessionId) {
                    requestData.session_id = this.sessionId // eslint-disable-line camelcase
                }

                const response = await axios.post(`${this.backendUrl}/chat`, requestData, {
                    headers: {
                        'Content-Type': 'application/json',
                        ...(this.sessionId && { 'X-Session-ID': this.sessionId })
                    }
                })

                this.isTyping = false

                // Add assistant response
                this.addMessage('assistant', response.data.response, response.data.analysis)

                // Update session ID if provided
                if (response.data.session_id) { // eslint-disable-line camelcase
                    this.sessionId = response.data.session_id // eslint-disable-line camelcase
                }
            } catch (error) {
                this.isTyping = false
                console.error('Chat error:', error)
                console.error('Error response:', error.response)
                console.error('Error status:', error.response?.status)
                console.error('Error data:', error.response?.data)

                let errorMessage = 'Sorry, I encountered an error processing your request.'
                if (error.response?.data?.detail) {
                    errorMessage = error.response.data.detail
                } else if (error.message) {
                    errorMessage = `Error: ${error.message}`
                }

                this.addMessage('assistant', errorMessage)
            }
        },

        askQuickQuestion (question) {
            this.currentMessage = question
            this.sendMessage()
        },

        addMessage (role, content, analysis = null) {
            const message = {
                id: Date.now() + Math.random(),
                role,
                content,
                analysis,
                timestamp: new Date()
            }
            this.messages.push(message)
            this.$nextTick(() => {
                this.scrollToBottom()
            })
        },

        addSystemMessage (content) {
            this.addMessage('system', content)
        },

        async endSession () {
            if (!this.sessionId) return

            try {
                await axios.delete(`${this.backendUrl}/session`, {
                    headers: {
                        'X-Session-ID': this.sessionId
                    }
                })

                this.resetSession()
                this.addSystemMessage('Session ended. Upload a new file to start a new analysis session.')
            } catch (error) {
                console.error('Error ending session:', error)
                // Reset anyway
                this.resetSession()
            }
        },

        clearChat () {
            this.messages = []
            this.addSystemMessage('Chat cleared. Your session is still active.')
        },

        async downloadChat () {
            if (!this.sessionId || this.messages.length === 0) {
                this.addSystemMessage('No chat history to download.')
                return
            }

            try {
                // Try to use backend download API first (more comprehensive)
                try {
                    const response = await axios.get(`${this.backendUrl}/session/download`, {
                        params: { format: this.downloadFormat },
                        headers: {
                            'X-Session-ID': this.sessionId
                        },
                        responseType: 'blob'
                    })

                    // Create download link
                    const url = window.URL.createObjectURL(new Blob([response.data]))
                    const link = document.createElement('a')
                    link.href = url

                    // Extract filename from response headers or create default
                    const contentDisposition = response.headers['content-disposition']
                    const sessionShort = this.sessionId.substring(0, 8)
                    const dateStr = new Date().toISOString().split('T')[0]
                    let filename = `uav-chat-${sessionShort}-${dateStr}.${this.downloadFormat}`

                    if (contentDisposition) {
                        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
                        if (filenameMatch && filenameMatch[1]) {
                            filename = filenameMatch[1].replace(/['"]/g, '')
                        }
                    }

                    link.download = filename
                    document.body.appendChild(link)
                    link.click()
                    document.body.removeChild(link)
                    window.URL.revokeObjectURL(url)

                    const successMsg = `Chat history downloaded successfully as ${this.downloadFormat.toUpperCase()}!`
                    this.addSystemMessage(successMsg)
                    return
                } catch (backendError) {
                    console.warn('Backend download failed, falling back to frontend generation:', backendError)

                    // Fallback to frontend-only download for txt format
                    if (this.downloadFormat === 'txt') {
                        const chatContent = this.formatChatForDownload(this.messages)
                        const blob = new Blob([chatContent], { type: 'text/plain;charset=utf-8' })
                        const url = window.URL.createObjectURL(blob)

                        const link = document.createElement('a')
                        link.href = url
                        const sessionShort = this.sessionId.substring(0, 8)
                        const dateStr = new Date().toISOString().split('T')[0]
                        link.download = `uav-chat-${sessionShort}-${dateStr}.txt`
                        document.body.appendChild(link)
                        link.click()
                        document.body.removeChild(link)
                        window.URL.revokeObjectURL(url)

                        this.addSystemMessage('Chat history downloaded successfully!')
                        return
                    } else {
                        throw backendError
                    }
                }
            } catch (error) {
                console.error('Error downloading chat:', error)
                this.addSystemMessage('Failed to download chat history. Please try again.')
            }
        },

        formatChatForDownload (messages) {
            const header = `UAV Agentic Analysis Chat Log
Session ID: ${this.sessionId}
Generated: ${new Date().toLocaleString()}
========================================

`

            let content = header

            messages.forEach(message => {
                const timestamp = new Date(message.timestamp).toLocaleString()
                const role = message.role.toUpperCase()

                content += `[${timestamp}] ${role}:\n`
                content += `${message.content}\n`

                // Add analysis data if present
                if (message.analysis && Object.keys(message.analysis).length > 0) {
                    content += '\nANALYSIS DATA:\n'
                    content += JSON.stringify(message.analysis, null, 2)
                    content += '\n'
                }

                content += `\n${'='.repeat(50)}\n\n`
            })

            return content
        },

        resetSession () {
            this.sessionId = null
            this.hasUploadedFile = false
            this.messages = []
            this.currentMessage = ''
            this.isTyping = false
            this.uploadProgress = 0
            this.uploadError = null
            this.useWebSocket = true // Reset WebSocket flag
            this.disconnectWebSocket() // Close any existing WebSocket connection
        },

        scrollToBottom () {
            this.$nextTick(() => {
                const chatMessages = this.$refs.chatMessages
                if (chatMessages) {
                    chatMessages.scrollTop = chatMessages.scrollHeight
                }
            })
        },

        formatTime (timestamp) {
            return new Date(timestamp).toLocaleTimeString()
        },

        formatResponse (text) {
            // Convert markdown-like formatting to HTML
            return text
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/\n/g, '<br>')
        },

        formatAnalysisKey (key) {
            return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
        },

        connectWebSocket () {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                return Promise.resolve()
            }

            // Close existing connection if any
            if (this.websocket) {
                this.websocket.close()
                this.websocket = null
            }

            const wsUrl = this.backendUrl.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/chat'
            console.log('Connecting to WebSocket:', wsUrl)

            return new Promise((resolve, reject) => {
                this.websocket = new WebSocket(wsUrl)

                this.websocket.onopen = () => {
                    console.log('WebSocket connected successfully')
                    resolve()
                }

                this.websocket.onmessage = (event) => {
                    const data = JSON.parse(event.data)
                    this.handleWebSocketMessage(data)
                }

                this.websocket.onclose = (event) => {
                    console.log('WebSocket disconnected:', event.code, event.reason)
                    this.websocket = null
                }

                this.websocket.onerror = (error) => {
                    console.error('WebSocket connection error:', error)
                    console.warn('Disabling WebSocket, will use HTTP fallback')
                    this.useWebSocket = false
                    this.websocket = null
                    reject(error)
                }

                // Timeout after 5 seconds
                setTimeout(() => {
                    if (this.websocket && this.websocket.readyState !== WebSocket.OPEN) {
                        console.warn('WebSocket connection timeout')
                        this.websocket.close()
                        this.websocket = null
                        this.useWebSocket = false
                        reject(new Error('WebSocket connection timeout'))
                    }
                }, 5000)
            })
        },

        disconnectWebSocket () {
            if (this.websocket) {
                this.websocket.close()
                this.websocket = null
            }
        },

        handleWebSocketMessage (data) {
            switch (data.type) {
            case 'start':
                this.isTyping = true
                this.streamingMessage = {
                    id: Date.now() + Math.random(),
                    role: 'assistant',
                    content: '',
                    analysis: null,
                    timestamp: new Date(),
                    isStreaming: true
                }
                this.messages.push(this.streamingMessage)
                this.scrollToBottom()
                break

            case 'token':
                if (this.streamingMessage) {
                    this.streamingMessage.content = data.full_content
                    this.scrollToBottom()
                }
                break

            case 'complete':
                this.isTyping = false
                if (this.streamingMessage) {
                    this.streamingMessage.content = data.content
                    this.streamingMessage.analysis = data.analysis
                    this.streamingMessage.isStreaming = false
                    this.streamingMessage = null
                }
                this.scrollToBottom()
                break

            case 'error':
                this.isTyping = false
                if (this.streamingMessage) {
                    // Remove the streaming message and add error message
                    const index = this.messages.indexOf(this.streamingMessage)
                    if (index > -1) {
                        this.messages.splice(index, 1)
                    }
                    this.streamingMessage = null
                }
                this.addMessage('assistant', data.message)
                break
            }
        },

        async sendMessageWebSocket (message) {
            try {
                // Ensure WebSocket is connected
                if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
                    console.log('WebSocket not connected, attempting to connect...')
                    await this.connectWebSocket()
                }

                if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                    console.log('Sending message via WebSocket')
                    this.websocket.send(JSON.stringify({
                        message: message,
                        session_id: this.sessionId // eslint-disable-line camelcase
                    }))
                    return true
                } else {
                    console.warn('WebSocket connection failed, falling back to HTTP')
                    return false
                }
            } catch (error) {
                console.error('WebSocket send error:', error)
                this.useWebSocket = false
                return false
            }
        }
    }
}
</script>

<style scoped>
.agentic-chat-container {
    height: 100vh;
    display: flex;
    flex-direction: column;
    background: #f8f9fa;
    overflow: hidden;
}

.chat-header {
    background: white;
    padding: 1rem;
    border-bottom: 1px solid #dee2e6;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.chat-header h3 {
    margin: 0;
    color: #495057;
}

.connection-status {
    display: flex;
    align-items: center;
}

.status-indicator {
    font-size: 0.8rem;
    padding: 0.25rem 0.5rem;
    border-radius: 12px;
    font-weight: 500;
}

.ws-connected {
    background: #d4edda;
    color: #155724;
}

.ws-disconnected {
    background: #f8d7da;
    color: #721c24;
}

.session-info {
    margin-top: 0.5rem;
}

.upload-section {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
}

.upload-card {
    background: white;
    border-radius: 8px;
    padding: 2rem;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    max-width: 500px;
    width: 100%;
}

.upload-dropzone {
    border: 2px dashed #dee2e6;
    border-radius: 8px;
    padding: 3rem 2rem;
    text-align: center;
    transition: all 0.3s ease;
    cursor: pointer;
}

.upload-dropzone:hover,
.upload-dropzone.drag-over {
    border-color: #007bff;
    background-color: #f8f9ff;
}

.upload-content {
    color: #6c757d;
}

.chat-interface {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    background: #f8f9fa;
    min-height: 0;
    scroll-behavior: smooth;
}

.message-wrapper {
    margin-bottom: 1rem;
}

.message {
    display: flex;
    align-items: flex-start;
    max-width: 80%;
}

.user-message {
    margin-left: auto;
    flex-direction: row-reverse;
}

.assistant-message {
    margin-right: auto;
}

.system-message {
    justify-content: center;
    margin: 1rem auto;
    max-width: 60%;
}

.system-content {
    background: #e9ecef;
    color: #495057;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.9rem;
    text-align: center;
}

.message-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 0.5rem;
    flex-shrink: 0;
}

.user-message .message-avatar {
    background: #007bff;
    color: white;
}

.assistant-message .message-avatar {
    background: #28a745;
    color: white;
}

.message-content {
    background: white;
    border-radius: 18px;
    padding: 0.75rem 1rem;
    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    max-width: 100%;
}

.user-message .message-content {
    background: #007bff;
    color: white;
}

.message-text {
    word-wrap: break-word;
}

.message-time {
    font-size: 0.75rem;
    opacity: 0.7;
    margin-top: 0.25rem;
}

.analysis-section {
    border-top: 1px solid #dee2e6;
    padding-top: 1rem;
}

.analysis-cards {
    display: grid;
    gap: 0.5rem;
}

.analysis-card {
    background: #f8f9fa;
    padding: 0.5rem;
    border-radius: 4px;
    font-size: 0.9rem;
}

.analysis-json {
    background: #f1f3f4;
    padding: 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    margin-top: 0.25rem;
    white-space: pre-wrap;
    overflow-x: auto;
}

.typing-indicator {
    display: flex;
    align-items: center;
    gap: 4px;
}

.typing-indicator span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #6c757d;
    animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes typing {
    0%, 80%, 100% { transform: scale(0); opacity: 0.5; }
    40% { transform: scale(1); opacity: 1; }
}

.streaming-cursor {
    display: inline-block;
    animation: blink 1s infinite;
    color: #28a745;
    font-weight: bold;
}

@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}

.chat-input-section {
    background: white;
    padding: 1rem;
    border-top: 1px solid #dee2e6;
    flex-shrink: 0;
}

.quick-questions {
    margin-top: 0.5rem;
}

.quick-question-buttons {
    margin-top: 0.25rem;
}

.session-actions {
    background: white;
    padding: 0.5rem 1rem;
    border-top: 1px solid #dee2e6;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.5rem;
    flex-shrink: 0;
}

.session-info-actions {
    flex: 0 0 auto;
}

.action-buttons {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.download-section {
    flex: 0 0 auto;
}

.download-section .input-group {
    width: auto;
    min-width: 200px;
}

.upload-progress {
    margin-top: 1rem;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .agentic-chat-container {
        height: 100vh;
        height: -webkit-fill-available; /* iOS Safari fix */
    }

    .message {
        max-width: 95%;
    }

    .upload-card {
        margin: 1rem;
        padding: 1.5rem;
    }

    .upload-dropzone {
        padding: 2rem 1rem;
    }

    .chat-header {
        padding: 0.75rem 1rem;
    }

    .header-content {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.5rem;
    }

    .chat-header h3 {
        font-size: 1.25rem;
    }

    .status-indicator {
        font-size: 0.7rem;
        padding: 0.2rem 0.4rem;
    }

    .chat-messages {
        padding: 0.75rem;
    }

    .message-avatar {
        width: 32px;
        height: 32px;
        margin: 0 0.25rem;
    }

    .message-content {
        padding: 0.5rem 0.75rem;
        font-size: 0.9rem;
    }

    .chat-input-section {
        padding: 0.75rem;
    }

    .quick-question-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 0.25rem;
    }

    .quick-question-buttons .btn {
        font-size: 0.8rem;
        padding: 0.25rem 0.5rem;
    }

    .session-actions {
        flex-direction: column;
        align-items: stretch;
        gap: 1rem;
        padding: 0.75rem;
    }

    .action-buttons {
        flex-direction: column;
        gap: 0.5rem;
    }

    .download-section .input-group {
        min-width: 100%;
    }
}

/* Extra small devices */
@media (max-width: 480px) {
    .chat-header h3 {
        font-size: 1.1rem;
    }

    .upload-card {
        margin: 0.5rem;
        padding: 1rem;
    }

    .upload-dropzone {
        padding: 1.5rem 0.5rem;
    }

    .message-content {
        font-size: 0.85rem;
    }

    .analysis-card {
        font-size: 0.8rem;
    }
}

/* Landscape mobile devices */
@media (max-height: 500px) and (orientation: landscape) {
    .agentic-chat-container {
        height: 100vh;
    }

    .chat-header {
        padding: 0.5rem 1rem;
    }

    .chat-header h3 {
        font-size: 1rem;
        margin: 0;
    }

    .session-info {
        margin-top: 0.25rem;
    }

    .upload-section {
        padding: 1rem;
    }

    .upload-card {
        padding: 1rem;
    }

    .upload-dropzone {
        padding: 1rem;
    }
}
</style>
