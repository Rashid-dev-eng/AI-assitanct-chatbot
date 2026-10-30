export const apiConfig = {
  mode: import.meta.env.VITE_CHAT_MODE === 'api' ? 'api' : 'mock',
  baseUrl: (import.meta.env.VITE_CHATBOT_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, ''),
};
