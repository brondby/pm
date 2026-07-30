"""Tests for FastAPI endpoints not covered by a more specific test file.

Board routes moved to ``test_boards_routes.py`` and auth routes to
``test_auth_routes.py`` as of Part 13, when the old ``/api/board/{username}``
routes were removed in favor of session-scoped ``/api/boards*``.
"""

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
