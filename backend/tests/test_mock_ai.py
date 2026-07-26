"""Unit tests for deterministic mock AI parser and board mutation logic."""

from __future__ import annotations

from backend.ai.mock_ai import process_chat_command


def sample_board() -> dict:
    return {
        "columns": [
            {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1"]},
            {"id": "col-done", "title": "Done", "cardIds": ["card-2"]},
        ],
        "cards": {
            "card-1": {"id": "card-1", "title": "Plan release", "details": "Draft milestones."},
            "card-2": {"id": "card-2", "title": "Ship update", "details": "Publish changelog."},
        },
    }


def test_move_card_matches_titles_case_insensitively_and_trims_message():
    board = sample_board()

    result = process_chat_command(board, "   move card plan release to done   ")

    assert result.is_invalid_command is False
    assert result.should_persist is True
    assert result.reply == 'Moved "Plan release" to "Done".'
    assert result.board["columns"][0]["cardIds"] == []
    assert result.board["columns"][1]["cardIds"] == ["card-2", "card-1"]


def test_rename_column_matches_case_insensitively():
    board = sample_board()

    result = process_chat_command(board, "rename column backlog to Ready")

    assert result.is_invalid_command is False
    assert result.should_persist is True
    assert result.board["columns"][0]["title"] == "Ready"
    assert result.reply == 'Renamed column "Backlog" to "Ready".'


def test_create_card_generates_collision_safe_id():
    board = sample_board()

    result = process_chat_command(board, "create card New Follow Up in backlog")

    assert result.is_invalid_command is False
    assert result.should_persist is True
    created_ids = [card_id for card_id in result.board["cards"] if card_id not in {"card-1", "card-2"}]
    assert len(created_ids) == 1
    assert created_ids[0].startswith("card-")
    assert created_ids[0] in result.board["columns"][0]["cardIds"]


def test_returns_friendly_message_when_card_not_found():
    board = sample_board()

    result = process_chat_command(board, "delete card Missing card")

    assert result.is_invalid_command is False
    assert result.should_persist is False
    assert result.reply == 'Could not find a card named "Missing card".'
    assert result.board == sample_board()


def test_returns_friendly_message_when_column_not_found():
    board = sample_board()

    result = process_chat_command(board, "move card Plan release to In Progress")

    assert result.is_invalid_command is False
    assert result.should_persist is False
    assert result.reply == 'Could not find a column named "In Progress".'
    assert result.board == sample_board()


def test_unknown_command_is_invalid_and_does_not_mutate_board():
    board = sample_board()

    result = process_chat_command(board, "summarize this board")

    assert result.is_invalid_command is True
    assert result.should_persist is False
    assert "could not understand" in result.reply.lower()
    assert result.board == board