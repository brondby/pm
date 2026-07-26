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

## Tables and constraints

### `users`

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `username TEXT NOT NULL UNIQUE`
- `password_hash TEXT NOT NULL`
- `created_at TEXT NOT NULL DEFAULT STRFTIME(...)`

Rules:
- Username is unique.

### `boards`

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `user_id INTEGER NOT NULL UNIQUE`
- `board_data TEXT NOT NULL` (JSON text)
- `created_at TEXT NOT NULL DEFAULT STRFTIME(...)`
- `updated_at TEXT NOT NULL DEFAULT STRFTIME(...)`
- `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`

Rules:
- Exactly one board per user (`UNIQUE(user_id)`).
- Board rows must reference a valid user (`FOREIGN KEY`).
- SQLite FK checks are enabled per connection with `PRAGMA foreign_keys = ON`.

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

- Passwords are represented as hashes via `password_hash` (no plaintext password column).
- Part 5 does not implement authentication routes or password verification logic.
- No auth/session/JWT logic is implemented in backend yet.
- No public board API routes are implemented in Part 5.