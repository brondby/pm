# Project Management App

## Project overview

This repository contains a local-first Project Management app with:

- FastAPI backend
- Next.js frontend
- SQLite persistence
- Real per-user accounts (signup/login/logout, server-side sessions)
- Multiple Kanban boards per user, with create/rename/archive/delete/switch
- Kanban board editing (rename columns, add/edit/delete cards, drag-and-drop, optional label/due date/assignee
  per card)
- AI sidebar integrated with OpenRouter for structured board operations (move/create/update/delete cards,
  rename columns)

Sign-in is a real account (not a shared demo credential), and each user's boards are private to them.

## Architecture

```text
+---------------------------+
|        Browser UI         |
|  Next.js (exported app)   |
|  - Board switcher          |
|  - Kanban board             |
|  - AI chat sidebar         |
+------------+--------------+
             |
             | HTTP (/api/*, /)
             v
+---------------------------+
|      FastAPI backend      |
|  - Auth (signup/login/     |
|    logout/sessions)        |
|  - Board CRUD + ownership  |
|  - AI orchestration        |
|  - Static frontend serve  |
+------------+--------------+
             |
             | sqlite3
             v
+---------------------------+
|      SQLite database      |
|   backend/data/pm.db      |
|  - users                  |
|  - sessions                |
|  - boards (multi per user) |
+---------------------------+
             ^
             |
             | HTTPS
+---------------------------+
|        OpenRouter         |
|   model: gpt-oss-120b     |
+---------------------------+
```

## Tech stack

- Frontend: Next.js (App Router), TypeScript, Tailwind CSS, DnD Kit
- Backend: FastAPI, Python 3.12
- Database: SQLite (`sqlite3` stdlib, no ORM)
- Auth: `bcrypt` password hashing, opaque DB-backed session tokens (cookie-based)
- AI Provider: OpenRouter (`openai/gpt-oss-120b`)
- Packaging/runtime: Docker, docker compose
- Tests:
  - Backend: pytest
  - Frontend: Vitest + Testing Library + Playwright

## Installation (local development)

From project root:

1. Install Python dependencies (if running backend outside Docker):
   - `pip install -r backend/requirements.txt`
2. Install frontend dependencies:
   - `cd frontend && npm install`

## Docker

Build and run:

- Start:
  - `./scripts/start.sh` (Linux)
  - `./scripts/start.command` (macOS)
  - `scripts\start.bat` (Windows)
- Stop:
  - `./scripts/stop.sh` (Linux)
  - `./scripts/stop.command` (macOS)
  - `scripts\stop.bat` (Windows)

Or use compose directly:

- `docker compose build`
- `docker compose up`

App is served by FastAPI at `http://localhost:8000`.

## Environment variables

Set these in `.env` (project root):

- `OPENROUTER_API_KEY` (required for AI chat)
- `AI_MODEL` (optional, default `openai/gpt-oss-120b`)
- `AI_TIMEOUT_SECONDS` (optional, default `20`)
- `AI_MAX_TOKENS` (optional, default `1200`)
- `PM_DB_PATH` (optional, default `backend/data/pm.db`)

## OpenRouter setup

1. Create an OpenRouter account and API key.
2. Add to `.env`:
   - `OPENROUTER_API_KEY=your_key_here`
3. Ensure the selected model is available:
   - `AI_MODEL=openai/gpt-oss-120b` (default already set in backend code)

If key is missing or OpenRouter is unavailable, the app returns friendly AI error messages and preserves board
state.

## Features

- Real accounts: signup/login/logout with bcrypt-hashed passwords and server-side sessions (httpOnly cookie)
- Multiple boards per user: create, rename, archive/unarchive, delete (with confirmation), switch between them
- Board data is private per account - one user can never read or write another user's boards
- Column rename, card add/edit/delete, drag-and-drop move
- Optional card metadata: label, due date, assignee - collapsed by default so quick card creation is unaffected
- AI sidebar that can move/create/update/delete cards (including setting label/due date/assignee) and rename
  columns, in one message
- Friendly handling for invalid AI output and network/auth errors (no raw backend errors surface to the UI)
- Chat UX polish: loading indicator, Enter to send/Shift+Enter newline, send disabled while waiting

## Documentation

- `AGENTS.md` - business requirements, technical decisions, coding standards
- `CLAUDE.md` - architecture reference for AI coding assistants working in this repo
- `docs/PLAN.md` - full phased build history (Parts 1-15) and the future roadmap
- `docs/DB_SCHEMA.md` - database schema and board JSON contract

## Future improvements

See `docs/PLAN.md`'s "Recommended future roadmap (v2)" section for the full list. Highlights: hosted/
multi-tenant deployment, real-time collaboration/presence, richer AI planning controls (operation preview
before applying), and observability (metrics, tracing, error dashboards).
