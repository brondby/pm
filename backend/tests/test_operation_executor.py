"""Unit tests for Part 9 operation execution."""

from __future__ import annotations

import copy

import pytest

from backend.ai.openrouter_ai import AIServiceError
from backend.ai.operation_executor import execute_operations


def sample_board() -> dict:
    return {
        "columns": [
            {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1"]},
            {"id": "col-inprogress", "title": "In Progress", "cardIds": []},
            {"id": "col-done", "title": "Done", "cardIds": ["card-2"]},
        ],
        "cards": {
            "card-1": {"id": "card-1", "title": "Plan release", "details": "Draft milestones."},
            "card-2": {"id": "card-2", "title": "Ship update", "details": "Publish changelog."},
        },
    }


def test_execute_operations_applies_supported_operations():
    board = sample_board()

    result = execute_operations(
        board,
        [
            {"type": "rename_column", "column_title": "Backlog", "new_title": "Ideas"},
            {"type": "create_card", "column_title": "Ideas", "title": "Draft scope"},
            {"type": "move_card", "card_title": "Plan release", "to_column_title": "In Progress"},
        ],
    )

    assert result.should_persist is True
    assert result.board["columns"][0]["title"] == "Ideas"
    assert "card-1" in result.board["columns"][1]["cardIds"]


def test_execute_operations_is_case_insensitive_for_titles():
    board = sample_board()

    result = execute_operations(
        board,
        [{"type": "move_card", "card_title": "plan RELEASE", "to_column_title": "done"}],
    )

    assert result.should_persist is True
    assert "card-1" in result.board["columns"][2]["cardIds"]


def test_execute_operations_ignores_unsupported_operation_type():
    board = sample_board()
    snapshot = copy.deepcopy(board)

    result = execute_operations(board, [{"type": "archive_card", "card_title": "Plan release"}])

    assert result.should_persist is False
    assert result.board == snapshot


def test_execute_operations_rejects_malformed_supported_operation_atomically():
    board = sample_board()
    snapshot = copy.deepcopy(board)

    with pytest.raises(AIServiceError) as error:
        execute_operations(
            board,
            [
                {"type": "rename_column", "column_title": "Backlog", "new_title": "Ideas"},
                {"type": "move_card", "card_title": "Plan release"},
            ],
        )

    assert 'move_card requires "to_column_id" or "to_column_title".' in error.value.detail
    assert board == snapshot


def test_execute_operations_rejects_non_object_operation():
    with pytest.raises(AIServiceError) as error:
        execute_operations(sample_board(), ["bad"])

    assert "operation at index 0 must be an object" in error.value.detail.lower()


def test_execute_operations_generates_collision_safe_card_ids():
    board = sample_board()

    result = execute_operations(
        board,
        [{"type": "create_card", "column_id": "col-backlog", "title": "New task"}],
    )

    assert result.should_persist is True
    card_ids = set(result.board["cards"].keys())
    assert "card-1" in card_ids
    assert "card-2" in card_ids
    assert len(card_ids) == 3