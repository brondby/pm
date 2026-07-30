# Part 5: SQLite schema and board JSON contract

## Database location

- Default path: `backend/data/pm.db`
- Override with env var: `PM_DB_PATH`
- The DB file is outside `backend/static` so it is never served as a static asset.

## Initialization strategy

- `backend/db.py` exposes `init_db()`.
- On first run, it creates parent directories and runs `CREATE TABLE IF NOT EXISTS`.
- No separate migration framework is used for MVP.

## Migration strategy (MVP)

- Schema changes are managed manually in `backend/db.py`.
- For MVP this is acceptable because the schema is small and local-only.
- If schema evolution grows, add versioned migrations in a later phase.
- As of Part 11, one-time **data** migrations (as opposed to new-table schema additions, which just use
  `CREATE TABLE IF NOT EXISTS`) live in `backend/migrations.py` and run from `startup_event()` on every boot.
  Each migration checks whether there's anything left to do before touching the database, so a normal startup
  after the migration has already run is a no-op. When a migration does have work to do, it prints the
  resolved DB path and writes a timestamped backup (`pm.db.<UTC-timestamp>.bak`, never overwriting a prior
  backup) before making any change.

## Tables and constraints

### `users`

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `username TEXT NOT NULL UNIQUE`
- `password_hash TEXT NOT NULL`
- `created_at TEXT NOT NULL DEFAULT STRFTIME(...)`

Rules:
- Username is unique.
- `password_hash` holds a real `bcrypt` hash as of Part 11 (previously a hardcoded sentinel value with no
  real verification). A startup migration (`backend/migrations.py`) upgrades any row still holding the old
  sentinel to a real hash of the MVP demo password, so existing local logins keep working unchanged.

### `sessions` (added Part 11)

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `token TEXT NOT NULL UNIQUE` — opaque `secrets.token_urlsafe(32)` value, stored raw (not hashed): the token
  already has 256 bits of entropy, so hashing it would add complexity without a meaningful security gain at
  this scale.
- `user_id INTEGER NOT NULL` (`FOREIGN KEY` -> `users(id) ON DELETE CASCADE`)
- `created_at TEXT NOT NULL DEFAULT STRFTIME(...)`
- `expires_at TEXT NOT NULL` — flat 30-day expiry from creation, no sliding renewal, no login rate-limiting.

Rules:
- A session is valid only if its token exists and `expires_at` is in the future; `backend/auth.py` enforces
  this on every lookup.
- Logout deletes the row outright (real revocation), not just a client-side cookie clear.
- Delivered to the browser as an `httpOnly`, `SameSite=Lax` cookie (`secure=False` since this app is local
  HTTP-only Docker; flip to `True` if TLS is ever introduced). No CSRF token is used — `SameSite=Lax` already
  blocks the cookie being attached to cross-site subrequests, which is the vector CSRF exploits, and no
  mutating route accepts `GET`.

### `boards`

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `user_id INTEGER NOT NULL` (no longer unique as of Part 13 - see below)
- `name TEXT NOT NULL` (added Part 13)
- `board_data TEXT NOT NULL` (JSON text)
- `is_archived INTEGER NOT NULL DEFAULT 0` (added Part 13)
- `created_at TEXT NOT NULL DEFAULT STRFTIME(...)`
- `updated_at TEXT NOT NULL DEFAULT STRFTIME(...)`
- `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`

Rules:
- As of Part 13, a user may own any number of boards (the earlier `UNIQUE(user_id)` constraint is gone).
- Board rows must reference a valid user (`FOREIGN KEY`).
- SQLite FK checks are enabled per connection with `PRAGMA foreign_keys = ON`.
- Every `/api/boards*` route enforces ownership directly in its SQL (`WHERE id = ? AND user_id = ?`); a
  missing board and a board owned by someone else are indistinguishable from the outside - both 404
  (`backend/main.py`'s `_get_owned_board_or_404`, and the `rowcount`-checked helpers in `backend/db.py`:
  `get_board`, `update_board_data`, `patch_board`, `delete_board`).
- No "last active board" column exists - the frontend defaults to the most recently updated non-archived
  board on load, or a first-class empty state if there is none (never auto-creates a replacement board; see
  `frontend/src/components/BoardWorkspace.tsx`).
- `GET /api/boards` returns metadata only (`id`, `name`, `is_archived`, `created_at`, `updated_at`) -
  `board_data` is only returned by the single-board routes, to keep the list endpoint cheap.

**Migration (Part 13)**: SQLite can't drop a column-level `UNIQUE` constraint via `ALTER TABLE`, so
`backend/migrations.py`'s `rebuild_boards_table()` rebuilds the table (create the new shape, copy every
existing row over with `name = 'My Board'` and `is_archived = 0`, drop the old table, rename the new one into
place) rather than altering it in place. Same pattern as the Part 11 migration: idempotency check first
(skips if `name` column already exists), prints the DB path, writes a timestamped backup before any change,
and toggles `PRAGMA foreign_keys` off/on around the rebuild (required since `boards` has an FK to `users`).
No board or card data is lost - every existing row is carried over as-is.

## Board JSON contract

Contract is aligned to the current frontend `BoardData` shape:

```json
{
  "columns": [
    {
      "id": "col-backlog",
      "title": "Backlog",
      "cardIds": ["card-1", "card-2"]
    }
  ],
  "cards": {
    "card-1": {
      "id": "card-1",
      "title": "Task title",
      "details": "Task details"
    }
  }
}
```

Validation rules in `validate_board_data()`:

- Root object must contain:
  - `columns` array
  - `cards` object
- Each column requires:
  - `id` non-empty string (unique across columns)
  - `title` non-empty string
  - `cardIds` array of non-empty strings
- Each card object requires:
  - key is card id (non-empty string)
  - `id` non-empty string and must match key
  - `title` non-empty string
  - `details` string
- Cross-reference rules:
  - every `cardIds` entry must exist in `cards`
  - each card appears in columns exactly once
  - no unplaced cards in `cards`

## Assumptions and limitations

- Passwords are represented as hashes via `password_hash` (no plaintext password column); real `bcrypt`
  verification landed in Part 11 via `backend/auth.py` and `/api/auth/*` routes.
- Sessions are DB-backed (`sessions` table), not JWTs, so logout is real revocation (see Part 11 above).
- As of Part 13, the old unauthenticated `/api/board/{username}*` routes are removed entirely, replaced by
  session-scoped `/api/boards*` routes with per-request ownership checks. The frontend (Parts 12-13) uses
  real accounts and real multi-board data end-to-end - there is no remaining trust-the-path-param behavior.
- No rate-limiting/lockout on login, flat 30-day session expiry, no CSRF token, hard delete instead of
  soft-delete-with-undo for boards - all deliberate simplicity choices for this local, single-container MVP.