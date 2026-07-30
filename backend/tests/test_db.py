"""Tests for the SQLite data layer (Part 5 users/boards, Part 13 multi-board)."""

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
    delete_board,
    get_board,
    get_connection,
    get_user_by_username,
    init_db,
    list_boards,
    patch_board,
    update_board_data,
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
        assert "sessions" in table_names


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


def test_multiple_boards_per_user_are_allowed(db_path: pathlib.Path):
    """As of Part 13, a user may own more than one board (no more UNIQUE(user_id))."""
    init_db(db_path)
    with get_connection(db_path) as connection:
        user_id = create_user(connection, "user", "dummy_hash_v1")
        create_board(connection, user_id, sample_board(), name="Board One")
        create_board(connection, user_id, sample_board(), name="Board Two")

        boards = list_boards(connection, user_id)

    assert {board["name"] for board in boards} == {"Board One", "Board Two"}


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


def test_validate_board_data_accepts_cards_without_metadata_fields():
    """Older boards/cards that predate Part 14 metadata must keep loading fine."""
    validate_board_data(sample_board())


def test_validate_board_data_accepts_optional_metadata_fields():
    board = sample_board()
    board["cards"]["card-1"]["label"] = "Urgent"
    board["cards"]["card-1"]["dueDate"] = "2026-08-15"
    board["cards"]["card-1"]["assignee"] = "Alex"

    validate_board_data(board)


def test_validate_board_data_accepts_null_metadata_fields():
    board = sample_board()
    board["cards"]["card-1"]["label"] = None
    board["cards"]["card-1"]["dueDate"] = None
    board["cards"]["card-1"]["assignee"] = None

    validate_board_data(board)


def test_validate_board_data_rejects_non_string_label():
    board = sample_board()
    board["cards"]["card-1"]["label"] = 42

    with pytest.raises(ValueError, match="label"):
        validate_board_data(board)


def test_validate_board_data_rejects_non_string_assignee():
    board = sample_board()
    board["cards"]["card-1"]["assignee"] = ["Alex"]

    with pytest.raises(ValueError, match="assignee"):
        validate_board_data(board)


@pytest.mark.parametrize("bad_due_date", ["08/15/2026", "2026-8-15", "not-a-date", ""])
def test_validate_board_data_rejects_malformed_due_date(bad_due_date):
    board = sample_board()
    board["cards"]["card-1"]["dueDate"] = bad_due_date

    with pytest.raises(ValueError, match="dueDate"):
        validate_board_data(board)


def test_update_board_data_rejects_invalid_payload(db_path: pathlib.Path):
    init_db(db_path)

    with get_connection(db_path) as connection:
        user_id = create_user(connection, "user", "dummy_hash_v1")
        board_id = create_board(connection, user_id, sample_board())

        invalid_board = sample_board()
        invalid_board["cards"]["card-1"]["details"] = None

        with pytest.raises(ValueError, match="cards\\[card-1\\]\\.details must be a string"):
            update_board_data(connection, user_id, board_id, invalid_board)


def test_list_boards_excludes_board_data(db_path: pathlib.Path):
    init_db(db_path)
    with get_connection(db_path) as connection:
        user_id = create_user(connection, "user", "dummy_hash_v1")
        create_board(connection, user_id, sample_board(), name="My Board")

        boards = list_boards(connection, user_id)

    assert len(boards) == 1
    assert set(boards[0].keys()) == {"id", "name", "is_archived", "created_at", "updated_at"}


def test_get_board_returns_none_for_wrong_owner(db_path: pathlib.Path):
    init_db(db_path)
    with get_connection(db_path) as connection:
        owner_id = create_user(connection, "owner", "dummy_hash_v1")
        other_id = create_user(connection, "other", "dummy_hash_v1")
        board_id = create_board(connection, owner_id, sample_board())

        assert get_board(connection, other_id, board_id) is None
        assert get_board(connection, owner_id, board_id) is not None


def test_get_board_returns_none_for_missing_board(db_path: pathlib.Path):
    init_db(db_path)
    with get_connection(db_path) as connection:
        user_id = create_user(connection, "user", "dummy_hash_v1")
        assert get_board(connection, user_id, 9999) is None


def test_update_board_data_rejects_wrong_owner(db_path: pathlib.Path):
    init_db(db_path)
    with get_connection(db_path) as connection:
        owner_id = create_user(connection, "owner", "dummy_hash_v1")
        other_id = create_user(connection, "other", "dummy_hash_v1")
        board_id = create_board(connection, owner_id, sample_board())

        updated = update_board_data(connection, other_id, board_id, sample_board())
        assert updated is False


def test_patch_board_renames_and_archives(db_path: pathlib.Path):
    init_db(db_path)
    with get_connection(db_path) as connection:
        user_id = create_user(connection, "user", "dummy_hash_v1")
        board_id = create_board(connection, user_id, sample_board(), name="Original")

        assert patch_board(connection, user_id, board_id, name="Renamed") is True
        assert patch_board(connection, user_id, board_id, is_archived=True) is True

        boards = list_boards(connection, user_id)

    assert boards[0]["name"] == "Renamed"
    assert boards[0]["is_archived"] is True


def test_patch_board_rejects_wrong_owner(db_path: pathlib.Path):
    init_db(db_path)
    with get_connection(db_path) as connection:
        owner_id = create_user(connection, "owner", "dummy_hash_v1")
        other_id = create_user(connection, "other", "dummy_hash_v1")
        board_id = create_board(connection, owner_id, sample_board())

        assert patch_board(connection, other_id, board_id, name="Hijacked") is False


def test_delete_board_removes_row_and_rejects_wrong_owner(db_path: pathlib.Path):
    init_db(db_path)
    with get_connection(db_path) as connection:
        owner_id = create_user(connection, "owner", "dummy_hash_v1")
        other_id = create_user(connection, "other", "dummy_hash_v1")
        board_id = create_board(connection, owner_id, sample_board())

        assert delete_board(connection, other_id, board_id) is False
        assert delete_board(connection, owner_id, board_id) is True
        assert get_board(connection, owner_id, board_id) is None


def test_user_and_board_crud_round_trip_with_updated_timestamp(db_path: pathlib.Path):
    init_db(db_path)

    with get_connection(db_path) as connection:
        user_id = create_user(connection, "user", "dummy_hash_v1")
        user = get_user_by_username(connection, "user")

        assert user is not None
        assert user["id"] == user_id
        assert user["username"] == "user"
        assert user["password_hash"] == "dummy_hash_v1"

        board_id = create_board(connection, user_id, sample_board())
        created_board = get_board(connection, user_id, board_id)

        assert created_board is not None
        assert created_board["user_id"] == user_id
        assert created_board["board_data"] == sample_board()

        # Force a known old timestamp so we can assert update changed it deterministically.
        connection.execute(
            "UPDATE boards SET updated_at = '2000-01-01T00:00:00.000Z' WHERE id = ?",
            (board_id,),
        )
        connection.commit()

        updated_board_data = sample_board()
        updated_board_data["cards"]["card-1"]["title"] = "Updated title"
        update_board_data(connection, user_id, board_id, updated_board_data)

        updated_board = get_board(connection, user_id, board_id)
        assert updated_board is not None
        assert updated_board["board_data"]["cards"]["card-1"]["title"] == "Updated title"
        assert updated_board["updated_at"] != "2000-01-01T00:00:00.000Z"
