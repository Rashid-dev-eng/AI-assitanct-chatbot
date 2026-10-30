# Backend implementation map

The API is in `backend/`, separated from the existing Vite frontend.

- `config/`: Django settings, routing, OpenAPI and deployment configuration.
- `chatbot/models.py`: conversations/messages, reviewed knowledge and lexicon, feedback, evaluation datasets/runs, and metadata-only audit events.
- `chatbot/services/`: Unicode normalization, explainable bilingual intent matching, source-filtered chunk retrieval, optional cosine embeddings, bounded tool-calling agent loop, explicit safe tool registry, grounded LLM adapter, and safe response construction.
- `chatbot/management/commands/seed_demo_data.py`: synthetic-only seed examples; `purge_expired_conversations.py`: retention cleanup command.
- `chatbot/views.py`: versioned REST endpoints and ownership/role enforcement.
- `integrations/moodle/`: disabled HTTPS REST adapter with bounded retries and a read-only candidate allowlist.
- `chatbot/tests/`: semantic/API/ownership and mocked Moodle adapter checks.
- `backend/data/lexicon_initial.json`: source-referenced prototype vocabulary, with user-supplied Kiswahili examples marked proposed.
- `chatbot/management/commands/import_lexicon.py`: validated JSON/CSV import with duplicate detection and revision snapshots.
- `chatbot/management/commands/ingest_knowledge.py`: source-tracked Markdown/TXT/HTML/DOCX ingestion, chunking, pending-review status, duplicate reporting, and JSON ingestion report.
- `chatbot/services/tool_registry.py`: only reviewed knowledge search and sanitized local Moodle configuration status are callable; no learner-record or write tools are registered.
- `chatbot/services/agent.py`: model tool-call parsing, schema/allowlist enforcement, duplicate detection, iteration limits, citations and source mapping.
- `chatbot/models.py`: versioned knowledge documents/chunks; only reviewed, non-expired, role-appropriate chunks are eligible for retrieval.

Use [`../backend/README.md`](../backend/README.md) for Windows setup and [`MOODLE_INTEGRATION.md`](MOODLE_INTEGRATION.md) for DMI ICT handoff requirements. No Moodle call is made in the default demo setup.
See [`LEXICON_MAINTENANCE.md`](LEXICON_MAINTENANCE.md) for the source audit and missing live-site materials needed to complete official terminology.
