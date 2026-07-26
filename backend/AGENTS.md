# Backend agent guide

## Purpose and current state

- Framework: FastAPI.
- Runtime: Python 3.12 (containerized in Docker).
- Current UI serving model: backend serves statically exported Next.js files from `backend/static` at `/`.
- Existing API endpoints:
  - `GET /health`
  - `GET /api/sample`

## Database modeling (Part 5)

- Database: SQLite (stdlib `sqlite3`, no ORM).
- Core data module: `backend/db.py`.
- Default DB location: `backend/data/pm.db` (outside static assets), overridable via `PM_DB_PATH`.
- Schema:
  - `users` table with unique `username` and `password_hash` (no plaintext password field).
  - `boards` table with one-board-per-user (`UNIQUE(user_id)`) and FK to `users(id)`.
  - `board_data` stored as JSON text.
- Foreign keys are enabled per connection via `PRAGMA foreign_keys = ON`.

MVP auth boundary for Part 5:
- Do not add authentication routes or password verification logic in this phase.

## Code organization

- `backend/main.py`: app creation, static file mounting, scaffold routes.
- `backend/db.py`: DB path resolution, connection/init helpers, board JSON validation, basic CRUD helpers.
- `backend/tests/test_main.py`: endpoint scaffold tests.
- `backend/tests/test_db.py`: Part 5 DB schema/constraint/validation/CRUD tests using temporary DB files.

## Constraints for future backend work

- Keep MVP implementation simple and avoid over-engineering.
- Preserve separation of concerns: data access in `db.py`, API handlers in route modules.
- Do not serve database files from static directories.
- Keep tests deterministic by using temporary SQLite files.