# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Local-first Project Management MVP: Next.js frontend + FastAPI backend + SQLite, packaged into a single Docker
container, with an AI sidebar (OpenRouter) that can edit the Kanban board via structured operations. See
`AGENTS.md` for full business requirements and `docs/PLAN.md` for the phased build plan (Parts 1-10, all complete
per `git log`).

MVP scope limits to keep in mind: hardcoded login (`user`/`password`, client-side only, no real auth/sessions),
one board per user, local Docker-only deployment.

## Commands

### Frontend (`cd frontend`)

```bash
npm install
npm run dev          # dev server
npm run build         # production build (static export via `output: "export"`)
npm run lint
npm run test:unit          # vitest run
npm run test:unit:watch    # vitest watch
npm run test:e2e           # playwright (needs a running server)
npm run test:all           # unit + e2e
```

Run a single unit test file: `npx vitest run src/lib/kanban.test.ts`.
Run a single e2e test: `npx playwright test tests/kanban.spec.ts`.

### Backend (from repo root)

```bash
pip install -r backend/requirements.txt
python -m pytest backend/tests
python -m pytest backend/tests/test_db.py -k some_test   # single test
```

Backend tests import via `backend.main` / `backend.db`, so run pytest from the repo root, not from `backend/`.
Tests use temporary SQLite files (via `PM_DB_PATH` monkeypatching) — never point tests at the real
`backend/data/pm.db`.

### Docker (full stack)

```bash
./scripts/start.sh   # or start.command (macOS) / start.bat (Windows)
./scripts/stop.sh     # or stop.command / stop.bat
# equivalent to:
docker compose build && docker compose up
```

Serves the app at `http://localhost:8000`. Requires `OPENROUTER_API_KEY` in a root `.env` file for the AI sidebar
to work (chat gracefully degrades to an error message if missing).

## Architecture

### Request flow

Single FastAPI app (`backend/main.py`) serves both the API and the statically-exported Next.js build:

- `Dockerfile` builds the frontend (`next build` with `output: "export"`) and copies `frontend/out/` into
  `backend/static/` before the Python image is assembled. Outside Docker, `backend/static/` may be stale/absent.
- Route mount order in `main.py` matters: `/_next` and `/static` are mounted first, explicit API routes are
  declared next, and `StaticFiles(..., html=True)` is mounted at `/` **last** so it doesn't shadow the API routes.
- There is no reverse proxy or separate frontend server in production — the frontend always talks to same-origin
  `/api/*` routes (see `frontend/src/lib/boardApi.ts`).

### Auth

Login is entirely client-side (`frontend/src/app/page.tsx`): credentials are checked against hardcoded
`user`/`password`, and the authenticated flag is persisted in `sessionStorage`. The backend has no session/auth
layer — `GET/PUT /api/board/{username}` and `POST /api/board/{username}/chat` trust the `username` path param
directly and auto-create the user/board row on first access (`_ensure_user_and_board` in `main.py`). Do not add
real authentication without an explicit request — the DB schema anticipates multi-user support, but auth wiring
is explicitly out of scope for the MVP.

### Data layer (`backend/db.py`)

- Raw `sqlite3` (no ORM). DB path resolves to `backend/data/pm.db`, overridable via `PM_DB_PATH`.
- `users` (unique `username`) and `boards` (`UNIQUE(user_id)` — exactly one board per user, `ON DELETE CASCADE`).
- Board state is stored as a single JSON blob per user. `validate_board_data()` enforces the contract documented
  in `docs/DB_SCHEMA.md`: `columns[]` with unique ids and `cardIds[]`, `cards{}` keyed by card id, every card
  placed in exactly one column, no orphaned references. This validator is the single source of truth for board
  shape — both the `PUT` endpoint and AI-driven updates run through it before persisting.

### AI sidebar (`backend/ai/`)

The AI never receives or returns a full replacement board — only a `reply` string plus a list of typed
**operations**, which is deliberately safer/cheaper than round-tripping the whole board:

1. `prompt_builder.py` builds a system prompt (JSON-only, operations-only contract) and a user prompt embedding
   the current board JSON + the user's message.
2. `openrouter_ai.py` (`request_openrouter`) calls OpenRouter (`OPENROUTER_API_KEY`, model configurable via
   `AI_MODEL`, default `openai/gpt-oss-120b`) and `parse_structured_output` extracts/validates the
   `{"reply": str, "operations": [...]}` JSON from the model's response (handles code-fence stripping; explicitly
   rejects a `"board"` key if the model tries to return a full board).
3. `operation_executor.py` (`execute_operations`) applies operations (`move_card`, `rename_column`, `create_card`,
   `delete_card`) to a **deep copy** of the board, atomically: unsupported operation types are silently ignored,
   but any malformed supported operation raises and aborts the whole batch (no partial writes). The result is
   only persisted (`should_persist=True`) if at least one operation actually applied, and it's re-validated with
   `validate_board_data` before being written.
4. `main.py`'s `chat_board` route wires these together and persists via `db.update_board` only on success.

`mock_ai.py` exists alongside the real OpenRouter client — check whether tests/routes should target the mock or
the live client when working in this area.

### Frontend structure (`frontend/src`)

- `app/page.tsx` — login gate + renders `KanbanBoard`.
- `components/KanbanBoard.tsx` — owns board state, loads/saves via `lib/boardApi.ts`, drag-and-drop (dnd-kit),
  and the AI chat sidebar (`data-testid="ai-sidebar"`), including a one-level undo for AI-driven changes.
- `components/KanbanColumn.tsx`, `KanbanCard.tsx`, `KanbanCardPreview.tsx`, `NewCardForm.tsx` — presentational
  pieces.
- `lib/kanban.ts` — `Card`/`Column`/`BoardData` types and pure board logic (e.g. `moveCard`).
- `lib/boardApi.ts` — the only place that calls backend `/api/board/*` routes; validates response shapes
  (`isBoardData`) before trusting them.

## Coding standards (from `AGENTS.md`)

- Use latest stable library versions and idiomatic patterns.
- Keep it simple — no over-engineering, no speculative features, no unnecessary defensive programming.
- No emojis, anywhere (code, docs, commit messages).
- When debugging, find the root cause with evidence before applying a fix — don't guess.
- Color palette (Tailwind CSS variables in `globals.css`): Accent Yellow `#ecad0a`, Blue Primary `#209dd7`,
  Purple Secondary `#753991`, Dark Navy `#032147`, Gray Text `#888888`.

## Working process

`docs/PLAN.md` is the execution source of truth, broken into approval-gated Parts. If asked to implement a new
feature in this repo, read `docs/PLAN.md` first, then propose a plan and wait for approval before writing code —
per `AGENTS.md`. After implementing, run the relevant tests and build, fix all errors, and summarize changed
files before considering the work done.
