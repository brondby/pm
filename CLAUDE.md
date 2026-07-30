# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A local-first Project Management app: Next.js frontend + FastAPI backend + SQLite, packaged into a single
Docker container, with an AI sidebar (OpenRouter) that edits Kanban boards via structured operations. See
`AGENTS.md` for business requirements and `docs/PLAN.md` for the phased build history (Parts 1-15, all
complete per `git log`).

Real per-user accounts, multiple boards per user with full lifecycle management (create/rename/archive/
delete/switch), and optional card metadata (label/due date/assignee) all landed in Parts 11-14. The only
remaining MVP-style constraint is deployment shape: local, single-container Docker only (see `docs/PLAN.md`
Part 15 "Recommended future roadmap" for what's deliberately out of scope today).

## Commands

### Frontend (`cd frontend`)

```bash
npm install
npm run dev          # dev server
npm run build         # production build (static export via `output: "export"`)
npm run lint
npm run test:unit          # vitest run
npm run test:unit:watch    # vitest watch
npm run test:e2e           # playwright (builds+serves frontend/out automatically)
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
`backend/data/pm.db`. One test (`test_container_root_integration.py`) is skipped by default; it builds and
runs the real Docker image and only executes when `RUN_CONTAINER_INTEGRATION_TESTS=1` is set.

### Docker (full stack)

```bash
./scripts/start.sh   # or start.command (macOS) / start.bat (Windows)
./scripts/stop.sh     # or stop.command / stop.bat
# equivalent to:
docker compose build && docker compose up
```

Serves the app at `http://localhost:8000`. Requires `OPENROUTER_API_KEY` in a root `.env` file for the AI sidebar
to work (chat gracefully degrades to an error message if missing).

## Architecture overview

### Request flow

Single FastAPI app (`backend/main.py`) serves both the API and the statically-exported Next.js build:

- `Dockerfile` builds the frontend (`next build` with `output: "export"`) and copies `frontend/out/` into
  `backend/static/` before the Python image is assembled. Outside Docker, `backend/static/` may be stale/absent.
- Route mount order in `main.py` matters: `/_next` and `/static` are mounted first, explicit API routes are
  declared next, and `StaticFiles(..., html=True)` is mounted at `/` **last** so it doesn't shadow the API routes.
- There is no reverse proxy or separate frontend server in production — the frontend always talks to same-origin
  `/api/*` routes.

### Authentication flow

Real per-user accounts with server-side sessions (Part 11), not the original hardcoded MVP credential:

- `backend/auth.py`: `hash_password`/`verify_password` via `bcrypt`; `create_session`/`get_session_user`/
  `delete_session` manage a DB-backed `sessions` table.
- Sessions are opaque `secrets.token_urlsafe(32)` tokens (not JWT), delivered as an `httpOnly`, `SameSite=Lax`
  cookie (`secure=False` — local HTTP-only Docker), flat 30-day expiry, no sliding renewal, no login rate
  limiting. No CSRF token is needed: `SameSite=Lax` already blocks the cookie on cross-site subrequests, and no
  mutating route accepts `GET`.
- Routes: `POST /api/auth/signup` (409 on duplicate username), `POST /api/auth/login` (identical response
  shape for "unknown username" and "wrong password" — no enumeration), `POST /api/auth/logout` (deletes the
  session row server-side, real revocation, not just a cookie clear), `GET /api/auth/me` (current username or
  401).
- `get_current_user` (a FastAPI dependency in `main.py`) resolves the session cookie to a user on every
  `/api/boards*` and `/api/auth/me` request; missing/invalid/expired session -> 401.
- Frontend (`app/page.tsx`): real signup/login forms; on mount, calls `GET /api/auth/me` to rehydrate session
  state from the cookie (no client-side session storage of credentials). Logout calls `POST /api/auth/logout`.

### Board lifecycle

Each user may own any number of boards (Part 13 removed the earlier one-board-per-user constraint):

- `backend/db.py`: `create_board`, `list_boards` (metadata only — `id`/`name`/`is_archived`/timestamps, no
  `board_data`, to keep the list endpoint cheap), `get_board`, `update_board_data`, `patch_board` (rename
  and/or archive/unarchive), `delete_board` (hard delete). Every one of these enforces ownership **in its SQL**
  (`WHERE id = ? AND user_id = ?`), not as a separate check — a missing board and a board owned by someone else
  are indistinguishable from the caller's side, both surfacing as 404 (never 403) via `main.py`'s
  `_get_owned_board_or_404`.
- Routes: `GET/POST /api/boards`, `GET/PUT/PATCH/DELETE /api/boards/{id}`, `POST /api/boards/{id}/chat` — all
  behind `get_current_user`.
- Frontend: `components/BoardWorkspace.tsx` owns the board list and active-board selection; `pickDefaultBoardId`
  always excludes archived boards, so an archived board can never silently become the active one. Zero boards
  and "every board is archived" are both first-class empty states (never auto-creates a replacement board — a
  new board only appears from an explicit user action). `components/BoardSwitcher.tsx` provides the
  create/rename/archive-toggle/two-step-confirm-delete UI.
- The old, unauthenticated `/api/board/{username}*` routes (which trusted a `username` path param with no
  verification) were removed entirely in Part 13 — there is no compatibility shim.

### AI sidebar (`backend/ai/`)

The AI never receives or returns a full replacement board — only a `reply` string plus a list of typed
**operations**, which is deliberately safer/cheaper than round-tripping the whole board:

1. `prompt_builder.py` builds a system prompt (JSON-only, operations-only contract) and a user prompt embedding
   the current board JSON + the user's message. Supported operation types: `move_card`, `rename_column`,
   `create_card` (optionally sets `label`/`due_date`/`assignee`), `update_card` (changes an existing card's
   title/details/label/due_date/assignee — fields omitted from the operation are left untouched, so editing one
   field never wipes the others; passing `null` for a metadata field clears it), `delete_card`.
2. `openrouter_ai.py` (`request_openrouter`) calls OpenRouter (`OPENROUTER_API_KEY`, model configurable via
   `AI_MODEL`, default `openai/gpt-oss-120b`) and `parse_structured_output` extracts/validates the
   `{"reply": str, "operations": [...]}` JSON from the model's response (handles code-fence stripping; explicitly
   rejects a `"board"` key if the model tries to return a full board).
3. `operation_executor.py` (`execute_operations`) applies operations to a **deep copy** of the board, atomically:
   unsupported operation types are silently ignored, but any malformed supported operation raises and aborts the
   whole batch (no partial writes). The result is only persisted (`should_persist=True`) if at least one
   operation actually applied, and it's re-validated with `validate_board_data` before being written.
4. `main.py`'s `chat_board_route` wires these together: board ownership is verified **before** the OpenRouter
   call (so a cross-user probe never burns an AI request before being rejected), and persists via
   `db.update_board_data` only on success.

### Database schema (`backend/db.py`, full contract in `docs/DB_SCHEMA.md`)

- `users`: unique `username`, `password_hash` (real `bcrypt` hash since Part 11).
- `sessions` (Part 11): opaque token, `user_id` FK, `expires_at`.
- `boards` (rebuilt in Part 13): `user_id` FK (no longer unique — multiple boards per user), `name`,
  `board_data` (JSON blob), `is_archived`, timestamps.
- `board_data` JSON contract: `columns[]` (unique ids, `cardIds[]`) + `cards{}` keyed by card id, every card
  placed in exactly one column, no orphaned references. Cards may optionally carry `label`/`dueDate`
  (`YYYY-MM-DD`)/`assignee` (Part 14) — a card predating these simply omits the keys, which is valid, so no DB
  migration was needed for that change. `validate_board_data()` is the single source of truth for board shape —
  both the `PUT` endpoint and AI-driven updates run through it before persisting.
- One-time **data** migrations (as opposed to new-table schema additions, which use `CREATE TABLE IF NOT
  EXISTS`) live in `backend/migrations.py` and run from `startup_event()` on every boot: upgrading the legacy
  demo password hash to a real `bcrypt` hash, and rebuilding `boards` from one-per-user to multi-board (SQLite
  can't drop a column-level `UNIQUE` via `ALTER TABLE`, so this is a create-copy-drop-rename). Each migration
  checks whether there's anything left to do before touching the database (idempotent no-op on a normal
  restart), and prints the resolved DB path plus a timestamped backup path before making any change.

### Frontend structure (`frontend/src`)

- `app/page.tsx` — real signup/login/logout; renders `BoardWorkspace` once authenticated.
- `components/BoardWorkspace.tsx` — owns the board list + active-board state; renders `BoardSwitcher` +
  `KanbanBoard`, or a first-class empty state (zero boards / all archived).
- `components/BoardSwitcher.tsx` — floating board list UI (select/create/rename/archive/delete).
- `components/KanbanBoard.tsx` — owns one board's card/column state, loads/saves via `lib/boardApi.ts`,
  drag-and-drop (dnd-kit), and the AI chat sidebar (`data-testid="ai-sidebar"`), with per-board chat history in
  `sessionStorage`.
- `components/KanbanColumn.tsx`, `KanbanCard.tsx` (card metadata badges + inline edit form),
  `KanbanCardPreview.tsx`, `NewCardForm.tsx` (metadata fields collapsed behind a "+ Add label, due date, or
  assignee" toggle so quick card creation is unaffected), `CardBadges.tsx` — presentational pieces.
- `lib/kanban.ts` — `Card`/`Column`/`BoardData`/`CardMetadata` types, pure board logic (`moveCard`,
  `applyCardMetadata`).
- `lib/authApi.ts`, `lib/boardsApi.ts`, `lib/boardApi.ts` — the only places that call backend `/api/auth/*`,
  `/api/boards` (list/create/rename/archive/delete), and `/api/boards/{id}*` (single-board read/write/chat)
  routes respectively; each validates response shapes before trusting them and maps network/HTTP failures to
  friendly error messages (never surfaces raw backend exceptions to the UI).

### Testing strategy

- Backend: `pytest` unit tests per module (`test_db.py`, `test_auth.py`, `test_operation_executor.py`,
  `test_prompt_builder.py`, `test_openrouter_ai.py`, `test_boards_migration.py`) plus integration tests against
  a real `TestClient` (`test_auth_routes.py`, `test_boards_routes.py`, `test_main.py`) covering the full
  ownership-isolation matrix (every verb, wrong-owner and no-cookie cases -> 401/404) and migration
  data-preservation/idempotency. All use temporary SQLite files, never the real `backend/data/pm.db`. One
  Docker-container integration test is opt-in via an env var.
- Frontend: Vitest + Testing Library for component/unit tests (one file per component/lib module), Playwright
  for e2e (`frontend/tests/*.spec.ts`) driving a real browser against the static-exported build with the
  backend mocked via `page.route`, covering auth, multi-board lifecycle, and card CRUD including metadata.

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
files before considering the work done. Never modify `backend/data/pm.db` directly, and never commit/push
without an explicit request.
