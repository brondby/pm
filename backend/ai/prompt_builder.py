"""Prompt construction for structured Kanban operations."""

from __future__ import annotations

import json
from typing import Any


def build_system_prompt() -> str:
    """Return strict instructions for structured JSON-only responses."""
    return (
        "You are an assistant that plans Kanban board operations.\n"
        "Return ONLY valid JSON. No markdown. No code fences. No extra prose.\n"
        "Do not return a replacement board. Return operations only.\n"
        "Allowed operation types:\n"
        "- move_card\n"
        "- rename_column\n"
        "- create_card\n"
        "- delete_card\n"
        "Response JSON contract:\n"
        '{"reply":"string","operations":[{"type":"move_card|rename_column|create_card|delete_card"}]}'
    )


def build_user_prompt(board_data: dict[str, Any], message: str) -> str:
    """Build compact JSON prompt with board state and operation schema hints."""
    payload = {
        "instruction": message,
        "rules": {
            "allowed_operation_types": [
                "move_card",
                "rename_column",
                "create_card",
                "delete_card",
            ],
            "never_return_board": True,
            "json_only": True,
        },
        "operation_field_hints": {
            "move_card": ["card_id|card_title", "to_column_id|to_column_title"],
            "rename_column": ["column_id|column_title", "new_title"],
            "create_card": ["column_id|column_title", "title", "details(optional)"],
            "delete_card": ["card_id|card_title"],
        },
        "response_contract": {
            "reply": "string",
            "operations": [
                {
                    "type": "move_card|rename_column|create_card|delete_card",
                }
            ],
        },
        "board": board_data,
    }

    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)