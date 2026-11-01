# Student Project Platform

The Student Project Platform is the deliberately small web application used by all SCC26 student teams in Weeks 3–4. It replaces the need to clone or understand the full production `quantum-platform` repository.

## Goals

Teach, with the least unnecessary code:

- an Astro-based user-facing frontend;
- a small authenticated backend/API;
- PostgreSQL-backed persistent application state;
- container images built by GitHub Actions and published to GHCR;
- deployment through this repository's GitOps path;
- health/readiness probes and Prometheus-friendly telemetry;
- a server-side Agent Control Plane client added in Week 4.

## Non-goals

Do not reproduce production research-programme management, PI workflows, SSH/WireGuard registration, JupyterHub integration, full MFA/account administration or the wider Quantum Platform data model.

## Minimal Week-3 product

```text
User
 ├── username/email
 └── display name

Team
 ├── name
 └── project slug
```

A team landing/dashboard page should prove authentication and persistence. Keep the UI polished but small.

## Week-4 extension

Add a server-side ACP client and a simple Agent Control Plane panel. The browser talks to the Student Platform; the Student Platform authenticates/authorises and talks privately to ACP.

Never place ACP signing keys, model credentials or database passwords in frontend JavaScript/localStorage/URLs.

## Suggested source layout

```text
platform/
├── frontend/        # Astro
├── api/             # small backend/auth/API
├── tests/
└── README.md
```

Exact starter implementation may evolve before the programme baseline is frozen. Preserve the contract even if framework details are adjusted.

## Crypty (Week 4): server-side ACP integration

`/crypty/` lets an allowlisted, signed-in user (own password set) run the **one fixed read-only diagnostic** through the Agent Control Plane and read its history, evidence and explanation. "Crypty" is the display name; records always name the real approved model.

- The browser only calls this app (`/api/crypty`, `/api/crypty/diagnostics`, `/api/crypty/tasks[/:id]`). It never sees ACP, the signing key or an assertion.
- For each call the backend signs a fresh **EdDSA assertion valid for 60 s** (ACP rejects anything over 90 s): `iss=quantum-platform`, `aud=agent-control-plane`, `sub=urn:quantum-platform:user:<agent_principal UUID>`, `tenant`, `scope=admin:diagnostics`, unique `jti` (`api/src/acp.js`). Checked against ACP's own PyJWT verification settings.
- `users.agent_principal` is a random UUID per user, so the ACP subject never reveals the username or row id; `/api/me` doesn't return it.
- ACP errors stay errors (401 → 502, 404, 429, 503 passed through; anything else → 502). A failed run is shown as failed, never as healthy.
- Configuration (Deployment env, not secrets): `ACP_URL`, `ACP_TENANT_ID`, `ACP_ALLOWED_USERS` (comma-separated usernames), optional `ACP_MODEL_LABEL`; `ACP_SIGNING_KEY_FILE` points at the mounted `acp-signing` SealedSecret. Without them the page says Crypty isn't configured.
