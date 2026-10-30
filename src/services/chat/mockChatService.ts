import { chatCopy } from '../../i18n/chat';
import type { ChatRequest, ChatResponse, ChatService } from '../../types/chat';

export const mockChatService: ChatService = {
  async sendMessage({ message, language, conversationId }: ChatRequest): Promise<ChatResponse> {
    await new Promise((resolve) => window.setTimeout(resolve, 520));
    const text = message.toLowerCase();
    const copy = chatCopy[language];
    let response = copy.fallback as string;
    if (text.includes('assignment') || text.includes('kazi')) response = copy.assignment as string;
    else if (text.includes('quiz') || text.includes('jaribio')) response = copy.quiz as string;
    return {
      conversationId: conversationId ?? null,
      message: response,
      language,
      source: 'mock',
    };
  },
};
