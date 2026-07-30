"""Unit tests for Part 9 prompt construction."""

from __future__ import annotations

import json

from backend.ai.prompt_builder import build_system_prompt, build_user_prompt


def sample_board() -> dict:
    return {
        "columns": [
            {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1"]},
            {"id": "col-done", "title": "Done", "cardIds": []},
        ],
        "cards": {
            "card-1": {"id": "card-1", "title": "Plan release", "details": "Draft milestones."},
        },
    }


def test_build_system_prompt_includes_strict_json_contract():
    prompt = build_system_prompt()

    assert "Return ONLY valid JSON" in prompt
    assert "Do not return a replacement board" in prompt
    assert "move_card" in prompt
    assert "rename_column" in prompt
    assert "create_card" in prompt
    assert "update_card" in prompt
    assert "delete_card" in prompt


def test_build_user_prompt_embeds_message_and_board():
    board = sample_board()
    message = "rename backlog to ideas"

    prompt = build_user_prompt(board, message)
    payload = json.loads(prompt)

    assert payload["instruction"] == message
    assert payload["board"] == board
    assert payload["rules"]["never_return_board"] is True
    assert payload["rules"]["json_only"] is True
    assert payload["rules"]["allowed_operation_types"] == [
        "move_card",
        "rename_column",
        "create_card",
        "update_card",
        "delete_card",
    ]