import axios from 'axios';

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || ''

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const chatService = {
  sendMessage: async (message, sessionId, flightData) => {
    try {
      const response = await api.post('/chat', {
        message,
        sessionId,
        flightData,
      });
      return response.data;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  },
};

export default api; 