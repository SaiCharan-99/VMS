# AGENTS.md

Instructions for AI coding agents (Claude Code, Codex, Cursor, Copilot, etc.).

## Setting the project up for a user

Run the setup yourself; don't hand the user a list of commands.

1. `docker info` must succeed. If not, start Docker Desktop and wait for it.
2. Windows: `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`
   macOS/Linux: `bash scripts/setup.sh`
3. Check `http://localhost:<VMS_HTTP_PORT>/api/v1/health` returns `"status":"ok"`.
4. Tell the user the URL and the demo logins listed in README.md.

The script is idempotent and keeps an existing `.env`. Details: README.md → "Quick setup".

## Changing the code

Read `CLAUDE.md` first (conventions, commands, session protocol), then `PROGRESS.md`.

## Never

- Commit `.env`, `data/`, videos, or model weights (`*.pt`).
- Delete `data/`, `audit_results.db`, or Docker volumes (`docker compose down -v`) without the
  user's explicit OK: they contain audit records.
- Weaken the review-first rule: a missing barcode or poor video quality must never produce `pass`.
