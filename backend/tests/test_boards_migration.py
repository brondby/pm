"""Tests for the Part 13 boards-table migration (one-board-per-user -> multi-board)."""

from __future__ import annotations

import json
import pathlib
import sqlite3
import sys

# Ensure repo root is on sys.path so package imports like ``backend.db`` work.
repo_root = pathlib.Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend import db, migrations  # noqa: E402


def _sample_board_data() -> dict:
    return {
        "columns": [
            {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1"]},
            {"id": "col-done", "title": "Done", "cardIds": []},
        ],
        "cards": {
            "card-1": {"id": "card-1", "title": "Plan release", "details": "Draft milestones."},
        },
    }


def _seed_legacy_schema(db_path: pathlib.Path, username: str, board_data: dict) -> None:
    """Build the pre-Part-13 schema by hand: one board per user, no name/is_archived."""
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                board_data TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
                updated_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cursor = connection.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, "some_hash"),
        )
        user_id = cursor.lastrowid
        connection.execute(
            "INSERT INTO boards (user_id, board_data) VALUES (?, ?)",
            (user_id, json.dumps(board_data)),
        )
        connection.commit()


def test_rebuild_preserves_existing_board_and_card_data(tmp_path: pathlib.Path):
    db_path = tmp_path / "test_pm.db"
    board_data = _sample_board_data()
    _seed_legacy_schema(db_path, "alice", board_data)

    with db.get_connection(db_path) as connection:
        migrations.rebuild_boards_table(connection, db_path)

    with db.get_connection(db_path) as connection:
        user = db.get_user_by_username(connection, "alice")
        boards = db.list_boards(connection, user["id"])
        full_board = db.get_board(connection, user["id"], boards[0]["id"])

    assert len(boards) == 1
    assert boards[0]["name"] == "My Board"
    assert boards[0]["is_archived"] is False
    assert full_board["board_data"] == board_data


def test_rebuild_creates_timestamped_backup_and_prints_path(tmp_path: pathlib.Path, capsys):
    db_path = tmp_path / "test_pm.db"
    _seed_legacy_schema(db_path, "alice", _sample_board_data())

    with db.get_connection(db_path) as connection:
        migrations.rebuild_boards_table(connection, db_path)

    captured = capsys.readouterr()
    assert str(db_path) in captured.out
    assert "Backed up database to" in captured.out

    backups = list(tmp_path.glob("test_pm.db.*.bak"))
    assert len(backups) == 1


def test_rebuild_is_idempotent(tmp_path: pathlib.Path):
    db_path = tmp_path / "test_pm.db"
    _seed_legacy_schema(db_path, "alice", _sample_board_data())

    with db.get_connection(db_path) as connection:
        migrations.rebuild_boards_table(connection, db_path)

    with db.get_connection(db_path) as connection:
        migrations.rebuild_boards_table(connection, db_path)

    backups = list(tmp_path.glob("test_pm.db.*.bak"))
    assert len(backups) == 1  # second run found nothing to migrate, so no extra backup


def test_rebuild_allows_multiple_boards_per_user_afterward(tmp_path: pathlib.Path):
    db_path = tmp_path / "test_pm.db"
    _seed_legacy_schema(db_path, "alice", _sample_board_data())

    with db.get_connection(db_path) as connection:
        migrations.rebuild_boards_table(connection, db_path)

    with db.get_connection(db_path) as connection:
        user = db.get_user_by_username(connection, "alice")
        # Would have raised sqlite3.IntegrityError under the old UNIQUE(user_id) schema.
        db.create_board(connection, user["id"], _sample_board_data(), name="Second Board")
        boards = db.list_boards(connection, user["id"])

    assert len(boards) == 2


def test_rebuild_skips_already_migrated_database(tmp_path: pathlib.Path):
    db_path = tmp_path / "test_pm.db"
    db.init_db(db_path)  # fresh DB already has the new schema directly

    with db.get_connection(db_path) as connection:
        migrations.rebuild_boards_table(connection, db_path)

    assert not list(tmp_path.glob("test_pm.db.*.bak"))
