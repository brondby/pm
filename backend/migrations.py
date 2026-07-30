"""One-time, idempotent data migrations run at startup.

Each migration prints the resolved DB path and writes a timestamped backup
before making any change, but only when there is actually something to
migrate, so a normal startup on an already-migrated database is a silent
no-op with no backup churn. Backup filenames include microseconds so two
migrations run back-to-back in the same startup never collide.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import auth

# Sentinel written for every auto-created user prior to Part 11 (see
# ``main.py``'s pre-auth ``_ensure_user_and_board``). Any row still holding
# this value has never had a real password set.
LEGACY_PASSWORD_HASH = "mvp_dummy_password_hash"

# The MVP's hardcoded demo password - used so pre-existing local logins keep
# working unchanged after the upgrade.
LEGACY_DEMO_PASSWORD = "password"


def backup_database(db_path: Path) -> Path | None:
    """Copy the DB file to a timestamped backup. Returns ``None`` if there's no file yet."""
    if not db_path.exists():
        return None

    # Microsecond precision so two migrations run in the same startup never
    # collide on the same backup filename.
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    backup_path = db_path.with_name(f"{db_path.name}.{timestamp}.bak")
    shutil.copy2(db_path, backup_path)
    return backup_path


def upgrade_legacy_password_hashes(connection: sqlite3.Connection, db_path: Path) -> None:
    """Replace the pre-Part-11 sentinel password hash with a real bcrypt hash.

    Matches on the hash value (not on a specific username) so it also covers
    any other demo accounts auto-created by hitting the old
    ``/api/board/{username}`` routes before real auth existed.
    """
    legacy_rows = connection.execute(
        "SELECT id FROM users WHERE password_hash = ?", (LEGACY_PASSWORD_HASH,)
    ).fetchall()

    if not legacy_rows:
        return

    print(f"[migrations] Database path: {db_path}")
    backup_path = backup_database(db_path)
    print(f"[migrations] Backed up database to: {backup_path}")

    real_hash = auth.hash_password(LEGACY_DEMO_PASSWORD)
    connection.execute(
        "UPDATE users SET password_hash = ? WHERE password_hash = ?",
        (real_hash, LEGACY_PASSWORD_HASH),
    )
    connection.commit()


def _boards_table_needs_rebuild(connection: sqlite3.Connection) -> bool:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(boards)").fetchall()}
    # Pre-Part-13 schema has no ``name``/``is_archived`` columns and a
    # UNIQUE(user_id) constraint (one board per user). Presence of ``name``
    # is enough to tell the two schemas apart.
    return "name" not in columns


def rebuild_boards_table(connection: sqlite3.Connection, db_path: Path) -> None:
    """Migrate ``boards`` from one-per-user to multi-board.

    SQLite can't drop a column-level UNIQUE constraint via ALTER TABLE, so
    this rebuilds the table: create the new shape, copy every existing row
    over (defaulting ``name`` to "My Board", ``is_archived`` to 0 - so no
    board or card data is lost), drop the old table, and rename the new one
    into place. All existing rows get preserved; only the schema changes.
    """
    if not _boards_table_needs_rebuild(connection):
        return

    print(f"[migrations] Database path: {db_path}")
    backup_path = backup_database(db_path)
    print(f"[migrations] Backed up database to: {backup_path}")

    # FK pragma changes are no-ops inside a transaction, so this must run
    # before BEGIN. The boards->users FK would otherwise block the rebuild.
    connection.execute("PRAGMA foreign_keys = OFF")

    connection.executescript(
        """
        BEGIN IMMEDIATE;

        CREATE TABLE boards_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            board_data TEXT NOT NULL,
            is_archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
            updated_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        INSERT INTO boards_new (id, user_id, name, board_data, is_archived, created_at, updated_at)
        SELECT id, user_id, 'My Board', board_data, 0, created_at, updated_at
        FROM boards;

        DROP TABLE boards;

        ALTER TABLE boards_new RENAME TO boards;

        COMMIT;
        """
    )

    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(
            f"Boards table migration left {len(violations)} dangling foreign key(s); "
            f"restore from the backup at {backup_path} and investigate before retrying."
        )

    connection.execute("PRAGMA foreign_keys = ON")


def run_migrations(connection: sqlite3.Connection, db_path: Path) -> None:
    upgrade_legacy_password_hashes(connection, db_path)
    rebuild_boards_table(connection, db_path)
