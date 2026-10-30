# Frontend architecture

The React/TypeScript/Vite preview renders a blank white page and a floating assistant. `src/app/App.tsx` owns chat open state, the selected reply language, and current visible messages. `ChatWidget` owns loading/error/retry state, conversation identifier, and the optional Student/Teacher/Administrator interface context.

`src/services/chat/index.ts` selects the mock service or backend API based on `VITE_CHAT_MODE`. The ignored local `.env.local` config selects API mode. API mode asks the lexicon to interpret or translate a query, then sends service requests to Django for reviewed-source retrieval and optional grounded LLM generation. An unmatched lexicon query still reaches retrieval; ambiguous matches request clarification. The reply language and query language are separate.

Conversation behavior:

- The initial reply language is English.
- Minimize hides the panel while preserving the current messages and backend conversation.
- Close clears the visible conversation, resets English and interface context, and requests deletion of the backend conversation.
- A page reload starts a fresh preview session; no chat transcript is restored from browser storage.
- An interface selection is a retrieval hint only. It does not authenticate the visitor or grant access to Moodle.

Messages are rendered as React text, and source URLs are rendered as links only when they use HTTP or HTTPS. The panel supports keyboard focus, screen-reader live updates, Enter to send, Shift+Enter for a newline, responsive sizing, and reduced-motion styles. The API key is configured only in backend environment variables.
