import { apiConfig } from '../api/config';
import { chatApiClient } from '../api/chatApiClient';
import { mockChatService } from './mockChatService';
import type { ChatService } from '../../types/chat';

export const chatService: ChatService = apiConfig.mode === 'api' ? chatApiClient : mockChatService;
