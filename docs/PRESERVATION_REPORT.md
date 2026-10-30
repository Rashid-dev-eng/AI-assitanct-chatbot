# Project audit and modification report

Audit date: 2026-10-29

## Existing architecture inspected

- React 18, TypeScript, Vite frontend; Django 5.2 and Django REST Framework backend.
- Existing chatbot widget, bilingual copy, mock/API service boundary, lexicon models/import, conversation/feedback APIs, reviewed-knowledge model, and disabled Moodle adapter.
- Backend had no source-file ingestion workflow, chunk model, vector similarity retrieval, configurable LLM provider, knowledge-status endpoint, or API-grounded source display.
- Frontend previously opened a synthetic login screen and dashboard before showing the assistant.

## Changes in this pass

- Replaced the preview route with a blank white page and floating chat launcher. The widget supports language and interface selection, typing/loading, retry, sources, Enter/Shift+Enter, close-and-clear, and minimize-with-history.
- Added source-tracked knowledge chunks, hybrid lexical/cosine retrieval, a reviewed-content filter, pending-review ingestion for Markdown/TXT/HTML/DOCX, duplicate detection, and a JSON ingestion report.
- Added optional OpenAI-compatible chat and embedding adapters. LLM answers are restricted to retrieved evidence and must cite returned source indices. If the LLM is not configured or fails, the response is explicitly a retrieved passage fallback; no evidence produces an honest fallback.
- Added public knowledge status counts and interface context as a retrieval filter, never as identity or authorization proof.
- Added setup, source-audit, ingestion and RAG documentation. Moodle remains disabled pending DMI ICT authorization.

## Source control and backup note

The project folder was not a Git repository. The existing `backup/index.original.html` is the only pre-existing backup found; it does not preserve the full React/Django project. The master prompt requested a pre-change backup, but no full source snapshot or version-control baseline was available before this modification. Do not treat this report as a claim that a full pre-change backup was made.

## Verified source limitations

No official DMI page exports, screenshots, extracted live-site text, validated Kiswahili glossary, or approved role-access matrix were present in the checkout. The checked-in interface and HTML backup are prototype sources. `docs/KNOWLEDGE_INGESTION_REPORT.md` records the missing sources. Ingested content starts pending review; no live DMI data is claimed.

## Known limitations

- The frontend production bundle and browser-level manual preview could not be run in this sandbox: Node's CLI exits with `EPERM` while traversing the Desktop profile path. TypeScript compiler diagnostics were run directly and passed.
- Existing React project has no frontend test runner. New RAG ingestion/retrieval tests were added to Django's suite.
- PDF/screenshot OCR is not implemented. Provide reviewed extracted text or DOCX/Markdown/TXT/HTML sources.
- OpenAI-compatible provider and vector embeddings are optional and not configured in this local project. The currently running backend reports no reviewed knowledge chunks and no configured LLM.
- Live Moodle integration, institutional SSO, official translations, and learner-specific data are not active.
