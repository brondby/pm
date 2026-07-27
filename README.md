# Project Management MVP (v1.0 Release Candidate)

## Project overview

This repository contains a local-first Project Management MVP with:

- FastAPI backend
- Next.js frontend
- SQLite persistence
- Kanban board editing (rename, add, delete, drag-and-drop)
- AI sidebar integrated with OpenRouter for structured board operations

The app supports a simple MVP sign-in flow (`user` / `password`) and stores one board per user.

## Architecture

```text
+---------------------------+
|        Browser UI         |
|  Next.js (exported app)   |
|  - Kanban board           |
|  - AI chat sidebar        |
+------------+--------------+
             |
             | HTTP (/api/*, /)
             v
+---------------------------+
|      FastAPI backend      |
|  - Board read/write API   |
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
|  - boards                 |
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
- Database: SQLite (`sqlite3` stdlib)
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

If key is missing or OpenRouter is unavailable, the app returns friendly AI error messages and preserves board state.

## Features

- Hardcoded MVP sign-in (`user` / `password`)
- Single Kanban board per user persisted in SQLite
- Column rename, card add/delete, drag-and-drop move
- AI sidebar that can perform multiple board operations in one message
- AI result summaries with per-operation feedback
- Friendly handling for invalid AI output
- One-level Undo for the most recent AI-driven board change
- Chat UX polish:
  - timestamps
  - loading indicator
  - Enter to send, Shift+Enter newline
  - send disabled while waiting
  - auto-scroll to latest message

## Screenshots

Placeholder: add release screenshots here.

## Future improvements

- Real authentication and sessions
- Multi-board support per user
- Richer AI planning controls and operation preview
- Collaboration and presence
- Background jobs / retry policies for AI tasks
- Observability (metrics, tracing, error dashboards)