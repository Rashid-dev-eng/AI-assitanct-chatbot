import type { ChatMessage } from '../../types/chat';

const CHAT_KEY = 'delms-chat';
const LANGUAGE_KEY = 'delms-language';
const CONVERSATION_KEY = 'delms-conversation-id';
const SESSION_KEY = 'delms-session';

function removeItem(key: string): void {
  try { localStorage.removeItem(key); } catch { /* Storage can be disabled by browser policy. */ }
}

export function loadMessages(): ChatMessage[] {
  let raw: string | null;
  try {
    raw = localStorage.getItem(CHAT_KEY);
  } catch {
    return [];
  }
  try {
    const parsed: unknown = JSON.parse(raw || '[]');
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is ChatMessage =>
      item && (item.role === 'user' || item.role === 'assistant') && typeof item.text === 'string',
    );
  } catch {
    removeItem(CHAT_KEY);
    return [];
  }
}

export function saveMessages(messages: ChatMessage[]): void {
  try { localStorage.setItem(CHAT_KEY, JSON.stringify(messages)); } catch { /* Keep the UI usable without storage. */ }
}

export function saveLanguage(language: 'ENG' | 'SW'): void {
  try { localStorage.setItem(LANGUAGE_KEY, language); } catch { /* Keep the UI usable without storage. */ }
}

export function loadConversationId(): string | null {
  try { return localStorage.getItem(CONVERSATION_KEY); } catch { return null; }
}

export function saveConversationId(conversationId: string | null): void {
  try {
    if (conversationId) localStorage.setItem(CONVERSATION_KEY, conversationId);
    else localStorage.removeItem(CONVERSATION_KEY);
  } catch { /* The conversation continues in in-memory state if storage is unavailable. */ }
}

export function clearChat(): void {
  removeItem(CHAT_KEY);
  removeItem(CONVERSATION_KEY);
  try { localStorage.setItem(LANGUAGE_KEY, 'ENG'); } catch { /* Keep the UI usable without storage. */ }
}

export function loadDemoSessionStarted(): number {
  try { return Number(localStorage.getItem(SESSION_KEY) || Date.now()); } catch { return Date.now(); }
}

export function saveDemoSessionStarted(timestamp: number): void {
  try { localStorage.setItem(SESSION_KEY, String(timestamp)); } catch { /* Session remains local to this tab. */ }
}

export function clearDemoSession(): void {
  removeItem(SESSION_KEY);
}
