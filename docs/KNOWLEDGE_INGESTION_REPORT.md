# Knowledge source audit and ingestion status

Audit date: 2026-10-29

## Available material inspected

- Existing frontend React/TypeScript files and `src/data/courses.ts`.
- `backup/index.original.html`, the checked-in prototype backup.
- Existing backend models, lexicon seed, API, and project documentation.
- The user-supplied master prompt, which names example interface labels and service areas.

These materials identify useful terminology, but the checked-in frontend and backup are demonstration UI, not exports from the live DMI DeLMS. The prompt's examples are research leads, not source records. The existing lexicon remains explicitly marked as prototype-derived or proposed.

## Missing authoritative sources

- Extracted text or page exports from https://elms.dmi.ac.tz/.
- Screenshots or PDF captures of student, teacher, and administrator pages.
- Approved English–Kiswahili glossary/reviewer sign-off.
- Confirmed DMI navigation paths, official response references, and role-access matrix.

No live-site crawl or screenshot OCR was performed. No content has therefore been marked as verified or claimed as ingested from the official platform.

## Current ingestion result

There are no authoritative source files in the checkout to index. The ingestion workflow is implemented, but the knowledge base must remain empty/pending until material is supplied and reviewed. `GET /api/v1/knowledge/status/` reports database counts at runtime.

Use the backend command below with a folder containing supplied source files. Supported text extraction formats are Markdown, TXT, HTML, and DOCX. PDF and image files are reported as skipped; provide reviewed extracted text for them. Every newly imported document and chunk is marked pending review and cannot affect answers until a reviewer approves it in Django admin.

```powershell
cd backend
python manage.py ingest_knowledge ..\knowledge_sources
```

Optional per-file metadata: create `filename.ext.metadata.json` beside a source. Supported keys: `document_id`, `title`, `language` (`en`, `sw`, or `mixed`), `source_url`, `provenance`, `document_version`, `canonical_topic`, `interface_role`, and `allowed_roles` (for example `['teacher']`). Keep source provenance precise. Approval is a separate reviewer action in Django admin; the reviewer name and review timestamp are saved at approval.

The command writes `ingestion-report.json` in the source directory. It reports indexed files, chunk counts, duplicate skips, unsupported files, extraction failures, and the pending-review status. Embeddings are added to chunks when an embedding model is configured; keyword retrieval remains available if not.
