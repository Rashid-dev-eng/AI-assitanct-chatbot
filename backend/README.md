# DMI-DeLMS chatbot backend

Separate Django REST API for the React/Vite frontend. This package currently runs in synthetic demo mode. It does not connect to DMI Moodle or contain official records.

## Local Windows setup

From PowerShell in this `backend` directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_data
python manage.py check
python manage.py test
python manage.py runserver 127.0.0.1:8000
```

The current configuration uses SQLite for local development. The backend can instead use PostgreSQL by setting `DATABASE_URL` to a PostgreSQL connection string; set `DB_SSLMODE=require` for hosted databases. Back up and protect production database credentials. The requirements include `psycopg[binary]` for PostgreSQL.

Copy `backend/.env.example` to `backend/.env` and set `LLM_API_KEY` there to enable OpenAI. This ignored local file is loaded by Django; environment variables set by the process or deployment take precedence. Keep API keys server-side and out of frontend `.env.local`, source control, screenshots, and chat. The default model is `gpt-4.1-mini`; change `LLM_MODEL` only to a model available to your OpenAI API account. OpenAI API usage may incur charges.

In another PowerShell window at the project root, set the frontend to call this API:

```powershell
Set-Content .env.local "VITE_CHAT_MODE=api`nVITE_CHATBOT_API_BASE_URL=http://127.0.0.1:8000/api/v1"
npm run dev
```

The frontend uses a fixed development identity when Django `DEBUG` and `DEMO_AUTH_MODE` are enabled. This is only for local preview and shares one synthetic demo account. Do not deploy demo authentication. A production deployment requires DMI-approved SSO/session authentication and a server-side mapping from authenticated institutional identity to Moodle identity.

The preview page is a blank white page with a floating assistant launcher. The language defaults to ENG; closing clears the visible conversation and minimizing preserves it. The chatbot UI does not expose a user-selectable role; role filtering should come from authenticated server-side identity when institutional authentication is implemented.

## API and included demo data

- OpenAPI JSON: `GET /api/schema/`
- Interactive API docs: `GET /api/docs/`
- Health: `GET /api/v1/health/`
- Knowledge ingestion status: `GET /api/v1/knowledge/status/`
- Chat: `POST /api/v1/chat/messages/`
- Conversation list/detail/delete: `/api/v1/chat/conversations/`
- Reviewed knowledge search: `GET /api/v1/knowledge/search/?q=...&language=en`
- Sanitized integration state: `GET /api/v1/integration/status/`
- Research endpoints (staff only): `/api/v1/lexicon/`, `/api/v1/evaluation/...`
- Translation/service interpretation: `POST /api/v1/lexicon/interpret/`

`seed_demo_data` loads 42 exact terms from checked-in prototype UI files and the original prototype HTML backup. Those labels and many content examples are explicitly fictional/demo material, not verified live-site terms. It also loads three English/Kiswahili query pairs copied from the user's prompt; they are marked `proposed` and are not verified translations. Live learner-data intents return an unavailable notice; the API never fabricates assignment, quiz, course enrolment, or grade records.

## RAG sources and LLM

The source ingestion command is `python manage.py ingest_knowledge <source-folder>`. It supports `.md`, `.txt`, `.html`, `.htm`, and `.docx`, splits text into source-tracked chunks, optionally stores embeddings, and always imports as pending review. Images/PDFs are listed as unsupported in the JSON ingestion report; supply extracted text for those. Review sources in Django admin before setting the document status to Verified. See [`../docs/KNOWLEDGE_INGESTION_REPORT.md`](../docs/KNOWLEDGE_INGESTION_REPORT.md) for the source audit and [`../docs/RAG_AND_LLM.md`](../docs/RAG_AND_LLM.md) for provider configuration and response behavior.

An OpenAI-compatible LLM is optional. Configure backend environment variables from `backend/.env.example`; `LLM_API_KEY` and `LLM_MODEL` enable grounded response generation, and `EMBEDDING_MODEL` enables vector similarity. Without them, reviewed chunks use a clearly identified deterministic retrieval excerpt. No DMI page exports, verified DMI glossary, or official role matrix were present during this audit, so none are represented as indexed.

When an LLM is configured, it receives only the registered read-only functions `search_delms_knowledge` and `get_delms_integration_status`. The latter reports local adapter configuration only; it does not contact Moodle. No student-specific, teacher participant/grade, administrator, or write operation is registered. See [`../docs/API_INVENTORY.md`](../docs/API_INVENTORY.md) for methods, permissions, side effects, limits and missing integration confirmations, and [`../docs/RAG_AND_LLM.md`](../docs/RAG_AND_LLM.md) for tool registration guidance.

The initial bilingual term dataset and import format are documented in [`../docs/LEXICON_MAINTENANCE.md`](../docs/LEXICON_MAINTENANCE.md). It currently contains prototype source labels only; official screenshots/pages and validated translations have not been supplied.

## Configure Moodle only after DMI authorization

See [`../docs/MOODLE_INTEGRATION.md`](../docs/MOODLE_INTEGRATION.md). The adapter is disabled by default, accepts only an HTTPS endpoint and server-side token, and rejects function names outside its reviewed read-only candidate list. Configuration is reported as `configured_unverified` until tested against an authorized non-production DMI service. The adapter is not yet wired to live chat answers.

## Production readiness

This is a development backend foundation, not a deployment-ready institutional service. Before launch, DMI must approve hosting, SSO, data retention, privacy notice, PostgreSQL operations, HTTPS, security review, Moodle service/account scopes, and a non-production integration test. See [`../docs/SECURITY_AND_PRIVACY.md`](../docs/SECURITY_AND_PRIVACY.md).
