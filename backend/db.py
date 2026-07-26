"""Minimal SQLite data layer for Part 5 (database modeling).

This module intentionally keeps scope small:

* create/open SQLite database
* initialize schema for users + boards
* validate board JSON contract
* provide basic user/board CRUD helpers for tests and future API wiring
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "pm.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS boards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    board_data TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
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


def validate_board_data(board_data: Any) -> None:
    """Validate board JSON contract aligned with frontend ``BoardData``.

    Required shape:
    {
      "columns": [{"id": str, "title": str, "cardIds": string[]}],
      "cards": {"card-id": {"id": str, "title": str, "details": str}}
    }
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


def create_board(connection: sqlite3.Connection, user_id: int, board_data: dict[str, Any]) -> int:
    payload = _serialize_board_data(board_data)

    cursor = connection.execute(
        "INSERT INTO boards (user_id, board_data) VALUES (?, ?)",
        (user_id, payload),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_board_by_user_id(connection: sqlite3.Connection, user_id: int) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT id, user_id, board_data, created_at, updated_at FROM boards WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    if row is None:
        return None

    return {
        "id": int(row["id"]),
        "user_id": int(row["user_id"]),
        "board_data": json.loads(str(row["board_data"])),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def update_board(connection: sqlite3.Connection, user_id: int, board_data: dict[str, Any]) -> None:
    payload = _serialize_board_data(board_data)

    cursor = connection.execute(
        """
        UPDATE boards
        SET board_data = ?,
            updated_at = STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')
        WHERE user_id = ?
        """,
        (payload, user_id),
    )

    if cursor.rowcount == 0:
        raise ValueError("Board not found for user.")

    connection.commit()