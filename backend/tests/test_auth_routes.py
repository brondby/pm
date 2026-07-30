"""Integration tests for Part 11 auth routes (/api/auth/*)."""

from __future__ import annotations

import importlib
import pathlib
import sys

from fastapi.testclient import TestClient

# Ensure repo root is on sys.path so package imports like ``backend.main`` work.
repo_root = pathlib.Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


def _load_main_with_db(monkeypatch, db_path: pathlib.Path):
    monkeypatch.setenv("PM_DB_PATH", str(db_path))

    if "backend.main" in sys.modules:
        del sys.modules["backend.main"]

    main_module = importlib.import_module("backend.main")
    importlib.reload(main_module)
    return main_module


def test_signup_creates_account_and_session(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/auth/signup", json={"username": "alice", "password": "s3cret"}
        )
        assert response.status_code == 200
        assert response.json() == {"username": "alice"}
        assert "pm_session" in response.cookies

        me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json() == {"username": "alice"}


def test_signup_rejects_duplicate_username(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        client.post("/api/auth/signup", json={"username": "alice", "password": "s3cret"})
        response = client.post(
            "/api/auth/signup", json={"username": "alice", "password": "different"}
        )

    assert response.status_code == 409


def test_login_succeeds_with_correct_credentials(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        client.post("/api/auth/signup", json={"username": "alice", "password": "s3cret"})
        client.post("/api/auth/logout")

        response = client.post(
            "/api/auth/login", json={"username": "alice", "password": "s3cret"}
        )
    assert response.status_code == 200
    assert response.json() == {"username": "alice"}


def test_login_rejects_wrong_password(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        client.post("/api/auth/signup", json={"username": "alice", "password": "s3cret"})

        response = client.post(
            "/api/auth/login", json={"username": "alice", "password": "wrong"}
        )
    assert response.status_code == 401


def test_login_unknown_user_matches_wrong_password_response(
    tmp_path: pathlib.Path, monkeypatch
):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        client.post("/api/auth/signup", json={"username": "alice", "password": "s3cret"})

        wrong_password_response = client.post(
            "/api/auth/login", json={"username": "alice", "password": "wrong"}
        )
        unknown_user_response = client.post(
            "/api/auth/login", json={"username": "nobody", "password": "wrong"}
        )

    assert wrong_password_response.status_code == unknown_user_response.status_code == 401
    assert wrong_password_response.json() == unknown_user_response.json()


def test_logout_invalidates_session(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        client.post("/api/auth/signup", json={"username": "alice", "password": "s3cret"})
        logout_response = client.post("/api/auth/logout")
        assert logout_response.status_code == 200

        me_response = client.get("/api/auth/me")
    assert me_response.status_code == 401


def test_me_requires_authentication(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_rejects_tampered_cookie(tmp_path: pathlib.Path, monkeypatch):
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        client.cookies.set("pm_session", "not-a-real-token")
        response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_old_username_scoped_board_routes_are_gone(tmp_path: pathlib.Path, monkeypatch):
    """Part 13 removes the legacy trust-the-path-param routes entirely (see test_boards_routes.py)."""
    main_module = _load_main_with_db(monkeypatch, tmp_path / "test_pm.db")

    with TestClient(main_module.app) as client:
        response = client.get("/api/board/someone")
    assert response.status_code == 404
