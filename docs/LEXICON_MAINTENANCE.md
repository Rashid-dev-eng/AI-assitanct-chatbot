# Bilingual semantic lexicon: source and maintenance

## What was available and what is missing

The initial dataset is traceable to text in this repository: `src/data/courses.ts`, `src/components/navigation/Sidebar.tsx`, `src/components/navigation/Topbar.tsx`, `src/pages/PageContent.tsx`, `src/pages/Dashboard.tsx`, `src/pages/LoginPage.tsx`, and `backup/index.original.html`. These are prototype frontend files. The backup itself calls its course, quiz, assignment, and account content demonstration/fictional. This dataset therefore records project UI terminology only; it does not claim that the labels, course titles, services, paths, or translations match the live DMI Moodle site.

The project does not contain the previously analyzed live DMI DeLMS screenshots, exported live Moodle pages/HTML, extracted page text, approved English–Kiswahili glossary, official role-to-page matrix, or reviewed navigation instructions. No official Kiswahili equivalents have been supplied in the project. In particular, there are no source terms for module/topic hierarchies or announcements beyond the prototype's generic navigation items, and no verified account, grade, or learning-material instructions. Please provide those source files/screenshots/text (and, if available, an approved terminology list and reviewer contact) so the lexicon can be completed against the real service. Until then, imported prototype terms stay `pending` and translations stay `missing` or `proposed`.

The three English/Kiswahili query pairs in the initial dataset come verbatim from the user’s development prompt. They are test inputs only and have `translation_status=proposed`, `verification_status=pending`, with provenance explicitly pointing to that prompt. They are not labeled as extracted UI text or official translations.

## Lexicon fields

`backend/data/lexicon_initial.json` is the current JSON dataset. Each concept can store its English canonical label, Kiswahili equivalent, English/Kiswahili/mixed expressions, synonyms, spelling variants, abbreviations, service area, UI page label, source navigation path, context, role restrictions, examples, intent, translation/source verification status, provenance, reviewer, date, and lexicon version. Empty Kiswahili fields are intentionally left empty where no reviewed term is available.

Allowed translation states are `missing`, `proposed`, `verified`, and `not_applicable`. `verified` translation imports require a Kiswahili equivalent, translation source, reviewer, and ISO date in `reviewed_at`. Institutional-source verification is a separate field; a term marked verified requires a source reference, reviewer, and review date. Admin edits and imports write versioned snapshots to `LexiconRevision`.

## Import and update

The importer accepts JSON `{ "version": "...", "entries": [...] }` and CSV with the same snake_case field names. Array-valued CSV cells must be JSON arrays, for example `"[\"my courses\", \"course list\"]"`. Canonical term, intent, service area, source reference, and provenance are required. Unknown fields, malformed arrays, missing provenance, duplicate normalized terms within a file, invalid status values, and unsubstantiated verified rows reject the full transaction before rows are written.

From `backend/` in PowerShell:

```powershell
python manage.py import_lexicon data\lexicon_initial.json
python manage.py import_lexicon data\lexicon_import_template.csv --update-existing --change-note "Reviewed against approved terminology source"
```

The first command is for an empty lexicon. Existing canonical/intent/language records are rejected unless `--update-existing` is specified. Updates create a revision snapshot; use a change note that names the source/review event. Never mark a translation verified until a qualified reviewer has checked it against an authoritative DMI source. For production, run the same command with the approved `DATABASE_URL` pointing to PostgreSQL.

Admin-managed changes also create revision snapshots. The history is viewable in Django admin under Lexicon revisions; entries remain pending until a reviewer confirms both terminology and context. Retain provenance when merging duplicates; do not silently replace source wording.

## Translation and service interpretation are separate

`POST /api/v1/lexicon/interpret/` accepts a query, input language, and explicit `request_type`:

- `translation` requires `target_language`. It returns a stored equivalent and its review status only. Missing/unverified translations remain blank or visibly proposed; the endpoint does not invent a translation.
- `service` maps the query to an intent, service area, and source path. It reports `retrieval=separate_step_required`; it does not answer a learner-specific request. Chat answer retrieval remains a separate step, and live learner records remain unavailable until the authorized Moodle integration is implemented.

The query matcher combines exact phrases, source-backed aliases, user-supplied proposed examples, conservative token overlap, and a small spelling-tolerance rule. Proposed and pending aliases may help classify a query, but cannot become verified answers. Ambiguous matches request clarification.

## Evaluation

The evaluation dataset includes each user-provided English and Kiswahili prompt example, plus separate synthetic translation and clarification cases. The user-supplied Kiswahili is unverified, so those cases measure intent mapping only until qualified reviewers validate the wording. Evaluation cases carry a source reference, safe-handling reference answer, and `is_synthetic` marker; these are not validated content-answer benchmarks for the live DMI platform.

Staff-only endpoints are `GET /api/v1/evaluation/cases/` and `POST /api/v1/evaluation/runs/`. Submit the full active dataset on each run with predicted intent, predicted service area, response correctness, optional translation correctness for translation cases, and clarification appropriateness for clarification cases. Metrics are stored separately: query interpretation accuracy, service mapping accuracy, response correctness, translation quality (only translation cases scored), and clarification appropriateness (only expected-clarification cases scored). Runs also report macro and per-intent precision/recall/F1.

Do not use the proposed examples as a final benchmark. Once official source text and reviewed reference translations/answers are supplied, create a new versioned dataset and preserve the old results for comparison.
