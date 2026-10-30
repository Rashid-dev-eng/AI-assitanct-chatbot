import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { chatCopy } from '../../i18n/chat';
import { chatService } from '../../services/chat';
import { loadConversationId, saveConversationId } from '../../services/storage/chatStorage';
import type { ChatLanguage, ChatMessage } from '../../types/chat';
import dmiSeal from '../../assets/dmi-seal.png';

interface ChatWidgetProps {
  open: boolean;
  language: ChatLanguage;
  messages: ChatMessage[];
  onMessagesChange: (messages: ChatMessage[]) => void;
  onLanguageChange: (language: ChatLanguage) => void;
  onOpen: () => void;
  onMinimize: () => void;
  onClose: () => void;
}

function AssistantIcon() {
  return <img src={dmiSeal} alt="" aria-hidden="true" />;
}

function SendIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" /></svg>;
}

function responseLabel(mode: string, language: ChatLanguage): string {
  const labels: Record<string, Record<ChatLanguage, string>> = {
    llm: { en: 'AI answer · sourced', sw: 'Jibu la AI · lina chanzo' },
    tool_agent: { en: 'Checked reviewed sources', sw: 'Vyanzo vilivyokaguliwa' },
    retrieval_fallback: { en: 'From a reviewed source', sw: 'Kutoka chanzo kilichokaguliwa' },
  };
  return labels[mode]?.[language] ?? '';
}

function isExternalHttpUrl(value: string | null | undefined): value is string {
  if (!value) return false;
  try {
    const url = new URL(value);
    return (url.protocol === 'http:' || url.protocol === 'https:') && !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  } catch {
    return false;
  }
}

export function ChatWidget({ open, language, messages, onMessagesChange, onLanguageChange, onOpen, onMinimize, onClose }: ChatWidgetProps) {
  const copy = chatCopy[language];
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(loadConversationId);
  const bodyRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const requestVersion = useRef(0);
  const [retryText, setRetryText] = useState('');

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages, busy, open]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
    panelRef.current?.toggleAttribute('inert', !open);
  }, [open]);

  useEffect(() => {
    if (messages.length === 0) {
      setConversationId(null);
      saveConversationId(null);
    }
  }, [messages.length]);

  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    const version = ++requestVersion.current;
    setError('');
    onMessagesChange([...messages, { role: 'user', text: trimmed }]);
    setBusy(true);
    try {
      const response = await chatService.sendMessage({ message: trimmed, language, ...(conversationId ? { conversationId } : {}) });
      if (version !== requestVersion.current) return;
      if (response.conversationId) {
        setConversationId(response.conversationId);
        saveConversationId(response.conversationId);
      }
      setRetryText('');
      onMessagesChange([...messages, { role: 'user', text: trimmed }, { role: 'assistant', text: response.message, sourceReferences: response.sourceReferences, responseMode: response.responseMode }]);
    } catch {
      if (version !== requestVersion.current) return;
      setError(language === 'sw' ? 'Msaidizi hapatikani kwa sasa. Tafadhali jaribu tena.' : 'The assistant is unavailable right now. Please try again.');
      setRetryText(trimmed);
    } finally {
      if (version === requestVersion.current) setBusy(false);
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = inputRef.current;
    if (!input) return;
    const text = input.value;
    input.value = '';
    void sendMessage(text);
  }

  function onInputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  function closeAndClear() {
    requestVersion.current += 1;
    setBusy(false);
    setError('');
    setRetryText('');
    if (conversationId) void chatService.clearConversation?.(conversationId).catch(() => undefined);
    setConversationId(null);
    saveConversationId(null);
    if (inputRef.current) inputRef.current.value = '';
    onClose();
  }

  return (
    <>
      <button className="chat-launch" aria-label="Open DMI DeLMS Assistant" aria-expanded={open} onClick={open ? onMinimize : onOpen}>
        <AssistantIcon />
      </button>
      <section ref={panelRef} className={`chat ${open ? 'open' : ''}`} aria-label="DMI DeLMS Assistant" aria-hidden={!open}>
        <header className="chat-head">
          <div className="assistant-title"><span className="assistant-icon"><AssistantIcon /></span><span><strong>DMI DeLMS Assistant</strong></span></div>
          <div className="chat-actions">
            <select className="chat-select" aria-label="Chat language" value={language} onChange={(event) => onLanguageChange(event.target.value as ChatLanguage)}><option value="en">ENG</option><option value="sw">SW</option></select>
            <button type="button" aria-label="Minimize assistant" title="Minimize" onClick={onMinimize}>−</button>
            <button type="button" aria-label="Close assistant and clear this conversation" title="Close" onClick={closeAndClear}>×</button>
          </div>
        </header>
        <div className="chat-body" id="chat-body" ref={bodyRef} role="log" aria-live="polite" aria-relevant="additions text" aria-busy={busy}>
          {messages.length ? messages.map((message, index) => <div className={`message-row ${message.role === 'user' ? 'user' : ''}`} key={`${index}-${message.role}`}>{message.role === 'assistant' && <img className="message-logo" src={dmiSeal} alt="DMI assistant" />}<div className={`message ${message.role === 'user' ? 'user' : ''}`}><span>{message.text}</span>{message.role === 'assistant' && message.responseMode && responseLabel(message.responseMode, language) && <small className="response-mode">{responseLabel(message.responseMode, language)}</small>}{message.sourceReferences?.map((source, sourceIndex) => isExternalHttpUrl(source.url) ? <a className="source-link" href={source.url} target="_blank" rel="noreferrer" key={`${source.title}-${sourceIndex}`}>{sourceIndex + 1}. {source.title}</a> : <small className="source-link" key={`${source.title}-${sourceIndex}`}>{sourceIndex + 1}. {source.title}</small>)}</div></div>) : <p className="chat-intro">{copy.welcome}</p>}
          {busy && <div className="typing" role="status" aria-label={copy.working}><i /><i /><i /><small className="typing-label">{copy.working}</small></div>}
          {error && <div className="message" role="alert">{error}{retryText && <button className="retry" type="button" onClick={() => void sendMessage(retryText)}>{language === 'sw' ? 'Jaribu tena' : 'Retry'}</button>}</div>}
        </div>
        {!messages.length && <div className="suggestions">{copy.suggestions.map((question) => <button type="button" key={question} onClick={() => void sendMessage(question)}>{question}</button>)}</div>}
        <form className="chat-form" onSubmit={onSubmit}><textarea ref={inputRef} aria-label="Message" placeholder={copy.placeholder} rows={1} onKeyDown={onInputKeyDown} /><button className="send" aria-label="Send message" disabled={busy}><SendIcon /></button></form>
      </section>
    </>
  );
}
