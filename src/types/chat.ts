export type ChatLanguage = 'en' | 'sw';
export type ChatSource = 'mock' | 'conversation' | 'api' | 'knowledge' | 'llm';

export interface ChatRequest {
  message: string;
  language: ChatLanguage;
  queryLanguage?: ChatLanguage | 'mixed';
  conversationId?: string;
}

export interface ChatResponse {
  conversationId: string | null;
  message: string;
  language: ChatLanguage;
  source: ChatSource;
  relatedQuestions?: string[];
  intent?: string | null;
  confidence?: number | null;
  needsClarification?: boolean;
  sourceReferences?: Array<{ title: string; url?: string | null; verificationStatus?: string }>;
  integrationStatus?: string;
  retrievalStatus?: string;
  responseMode?: string;
}

export interface ChatService {
  sendMessage(request: ChatRequest): Promise<ChatResponse>;
  clearConversation?(conversationId: string): Promise<void>;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  sourceReferences?: ChatResponse['sourceReferences'];
  responseMode?: string;
}
