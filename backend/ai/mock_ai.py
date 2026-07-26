"""Deterministic mock AI command parser and board mutator for Part 8.

This module is intentionally standalone from FastAPI so it can be replaced
later by a real LLM adapter without changing route orchestration.
"""

from __future__ import annotations

import copy
import re
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class ChatCommandResult:
    reply: str
    board: dict[str, Any]
    should_persist: bool
    is_invalid_command: bool


def _normalize_text(value: str) -> str:
    return value.strip()


def _normalize_match_value(value: str) -> str:
    normalized = _normalize_text(value)
    if (
        len(normalized) >= 2
        and normalized[0] == normalized[-1]
        and normalized[0] in {"'", '"'}
    ):
        return normalized[1:-1].strip()
    return normalized


def _match_text(value: str) -> str:
    return _normalize_text(value).casefold()


def _find_column_index_by_title(board: dict[str, Any], title: str) -> int | None:
    title_key = _match_text(title)
    for index, column in enumerate(board["columns"]):
        if _match_text(column["title"]) == title_key:
            return index
    return None


def _find_card_id_by_title(board: dict[str, Any], title: str) -> str | None:
    title_key = _match_text(title)
    for card_id, card in board["cards"].items():
        if _match_text(card["title"]) == title_key:
            return card_id
    return None


def _find_column_index_containing_card(board: dict[str, Any], card_id: str) -> int | None:
    for index, column in enumerate(board["columns"]):
        if card_id in column["cardIds"]:
            return index
    return None


def _create_card_id(existing_cards: dict[str, Any]) -> str:
    while True:
        candidate = f"card-{uuid.uuid4().hex}"
        if candidate not in existing_cards:
            return candidate


def _result(
    *,
    reply: str,
    board: dict[str, Any],
    should_persist: bool,
    is_invalid_command: bool,
) -> ChatCommandResult:
    return ChatCommandResult(
        reply=reply,
        board=board,
        should_persist=should_persist,
        is_invalid_command=is_invalid_command,
    )


def _create_card(board: dict[str, Any], card_title: str, column_title: str) -> ChatCommandResult:
    normalized_card_title = _normalize_match_value(card_title)
    normalized_column_title = _normalize_match_value(column_title)

    if not normalized_card_title:
        return _result(
            reply="Please provide a card title to create.",
            board=board,
            should_persist=False,
            is_invalid_command=True,
        )

    column_index = _find_column_index_by_title(board, normalized_column_title)
    if column_index is None:
        return _result(
            reply=f'Could not find a column named "{normalized_column_title}".',
            board=board,
            should_persist=False,
            is_invalid_command=False,
        )

    card_id = _create_card_id(board["cards"])
    board["cards"][card_id] = {
        "id": card_id,
        "title": normalized_card_title,
        "details": "No details yet.",
    }
    board["columns"][column_index]["cardIds"].append(card_id)

    return _result(
        reply=f'Created card "{normalized_card_title}" in "{board["columns"][column_index]["title"]}".',
        board=board,
        should_persist=True,
        is_invalid_command=False,
    )


def _move_card(board: dict[str, Any], card_title: str, column_title: str) -> ChatCommandResult:
    normalized_card_title = _normalize_match_value(card_title)
    normalized_column_title = _normalize_match_value(column_title)

    card_id = _find_card_id_by_title(board, normalized_card_title)
    if card_id is None:
        return _result(
            reply=f'Could not find a card named "{normalized_card_title}".',
            board=board,
            should_persist=False,
            is_invalid_command=False,
        )

    target_column_index = _find_column_index_by_title(board, normalized_column_title)
    if target_column_index is None:
        return _result(
            reply=f'Could not find a column named "{normalized_column_title}".',
            board=board,
            should_persist=False,
            is_invalid_command=False,
        )

    source_column_index = _find_column_index_containing_card(board, card_id)
    if source_column_index is None:
        return _result(
            reply=f'Could not find the current column for card "{normalized_card_title}".',
            board=board,
            should_persist=False,
            is_invalid_command=False,
        )

    if source_column_index == target_column_index:
        return _result(
            reply=f'Card "{board["cards"][card_id]["title"]}" is already in "{board["columns"][target_column_index]["title"]}".',
            board=board,
            should_persist=False,
            is_invalid_command=False,
        )

    board["columns"][source_column_index]["cardIds"] = [
        existing_id
        for existing_id in board["columns"][source_column_index]["cardIds"]
        if existing_id != card_id
    ]
    board["columns"][target_column_index]["cardIds"].append(card_id)

    return _result(
        reply=f'Moved "{board["cards"][card_id]["title"]}" to "{board["columns"][target_column_index]["title"]}".',
        board=board,
        should_persist=True,
        is_invalid_command=False,
    )


def _rename_column(board: dict[str, Any], current_title: str, new_title: str) -> ChatCommandResult:
    normalized_current_title = _normalize_match_value(current_title)
    normalized_new_title = _normalize_match_value(new_title)

    if not normalized_new_title:
        return _result(
            reply="Please provide a new column title.",
            board=board,
            should_persist=False,
            is_invalid_command=True,
        )

    column_index = _find_column_index_by_title(board, normalized_current_title)
    if column_index is None:
        return _result(
            reply=f'Could not find a column named "{normalized_current_title}".',
            board=board,
            should_persist=False,
            is_invalid_command=False,
        )

    existing_title = board["columns"][column_index]["title"]
    if _match_text(existing_title) == _match_text(normalized_new_title):
        return _result(
            reply=f'Column "{existing_title}" already has that title.',
            board=board,
            should_persist=False,
            is_invalid_command=False,
        )

    board["columns"][column_index]["title"] = normalized_new_title
    return _result(
        reply=f'Renamed column "{existing_title}" to "{normalized_new_title}".',
        board=board,
        should_persist=True,
        is_invalid_command=False,
    )


def _delete_card(board: dict[str, Any], card_title: str) -> ChatCommandResult:
    normalized_card_title = _normalize_match_value(card_title)

    card_id = _find_card_id_by_title(board, normalized_card_title)
    if card_id is None:
        return _result(
            reply=f'Could not find a card named "{normalized_card_title}".',
            board=board,
            should_persist=False,
            is_invalid_command=False,
        )

    card_title_actual = board["cards"][card_id]["title"]
    del board["cards"][card_id]

    for column in board["columns"]:
        column["cardIds"] = [existing_id for existing_id in column["cardIds"] if existing_id != card_id]

    return _result(
        reply=f'Deleted card "{card_title_actual}".',
        board=board,
        should_persist=True,
        is_invalid_command=False,
    )


CREATE_CARD_RE = re.compile(r"^(?:add|create)\s+card\s+(.+?)\s+(?:in|to)\s+(.+)$", re.IGNORECASE)
MOVE_CARD_RE = re.compile(r"^move\s+card\s+(.+?)\s+to\s+(.+)$", re.IGNORECASE)
RENAME_COLUMN_RE = re.compile(r"^rename\s+column\s+(.+?)\s+to\s+(.+)$", re.IGNORECASE)
DELETE_CARD_RE = re.compile(r"^delete\s+card\s+(.+)$", re.IGNORECASE)


def process_chat_command(board_data: dict[str, Any], message: str) -> ChatCommandResult:
    """Parse a deterministic chat command and return resulting board intent."""
    normalized_message = _normalize_text(message)
    if not normalized_message:
        return _result(
            reply="Please enter a command.",
            board=board_data,
            should_persist=False,
            is_invalid_command=True,
        )

    board_copy = copy.deepcopy(board_data)

    create_match = CREATE_CARD_RE.match(normalized_message)
    if create_match:
        return _create_card(board_copy, create_match.group(1), create_match.group(2))

    move_match = MOVE_CARD_RE.match(normalized_message)
    if move_match:
        return _move_card(board_copy, move_match.group(1), move_match.group(2))

    rename_match = RENAME_COLUMN_RE.match(normalized_message)
    if rename_match:
        return _rename_column(board_copy, rename_match.group(1), rename_match.group(2))

    delete_match = DELETE_CARD_RE.match(normalized_message)
    if delete_match:
        return _delete_card(board_copy, delete_match.group(1))

    return _result(
        reply="I could not understand that command. Try create, move, rename, or delete commands.",
        board=board_data,
        should_persist=False,
        is_invalid_command=True,
    )