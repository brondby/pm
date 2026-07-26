"""Tests for FastAPI endpoints including Part 6 board persistence routes."""

from __future__ import annotations

import importlib
import pathlib
import sqlite3
import sys

from fastapi.testclient import TestClient

# Ensure repo root is on sys.path so package imports like ``backend.main`` work.
repo_root = pathlib.Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


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


def _load_main_with_db(monkeypatch, db_path: pathlib.Path):
    monkeypatch.setenv("PM_DB_PATH", str(db_path))

    if "backend.main" in sys.modules:
        del sys.modules["backend.main"]

    main_module = importlib.import_module("backend.main")
    importlib.reload(main_module)
    return main_module


def test_root_returns_html(tmp_path: pathlib.Path, monkeypatch):
    db_path = tmp_path / "test_pm.db"
    main_module = _load_main_with_db(monkeypatch, db_path)

    with TestClient(main_module.app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<html" in response.text.lower()


def test_health_endpoint(tmp_path: pathlib.Path, monkeypatch):
    db_path = tmp_path / "test_pm.db"
    main_module = _load_main_with_db(monkeypatch, db_path)

    with TestClient(main_module.app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sample_endpoint(tmp_path: pathlib.Path, monkeypatch):
    db_path = tmp_path / "test_pm.db"
    main_module = _load_main_with_db(monkeypatch, db_path)

    with TestClient(main_module.app) as client:
        response = client.get("/api/sample")
    assert response.status_code == 200
    assert response.json() == {"message": "sample response"}


def test_get_board_auto_creates_user_and_default_board(tmp_path: pathlib.Path, monkeypatch):
    db_path = tmp_path / "test_pm.db"
    main_module = _load_main_with_db(monkeypatch, db_path)

    with TestClient(main_module.app) as client:
        response = client.get("/api/board/user")
    assert response.status_code == 200
    assert response.json() == {"columns": [], "cards": {}}


def test_get_existing_board_returns_persisted_data(tmp_path: pathlib.Path, monkeypatch):
    db_path = tmp_path / "test_pm.db"
    main_module = _load_main_with_db(monkeypatch, db_path)

    payload = sample_board()

    with TestClient(main_module.app) as client:
        put_response = client.put("/api/board/user", json=payload)
        assert put_response.status_code == 200
        get_response = client.get("/api/board/user")

    assert get_response.status_code == 200
    assert get_response.json() == payload


def test_put_board_updates_existing_board(tmp_path: pathlib.Path, monkeypatch):
    db_path = tmp_path / "test_pm.db"
    main_module = _load_main_with_db(monkeypatch, db_path)

    with TestClient(main_module.app) as client:
        client.get("/api/board/user")

        payload = sample_board()
        payload["cards"]["card-1"]["title"] = "Updated by PUT"

        put_response = client.put("/api/board/user", json=payload)

    assert put_response.status_code == 200
    assert put_response.json()["cards"]["card-1"]["title"] == "Updated by PUT"


def test_put_board_rejects_invalid_payload(tmp_path: pathlib.Path, monkeypatch):
    db_path = tmp_path / "test_pm.db"
    main_module = _load_main_with_db(monkeypatch, db_path)

    invalid_payload = {"columns": [], "cards": []}

    with TestClient(main_module.app) as client:
        response = client.put("/api/board/user", json=invalid_payload)

    assert response.status_code == 400
    assert "board_data.cards must be an object" in response.json()["detail"]


def test_persistence_across_requests_and_clients(tmp_path: pathlib.Path, monkeypatch):
    db_path = tmp_path / "test_pm.db"
    main_module = _load_main_with_db(monkeypatch, db_path)

    payload = sample_board()
    payload["cards"]["card-2"]["details"] = "Persisted detail"

    with TestClient(main_module.app) as first_client:
        put_response = first_client.put("/api/board/user", json=payload)
        assert put_response.status_code == 200

    with TestClient(main_module.app) as second_client:
        get_response = second_client.get("/api/board/user")

    assert get_response.status_code == 200
    assert get_response.json()["cards"]["card-2"]["details"] == "Persisted detail"


def test_startup_bootstrap_creates_missing_database_file(tmp_path: pathlib.Path, monkeypatch):
    db_path = tmp_path / "missing.db"
    assert not db_path.exists()

    main_module = _load_main_with_db(monkeypatch, db_path)

    with TestClient(main_module.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert db_path.exists()


def test_startup_bootstrap_creates_missing_tables(tmp_path: pathlib.Path, monkeypatch):
    db_path = tmp_path / "partial.db"

    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE preexisting (id INTEGER PRIMARY KEY)")
        connection.commit()

    main_module = _load_main_with_db(monkeypatch, db_path)

    with TestClient(main_module.app) as client:
        response = client.get("/health")
    assert response.status_code == 200

    with sqlite3.connect(db_path) as connection:
        table_rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {row[0] for row in table_rows}

    assert "preexisting" in table_names
    assert "users" in table_names
    assert "boards" in table_names


def test_chat_board_rejects_invalid_payload_type(tmp_path: pathlib.Path, monkeypatch):
    db_path = tmp_path / "test_pm.db"
    main_module = _load_main_with_db(monkeypatch, db_path)

    with TestClient(main_module.app) as client:
        response = client.post("/api/board/user/chat", json={"message": 123})

    assert response.status_code == 400
    assert response.json()["detail"] == "message must be a string."


def test_chat_board_applies_valid_ai_operations_and_persists(tmp_path: pathlib.Path, monkeypatch):
    db_path = tmp_path / "test_pm.db"
    main_module = _load_main_with_db(monkeypatch, db_path)

    payload = sample_board()
    updated_board = sample_board()
    updated_board["columns"][0]["title"] = "Ideas"

    monkeypatch.setattr(main_module, "build_system_prompt", lambda: "sys")
    monkeypatch.setattr(main_module, "build_user_prompt", lambda _board, _message: "user")
    monkeypatch.setattr(main_module, "request_openrouter", lambda _sys, _user: {"choices": []})
    monkeypatch.setattr(
        main_module,
        "parse_structured_output",
        lambda _provider: ('Renamed column "Backlog" to "Ideas".', [{"type": "rename_column"}]),
    )

    from backend.ai.operation_executor import OperationExecutionResult

    monkeypatch.setattr(
        main_module,
        "execute_operations",
        lambda _board, _operations: OperationExecutionResult(
            board=updated_board,
            should_persist=True,
        ),
    )

    with TestClient(main_module.app) as first_client:
        put_response = first_client.put("/api/board/user", json=payload)
        assert put_response.status_code == 200

        chat_response = first_client.post(
            "/api/board/user/chat",
            json={"message": "rename backlog"},
        )
        assert chat_response.status_code == 200
        assert chat_response.json()["reply"] == 'Renamed column "Backlog" to "Ideas".'
        assert chat_response.json()["board"]["columns"][0]["title"] == "Ideas"

    with TestClient(main_module.app) as second_client:
        refreshed_response = second_client.get("/api/board/user")

    assert refreshed_response.status_code == 200
    assert refreshed_response.json()["columns"][0]["title"] == "Ideas"


def test_chat_board_returns_friendly_provider_error_without_persisting(tmp_path: pathlib.Path, monkeypatch):
    db_path = tmp_path / "test_pm.db"
    main_module = _load_main_with_db(monkeypatch, db_path)

    from backend.ai.openrouter_ai import AIServiceError

    payload = sample_board()

    monkeypatch.setattr(main_module, "build_system_prompt", lambda: "sys")
    monkeypatch.setattr(main_module, "build_user_prompt", lambda _board, _message: "user")

    def _raise_provider_error(_sys, _user):
        raise AIServiceError("AI request timed out. Please try again.", status_code=502)

    monkeypatch.setattr(main_module, "request_openrouter", _raise_provider_error)

    with TestClient(main_module.app) as client:
        put_response = client.put("/api/board/user", json=payload)
        assert put_response.status_code == 200

        chat_response = client.post("/api/board/user/chat", json={"message": "move card a to b"})
        assert chat_response.status_code == 502
        assert chat_response.json()["detail"] == "AI request timed out. Please try again."

        get_response = client.get("/api/board/user")

    assert get_response.status_code == 200
    assert get_response.json() == payload


def test_chat_board_rejects_malformed_operation_result_without_persisting(
    tmp_path: pathlib.Path, monkeypatch
):
    db_path = tmp_path / "test_pm.db"
    main_module = _load_main_with_db(monkeypatch, db_path)

    from backend.ai.openrouter_ai import AIServiceError

    payload = sample_board()

    monkeypatch.setattr(main_module, "build_system_prompt", lambda: "sys")
    monkeypatch.setattr(main_module, "build_user_prompt", lambda _board, _message: "user")
    monkeypatch.setattr(main_module, "request_openrouter", lambda _sys, _user: {"choices": []})
    monkeypatch.setattr(
        main_module,
        "parse_structured_output",
        lambda _provider: ("Applied.", [{"type": "rename_column"}]),
    )

    def _raise_operation_error(_board, _operations):
        raise AIServiceError('rename_column requires "column_id" or "column_title".')

    monkeypatch.setattr(main_module, "execute_operations", _raise_operation_error)

    with TestClient(main_module.app) as client:
        put_response = client.put("/api/board/user", json=payload)
        assert put_response.status_code == 200

        chat_response = client.post("/api/board/user/chat", json={"message": "anything"})
        assert chat_response.status_code == 400
        assert 'rename_column requires "column_id" or "column_title".' in chat_response.json()["detail"]

        get_response = client.get("/api/board/user")

    assert get_response.status_code == 200
    assert get_response.json() == payload


def test_chat_board_reply_only_result_does_not_persist_changes(tmp_path: pathlib.Path, monkeypatch):
    db_path = tmp_path / "test_pm.db"
    main_module = _load_main_with_db(monkeypatch, db_path)

    payload = sample_board()
    unchanged_board = sample_board()

    monkeypatch.setattr(main_module, "build_system_prompt", lambda: "sys")
    monkeypatch.setattr(main_module, "build_user_prompt", lambda _board, _message: "user")
    monkeypatch.setattr(main_module, "request_openrouter", lambda _sys, _user: {"choices": []})
    monkeypatch.setattr(
        main_module,
        "parse_structured_output",
        lambda _provider: ("I reviewed your board. No changes needed.", [{"type": "archive_card"}]),
    )

    from backend.ai.operation_executor import OperationExecutionResult

    monkeypatch.setattr(
        main_module,
        "execute_operations",
        lambda _board, _operations: OperationExecutionResult(
            board=unchanged_board,
            should_persist=False,
        ),
    )

    with TestClient(main_module.app) as client:
        put_response = client.put("/api/board/user", json=payload)
        assert put_response.status_code == 200

        chat_response = client.post("/api/board/user/chat", json={"message": "summarize board"})
        assert chat_response.status_code == 200
        assert chat_response.json()["reply"] == "I reviewed your board. No changes needed."

        get_response = client.get("/api/board/user")

    assert get_response.status_code == 200
    assert get_response.json() == payload
