<!--
This Vue component implements a fully functional chatbot UI named 'Aero Flight Assistant'.
It allows users to:
- Upload a UAV flight log (.bin file).
- Interact with a backend service to ask questions about the flight log.
- Switch between light/dark mode.
- Start a new chat session.
- Download/export the chat history.

Component Features:
- Uses scoped styles for isolated visual design.
- Axios is used for backend communication.
- Vue 2 is used with reactive state management and events.
-->
<template>
    <!-- Chatbot container with dark mode binding -->
    <div :class="{ 'dark-mode-active': isDarkMode }">
        <!-- Floating button to toggle chatbot window -->
        <button @click="toggleChatWindow" class="chatbot-trigger-button" title="Open Aero Chat">
            <img
                src="/src/img/plane-doodle.png"
                alt="Aero Logo"
                class="chatbot-trigger-logo"
            />
            </button>

        <!-- Main chat window -->
        <div v-if="isChatOpen" class="chatbot-window" :class="{ 'dark-mode': isDarkMode }">

            <!-- Header with assistant logo and actions -->
            <div class="chatbot-header">
                <h3>
                    <img
                        src="/src/img/planedoodle.png"
                        alt="Aero Logo"
                        class="chatbot-header-logo"
                    />
                    Aero Flight Assistant
                </h3>

                <!-- Header buttons for reset, dark mode toggle, export, and close -->
                <div class="header-buttons">

                    <!-- Start a new chat session -->
                    <button
                        @click="startFreshConversation"
                        v-if="fileId"
                        class="header-icon-button fresh-chat-button"
                        title="Start Fresh Conversation"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                        >
                            <path d="M23 4v6h-6"></path>
                            <path d="M1 20v-6h6"></path>
                            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                        </svg>
                    </button>

                    <!-- Toggle light/dark mode -->
                    <button @click="toggleDarkMode" class="header-icon-button mode-toggle" title="Toggle Dark Mode">
                        <svg
                            v-if="isDarkMode"
                            xmlns="http://www.w3.org/2000/svg"
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                        >
                            <circle cx="12" cy="12" r="5"></circle>
                            <line x1="12" y1="1" x2="12" y2="3"></line>
                            <line x1="12" y1="21" x2="12" y2="23"></line>
                            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                            <line x1="1" y1="12" x2="3" y2="12"></line>
                            <line x1="21" y1="12" x2="23" y2="12"></line>
                            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
                        </svg>
                        <svg
                            v-else
                            xmlns="http://www.w3.org/2000/svg"
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                        >
                            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
                        </svg>
                    </button>

                    <!-- Download/export chat -->
                    <button
                        @click="downloadChatHistory"
                        v-if="fileId && currentConversationHistory.length > 0"
                        class="header-icon-button download-button"
                        title="Export Chat"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                        >
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                    </button>

                    <!-- Close chat window -->
                    <button @click="toggleChatWindow" class="header-icon-button close-chat-button" title="Close Chat">
                        &times;
                    </button>
                </div>
            </div>

            <!-- Chat content area -->
            <div class="chatbot-container">

                <!-- Display log info if a file is uploaded -->
                <p class="log-info" v-if="fileId">
                    Active Log: {{ uploadedFileName }}
                </p>

                <div class="chat-history" ref="chatHistory">
                    <div v-if="!fileId" class="message assistant-placeholder">
                        <img
                            src="/src/img/planedoodle.png"
                            alt="Aero Logo"
                            class="welcome-logo"
                        />
                        <h2>Welcome to Aero!</h2>
                        <p>
                            Your intelligent assistant for UAV flight log analysis.
                            Please upload a .BIN flight log using the section below to begin.
                        </p>
                    </div>

                    <!-- Display conversation if fileId exists -->
                    <template v-if="fileId">
                        <div
                            v-for="(message, index) in currentConversationHistory"
                            :key="index"
                            :class="['message', message.role]"
                        >
                            <strong class="message-sender">{{ message.role === 'user' ? 'You' : 'Aero' }}:</strong>
                            <span class="message-content" v-html="formatMessageContent(message.content)"></span>
                        </div>
                    </template>
                </div>

                <!-- Input area for typing messages -->
                <div class="chat-input-area">
                    <div class="chat-input">
                        <input
                            type="text"
                            v-model="currentUserMessage"
                            @keyup.enter="sendMessage"
                            :placeholder="fileId ? 'Ask Aero about the flight log...' : 'Upload a log to enable chat'"
                            :disabled="!fileId || isSendingMessage"
                            ref="chatInput"
                        />

                         <!-- Send message button -->
                        <button
                            @click="sendMessage"
                            :disabled="!fileId || !currentUserMessage.trim() || isSendingMessage"
                            class="send-button"
                            title="Send Message"
                        >
                            <svg
                                v-if="!isSendingMessage"
                                xmlns="http://www.w3.org/2000/svg"
                                width="20"
                                height="20"
                                viewBox="0 0 24 24"
                                fill="currentColor"
                            >
                                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                            </svg>
                            <div v-if="isSendingMessage" class="typing-indicator-send">
                                <div></div><div></div><div></div>
                            </div>
                        </button>

                        <!-- Inline clear chat button -->
                        <button
                            @click="clearChat"
                            v-if="fileId"
                            class="header-icon-button clear-chat-button-inline"
                            title="Clear Session & Upload New"
                        >
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                width="18"
                                height="18"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                stroke-width="2"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            >
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path
                                d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2">
                                </path>
                                <line x1="10" y1="11" x2="10" y2="17"></line>
                                <line x1="14" y1="11" x2="14" y2="17"></line>
                            </svg>
                        </button>
                    </div>
                    <p v-if="chatError" class="error-message">{{ chatError }}</p>
                </div>

                <!-- Upload section if no file is currently active -->
                <div class="upload-section" v-if="!fileId">
                    <label for="logFileCustom" class="upload-label">Upload .bin Log File:</label>
                    <div class="upload-controls">
                        <input
                            type="file"
                            @change="handleFileUpload"
                            accept=".bin"
                            ref="logFileInput"
                            class="file-input"
                            id="logFileCustom"
                        />
                        <label for="logFileCustom" class="file-input-label">
                            {{ selectedFile ? selectedFile.name : 'Choose File...' }}
                        </label>
                        <button @click="submitLogFile" :disabled="!selectedFile || isUploading" class="upload-button">
                            {{ isUploading ? 'Uploading...' : 'Upload Log' }}
                        </button>
                    </div>
                    <p v-if="uploadError" class="error-message">{{ uploadError }}</p>
                    <p v-if="uploadSuccessMessage" class="success-message">{{ uploadSuccessMessage }}</p>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import axios from 'axios'

// Base URL of the backend server
const API_BASE_URL = 'http://127.0.0.1:8000'

export default {
    name: 'ChatbotComponent',
    data () {
        return {
            // Controls visibility of the chatbot window
            isChatOpen: false,
            selectedFile: null,
            fileId: null,
            uploadedFileName: '',
            isUploading: false,
            uploadError: '',
            uploadSuccessMessage: '',

            // Chat interaction state
            currentUserMessage: '',
            isSendingMessage: false,
            chatError: '',

            // Theme state
            isDarkMode: false,

            // Object to track multiple file session histories
            sessions: {},
            activeFileId: null
        }
    },

    // Returns the current chat history for the active file
    computed: {
        currentConversationHistory () {
            if (this.activeFileId && this.sessions[this.activeFileId]) {
                return this.sessions[this.activeFileId]
            }
            return []
        }
    },
    methods: {

        // Opens or closes the chat window
        toggleChatWindow () {
            this.isChatOpen = !this.isChatOpen
            if (this.isChatOpen) {
                this.$nextTick(() => {
                    if (this.activeFileId && this.$refs.chatInput) {
                        this.$refs.chatInput.focus()
                    }
                })
            }
        },

        // Toggles dark mode styling
        toggleDarkMode () {
            this.isDarkMode = !this.isDarkMode
            if (this.isDarkMode) {
                document.documentElement.classList.add('dark-theme-active')
            } else {
                document.documentElement.classList.remove('dark-theme-active')
            }
        },

        // Stores selected file from input
        handleFileUpload (event) {
            this.selectedFile = event.target.files[0]
            this.uploadError = ''
            this.uploadSuccessMessage = ''
        },

        // Uploads selected .bin log file to backend
        async submitLogFile () {
            if (!this.selectedFile) {
                this.uploadError = 'Please select a .bin file first.'
                return
            }

            this.isUploading = true
            this.uploadError = ''
            this.uploadSuccessMessage = ''

            const formData = new FormData()
            formData.append('file', this.selectedFile)

            try {
                console.log('Attempting to upload log file...')
                const response = await axios.post(`${API_BASE_URL}/upload_log/`, formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data'
                    }
                })
                console.log('Upload response received:', response.data)

                if (response.data && response.data.fileId) {
                    this.fileId = response.data.fileId
                    this.activeFileId = response.data.fileId
                    this.uploadedFileName = response.data.filename

                    if (!this.sessions[this.activeFileId]) {
                        this.$set(this.sessions, this.activeFileId, [])
                    }

                    const greetingMessage =
                        `Log '${this.uploadedFileName}' processed successfully!\n` +
                        "I'm Aero, your flight analysis assistant. How can I help you with this log?"

                    // Add assistant greeting message
                    this.sessions[this.activeFileId].push({
                        role: 'assistant',
                        content: greetingMessage
                    })

                    console.log('fileId successfully set to:', this.fileId)
                    this.chatError = ''
                    this.$nextTick(() => {
                        if (this.$refs.chatInput) {
                            this.$refs.chatInput.focus()
                        }
                    })
                } else {
                    this.fileId = null
                    this.activeFileId = null
                    this.uploadError =
                        'Upload completed, but failed to initialize chat session. Missing fileId from server.'
                    console.error('fileId not found in upload response from backend:', response.data)
                }

                if (this.$refs.logFileInput) {
                    this.$refs.logFileInput.value = null
                }
                this.selectedFile = null
                this.$nextTick(() => this.scrollToBottom())
            } catch (error) {
                console.error('Error uploading log file:', error)
                this.fileId = null
                this.activeFileId = null
                this.uploadedFileName = ''
                if (error.response && error.response.data && error.response.data.detail) {
                    this.uploadError = `Upload failed: ${error.response.data.detail}`
                } else if (error.request) {
                    this.uploadError =
                        'Upload failed: No response from server. Check backend connection.'
                } else {
                    this.uploadError =
                        `Upload failed: ${error.message || 'An unexpected error occurred.'}`
                }
                console.log('fileId after failed upload:', this.fileId)
            } finally {
                this.isUploading = false
            }
        },

        // Sends user's message and updates conversation
        async sendMessage () {
            if (!this.currentUserMessage.trim() || !this.activeFileId || this.isSendingMessage) {
                console.warn('SendMessage conditions not met:', {
                    message: this.currentUserMessage,
                    fileId: this.activeFileId,
                    isSending: this.isSendingMessage
                })
                return
            }

            const userMessageContent = this.currentUserMessage
            this.sessions[this.activeFileId].push({
                role: 'user',
                content: userMessageContent
            })

            this.currentUserMessage = ''
            this.isSendingMessage = true
            this.chatError = ''
            this.$nextTick(() => this.scrollToBottom())

            try {
                const payload = {
                    fileId: this.activeFileId,
                    message: userMessageContent,
                    history: this.sessions[this.activeFileId].slice(0, -1).map(msg => ({
                        role: msg.role,
                        content: msg.content
                    }))
                }
                console.log('Sending chat payload:', payload)

                const response = await axios.post(`${API_BASE_URL}/chat/`, payload)
                console.log('Chat response:', response.data)
                this.$set(this.sessions, this.activeFileId, response.data.history)
            } catch (error) {
                console.error('Error sending message:', error)
                this.sessions[this.activeFileId].push({
                    role: 'assistant',
                    content: 'Sorry, I encountered an error processing your message. Please try again.'
                })
                if (error.response && error.response.data && error.response.data.detail) {
                    this.chatError = `Chat error: ${error.response.data.detail}`
                } else if (error.request) {
                    this.chatError =
                        'Chat error: No response from server. Check backend connection.'
                } else {
                    this.chatError =
                        'Failed to get response. An unexpected error occurred.'
                }
            } finally {
                this.isSendingMessage = false
                this.$nextTick(() => {
                    this.scrollToBottom()
                    if (this.$refs.chatInput) {
                        this.$refs.chatInput.focus()
                    }
                })
            }
        },

        // Resets the conversation history for current session
        startFreshConversation () {
            if (!this.activeFileId) return

            console.log('Starting fresh conversation for fileId:', this.activeFileId)
            this.$set(this.sessions, this.activeFileId, [])
            this.currentUserMessage = ''
            this.chatError = ''
            const freshGreeting = `Conversation reset for log '${this.uploadedFileName}'.` +
                                  ' How can I assist you further with this log?'
            this.sessions[this.activeFileId].push({
                role: 'assistant',
                content: freshGreeting
            })
            this.$nextTick(() => {
                this.scrollToBottom()
                if (this.$refs.chatInput) {
                    this.$refs.chatInput.focus()
                }
            })
        },

        // Clears all session and state for new upload
        clearChat () {
            console.log('Clearing chat session and uploaded file state.')
            this.fileId = null
            this.activeFileId = null
            this.uploadedFileName = ''
            this.selectedFile = null
            this.uploadError = ''
            this.uploadSuccessMessage = ''
            this.sessions = {}
            this.currentUserMessage = ''
            this.chatError = ''
            if (this.$refs.logFileInput) {
                this.$refs.logFileInput.value = null
            }
        },

        // Scroll chat history to bottom
        scrollToBottom () {
            const chatHistoryDiv = this.$refs.chatHistory
            if (chatHistoryDiv) {
                chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight
            }
        },

        // Escapes and formats message content to safely render HTML
        formatMessageContent (content) {
            if (typeof content !== 'string') {
                content = String(content)
            }
            const escapedContent = content
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;')
            return escapedContent.replace(/\n/g, '<br>')
        },

        // Exports the current chat history as a text file
        downloadChatHistory () {
            if (!this.activeFileId ||
                !this.sessions[this.activeFileId] ||
                this.sessions[this.activeFileId].length === 0
            ) {
                const alertMsg = this.activeFileId
                    ? 'No chat history to export for the current log.'
                    : 'Please upload a log file first.'
                alert(alertMsg)
                return
            }
            const historyToExport = this.sessions[this.activeFileId]
            const historyPreamble =
                `Chat History for Log: ${this.uploadedFileName}\n` +
                `File ID: ${this.activeFileId}\n` +
                `Exported on: ${new Date().toLocaleString()}\n\n` +
                '-------------------------------------------\n\n'
            const historyText = historyToExport
                .map(msg => `${msg.role === 'user' ? 'You' : 'Aero'}: ${msg.content.replace(/<br>/g, '\n')}`)
                .join('\n\n')

            const blob = new Blob([historyPreamble + historyText], { type: 'text/plain;charset=utf-8' })

            const url = URL.createObjectURL(blob)
            const link = document.createElement('a')
            link.href = url
            const safeFileNameBase = this.uploadedFileName.replace(/[^a-z0-9_.-]/gi, '_').toLowerCase()
            link.download = `aero_chat_history_${safeFileNameBase || 'current_log'}.txt`
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            URL.revokeObjectURL(url)
        }
    }
}
</script>

<style scoped>
:root {
    --chatbot-primary-color: #7f9fc2;
    --chatbot-primary-hover: #0056b3;
    --chatbot-secondary-color: #6c757d;
    --chatbot-light-bg: #6695c4;
    --chatbot-dark-bg: #9a9b9c;
    --chatbot-dark-surface: #343a40;
    --chatbot-dark-text: #f8f9fa;
    --chatbot-text-light: #030303;
    --chatbot-border-color: #808181;
    --chatbot-dark-border-color: #495057;
    --chatbot-text-dark-theme: #212529;
}

/* Floating circular button to launch chatbot */
.chatbot-trigger-button {
    position: fixed;
    bottom: 25px;
    right: 25px;
    background-color: var(--chatbot-primary-color);
    color: rgb(227, 229, 233);
    border: none;
    border-radius: 50%;
    width: 56px;
    height: 56px;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    box-shadow: 0 5px 15px rgba(249, 248, 248, 0.904);
    z-index: 10000;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.2s ease-in-out, transform 0.2s ease-in-out;
    padding: 0;
}

/* Hover animation for launch button */
.chatbot-trigger-button:hover {
    background-color: var(--chatbot-primary-hover);
    transform: translateY(-2px) scale(1.05);
}

/* Logo styling inside the trigger button */
.chatbot-trigger-button .chatbot-trigger-logo {
    width: 26px;
    height: 26px;
}
.chatbot-trigger-button svg {
    width: 26px;
    height: 26px;
}

/* Main chat window style */
.chatbot-window {
    position: fixed;
    bottom: 90px;
    right: 25px;
    width: 380px;
    max-height: 65vh;
    background-color: #ffffff;
    border: 1px solid var(--chatbot-border-color);
    border-radius: 12px;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12);
    z-index: 9999;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    font-family: 'Nunito Sans', sans-serif;
    transition: background-color 0.3s, color 0.3s;
}

/* Dark mode appearance for chat window */
.chatbot-window.dark-mode {
    background-color: var(--chatbot-dark-bg);
    color: var(--chatbot-dark-text);
    border-color: var(--chatbot-dark-border-color);
}

/* Header containing logo and action icons */
.chatbot-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 15px;
    background-color: var(--chatbot-light-bg);
    border-bottom: 1px solid var(--chatbot-border-color);
    transition: background-color 0.3s, border-color 0.3s;
}

/* Header adapts to dark mode */
.chatbot-window.dark-mode .chatbot-header {
    background-color: var(--chatbot-dark-surface);
    border-bottom-color: var(--chatbot-dark-border-color);
}

/* Title text and logo alignment */
.chatbot-header h3 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--chatbot-text-dark-theme);
    display: flex;
    align-items: center;
    transition: color 0.3s;
}
.chatbot-window.dark-mode .chatbot-header h3 {
    color: var(--chatbot-dark-text);
}

/* Logo inside the header */
.chatbot-header-logo {
    width: 22px;
    height: 22px;
    margin-right: 8px;
}
.header-buttons {
    display: flex;
    align-items: center;
    gap: 4px;
}

/* Buttons in the header bar */
.header-icon-button {
    background: none;
    border: none;
    color: var(--chatbot-secondary-color);
    cursor: pointer;
    padding: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: background-color 0.2s, color 0.2s;
}
.chatbot-window.dark-mode .header-icon-button {
    color: #bbb;
}
.header-icon-button:hover {
    background-color: #e0e0e0;
    color: var(--chatbot-text-dark-theme);
}
.chatbot-window.dark-mode .header-icon-button:hover {
    background-color: #555;
    color: var(--chatbot-dark-text);
}

.fresh-chat-button svg, .mode-toggle svg, .download-button svg {
    width: 16px;
    height: 16px;
}
.close-chat-button {
    font-size: 22px;
    font-weight: 400;
    line-height: 1;
}

.chatbot-container {
    padding: 15px;
    overflow-y: auto;
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    background-color: #fff;
    transition: background-color 0.3s;
}
.chatbot-window.dark-mode .chatbot-container {
    background-color: var(--chatbot-dark-bg);
}

.log-info {
    font-size: 0.75rem;
    color: var(--chatbot-text-light);
    margin-bottom: 8px;
    text-align: center;
    padding: 5px 8px;
    background-color: #76b0ea;
    border-radius: 4px;
    transition: background-color 0.3s, color 0.3s;
}
.chatbot-window.dark-mode .log-info {
    background-color: var(--chatbot-dark-surface);
    color: #ccc;
}

/* Chat message container with scroll */
.chat-history {
    flex-grow: 1;
    min-height: 150px;
    max-height: calc(65vh - 200px);
    border: 1px solid var(--chatbot-border-color);
    overflow-y: auto;
    padding: 10px;
    margin-bottom: 10px;
    background-color: var(--chatbot-light-bg);
    border-radius: 8px;
    transition: background-color 0.3s, border-color 0.3s;
}
.chatbot-window.dark-mode .chat-history {
    background-color: var(--chatbot-dark-surface);
    border-color: var(--chatbot-dark-border-color);
}

.message {
    margin-bottom: 8px;
    padding: 8px 12px;
    border-radius: 10px;
    word-wrap: break-word;
    overflow-wrap: break-word;
    max-width: 85%;
    line-height: 1.4;
    clear: both;
    box-shadow: 0 1px 1px rgba(0,0,0,0.04);
    transition: background-color 0.3s, color 0.3s;
}
.message-sender {
    display: block;
    margin-bottom: 2px;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--chatbot-text-light);
    opacity: 0.8;
    transition: color 0.3s;
}
.message-content {
    font-size: 0.85rem;
}

/* User message bubble styling */
.message.user {
    background-color: #85aafa;
    color: rgb(12, 11, 12);
    margin-left: auto;
    align-self: flex-end;
}
.message.user .message-sender {
   color: #0a0b0b;
}
.chatbot-window.dark-mode .message.user {
    background-color: #0056b3;
}

.message.assistant {
    background-color: #39f2d3;
    color: var(--chatbot-text-dark-theme);
    margin-right: auto;
    align-self: flex-start;
}
.chatbot-window.dark-mode .message.assistant {
    background-color: #404040;
    color: var(--chatbot-dark-text);
}
.message.assistant .message-sender {
   color: var(--chatbot-secondary-color);
}
.chatbot-window.dark-mode .message.assistant .message-sender {
   color: #f7f6f6;
}

/* Welcome message placeholder before upload */
.message.assistant-placeholder {
    color: var(--chatbot-secondary-color);
    font-style: italic;
    text-align: center;
    padding: 10px;
    background-color: transparent;
    border: none;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    overflow: visible;
    box-shadow: none;
    min-height: 100px;
}
.chatbot-window.dark-mode .message.assistant-placeholder,
.chatbot-window.dark-mode .message.assistant-placeholder h2,
.chatbot-window.dark-mode .message.assistant-placeholder p {
    color: #bbb;
}
.message.assistant-placeholder .welcome-logo {
    width: 32px;
    height: 32px;
    margin-bottom: 5px;
}
.message.assistant-placeholder h2 {
    font-size: 0.95rem;
    color: var(--chatbot-text-dark-theme);
    margin-bottom: 2px;
    font-weight: 600;
}
.message.assistant-placeholder p {
    font-size: 0.75rem;
    line-height: 1.3;
    max-width: 90%;
}

/* Input area with text box and buttons */
.chat-input-area {
    margin-top: auto;
    padding-top: 10px;
    border-top: 1px solid var(--chatbot-border-color);
    transition: border-color 0.3s;
}
.chatbot-window.dark-mode .chat-input-area {
    border-top-color: var(--chatbot-dark-border-color);
}

.chat-input {
    display: flex;
    align-items: center;
    gap: 8px;
}

.chat-input input {
    flex-grow: 1;
    padding: 9px 14px;
    border: 1px solid var(--chatbot-border-color);
    border-radius: 18px;
    font-size: 0.875rem;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s, background-color 0.3s, color 0.3s;
}
.chatbot-window.dark-mode .chat-input input {
    background-color: var(--chatbot-dark-surface);
    color: var(--chatbot-dark-text);
    border-color: var(--chatbot-dark-border-color);
}
.chatbot-window.dark-mode .chat-input input::placeholder {
    color: #888;
}
.chat-input input:focus {
    border-color: var(--chatbot-primary-color);
    box-shadow: 0 0 0 0.1rem rgba(0, 123, 255, 0.25);
}

.send-button {
    padding: 0;
    border: none;
    background-color: var(--chatbot-primary-color);
    color: rgb(123, 212, 250);
    border-radius: 50%;
    width: 38px;
    height: 38px;
    cursor: pointer;
    transition: background-color 0.2s ease-in-out;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.chatbot-window.dark-mode .send-button {
    background-color: #555;
}
.send-button:hover {
    background-color: var(--chatbot-primary-hover);
}
.chatbot-window.dark-mode .send-button:hover {
    background-color: #666;
}
.send-button:disabled {
    background-color: #9fa0a0;
    cursor: not-allowed;
}
.chatbot-window.dark-mode .send-button:disabled {
    background-color: #404040;
}
.send-button svg {
    width: 16px;
    height: 16px;
}
.clear-chat-button-inline {
    background: none;
    border: none;
    color: var(--chatbot-secondary-color);
    cursor: pointer;
    padding: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: background-color 0.2s, color 0.2s;
    flex-shrink: 0;
}
.clear-chat-button-inline:hover {
    background-color: #f0f0f0;
    color: var(--chatbot-error-color);
}
.chatbot-window.dark-mode .clear-chat-button-inline {
    color: #bbb;
}
.chatbot-window.dark-mode .clear-chat-button-inline:hover {
    background-color: #555;
    color: #ff8080;
}
.clear-chat-button-inline svg {
    width: 16px;
    height: 16px;
}

.typing-indicator-send {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 16px;
}
.typing-indicator-send div {
    width: 4px;
    height: 4px;
    margin: 0 1.5px;
    background-color: rgb(6, 6, 6);
    border-radius: 50%;
    animation: typing-bounce 1.2s infinite ease-in-out;
}
.typing-indicator-send div:nth-child(2) { animation-delay: -0.2s; }
.typing-indicator-send div:nth-child(3) { animation-delay: -0.4s; }

@keyframes typing-bounce {
    0%, 80%, 100% { transform: scale(0); }
    40% { transform: scale(1.0); }
}

.upload-section {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid var(--chatbot-border-color);
    display: flex;
    flex-direction: column;
    align-items: center;
    transition: border-color 0.3s;
}
.chatbot-window.dark-mode .upload-section {
    border-top-color: var(--chatbot-dark-border-color);
}
.upload-label {
    display: block;
    margin-bottom: 8px;
    font-weight: 500;
    font-size: 0.9rem;
    color: var(--chatbot-text-light);
    text-align: center;
    transition: color 0.3s;
}
.chatbot-window.dark-mode .upload-label {
    color: #ccc;
}

/* File upload controls and label styling */
.upload-controls {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    width: 100%;
    justify-content: center;
}
.file-input {
    width: 0.1px;
    height: 0.1px;
    opacity: 0;
    overflow: hidden;
    position: absolute;
    z-index: -1;
}
.file-input-label {
    padding: 7px 10px;
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--chatbot-primary-color);
    background-color: #fff;
    border: 1px solid var(--chatbot-primary-color);
    border-radius: 4px;
    cursor: pointer;
    display: inline-block;
    transition: background-color 0.2s, color 0.2s, border-color 0.3s;
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 130px;
}
.chatbot-window.dark-mode .file-input-label {
    background-color: var(--chatbot-dark-surface);
    color: var(--chatbot-primary-color);
    border-color: var(--chatbot-primary-color);
}
.file-input-label:hover {
    background-color: #f0f8ff;
}
.chatbot-window.dark-mode .file-input-label:hover {
    background-color: #444;
}

.upload-button {
    padding: 7px 14px;
    border: none;
    background-color: #28a745;
    color: white;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.8rem;
    transition: background-color 0.2s ease-in-out;
}
.upload-button:hover {
    background-color: #218838;
}
.upload-button:disabled {
    background-color: #ced4da;
    cursor: not-allowed;
}

/* Error message display */
.error-message {
    color: var(--chatbot-error-color);
    font-size: 0.75rem;
    margin-top: 6px;
    text-align: center;
}
.chatbot-window.dark-mode .error-message {
    color: #ff8080;
}

/* Success message display */
.success-message {
    color: var(--chatbot-success-color);
    font-size: 0.75rem;
    margin-top: 6px;
    text-align: center;
}
.chatbot-window.dark-mode .success-message {
    color: #70e094;
}
</style>
