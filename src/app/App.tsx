import { useState } from 'react';
import { ChatWidget } from '../components/chatbot/ChatWidget';
import type { ChatLanguage, ChatMessage } from '../types/chat';

export default function App() {
  const [open, setOpen] = useState(false);
  const [language, setLanguage] = useState<ChatLanguage>('en');
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  function closeChat() {
    setMessages([]);
    setLanguage('en');
    setOpen(false);
  }

  return (
    <main className="preview-page" aria-label="DMI DeLMS Assistant preview">
      <ChatWidget
        open={open}
        language={language}
        messages={messages}
        onMessagesChange={setMessages}
        onLanguageChange={setLanguage}
        onOpen={() => setOpen(true)}
        onMinimize={() => setOpen(false)}
        onClose={closeChat}
      />
    </main>
  );
}
