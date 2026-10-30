import { chatCopy } from '../../i18n/chat';
import type { ChatLanguage, ChatRequest, ChatResponse, ChatService } from '../../types/chat';
import { apiConfig } from './config';

interface TranslationInterpretation {
  requestType: 'translation';
  sourceTerm?: string;
  targetLanguage?: ChatLanguage;
  translation: string;
  translationStatus: 'verified' | 'proposed' | 'missing' | 'not_applicable' | string;
  needsClarification?: boolean;
}

function translationTarget(message: string, interfaceLanguage: ChatLanguage): ChatLanguage | null {
  const normalized = message.trim().toLocaleLowerCase();
  const explicitRequest = /\b(translate|translation|translated|tafsiri|tafsiriwa)\b|^what does\b|^how do (?:you|i) say\b|^what is .+ (?:called|said) in\b|^what is .+ in\s+(?:english|kiswahili|swahili)\b|^maana ya\b|^neno la\b/.test(normalized);
  if (!explicitRequest) return null;
  if (/\b(?:to|into|in)\s+(?:english)\b|kwa\s+kiingereza/.test(normalized)) return 'en';
  if (/\b(?:to|into|in)\s+(?:kiswahili|swahili)\b|kwa\s+kiswahili/.test(normalized)) return 'sw';
  return interfaceLanguage === 'en' ? 'sw' : 'en';
}

async function postInterpretation<T>(body: Record<string, string>): Promise<T> {
  const response = await fetch(`${apiConfig.baseUrl}/lexicon/interpret/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`Lexicon interpretation returned HTTP ${response.status}`);
  return response.json() as Promise<T>;
}

async function postChat(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${apiConfig.baseUrl}/chat/messages/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...request, queryLanguage: 'mixed' }),
  });
  if (!response.ok) throw new Error(`Chat service returned HTTP ${response.status}`);
  return response.json() as Promise<ChatResponse>;
}

function formatTemplate(template: string, values: Record<string, string>): string {
  return template.replace(/\{(language|term|translation)\}/g, (_, key: string) => values[key] ?? '');
}

function translationReply(result: TranslationInterpretation, language: ChatLanguage): string {
  const copy = chatCopy[language];
  const targetName = result.targetLanguage === 'sw' ? 'Kiswahili' : 'English';
  const term = result.sourceTerm || 'that phrase';
  if (result.needsClarification) return copy.clarify;
  if (result.translationStatus === 'verified' && result.translation) {
    return formatTemplate(copy.verifiedTranslation, { language: targetName, term, translation: result.translation });
  }
  if (result.translationStatus === 'proposed' && result.translation) {
    return formatTemplate(copy.proposedTranslation, { language: targetName, term, translation: result.translation });
  }
  if (result.translationStatus === 'proposed') {
    return formatTemplate(copy.proposedOnly, { language: targetName, term, translation: '' });
  }
  return formatTemplate(copy.noTranslation, { language: targetName, term, translation: '' });
}

export const chatApiClient: ChatService = {
  async clearConversation(conversationId: string): Promise<void> {
    const response = await fetch(`${apiConfig.baseUrl}/chat/conversations/${conversationId}/`, { method: 'DELETE' });
    if (!response.ok && response.status !== 404) throw new Error(`Conversation cleanup returned HTTP ${response.status}`);
  },
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const targetLanguage = translationTarget(request.message, request.language);
    if (targetLanguage) {
      const result = await postInterpretation<TranslationInterpretation>({
        query: request.message,
        language: 'mixed',
        request_type: 'translation',
        target_language: targetLanguage,
      });
      return {
        conversationId: request.conversationId ?? null,
        message: translationReply(result, request.language),
        language: request.language,
        source: 'api',
        intent: 'translation_lookup',
        needsClarification: result.needsClarification ?? false,
      };
    }

    // Service interpretation and clarification happen in the conversation endpoint,
    // where the backend can use conversation context. The client must not gate chat
    // on a context-free lexicon lookup (which rejected greetings and short follow-ups).
    return postChat({ ...request, queryLanguage: 'mixed' });
  },
};
