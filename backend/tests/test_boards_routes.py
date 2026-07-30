"""Integration tests for Part 13 multi-board routes (/api/boards*).

Covers CRUD, the zero-board state, and - critically - the ownership
isolation matrix: every mutating verb must 404 (never 403, never leak
whether the board exists) when the caller doesn't own the board, and the
chat route must verify ownership before ever calling OpenRouter.
"""

from __future__ import annotations

import importlib
import pathlib
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
        ],
        "cards": {
            "card-1": {"id": "card-1", "title": "Plan release", "details": "Draft milestones."},
        },
    }


def _load_main_with_db(monkeypatch, db_path: pathlib.Path):
    monkeypatch.setenv("PM_DB_PATH", str(db_path))

    if "backend.main" in sys.modules:
        del sys.modules["backend.main"]

    main_module = importlib.import_module("backend.main")
    importlib.reload(main_module)
    return main_module


def _signup(client: TestClient, username: str, password: str = "s3cret-pass") -> dict:
    response = client.post("/api/auth/signup", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()


def _default_board_id(client: TestClient) -> int:
    """Every signup seeds exactly one board; return its id."""
    boards = client.get("/api/boards").json()
    assert len(boards) == 1
    return boards[0]["id"]


# --- CRUD ---------------------------------------------------------------


def test_signup_seeds_exactly_one_default_board(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        _signup(client, "alice")
        boards = client.get("/api/boards").json()

    assert len(boards) == 1
    assert boards[0]["name"] == "My Board"
    assert boards[0]["is_archived"] is False


def test_list_boards_excludes_board_data(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        _signup(client, "alice")
        boards = client.get("/api/boards").json()

    assert set(boards[0].keys()) == {"id", "name", "is_archived", "created_at", "updated_at"}


def test_create_board_adds_a_second_board(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        _signup(client, "alice")
        create_response = client.post("/api/boards", json={"name": "Side Project"})
        assert create_response.status_code == 200

        boards = client.get("/api/boards").json()

    assert {board["name"] for board in boards} == {"My Board", "Side Project"}


def test_create_board_rejects_empty_name(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        _signup(client, "alice")
        response = client.post("/api/boards", json={"name": "   "})

    assert response.status_code == 400


def test_get_board_returns_board_data(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        _signup(client, "alice")
        board_id = _default_board_id(client)
        response = client.get(f"/api/boards/{board_id}")

    assert response.status_code == 200
    assert response.json() == {"columns": [], "cards": {}}


def test_put_board_persists_data(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        _signup(client, "alice")
        board_id = _default_board_id(client)

        put_response = client.put(f"/api/boards/{board_id}", json=sample_board())
        assert put_response.status_code == 200

        get_response = client.get(f"/api/boards/{board_id}")

    assert get_response.json() == sample_board()


def test_put_board_rejects_invalid_payload(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        _signup(client, "alice")
        board_id = _default_board_id(client)

        response = client.put(f"/api/boards/{board_id}", json={"columns": [], "cards": []})

    assert response.status_code == 400
    assert "board_data.cards must be an object" in response.json()["detail"]


def test_patch_board_renames(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        _signup(client, "alice")
        board_id = _default_board_id(client)

        response = client.patch(f"/api/boards/{board_id}", json={"name": "Renamed"})

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_patch_board_archives(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        _signup(client, "alice")
        board_id = _default_board_id(client)

        response = client.patch(f"/api/boards/{board_id}", json={"is_archived": True})

    assert response.status_code == 200
    assert response.json()["is_archived"] is True


def test_patch_board_requires_at_least_one_field(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        _signup(client, "alice")
        board_id = _default_board_id(client)

        response = client.patch(f"/api/boards/{board_id}", json={})

    assert response.status_code == 400


def test_delete_board_removes_it(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        _signup(client, "alice")
        board_id = _default_board_id(client)
        second_board = client.post("/api/boards", json={"name": "Second"}).json()

        delete_response = client.delete(f"/api/boards/{board_id}")
        assert delete_response.status_code == 200

        boards = client.get("/api/boards").json()

    assert [board["id"] for board in boards] == [second_board["id"]]


def test_deleting_the_final_board_does_not_auto_create_a_replacement(
    tmp_path: pathlib.Path, monkeypatch
):
    """A deliberate zero-board state must be reachable - no silent auto-provisioning."""
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        _signup(client, "alice")
        board_id = _default_board_id(client)

        client.delete(f"/api/boards/{board_id}")
        boards = client.get("/api/boards").json()

    assert boards == []


def test_get_missing_board_returns_404(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        _signup(client, "alice")
        response = client.get("/api/boards/999999")

    assert response.status_code == 404


# --- Ownership isolation matrix -----------------------------------------


def test_get_other_users_board_returns_404(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as owner_client:
        _signup(owner_client, "alice")
        board_id = _default_board_id(owner_client)

    with TestClient(main_module.app) as other_client:
        _signup(other_client, "bob")
        response = other_client.get(f"/api/boards/{board_id}")

    assert response.status_code == 404


def test_put_other_users_board_returns_404(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as owner_client:
        _signup(owner_client, "alice")
        board_id = _default_board_id(owner_client)

    with TestClient(main_module.app) as other_client:
        _signup(other_client, "bob")
        response = other_client.put(f"/api/boards/{board_id}", json=sample_board())

    assert response.status_code == 404


def test_patch_other_users_board_returns_404(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as owner_client:
        _signup(owner_client, "alice")
        board_id = _default_board_id(owner_client)

    with TestClient(main_module.app) as other_client:
        _signup(other_client, "bob")
        response = other_client.patch(f"/api/boards/{board_id}", json={"name": "Hijacked"})

    assert response.status_code == 404


def test_delete_other_users_board_returns_404(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as owner_client:
        _signup(owner_client, "alice")
        board_id = _default_board_id(owner_client)

    with TestClient(main_module.app) as other_client:
        _signup(other_client, "bob")
        response = other_client.delete(f"/api/boards/{board_id}")

    assert response.status_code == 404

    # Confirm it genuinely wasn't deleted, by logging back in as the owner.
    with TestClient(main_module.app) as owner_login_client:
        owner_login_client.post(
            "/api/auth/login", json={"username": "alice", "password": "s3cret-pass"}
        )
        still_there = owner_login_client.get(f"/api/boards/{board_id}")

    assert still_there.status_code == 200


def test_chat_other_users_board_returns_404_and_never_calls_openrouter(
    tmp_path: pathlib.Path, monkeypatch
):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    calls: list[object] = []
    monkeypatch.setattr(
        main_module,
        "request_openrouter",
        lambda *args, **kwargs: calls.append(1) or {"choices": []},
    )

    with TestClient(main_module.app) as owner_client:
        _signup(owner_client, "alice")
        board_id = _default_board_id(owner_client)

    with TestClient(main_module.app) as other_client:
        _signup(other_client, "bob")
        response = other_client.post(
            f"/api/boards/{board_id}/chat", json={"message": "steal this board"}
        )

    assert response.status_code == 404
    assert calls == []


# --- Unauthenticated access ----------------------------------------------


def test_boards_routes_require_authentication(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        assert client.get("/api/boards").status_code == 401
        assert client.post("/api/boards", json={"name": "x"}).status_code == 401
        assert client.get("/api/boards/1").status_code == 401
        assert client.put("/api/boards/1", json=sample_board()).status_code == 401
        assert client.patch("/api/boards/1", json={"name": "x"}).status_code == 401
        assert client.delete("/api/boards/1").status_code == 401
        assert client.post("/api/boards/1/chat", json={"message": "hi"}).status_code == 401


# --- Chat happy path (scoped to a board id, mocked AI) -------------------


def test_chat_applies_ai_operations_and_persists_to_the_right_board(
    tmp_path: pathlib.Path, monkeypatch
):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

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
        lambda _board, _operations: OperationExecutionResult(board=updated_board, should_persist=True),
    )

    with TestClient(main_module.app) as client:
        _signup(client, "alice")
        board_id = _default_board_id(client)
        client.put(f"/api/boards/{board_id}", json=sample_board())

        chat_response = client.post(
            f"/api/boards/{board_id}/chat", json={"message": "rename backlog"}
        )
        assert chat_response.status_code == 200
        assert chat_response.json()["reply"] == 'Renamed column "Backlog" to "Ideas".'
        assert chat_response.json()["board"]["columns"][0]["title"] == "Ideas"

        refreshed = client.get(f"/api/boards/{board_id}")

    assert refreshed.json()["columns"][0]["title"] == "Ideas"
