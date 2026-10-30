# DMI DeLMS frontend

A React, TypeScript and Vite preview for the DMI DeLMS Assistant. The page is blank white apart from its floating chatbot launcher. It uses the Django API in the local ignored `.env.local`; the chatbot answers only from reviewed sources and does not access real Moodle records.

## Requirements

- Node.js 20.19 or later, or 22.12 or later
- npm 10 or later

## Windows startup

Open PowerShell in this folder and run:

```powershell
npm install
npm run dev
```

Open the local URL printed by Vite. To create and preview a production build:

```powershell
npm run build
npm run preview
```

The local API preview configuration is in `.env.local`. Start the backend as described in [`backend/README.md`](backend/README.md), then start Vite. The current backend status endpoint reports whether reviewed sources and optional LLM/embeddings are configured. At the time of this audit there were no reviewed knowledge chunks, and no official DMI source records were available.

## Project layout

- `src/components/chatbot/`: floating assistant UI
- `src/app/App.tsx`: blank preview page and chat state
- `src/services/chat/`: mock assistant and service selection
- `src/services/api/`: frontend client for the separate Django REST backend
- `src/services/storage/`: guarded legacy demo storage helpers
- `src/i18n/`: English and Kiswahili chatbot copy
- `src/styles/app.css`: chatbot styles and blank-page overrides
- `backup/index.original.html`: available original HTML backup (not a full source snapshot)
- `docs/`: architecture, API contract, integration notes and preservation report
- `backend/`: separate Django REST API with synthetic demo data and a disabled Moodle adapter

See [`docs/RAG_AND_LLM.md`](docs/RAG_AND_LLM.md) and [`docs/KNOWLEDGE_INGESTION_REPORT.md`](docs/KNOWLEDGE_INGESTION_REPORT.md) for evidence ingestion and source gaps.
