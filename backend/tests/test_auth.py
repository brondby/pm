"""Unit tests for Part 11 auth helpers (backend/auth.py) and the password migration."""

from __future__ import annotations

import pathlib
import sys
from datetime import datetime, timedelta, timezone

# Ensure repo root is on sys.path so package imports like ``backend.auth`` work.
repo_root = pathlib.Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend import auth, db, migrations  # noqa: E402


def test_hash_password_roundtrip():
    hashed = auth.hash_password("correct horse")
    assert auth.verify_password("correct horse", hashed)


def test_verify_password_rejects_wrong_password():
    hashed = auth.hash_password("correct horse")
    assert not auth.verify_password("wrong password", hashed)


def test_hash_password_uses_distinct_salts():
    first = auth.hash_password("same password")
    second = auth.hash_password("same password")
    assert first != second


def test_verify_password_rejects_malformed_hash():
    assert not auth.verify_password("anything", "not-a-real-bcrypt-hash")


def _connection(tmp_path: pathlib.Path):
    db_path = tmp_path / "test_pm.db"
    db.init_db(db_path)
    return db.get_connection(db_path)


def test_create_session_then_get_session_user(tmp_path: pathlib.Path):
    with _connection(tmp_path) as connection:
        user_id = db.create_user(connection, "alice", auth.hash_password("pw"))

        token, _ = auth.create_session(connection, user_id)
        session_user = auth.get_session_user(connection, token)

    assert session_user == {"user_id": user_id, "username": "alice"}


def test_get_session_user_rejects_unknown_token(tmp_path: pathlib.Path):
    with _connection(tmp_path) as connection:
        assert auth.get_session_user(connection, "not-a-real-token") is None


def test_get_session_user_rejects_expired_session(tmp_path: pathlib.Path):
    with _connection(tmp_path) as connection:
        user_id = db.create_user(connection, "alice", auth.hash_password("pw"))

        expired = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        db.insert_session(connection, "expired-token", user_id, expired)

        assert auth.get_session_user(connection, "expired-token") is None


def test_delete_session_invalidates_token(tmp_path: pathlib.Path):
    with _connection(tmp_path) as connection:
        user_id = db.create_user(connection, "alice", auth.hash_password("pw"))
        token, _ = auth.create_session(connection, user_id)

        auth.delete_session(connection, token)

        assert auth.get_session_user(connection, token) is None


def test_upgrade_legacy_password_hashes_replaces_sentinel(tmp_path: pathlib.Path):
    db_path = tmp_path / "test_pm.db"
    db.init_db(db_path)

    with db.get_connection(db_path) as connection:
        db.create_user(connection, "user", migrations.LEGACY_PASSWORD_HASH)

    with db.get_connection(db_path) as connection:
        migrations.upgrade_legacy_password_hashes(connection, db_path)

    with db.get_connection(db_path) as connection:
        user = db.get_user_by_username(connection, "user")

    assert user["password_hash"] != migrations.LEGACY_PASSWORD_HASH
    assert auth.verify_password(migrations.LEGACY_DEMO_PASSWORD, user["password_hash"])

    backups = list(tmp_path.glob("test_pm.db.*.bak"))
    assert len(backups) == 1


def test_upgrade_legacy_password_hashes_is_idempotent(tmp_path: pathlib.Path):
    db_path = tmp_path / "test_pm.db"
    db.init_db(db_path)

    with db.get_connection(db_path) as connection:
        db.create_user(connection, "user", migrations.LEGACY_PASSWORD_HASH)

    with db.get_connection(db_path) as connection:
        migrations.upgrade_legacy_password_hashes(connection, db_path)

    with db.get_connection(db_path) as connection:
        migrations.upgrade_legacy_password_hashes(connection, db_path)

    # Second run found nothing left to migrate, so it must not create another backup.
    backups = list(tmp_path.glob("test_pm.db.*.bak"))
    assert len(backups) == 1


def test_upgrade_legacy_password_hashes_skips_real_hashes(tmp_path: pathlib.Path):
    db_path = tmp_path / "test_pm.db"
    db.init_db(db_path)

    real_hash = auth.hash_password("already-real")
    with db.get_connection(db_path) as connection:
        db.create_user(connection, "user", real_hash)
        migrations.upgrade_legacy_password_hashes(connection, db_path)

    with db.get_connection(db_path) as connection:
        user = db.get_user_by_username(connection, "user")

    assert user["password_hash"] == real_hash
    assert not list(tmp_path.glob("test_pm.db.*.bak"))
