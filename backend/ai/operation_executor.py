"""Validation and execution of AI-returned board operations."""

from __future__ import annotations

import copy
import re
import uuid
from dataclasses import dataclass
from typing import Any

from backend.ai.openrouter_ai import AIServiceError
from backend.db import validate_board_data


SUPPORTED_OPERATION_TYPES = {"move_card", "rename_column", "create_card", "delete_card", "update_card"}
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class OperationExecutionResult:
    board: dict[str, Any]
    should_persist: bool


def _normalize_text(value: str) -> str:
    return value.strip()


def _match_text(value: str) -> str:
    return _normalize_text(value).casefold()


def _require_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AIServiceError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _find_column_index_by_id_or_title(
    board: dict[str, Any],
    *,
    column_id: str | None = None,
    column_title: str | None = None,
) -> int | None:
    if column_id:
        for index, column in enumerate(board["columns"]):
            if column["id"] == column_id:
                return index

    if column_title:
        title_key = _match_text(column_title)
        for index, column in enumerate(board["columns"]):
            if _match_text(column["title"]) == title_key:
                return index

    return None


def _find_card_id_by_id_or_title(
    board: dict[str, Any],
    *,
    card_id: str | None = None,
    card_title: str | None = None,
) -> str | None:
    if card_id and card_id in board["cards"]:
        return card_id

    if card_title:
        title_key = _match_text(card_title)
        for existing_card_id, card in board["cards"].items():
            if _match_text(card["title"]) == title_key:
                return existing_card_id

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


def _validate_and_apply_move_card(board: dict[str, Any], operation: dict[str, Any]) -> None:
    card_id_value = operation.get("card_id")
    card_title_value = operation.get("card_title")
    to_column_id_value = operation.get("to_column_id")
    to_column_title_value = operation.get("to_column_title")

    card_id = card_id_value.strip() if isinstance(card_id_value, str) else None
    card_title = card_title_value.strip() if isinstance(card_title_value, str) else None
    to_column_id = to_column_id_value.strip() if isinstance(to_column_id_value, str) else None
    to_column_title = to_column_title_value.strip() if isinstance(to_column_title_value, str) else None

    if not card_id and not card_title:
        raise AIServiceError('move_card requires "card_id" or "card_title".')
    if not to_column_id and not to_column_title:
        raise AIServiceError('move_card requires "to_column_id" or "to_column_title".')

    resolved_card_id = _find_card_id_by_id_or_title(
        board,
        card_id=card_id,
        card_title=card_title,
    )
    if resolved_card_id is None:
        raise AIServiceError("Could not find the target card for move_card operation.")

    target_column_index = _find_column_index_by_id_or_title(
        board,
        column_id=to_column_id,
        column_title=to_column_title,
    )
    if target_column_index is None:
        raise AIServiceError("Could not find the destination column for move_card operation.")

    source_column_index = _find_column_index_containing_card(board, resolved_card_id)
    if source_column_index is None:
        raise AIServiceError("Could not find the current column for move_card operation.")

    if source_column_index == target_column_index:
        return

    board["columns"][source_column_index]["cardIds"] = [
        existing_card_id
        for existing_card_id in board["columns"][source_column_index]["cardIds"]
        if existing_card_id != resolved_card_id
    ]
    board["columns"][target_column_index]["cardIds"].append(resolved_card_id)


def _validate_and_apply_rename_column(board: dict[str, Any], operation: dict[str, Any]) -> None:
    column_id_value = operation.get("column_id")
    column_title_value = operation.get("column_title")
    new_title_value = operation.get("new_title")

    column_id = column_id_value.strip() if isinstance(column_id_value, str) else None
    column_title = column_title_value.strip() if isinstance(column_title_value, str) else None
    new_title = _require_non_empty_string(new_title_value, "rename_column.new_title")

    if not column_id and not column_title:
        raise AIServiceError('rename_column requires "column_id" or "column_title".')

    column_index = _find_column_index_by_id_or_title(
        board,
        column_id=column_id,
        column_title=column_title,
    )
    if column_index is None:
        raise AIServiceError("Could not find the target column for rename_column operation.")

    board["columns"][column_index]["title"] = new_title


def _validate_and_apply_create_card(board: dict[str, Any], operation: dict[str, Any]) -> None:
    column_id_value = operation.get("column_id")
    column_title_value = operation.get("column_title")
    title_value = operation.get("title")
    details_value = operation.get("details")

    column_id = column_id_value.strip() if isinstance(column_id_value, str) else None
    column_title = column_title_value.strip() if isinstance(column_title_value, str) else None
    title = _require_non_empty_string(title_value, "create_card.title")
    details = details_value if isinstance(details_value, str) else "No details yet."

    if not column_id and not column_title:
        raise AIServiceError('create_card requires "column_id" or "column_title".')

    column_index = _find_column_index_by_id_or_title(
        board,
        column_id=column_id,
        column_title=column_title,
    )
    if column_index is None:
        raise AIServiceError("Could not find the target column for create_card operation.")

    card_id = _create_card_id(board["cards"])
    card: dict[str, Any] = {
        "id": card_id,
        "title": title,
        "details": details,
    }

    label_value = operation.get("label")
    if isinstance(label_value, str) and label_value.strip():
        card["label"] = label_value.strip()

    assignee_value = operation.get("assignee")
    if isinstance(assignee_value, str) and assignee_value.strip():
        card["assignee"] = assignee_value.strip()

    due_date_value = operation.get("due_date")
    if isinstance(due_date_value, str) and due_date_value.strip():
        if not _DATE_PATTERN.match(due_date_value.strip()):
            raise AIServiceError('create_card.due_date must be an ISO date string ("YYYY-MM-DD").')
        card["dueDate"] = due_date_value.strip()

    board["cards"][card_id] = card
    board["columns"][column_index]["cardIds"].append(card_id)


def _apply_optional_clearable_field(card: dict[str, Any], operation: dict[str, Any], field_name: str) -> None:
    """Set, clear, or leave alone one optional string metadata field.

    Absent from ``operation`` -> preserve existing value untouched (this is how
    editing a card keeps its other metadata intact). Explicit ``null`` -> clear
    the field. Non-empty string -> set it.
    """
    if field_name not in operation:
        return

    value = operation[field_name]
    if value is None:
        card.pop(field_name, None)
        return

    if not isinstance(value, str) or not value.strip():
        raise AIServiceError(f"update_card.{field_name} must be a non-empty string or null.")
    card[field_name] = value.strip()


def _apply_due_date_field(card: dict[str, Any], operation: dict[str, Any]) -> None:
    if "due_date" not in operation:
        return

    value = operation["due_date"]
    if value is None:
        card.pop("dueDate", None)
        return

    if not isinstance(value, str) or not _DATE_PATTERN.match(value.strip()):
        raise AIServiceError('update_card.due_date must be an ISO date string ("YYYY-MM-DD") or null.')
    card["dueDate"] = value.strip()


def _validate_and_apply_update_card(board: dict[str, Any], operation: dict[str, Any]) -> None:
    card_id_value = operation.get("card_id")
    card_title_value = operation.get("card_title")

    card_id = card_id_value.strip() if isinstance(card_id_value, str) else None
    card_title = card_title_value.strip() if isinstance(card_title_value, str) else None

    if not card_id and not card_title:
        raise AIServiceError('update_card requires "card_id" or "card_title".')

    resolved_card_id = _find_card_id_by_id_or_title(board, card_id=card_id, card_title=card_title)
    if resolved_card_id is None:
        raise AIServiceError("Could not find the target card for update_card operation.")

    card = board["cards"][resolved_card_id]

    if "title" in operation:
        card["title"] = _require_non_empty_string(operation["title"], "update_card.title")

    if "details" in operation:
        details_value = operation["details"]
        if not isinstance(details_value, str):
            raise AIServiceError("update_card.details must be a string.")
        card["details"] = details_value

    _apply_optional_clearable_field(card, operation, "label")
    _apply_optional_clearable_field(card, operation, "assignee")
    _apply_due_date_field(card, operation)


def _validate_and_apply_delete_card(board: dict[str, Any], operation: dict[str, Any]) -> None:
    card_id_value = operation.get("card_id")
    card_title_value = operation.get("card_title")

    card_id = card_id_value.strip() if isinstance(card_id_value, str) else None
    card_title = card_title_value.strip() if isinstance(card_title_value, str) else None

    if not card_id and not card_title:
        raise AIServiceError('delete_card requires "card_id" or "card_title".')

    resolved_card_id = _find_card_id_by_id_or_title(
        board,
        card_id=card_id,
        card_title=card_title,
    )
    if resolved_card_id is None:
        raise AIServiceError("Could not find the target card for delete_card operation.")

    del board["cards"][resolved_card_id]
    for column in board["columns"]:
        column["cardIds"] = [existing_id for existing_id in column["cardIds"] if existing_id != resolved_card_id]


def _apply_supported_operation(board: dict[str, Any], operation: dict[str, Any]) -> bool:
    operation_type_value = operation.get("type")
    if not isinstance(operation_type_value, str):
        raise AIServiceError('Each operation requires a string "type".')

    operation_type = operation_type_value.strip()
    if operation_type not in SUPPORTED_OPERATION_TYPES:
        return False

    if operation_type == "move_card":
        _validate_and_apply_move_card(board, operation)
        return True

    if operation_type == "rename_column":
        _validate_and_apply_rename_column(board, operation)
        return True

    if operation_type == "create_card":
        _validate_and_apply_create_card(board, operation)
        return True

    if operation_type == "delete_card":
        _validate_and_apply_delete_card(board, operation)
        return True

    if operation_type == "update_card":
        _validate_and_apply_update_card(board, operation)
        return True

    return False


def execute_operations(board_data: dict[str, Any], operations: list[dict[str, Any]]) -> OperationExecutionResult:
    """Apply supported operations as an atomic set on a deep copy.

    Behavior:
    - Unsupported operation types are ignored.
    - Any malformed/invalid supported operation fails the whole set.
    - No partial persistence: caller persists only when this returns success.
    """
    board_copy = copy.deepcopy(board_data)
    supported_applied = False

    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise AIServiceError(f"Operation at index {index} must be an object.")

        applied = _apply_supported_operation(board_copy, operation)
        if applied:
            supported_applied = True

    if not supported_applied:
        return OperationExecutionResult(board=board_data, should_persist=False)

    try:
        validate_board_data(board_copy)
    except ValueError as error:
        raise AIServiceError(str(error))

    return OperationExecutionResult(board=board_copy, should_persist=True)