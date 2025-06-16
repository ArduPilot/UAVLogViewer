import axios from 'axios'

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || ''

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json'
    },
    httpsAgent: new (require('https').Agent)({
        rejectUnauthorized: false
    })
})

export const chatService = {
    sendMessage: async (message, sessionId, flightData) => {
        try {
            console.log('Server URL:', API_BASE_URL)
            const response = await api.post('/api/chat', {
                message,
                sessionId,
                flightData
            })
            console.log('Received API Response:', response.data)
            return response.data
        } catch (error) {
            console.error('Error sending message:', error)
            throw error
        }
    }
}

export default api
