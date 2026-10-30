# Backend integration guide

The Django REST backend is implemented in [`../backend/`](../backend/). Follow its [README](../backend/README.md) to install dependencies, run migrations and start the API. The frontend remains on mock mode by default. To use the local API, set `VITE_CHAT_MODE=api` and `VITE_CHATBOT_API_BASE_URL=http://127.0.0.1:8000/api/v1` in `.env.local`, then restart Vite.

The current frontend request/response contract is documented in [`CHATBOT_API_CONTRACT.md`](CHATBOT_API_CONTRACT.md). API mode uses a fixed synthetic development identity and seeded synthetic examples. It is intended for local preview only.

The backend does not yet have DMI-approved SSO, does not contain official DMI student records, and does not call Moodle. For the information DMI ICT must provide before any live integration, see [`MOODLE_INTEGRATION.md`](MOODLE_INTEGRATION.md). Never place backend credentials or Moodle tokens in frontend `VITE_` variables.
