# API inventory and agent tool audit

Audit date: 2026-10-29. This inventory describes code and configuration present in the repository; it does not imply that an external DMI service has been enabled or tested.

## Backend HTTP routes

All routes below are under `/api/v1/`, unless stated otherwise. Django REST Framework applies a 20 requests/minute anonymous and 40 requests/minute authenticated rate limit by default. In local `DEBUG` plus `DEMO_AUTH_MODE`, requests receive a fixed synthetic `preview` principal. That is development behavior only.

| Route | Method | Purpose and inputs | Auth / permissions | Side effects and status |
|---|---|---|---|---|
| `/health/` | GET | Database readiness | Public | Read-only; verified by database `SELECT 1`. |
| `/knowledge/status/` | GET | Ingestion, review, chunk, LLM and embedding counts/status | Public | Read-only; never includes secrets. |
| `/integration/status/` | GET | Sanitized Moodle adapter state | Authenticated | Read-only status; does not call Moodle or verify credentials. |
| `/chat/messages/` | POST | `message`, reply/query language, optional conversation ID and interface hint | Authenticated | Creates conversation if needed and stores user/assistant messages plus metadata audit event. Role hint is not identity or permission proof. |
| `/chat/conversations/` | GET | Current principal's conversation list | Authenticated, owner scoped | Read-only. |
| `/chat/conversations/{uuid}/` | GET, DELETE | Read or delete one owned conversation | Authenticated, owner scoped | DELETE permanently removes that conversation and messages. |
| `/feedback/` | POST | Rating/comment for an owned assistant message | Authenticated, owner checked | Creates feedback; unique feedback per user/message. |
| `/knowledge/search/` | GET | `q`, optional language | Authenticated | Read-only; reviewed knowledge only. |
| `/lexicon/` | GET | Lexicon entries | Staff/admin | Read-only. |
| `/lexicon/interpret/` | POST | Query, language, translation/service request type | Authenticated | Read-only classification/translation lookup; no Moodle call. |
| `/evaluation/cases/` | GET | Evaluation dataset | Admin | Read-only. |
| `/evaluation/runs/` | GET, POST | Read or submit evaluation results | Admin | POST records an evaluation run. |
| `/api/schema/`, `/api/docs/` | GET | OpenAPI schema and Swagger UI | Project config | Read-only schema/docs. |

The frontend's existing API client calls `/lexicon/interpret/`, `/chat/messages/`, and conversation DELETE when closing a chat. It does not call a DMI API directly.

## External/provider APIs and adapters

| API | Purpose and parameters | Auth / permissions | Timeout/retry | Verification and side effects |
|---|---|---|---|---|
| OpenAI-compatible `/chat/completions` | Optional grounded text generation; model, messages, bounded token count | Backend `LLM_API_KEY`; no browser secret | Configured 2–60 second timeout; no retry | Not configured in the audited environment. Provider and model must be configured by operator. No direct Moodle/database tools. |
| OpenAI-compatible `/embeddings` | Optional vector embeddings for supplied chunks and query text | Backend `LLM_API_KEY` | Configured 2–60 second timeout; no retry | Not configured. A keyword fallback remains available. |
| Moodle REST adapter | `POST` to configured HTTPS REST endpoint with `wsfunction`, token and scalar function parameters | Server-side token and approved function mapping; DMI permission/capability still required | Connect/read timeout configured; at most two attempts | Disabled by default and not wired to chat tools. A configured adapter is labelled `configured_unverified`. No call to `elms.dmi.ac.tz` has been verified. The implementation rejects redirects, verifies TLS, and redacts error payloads. |

The Moodle adapter has candidate function names in `integrations/moodle/adapter.py`: `core_webservice_get_site_info`, `core_enrol_get_users_courses`, `core_course_get_contents`, `mod_assign_get_assignments`, `mod_assign_get_submission_status`, `mod_quiz_get_quizzes_by_courses`, and `gradereport_overview_get_course_grades`. These are allowlist candidates only. The project does not contain DMI-confirmed function mappings, exact function argument contracts, service scopes, token, user-to-Moodle identity mapping, rate-limit confirmation, or non-production test results. They are not exposed as agent tools.

## Agent tool decision

Initially eligible read-only tools are limited to `search_delms_knowledge` (reviewed local knowledge retrieval) and `get_delms_integration_status` (sanitized adapter status). Both execute through a backend registry and return compact, source-aware data. They do not access learner records. Student grades/courses/submissions, teacher participants/grade reports, administrator data, and all write actions remain unavailable until DMI ICT confirms API functions, identity mapping, permissions, privacy scope, and a non-production test.

### Registering another tool

Add a fixed JSON schema, handler, least-privilege rule, timeout/retry classification, read/write class, and sanitized error path in `backend/chatbot/services/tool_registry.py`. Add it to the LLM's offered tool list only when its dependency is verified and permitted for the authenticated server principal. Never accept a URL, API function, user ID, or permission from model arguments. Add handler tests for valid arguments, malformed arguments, permission rejection, timeout, response redaction, and any side effects before enabling it.
