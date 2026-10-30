# Security and privacy notes

## Implemented safeguards

- The API uses a server-authenticated principal. Demo identity is a fixed development principal; user-supplied headers and chat context cannot select identity or role.
- Conversation reads, deletion, and feedback are scoped to the authenticated owner. Audit records capture event metadata without chat text.
- Moodle credentials are server-side only. The REST adapter requires HTTPS/TLS verification, disallows redirects, bounds timeouts/retries, filters function names through a read-only allowlist, and sanitizes failures.
- Synthetic knowledge is labeled as synthetic. Only verified, reviewed, unexpired knowledge entries are returned as institutionally verified. Live personal-record intents do not invent values.
- The model can call only the explicit read-only tool registry. Tool names/arguments are allowlisted and validated, tool rounds and calls are bounded, repeated calls are rejected, and audit events store tool name/outcome only. No learner-record or write tool is registered.
- Interface context sent by the browser is a topical hint only. Tool permissions and restricted knowledge use the authenticated server principal; request fields cannot provide a user ID or role grant.
- Request validation, API throttling, CORS allowlisting, secure-cookie/HSTS production settings, and an OpenAPI schema are configured.

## Required before institutional deployment

1. Replace demo auth with DMI-approved SSO, enforce CSRF/session or an approved token model, map identities server-side, and test role/capability boundaries.
2. Set a strong `DJANGO_SECRET_KEY` and `DJANGO_DEBUG=false`; configure exact `DJANGO_ALLOWED_HOSTS`, HTTPS proxy settings, CORS origins, secure cookies, and TLS.
3. Use managed PostgreSQL with backups, least-privilege DB credentials, encryption at rest/in transit, monitoring, migration/recovery procedures, and restricted network access.
4. Obtain DMI security/privacy approval for purpose limitation, notice/consent where required, retention/deletion, data-subject requests, audit access, incident response, and any AI/LLM processing. No external LLM provider is configured in this environment.
5. Review logs and observability to ensure no passwords, Moodle tokens, raw learner records, or unnecessary chat text are captured. Define and verify retention jobs and backup retention.
6. Complete dependency/SAST review, security testing, load/rate-limit testing, accessibility review, and an authorized non-production Moodle test before release.

The demo configuration is not suitable for public or production deployment. The project currently contains no official DMI Moodle data or credentials.
