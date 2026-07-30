"""SQLite data layer: users, sessions, and multi-board CRUD.

* create/open SQLite database
* initialize schema for users, sessions, and boards (multiple per user, Part 13)
* validate board JSON contract
* board CRUD helpers enforce per-user ownership directly in their SQL ``WHERE`` clauses
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "pm.db"

_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS boards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    board_data TEXT NOT NULL,
    is_archived INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""


def resolve_db_path(db_path: str | Path | None = None) -> Path:
    """Resolve the database path, defaulting to backend/data/pm.db.

    Priority:
    1. Explicit ``db_path`` argument
    2. ``PM_DB_PATH`` environment variable
    3. ``backend/data/pm.db``
    """
    if db_path is not None:
        return Path(db_path)

    env_db_path = os.getenv("PM_DB_PATH")
    if env_db_path:
        return Path(env_db_path)

    return DEFAULT_DB_PATH


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with foreign-key enforcement enabled."""
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def init_db(db_path: str | Path | None = None) -> Path:
    """Create the SQLite database and required tables if missing."""
    path = resolve_db_path(db_path)
    with get_connection(path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.commit()
    return path


def _require_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value


def _validate_optional_string_field(card: dict[str, Any], card_id: str, field_name: str) -> None:
    if field_name not in card or card[field_name] is None:
        return
    if not isinstance(card[field_name], str):
        raise ValueError(f"cards[{card_id}].{field_name} must be a string or null.")


def _validate_optional_due_date_field(card: dict[str, Any], card_id: str) -> None:
    value = card.get("dueDate")
    if value is None:
        return
    if not isinstance(value, str) or not _ISO_DATE_PATTERN.match(value):
        raise ValueError(f"cards[{card_id}].dueDate must be an ISO date string (YYYY-MM-DD) or null.")


def validate_board_data(board_data: Any) -> None:
    """Validate board JSON contract aligned with frontend ``BoardData``.

    Required shape:
    {
      "columns": [{"id": str, "title": str, "cardIds": string[]}],
      "cards": {
        "card-id": {
          "id": str, "title": str, "details": str,
          "label": str | null (optional), "dueDate": "YYYY-MM-DD" | null (optional),
          "assignee": str | null (optional)
        }
      }
    }

    ``label``/``dueDate``/``assignee`` are optional card metadata (Part 14): a card
    predating them simply omits the keys, which is valid.
    """
    if not isinstance(board_data, dict):
        raise ValueError("board_data must be an object.")

    columns = board_data.get("columns")
    cards = board_data.get("cards")

    if not isinstance(columns, list):
        raise ValueError("board_data.columns must be an array.")
    if not isinstance(cards, dict):
        raise ValueError("board_data.cards must be an object.")

    column_ids: set[str] = set()
    all_card_references: list[str] = []

    for index, column in enumerate(columns):
        if not isinstance(column, dict):
            raise ValueError(f"columns[{index}] must be an object.")

        column_id = _require_non_empty_string(column.get("id"), f"columns[{index}].id")
        _require_non_empty_string(column.get("title"), f"columns[{index}].title")

        if column_id in column_ids:
            raise ValueError("Column ids must be unique.")
        column_ids.add(column_id)

        card_ids = column.get("cardIds")
        if not isinstance(card_ids, list):
            raise ValueError(f"columns[{index}].cardIds must be an array.")

        for card_index, card_id in enumerate(card_ids):
            _require_non_empty_string(card_id, f"columns[{index}].cardIds[{card_index}]")
            all_card_references.append(card_id)

    card_keys = set(cards.keys())
    for card_id, card in cards.items():
        _require_non_empty_string(card_id, "cards key")

        if not isinstance(card, dict):
            raise ValueError(f"cards[{card_id}] must be an object.")

        payload_id = _require_non_empty_string(card.get("id"), f"cards[{card_id}].id")
        if payload_id != card_id:
            raise ValueError(f"cards[{card_id}].id must match its object key.")

        _require_non_empty_string(card.get("title"), f"cards[{card_id}].title")
        if not isinstance(card.get("details"), str):
            raise ValueError(f"cards[{card_id}].details must be a string.")

        _validate_optional_string_field(card, card_id, "label")
        _validate_optional_string_field(card, card_id, "assignee")
        _validate_optional_due_date_field(card, card_id)

    unique_references = set(all_card_references)
    if len(unique_references) != len(all_card_references):
        raise ValueError("A card may only appear once across all columns.")

    missing_cards = unique_references - card_keys
    if missing_cards:
        raise ValueError("Column cardIds include unknown card ids.")

    unplaced_cards = card_keys - unique_references
    if unplaced_cards:
        raise ValueError("Every card in cards must appear in exactly one column.")


def _serialize_board_data(board_data: dict[str, Any]) -> str:
    validate_board_data(board_data)
    return json.dumps(board_data, separators=(",", ":"), sort_keys=True)


def create_user(connection: sqlite3.Connection, username: str, password_hash: str) -> int:
    _require_non_empty_string(username, "username")
    _require_non_empty_string(password_hash, "password_hash")

    cursor = connection.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, password_hash),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_user_by_username(connection: sqlite3.Connection, username: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT id, username, password_hash, created_at FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if row is None:
        return None

    return {
        "id": int(row["id"]),
        "username": str(row["username"]),
        "password_hash": str(row["password_hash"]),
        "created_at": str(row["created_at"]),
    }


def create_board(
    connection: sqlite3.Connection, user_id: int, board_data: dict[str, Any], name: str = "My Board"
) -> int:
    _require_non_empty_string(name, "name")
    payload = _serialize_board_data(board_data)

    cursor = connection.execute(
        "INSERT INTO boards (user_id, name, board_data) VALUES (?, ?, ?)",
        (user_id, name, payload),
    )
    connection.commit()
    return int(cursor.lastrowid)


def _board_summary_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "name": str(row["name"]),
        "is_archived": bool(row["is_archived"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def list_boards(connection: sqlite3.Connection, user_id: int) -> list[dict[str, Any]]:
    """Return lightweight metadata (no ``board_data``) for every board owned by ``user_id``."""
    rows = connection.execute(
        """
        SELECT id, name, is_archived, created_at, updated_at
        FROM boards
        WHERE user_id = ?
        ORDER BY updated_at DESC
        """,
        (user_id,),
    ).fetchall()
    return [_board_summary_from_row(row) for row in rows]


def get_board(connection: sqlite3.Connection, user_id: int, board_id: int) -> dict[str, Any] | None:
    """Fetch one full board (including ``board_data``), scoped to its owner.

    Returns ``None`` if the board doesn't exist *or* belongs to a different
    user - callers must treat both cases identically (404), never leaking
    which one it was.
    """
    row = connection.execute(
        """
        SELECT id, user_id, name, board_data, is_archived, created_at, updated_at
        FROM boards
        WHERE id = ? AND user_id = ?
        """,
        (board_id, user_id),
    ).fetchone()

    if row is None:
        return None

    return {
        "id": int(row["id"]),
        "user_id": int(row["user_id"]),
        "name": str(row["name"]),
        "board_data": json.loads(str(row["board_data"])),
        "is_archived": bool(row["is_archived"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def update_board_data(
    connection: sqlite3.Connection, user_id: int, board_id: int, board_data: dict[str, Any]
) -> bool:
    """Replace a board's data. Returns ``False`` if the board doesn't exist or isn't owned by ``user_id``."""
    payload = _serialize_board_data(board_data)

    cursor = connection.execute(
        """
        UPDATE boards
        SET board_data = ?,
            updated_at = STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')
        WHERE id = ? AND user_id = ?
        """,
        (payload, board_id, user_id),
    )
    connection.commit()
    return cursor.rowcount > 0


def patch_board(
    connection: sqlite3.Connection,
    user_id: int,
    board_id: int,
    name: str | None = None,
    is_archived: bool | None = None,
) -> bool:
    """Rename and/or archive/unarchive a board. Returns ``False`` if not found/owned."""
    assignments = ["updated_at = STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')"]
    params: list[Any] = []

    if name is not None:
        assignments.append("name = ?")
        params.append(name)
    if is_archived is not None:
        assignments.append("is_archived = ?")
        params.append(1 if is_archived else 0)

    params.extend([board_id, user_id])

    cursor = connection.execute(
        f"UPDATE boards SET {', '.join(assignments)} WHERE id = ? AND user_id = ?",
        params,
    )
    connection.commit()
    return cursor.rowcount > 0


def delete_board(connection: sqlite3.Connection, user_id: int, board_id: int) -> bool:
    """Permanently delete a board. Returns ``False`` if not found/owned."""
    cursor = connection.execute(
        "DELETE FROM boards WHERE id = ? AND user_id = ?",
        (board_id, user_id),
    )
    connection.commit()
    return cursor.rowcount > 0


def insert_session(
    connection: sqlite3.Connection, token: str, user_id: int, expires_at: str
) -> None:
    _require_non_empty_string(token, "token")
    _require_non_empty_string(expires_at, "expires_at")

    connection.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at),
    )
    connection.commit()


def get_session_with_user(connection: sqlite3.Connection, token: str) -> dict[str, Any] | None:
    """Look up a session by token, joined with its owning user.

    Returns ``None`` if the token doesn't exist. Callers are responsible for
    checking ``expires_at`` against the current time.
    """
    row = connection.execute(
        """
        SELECT sessions.token AS token,
               sessions.user_id AS user_id,
               sessions.expires_at AS expires_at,
               users.username AS username
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.token = ?
        """,
        (token,),
    ).fetchone()

    if row is None:
        return None

    return {
        "token": str(row["token"]),
        "user_id": int(row["user_id"]),
        "expires_at": str(row["expires_at"]),
        "username": str(row["username"]),
    }


def delete_session(connection: sqlite3.Connection, token: str) -> None:
    connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
    connection.commit()