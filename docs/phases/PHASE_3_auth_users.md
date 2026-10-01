# Phase 3 — Authentication, Roles & Audit

**Goal:** Real users with roles (operator / reviewer / admin), JWT login, API keys for machine clients, warehouse and station management, per-role data visibility, and a complete audit log.

**Read:** IMPLEMENTATION.md §7 (users, api_keys, warehouses, stations, audit_log) and §8 (role column).
**Branch:** `phase-3-auth-users`

## Tasks

- [ ] Deps: pyjwt, argon2-cffi.
- [ ] Settings: `jwt_secret` (required outside `env=dev`; dev auto-generates one and logs a warning), `jwt_ttl_hours=12`, `env`.
- [ ] `services/users.py`: create, update, deactivate, verify password, change password. `services/api_keys.py`: create (returns plaintext once, stores sha256), verify, revoke.
- [ ] `api/deps.py`: `get_current_principal` (Bearer JWT **or** `X-API-Key`), `require_role(*roles)`. Inactive users get 401. An API key acts as role `operator` with `source=api` uploads plus the legacy endpoints.
- [ ] Routers: `auth` (login, me, change-password) and `admin` (users, warehouses, stations, api-keys CRUD per §8).
- [ ] Apply role guards to every existing route per the §8 table. Visibility: operators list and see only their own uploads (403 on others), reviewers and admins see all.
- [ ] Audit: log login success and failure, upload, reanalyze, delete, review, and user, station, and key changes. Add `GET /admin/audit-log` (filterable, paginated).
- [ ] Remove the system-admin stub from `get_current_user`. Keep the `system` user only as the actor for worker-written records.
- [ ] CLI: `python -m vms.cli create-admin --email --name` (prompts for the password) and `seed-demo` (1 warehouse, 2 stations, 1 user per role with printed dev passwords; dev only).
- [ ] Simple login rate limiting: per email+IP, 10 failures per 15 min → 429 (in-memory is fine for now; note it in Known Issues).
- [ ] Tests: login ok and bad, expired token, role matrix (parametrized over every route × role → expected status), operator isolation, API-key flow + revocation, audit rows written, password never returned by any endpoint.

## Acceptance criteria

1. Every `/api/v1` route except `/health` and `/auth/login` returns 401 without credentials.
2. The role matrix test covers every route in §8.
3. `create-admin` + login + `/auth/me` works end to end.
4. Tests green.

## Out of scope

SSO/OAuth, password reset email, and multi-tenant (multi-company) separation.

## Handoff notes

Demo credentials created by `seed-demo` (dev only), the role matrix summary, any §8 changes.
