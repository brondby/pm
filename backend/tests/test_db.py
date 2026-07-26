"""Tests for Part 5 SQLite modeling layer."""

from __future__ import annotations

import pathlib
import sqlite3
import sys

import pytest

# Keep import style consistent with existing backend tests.
backend_dir = pathlib.Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from db import (  # noqa: E402
    create_board,
    create_user,
    get_board_by_user_id,
    get_connection,
    get_user_by_username,
    init_db,
    update_board,
    validate_board_data,
)


def sample_board() -> dict:
    return {
        "columns": [
            {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1"]},
            {"id": "col-done", "title": "Done", "cardIds": ["card-2"]},
        ],
        "cards": {
            "card-1": {
                "id": "card-1",
                "title": "Plan release",
                "details": "Draft milestones.",
            },
            "card-2": {
                "id": "card-2",
                "title": "Ship update",
                "details": "Publish changelog.",
            },
        },
    }


@pytest.fixture
def db_path(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "test_pm.db"


def test_init_db_creates_database_file_and_tables(db_path: pathlib.Path):
    assert not db_path.exists()

    created_path = init_db(db_path)

    assert created_path == db_path
    assert db_path.exists()

    with get_connection(db_path) as connection:
        table_rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {row["name"] for row in table_rows}
        assert "users" in table_names
        assert "boards" in table_names


def test_init_db_creates_missing_tables_in_existing_database_file(db_path: pathlib.Path):
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE preexisting (id INTEGER PRIMARY KEY)")
        connection.commit()

    init_db(db_path)

    with get_connection(db_path) as connection:
        table_rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {row["name"] for row in table_rows}
        assert "preexisting" in table_names
        assert "users" in table_names
        assert "boards" in table_names


def test_unique_username_constraint(db_path: pathlib.Path):
    init_db(db_path)
    with get_connection(db_path) as connection:
        create_user(connection, "user", "dummy_hash_v1")

        with pytest.raises(sqlite3.IntegrityError):
            create_user(connection, "user", "dummy_hash_v2")


def test_one_board_per_user_constraint(db_path: pathlib.Path):
    init_db(db_path)
    with get_connection(db_path) as connection:
        user_id = create_user(connection, "user", "dummy_hash_v1")
        create_board(connection, user_id, sample_board())

        with pytest.raises(sqlite3.IntegrityError):
            create_board(connection, user_id, sample_board())


def test_foreign_key_constraint_on_boards(db_path: pathlib.Path):
    init_db(db_path)
    with get_connection(db_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            create_board(connection, 9999, sample_board())


def test_validate_board_data_accepts_valid_shape():
    validate_board_data(sample_board())


def test_validate_board_data_rejects_invalid_shape():
    invalid_board = sample_board()
    invalid_board["columns"][0]["cardIds"] = ["card-1", "missing-card"]

    with pytest.raises(ValueError, match="unknown card ids"):
        validate_board_data(invalid_board)


def test_update_board_rejects_invalid_payload(db_path: pathlib.Path):
    init_db(db_path)

    with get_connection(db_path) as connection:
        user_id = create_user(connection, "user", "dummy_hash_v1")
        create_board(connection, user_id, sample_board())

        invalid_board = sample_board()
        invalid_board["cards"]["card-1"]["details"] = None

        with pytest.raises(ValueError, match="cards\\[card-1\\]\\.details must be a string"):
            update_board(connection, user_id, invalid_board)


def test_user_and_board_crud_round_trip_with_updated_timestamp(db_path: pathlib.Path):
    init_db(db_path)

    with get_connection(db_path) as connection:
        user_id = create_user(connection, "user", "dummy_hash_v1")
        user = get_user_by_username(connection, "user")

        assert user is not None
        assert user["id"] == user_id
        assert user["username"] == "user"
        assert user["password_hash"] == "dummy_hash_v1"

        create_board(connection, user_id, sample_board())
        created_board = get_board_by_user_id(connection, user_id)

        assert created_board is not None
        assert created_board["user_id"] == user_id
        assert created_board["board_data"] == sample_board()

        # Force a known old timestamp so we can assert update changed it deterministically.
        connection.execute(
            "UPDATE boards SET updated_at = '2000-01-01T00:00:00.000Z' WHERE user_id = ?",
            (user_id,),
        )
        connection.commit()

        updated_board_data = sample_board()
        updated_board_data["cards"]["card-1"]["title"] = "Updated title"
        update_board(connection, user_id, updated_board_data)

        updated_board = get_board_by_user_id(connection, user_id)
        assert updated_board is not None
        assert updated_board["board_data"]["cards"]["card-1"]["title"] == "Updated title"
        assert updated_board["updated_at"] != "2000-01-01T00:00:00.000Z"