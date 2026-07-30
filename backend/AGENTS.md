# Backend agent guide

## Purpose and current state

- Framework: FastAPI.
- Runtime: Python 3.12 (containerized in Docker).
- UI serving model: backend serves statically exported Next.js files from `backend/static` at `/`.
- Full route list is documented in the `backend/main.py` module docstring; see `CLAUDE.md`'s Architecture
  overview for the auth flow, board lifecycle, and AI workflow this backend implements.

## Database (`backend/db.py`)

- Database: SQLite (stdlib `sqlite3`, no ORM).
- Default DB location: `backend/data/pm.db` (outside static assets), overridable via `PM_DB_PATH`.
- Schema: `users` (unique `username`, real `bcrypt` `password_hash`), `sessions` (opaque token, `user_id` FK,
  `expires_at`), `boards` (`user_id` FK, **not** unique - a user may own multiple boards, `name`, `board_data`
  JSON text, `is_archived`).
- Foreign keys are enabled per connection via `PRAGMA foreign_keys = ON`.
- One-time data migrations (as opposed to additive schema changes via `CREATE TABLE IF NOT EXISTS`) live in
  `backend/migrations.py` and run on every startup; see that module's docstring and `docs/DB_SCHEMA.md` for the
  backup/idempotency mechanics.

## Auth (`backend/auth.py`)

- `hash_password`/`verify_password` via `bcrypt`.
- `create_session`/`get_session_user`/`delete_session` manage the DB-backed `sessions` table (opaque token,
  flat 30-day expiry).
- Route handlers in `main.py` depend on `get_current_user`, which resolves the session cookie -> user, or 401.

## AI (`backend/ai/`)

- `prompt_builder.py`: builds the system/user prompts and the operations contract sent to the model.
- `openrouter_ai.py`: HTTP client for OpenRouter + structured-output parsing/validation.
- `operation_executor.py`: applies validated operations to a board copy, atomically.
- See `CLAUDE.md`'s "AI sidebar" section for the full request flow.

## Code organization

- `backend/main.py`: app creation, static file mounting, all API routes (auth, boards, AI chat, health/sample).
- `backend/db.py`: DB path resolution, connection/init helpers, board JSON validation (`validate_board_data`),
  user/session/board CRUD (ownership-scoped in SQL for every board operation).
- `backend/auth.py`, `backend/migrations.py`, `backend/ai/*.py`: see above.
- `backend/tests/`: one file per module/concern (see filenames) plus integration tests using `TestClient`
  against a temporary SQLite file. `test_container_root_integration.py` is skipped unless
  `RUN_CONTAINER_INTEGRATION_TESTS=1`.

## Constraints for future backend work

- Keep implementation simple and avoid over-engineering.
- Preserve separation of concerns: data access in `db.py`, session/password logic in `auth.py`, route handlers
  in `main.py`.
- Do not serve database files from static directories.
- Keep tests deterministic by using temporary SQLite files - never point a test at the real
  `backend/data/pm.db`.
- Every board-owning operation must enforce ownership in its SQL `WHERE` clause, not via a separate
  check-then-act step; a missing board and one owned by another user must both surface as 404, never 403.
- Any schema change that can't be expressed as an additive `CREATE TABLE IF NOT EXISTS` needs a migration in
  `backend/migrations.py` that prints the DB path and writes a timestamped backup before touching data, and is
  a no-op on an already-migrated database.
