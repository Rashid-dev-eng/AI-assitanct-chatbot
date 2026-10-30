# Chatbot API contract proposal

The implementation now lives in [`../backend/`](../backend/). The backend README documents its current endpoints. Live Moodle calls remain disabled pending DMI authorization; see [`MOODLE_INTEGRATION.md`](MOODLE_INTEGRATION.md).

The frontend uses API mode in the local `.env.local` preview configuration; mock mode remains available by setting `VITE_CHAT_MODE=mock`. `.env.local` is ignored by Git.

Base URL: `VITE_CHATBOT_API_BASE_URL` (example: `http://127.0.0.1:8000/api/v1`). JSON requests and responses use UTF-8.

## Send a message

`POST /chat/messages/`

Request:

```json
{
  "message": "How do I submit an assignment?",
  "language": "en",
  "queryLanguage": "mixed",
  "interface_context": "unspecified",
  "conversationId": "optional-existing-id"
}
```

Response:

```json
{
  "conversationId": "conversation-id",
  "message": "Answer grounded in reviewed source material.",
  "language": "en",
  "source": "llm",
  "relatedQuestions": [],
  "sourceReferences": [],
  "retrievalStatus": "matched",
  "responseMode": "llm"
}
```

`language` is the reply language (`en`, `sw`, or `mixed`). Optional `queryLanguage` can be `en`, `sw`, or `mixed` to let the backend interpret a Kiswahili or code-switched query while replying in the selected UI language. `conversationId` may be omitted for a new conversation. The shared TypeScript types are in `src/types/chat.ts`.

`interface_context` is `student`, `teacher`, `administrator`, or `unspecified`. It selects the role metadata used for general help retrieval only; it is not identity or permission evidence. The response includes source references, a retrieval status, and response mode (`llm`, `retrieval_fallback`, or `fallback`).

`GET /api/v1/knowledge/status/` reports indexed/reviewed document and chunk counts and whether optional LLM/embedding configuration is present. It does not expose secrets. Knowledge source ingestion and approval are described in [`KNOWLEDGE_INGESTION_REPORT.md`](KNOWLEDGE_INGESTION_REPORT.md) and [`RAG_AND_LLM.md`](RAG_AND_LLM.md).

## Feedback

`POST /api/v1/chat/feedback/` — implemented payload: `conversationId`, `messageId`, `rating` (`helpful` or `not_helpful`), and optional `comment`.

## Unanswered questions

Unanswered-question collection is not implemented.

## Health

`GET /api/v1/health/` — implemented readiness response: `{ "status": "ok", "mode": "demo" }`.

## Separate translation from service interpretation

`POST /api/v1/lexicon/interpret/` requires authentication and accepts:

```json
{
  "query": "Grades",
  "language": "en",
  "request_type": "translation",
  "target_language": "sw"
}
```

Translation requests return a stored equivalent and its `translationStatus`; the backend leaves missing translations blank and identifies proposed text. Service requests use `request_type: "service"` and return an intent, service area, source path, and `retrieval: "separate_step_required"`. This endpoint does not retrieve personal records or answer the service question.

The API uses authentication, CORS restrictions, throttling, validation, and a standard error envelope. Current development authentication is synthetic only. Production SSO and privacy decisions require DMI approval.
