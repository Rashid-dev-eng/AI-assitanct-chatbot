# Moodle integration handoff

## Current state

The backend contains a disabled-by-default adapter for Moodle's REST web-service API. It has not connected to `https://elms.dmi.ac.tz`, and the project has no DMI-issued API token, approved test account, or confirmed Moodle service configuration. No Moodle account data has been accessed. A configured adapter reports `configured_unverified`; it does not claim a successful connection. Live chatbot lookups remain disabled even when adapter configuration is present.

Moodle administrators control web-service enablement, custom services, functions, and capabilities. DMI ICT must approve this integration and provision credentials. Moodle's developer documentation describes [external services](https://moodledev.io/docs/5.0/apis/subsystems/external), and MoodleDocs describes [enabling web services for users](https://docs.moodle.org/500/en/How_to_enable_web_services_for_ordinary_users). Candidate API names can be cross-checked against Moodle's [web-service API function list](https://docs.moodle.org/dev/Web_service_API_functions). The target DMI Moodle version may differ, so these references do not confirm availability at DMI.

## Request from DMI ICT

Ask the authorized DMI Moodle administrator to provide through an approved secret-sharing channel:

1. A non-production Moodle URL/version and confirmation that REST web services are enabled.
2. A dedicated, least-privilege service account and a custom external service containing only explicitly approved read functions.
3. A short-lived or revocable token delivered directly to the deployment secret manager (never commit it or paste it into frontend configuration, tickets, or chat).
4. Written approval for the exact learner fields, purposes, user identity mapping, retention, and environments in scope.
5. Confirmed function names, required parameters, expected response shape, user/capability requirements, rate limits, and a test plan with test accounts.
6. The DMI-approved authentication/SSO mechanism. A browser-supplied Moodle user ID or request header is not proof of identity.

Potential read-only candidates for DMI to review are site info, the authenticated user's courses, course contents, assignment summaries/submission status, quiz summaries, and course-grade reports. Each has to be independently approved and checked against the target version, service definition and account capabilities. Do not enable any write function.

## Adapter configuration

Only after approval, place values in the backend's protected deployment environment or secret manager:

```text
MOODLE_ENABLED=true
MOODLE_REST_URL=https://<DMI-approved-host>/webservice/rest/server.php
MOODLE_SERVICE_TOKEN=<secret-manager-injected-token>
MOODLE_FUNCTIONS_JSON={"site_info":"core_webservice_get_site_info"}
```

Start with only a non-production site-info smoke test. Add one operation mapping at a time after reviewing the exact response fields and authorization. The adapter requires HTTPS, verifies TLS certificates, sends the token in a POST body, disallows redirects, uses bounded timeouts/retries, rejects non-allowlisted functions, and returns sanitized errors. Never log tokens or raw learner payloads.

Before live chat handlers are enabled, implement a server-side institutional-user-to-Moodle-user mapping and endpoint-specific validation/redaction. Grade, assignment and submission data must only be fetched for the authenticated learner and should not be persisted in chatbot conversation storage. Confirm that rules with DMI privacy/security staff. Until then the chatbot returns a clear no-live-records response.
