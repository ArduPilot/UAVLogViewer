<template>
    <div class="chatbot-container" :class="{ 'minimized': isMinimized }">
        <div class="chatbot-header" @click="toggleChat">
            <span v-if="!isMinimized">AI</span>
            <i v-else class="material-icons">chat</i>
            <button v-if="!isMinimized" class="minimize-btn">▼</button>
        </div>
        <div class="chatbot-body" v-show="!isMinimized">
            <div class="messages" ref="messagesContainer">
                <div v-for="(message, index) in messages" :key="index"
                    :class="['message', message.type]">
                    <div class="message-content">
                        {{ message.content }}
                    </div>
                </div>
            </div>
            <div class="input-area">
                <input
                    type="text"
                    v-model="userInput"
                    @keyup.enter="sendMessage"
                    placeholder="Ask about your flight data..."
                    :disabled="!isDataLoaded || isLoading"
                />
                <button @click="sendMessage" :disabled="!isDataLoaded || isLoading">
                    {{ isLoading ? 'Sending...' : 'Send' }}
                </button>
            </div>
        </div>
    </div>
</template>

<script>
// NOTE: $eventHub must be globally defined (e.g., Vue.prototype.$eventHub = new Vue()) for linting to pass
import { store } from '@/components/Globals.js'
import { chatService } from '@/libs/api.js'

export default {
    name: 'ChatBot',
    data () {
        return {
            messages: [
                {
                    type: 'bot',
                    content:
                        'Hello! I can help you analyze your MAVLink flight data. Upload a .bin file to get started.'
                }
            ],
            userInput: '',
            isMinimized: false,
            isDataLoaded: false,
            isLoading: false
        }
    },
    mounted () {
        this.$eventHub.$on('messagesDoneLoading', this.handleDataLoaded)
    },
    beforeDestroy () {
        this.$eventHub.$off('messagesDoneLoading')
    },
    methods: {
        toggleChat () {
            this.isMinimized = !this.isMinimized
        },
        handleDataLoaded () {
            console.log('this.state.messages: ', this.state.messages)
            if (!this.isDataLoaded) {
                this.isDataLoaded = true
                this.messages.push({
                    type: 'bot',
                    content:
                        'Flight data loaded! What would you like to know about your flight?'
                })
            }
        },
        async sendMessage () {
            if (!this.userInput.trim() || this.isLoading) return
            this.isLoading = true
            this.messages.push({
                type: 'user',
                content: this.userInput
            })
            const userQuery = this.userInput
            this.userInput = ''
            try {
                const response = await this.processQuery(userQuery)
                this.messages.push({
                    type: 'bot',
                    content: response
                })
            } catch (error) {
                this.messages.push({
                    type: 'bot',
                    content: 'Sorry, I encountered an error while processing your request. Please try again.'
                })
            } finally {
                this.isLoading = false
                this.$nextTick(() => {
                    const container = this.$refs.messagesContainer
                    if (container) container.scrollTop = container.scrollHeight
                })
            }
        },
        async processQuery (query) {
            const data = this.extractRelevantData()
            return this.generateResponse(query, data)
        },
        extractRelevantData () {
            // TODO: Parse messages to extract relevant data
            return this.state.messages
        },
        async generateResponse (query, data) {
            this.state.sessionId = this.state.sessionId || ''
            const flightData = this.state.sessionId ? {} : data
            try {
                const result = await chatService.sendMessage(query, this.state.sessionId, flightData)
                this.state.sessionId = result.sessionId
                console.log('result: ', result)
                return result.message
            } catch (error) {
                console.error('Error generating response:', error)
                return 'I\'m sorry, I encountered an error while processing your request. Please try again.'
            }
        },
        generateResponseOld (query, data) {
            const queryLower = query.toLowerCase()
            if (queryLower.includes('flight mode')) {
                return this.analyzeFlightModes(data.flightModes)
            } else if (queryLower.includes('trajectory') || queryLower.includes('path')) {
                return this.analyzeTrajectory(data.trajectory)
            } else if (queryLower.includes('attitude') || queryLower.includes('orientation')) {
                return this.analyzeAttitude(data.attitude)
            } else if (queryLower.includes('parameter') || queryLower.includes('param')) {
                return this.analyzeParameters(data.params)
            } else if (queryLower.includes('event')) {
                return this.analyzeEvents(data.events)
            }
            return `I'm not sure about that. You can ask me about flight modes, trajectory, attitude, 
            parameters, or events.`
        },
        analyzeFlightModes (flightModes) {
            if (!flightModes || flightModes.length === 0) {
                return 'No flight mode changes recorded in this log.'
            }
            const modeCount = flightModes.length
            const firstMode = flightModes[0].mode
            const lastMode = flightModes[modeCount - 1].mode
            return `The flight had ${modeCount} mode changes. Started in ${firstMode} and ended in ${lastMode}.`
        },
        analyzeTrajectory (trajectory) {
            if (!trajectory || trajectory.length === 0) {
                return 'No trajectory data available in this log.'
            }
            const distance = this.calculateTotalDistance(trajectory)
            return `The flight covered approximately ${distance.toFixed(2)} meters.`
        },
        analyzeAttitude (attitude) {
            if (!attitude || Object.keys(attitude).length === 0) {
                return 'No attitude data available in this log.'
            }
            return 'I can see the attitude data. What specific aspect would you like to know about?'
        },
        analyzeParameters (params) {
            if (!params) {
                return 'No parameter data available in this log.'
            }
            return 'I can help you analyze the parameters. What specific parameter would you like to know about?'
        },
        analyzeEvents (events) {
            if (!events || events.length === 0) {
                return 'No events recorded in this log.'
            }
            return `There were ${events.length} events recorded during the flight.`
        },
        calculateTotalDistance (trajectory) {
            let distance = 0
            for (let i = 1; i < trajectory.length; i++) {
                const prev = trajectory[i - 1]
                const curr = trajectory[i]
                distance += Math.sqrt(
                    Math.pow(curr.x - prev.x, 2) +
                    Math.pow(curr.y - prev.y, 2) +
                    Math.pow(curr.z - prev.z, 2)
                )
            }
            return distance
        }
    },
    computed: {
        state () {
            return store
        }
    }
}
</script>

<style scoped>
.chatbot-container {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 380px;
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    z-index: 1000;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
    transform-origin: bottom right;
}

.chatbot-container.minimized {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    cursor: pointer;
    overflow: hidden;
    transform: scale(0.8);
}

.chatbot-container.minimized:hover {
    transform: scale(0.85);
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.15);
}

.chatbot-header {
    background: linear-gradient(135deg, #2196F3, #1976D2);
    color: white;
    padding: 16px 20px;
    border-radius: 16px 16px 0 0;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;
    letter-spacing: 0.3px;
    transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.chatbot-container.minimized .chatbot-header {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    transform: scale(1.2);
}

.chatbot-container.minimized .chatbot-header i {
    font-size: 32px;
    color: white;
    opacity: 0;
    transform: scale(0.5) rotate(-180deg);
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.chatbot-container.minimized .chatbot-header i {
    opacity: 1;
    transform: scale(1) rotate(0);
}

.chatbot-body {
    height: 480px;
    display: flex;
    flex-direction: column;
    background: #f8f9fa;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    opacity: 1;
    transform: translateY(0);
}

.chatbot-container.minimized .chatbot-body {
    opacity: 0;
    transform: translateY(20px);
    pointer-events: none;
}

.minimize-btn {
    background: rgba(255, 255, 255, 0.2);
    border: none;
    color: white;
    cursor: pointer;
    font-size: 14px;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    transform: rotate(0);
}

.minimize-btn:hover {
    background: rgba(255, 255, 255, 0.3);
    transform: rotate(180deg);
}

.messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.message {
    margin-bottom: 4px;
    max-width: 85%;
    animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.message.user {
    margin-left: auto;
}

.message-content {
    padding: 12px 16px;
    border-radius: 18px;
    font-size: 14px;
    line-height: 1.5;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.message.user .message-content {
    background: #2196F3;
    color: white;
    border-bottom-right-radius: 4px;
}

.message.bot .message-content {
    background: white;
    color: #2c3e50;
    border-bottom-left-radius: 4px;
}

.input-area {
    padding: 16px;
    background: white;
    border-top: 1px solid #edf2f7;
    display: flex;
    gap: 12px;
    border-radius: 0 0 16px 16px;
}

input {
    flex: 1;
    padding: 12px 16px;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    outline: none;
    font-size: 14px;
    transition: all 0.2s ease;
    background: #f8f9fa;
}

input:focus {
    border-color: #2196F3;
    box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
    background: white;
}

input::placeholder {
    color: #a0aec0;
}

button {
    padding: 12px 20px;
    background: #2196F3;
    color: white;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    font-weight: 500;
    font-size: 14px;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 80px;
}

button:hover:not(:disabled) {
    background: #1976D2;
    transform: translateY(-1px);
}

button:disabled {
    background: #e2e8f0;
    color: #a0aec0;
    cursor: not-allowed;
    transform: none;
}

/* Custom scrollbar */
.messages::-webkit-scrollbar {
    width: 6px;
}

.messages::-webkit-scrollbar-track {
    background: transparent;
}

.messages::-webkit-scrollbar-thumb {
    background: #cbd5e0;
    border-radius: 3px;
}

.messages::-webkit-scrollbar-thumb:hover {
    background: #a0aec0;
}
</style>
