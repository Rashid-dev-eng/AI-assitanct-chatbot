# RAG and LLM operation

The chat answer pipeline keeps lexicon interpretation separate from evidence retrieval and answer generation:

1. A user may choose Student, Teacher, Administrator, or leave interface context unspecified. This only selects which reviewed help material to search; it is not proof of identity or authorization.
2. The service lexicon classifies the request. Unclear intent returns a clarification instead of inventing navigation.
3. With a configured LLM, the backend offers only the explicit registry in `chatbot/services/tool_registry.py`: `search_delms_knowledge` and sanitized `get_delms_integration_status`. The model can make zero, one, or multiple calls within a three-round/four-call limit. Arguments are schema checked, duplicate calls are stopped, results are bounded, and tool execution metadata is audited without storing arguments or result contents.
4. Knowledge search returns only active, reviewed, non-expired chunks whose role metadata allows the server-authenticated principal. The visitor's interface selection is a topical hint and cannot grant access. Search combines lexical overlap with cosine similarity when embeddings exist and applies a relevance threshold.
5. A configured OpenAI-compatible LLM can compose a concise answer from tool results and recent conversation turns. Tool output and conversation text are untrusted data. The model cannot access arbitrary URLs, SQL, shell, Moodle learner records, or write operations. Final factual answers must cite a valid returned source index.
6. Without an LLM credential, the assistant returns the best retrieved passage and labels the response `retrieval_fallback`. Without sufficient reviewed evidence it returns an honest fallback. The API returns source metadata, retrieval status, and response mode.

Ordinary greetings, acknowledgements, capability questions, and short follow-ups have local conversational responses and do not require RAG. When a chat model is configured, unmatched non-institutional questions may use a general conversational prompt without fabricated DMI citations. DMI-specific statements still require approved tool evidence. Without the model configuration, open-ended general questions have a limited local fallback; configure `LLM_API_KEY` and `LLM_MODEL` for free-form replies.

Set `LLM_API_KEY`, `LLM_MODEL`, and optionally `LLM_BASE_URL` and `EMBEDDING_MODEL` in the backend process environment. Do not put credentials in frontend variables. The provider uses `/chat/completions` and `/embeddings` routes under the configured base URL. Credentials are optional for deterministic local operation.

For local preview, run backend migrations, ingest provided sources, review them in Django admin, start Django on port 8000, then run Vite from the project root. The preview has no login form. Local Django demo authentication is fixed and development-only; production needs approved institutional authentication.

Moodle remains a separate, disabled adapter and no live records are queried. The integration-status agent tool only reads local sanitized configuration; it does not contact Moodle. A configured LLM does not make Moodle integration active. The full route and API audit is in [`API_INVENTORY.md`](API_INVENTORY.md).
