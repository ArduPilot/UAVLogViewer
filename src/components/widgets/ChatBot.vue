<template>
    <div class="chatbot-container">
        <div class="chatbot-header" @click="toggleChat">
            <span>AI</span>
            <button class="minimize-btn">{{ isMinimized ? '▲' : '▼' }}</button>
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
                    :disabled="!isDataLoaded"
                />
                <button @click="sendMessage" :disabled="!isDataLoaded">
                    Send
                </button>
            </div>
        </div>
    </div>
</template>

<script>
// NOTE: $eventHub must be globally defined (e.g., Vue.prototype.$eventHub = new Vue()) for linting to pass
import { store } from '@/components/Globals.js'

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
            isDataLoaded: false
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
            this.isDataLoaded = true
            this.messages.push({
                type: 'bot',
                content:
                    'Flight data loaded! What would you like to know about your flight?'
            })
        },
        async sendMessage () {
            if (!this.userInput.trim()) return
            this.messages.push({
                type: 'user',
                content: this.userInput
            })
            const userQuery = this.userInput
            this.userInput = ''
            const response = await this.processQuery(userQuery)
            this.messages.push({
                type: 'bot',
                content: response
            })
            this.$nextTick(() => {
                const container = this.$refs.messagesContainer
                if (container) container.scrollTop = container.scrollHeight
            })
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
            try {
                // TODO: Generate response based on query and data
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: query,
                        sessionId: this.state.sessionId,
                        flightData: data // TODO: Send only the relevant data
                    })
                })
                if (!response.ok) {
                    throw new Error('Failed to generate response')
                }
                const result = await response.json()
                this.state.sessionId = result.sessionId
                return result.response
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
    width: 350px;
    background: white;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    z-index: 1000;
}

.chatbot-header {
    background: #2196F3;
    color: white;
    padding: 10px 15px;
    border-radius: 10px 10px 0 0;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.minimize-btn {
    background: none;
    border: none;
    color: white;
    cursor: pointer;
    font-size: 16px;
}

.chatbot-body {
    height: 400px;
    display: flex;
    flex-direction: column;
}

.messages {
    flex: 1;
    overflow-y: auto;
    padding: 15px;
}

.message {
    margin-bottom: 10px;
    max-width: 80%;
}

.message.user {
    margin-left: auto;
}

.message-content {
    padding: 8px 12px;
    border-radius: 15px;
    background: #f0f0f0;
}

.message.user .message-content {
    background: #2196F3;
    color: white;
}

.message.bot .message-content {
    background: #f0f0f0;
    color: #333;
}

.input-area {
    padding: 10px;
    border-top: 1px solid #eee;
    display: flex;
    gap: 10px;
}

input {
    flex: 1;
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    outline: none;
}

button {
    padding: 8px 15px;
    background: #2196F3;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}

button:disabled {
    background: #ccc;
    cursor: not-allowed;
}
</style>
