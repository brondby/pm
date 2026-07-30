"""FastAPI application serving the exported frontend and API routes.

Routes:

* ``GET /`` – serves the exported Next.js Kanban app.
* ``GET /health`` – health-check JSON response.
* ``GET /api/sample`` – a simple JSON payload.
* ``POST /api/auth/signup`` – creates a real account and starts a session.
* ``POST /api/auth/login`` – verifies credentials and starts a session.
* ``POST /api/auth/logout`` – invalidates the current session.
* ``GET /api/auth/me`` – returns the current session's username, or 401.
* ``GET /api/boards`` – lists the current user's boards (metadata only, no board_data).
* ``POST /api/boards`` – creates a new board owned by the current user.
* ``GET /api/boards/{board_id}`` – returns one board's data; 404 if missing or not owned.
* ``PUT /api/boards/{board_id}`` – replaces a board's data with a validated payload.
* ``PATCH /api/boards/{board_id}`` – renames and/or archives/unarchives a board.
* ``DELETE /api/boards/{board_id}`` – permanently deletes a board.
* ``POST /api/boards/{board_id}/chat`` – applies AI-generated structured board operations.

All ``/api/boards*`` and ``/api/auth/me`` routes require a valid session cookie. Ownership is
enforced directly in SQL (``WHERE id = ? AND user_id = ?``); a board that doesn't exist and a
board owned by someone else are indistinguishable from the outside - both return 404.

Static frontend assets are served from ``backend/static``.
"""

from __future__ import annotations

import pathlib
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import auth
from .ai.openrouter_ai import AIServiceError, parse_structured_output, request_openrouter
from .ai.operation_executor import execute_operations
from .ai.prompt_builder import build_system_prompt, build_user_prompt
from .db import (
    create_board,
    create_user,
    delete_board,
    get_board,
    get_connection,
    get_user_by_username,
    init_db,
    list_boards,
    patch_board,
    update_board_data,
    validate_board_data,
)
from .migrations import run_migrations

app = FastAPI()

static_path = pathlib.Path(__file__).parent / "static"
next_static_path = static_path / "_next"

DEFAULT_BOARD_DATA = {"columns": [], "cards": {}}


@app.on_event("startup")
def startup_event() -> None:
    """Ensure database and tables exist, then run one-time data migrations."""
    db_path = init_db()
    with get_connection(db_path) as connection:
        run_migrations(connection, db_path)


def get_current_user(request: Request) -> dict[str, Any]:
    """FastAPI dependency: resolve the session cookie to a user, or 401."""
    token = request.cookies.get(auth.SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    with get_connection() as connection:
        session_user = auth.get_session_user(connection, token)

    if session_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    return session_user


def _set_session_cookie(response: JSONResponse, token: str) -> None:
    response.set_cookie(
        key=auth.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=auth.SESSION_TTL_DAYS * 24 * 60 * 60,
        path="/",
    )


@app.post("/api/auth/signup")
async def signup(request: Request):
    """Create a new user account and start a session."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    username = payload.get("username") if isinstance(payload, dict) else None
    password = payload.get("password") if isinstance(payload, dict) else None
    if not isinstance(username, str) or not username.strip():
        raise HTTPException(status_code=400, detail="username must be a non-empty string.")
    if not isinstance(password, str) or not password:
        raise HTTPException(status_code=400, detail="password must be a non-empty string.")

    normalized_username = username.strip()

    try:
        with get_connection() as connection:
            if get_user_by_username(connection, normalized_username) is not None:
                raise HTTPException(status_code=409, detail="Username is already taken.")

            password_hash = auth.hash_password(password)
            user_id = create_user(connection, normalized_username, password_hash)
            create_board(connection, user_id, DEFAULT_BOARD_DATA)
            token, _ = auth.create_session(connection, user_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected server error.")

    result = JSONResponse(content={"username": normalized_username})
    _set_session_cookie(result, token)
    return result


@app.post("/api/auth/login")
async def login(request: Request):
    """Verify credentials and start a session."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    username = payload.get("username") if isinstance(payload, dict) else None
    password = payload.get("password") if isinstance(payload, dict) else None
    if not isinstance(username, str) or not isinstance(password, str):
        raise HTTPException(status_code=400, detail="username and password are required.")

    invalid_credentials = HTTPException(status_code=401, detail="Invalid username or password.")

    try:
        with get_connection() as connection:
            user = get_user_by_username(connection, username.strip())
            if user is None or not auth.verify_password(password, user["password_hash"]):
                raise invalid_credentials

            token, _ = auth.create_session(connection, user["id"])
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected server error.")

    result = JSONResponse(content={"username": user["username"]})
    _set_session_cookie(result, token)
    return result


@app.post("/api/auth/logout")
def logout(request: Request):
    """Invalidate the current session, if any."""
    token = request.cookies.get(auth.SESSION_COOKIE_NAME)
    if token:
        with get_connection() as connection:
            auth.delete_session(connection, token)

    result = JSONResponse(content={"ok": True})
    result.delete_cookie(key=auth.SESSION_COOKIE_NAME, path="/")
    return result


@app.get("/api/auth/me")
def get_me(current_user: dict[str, Any] = Depends(get_current_user)):
    """Return the currently authenticated username."""
    return JSONResponse(content={"username": current_user["username"]})


# Serve Next.js hashed assets (/_next/static/...)
app.mount(
    "/_next",
    StaticFiles(directory=next_static_path, check_dir=False),
    name="next-assets",
)

# Serve other exported static files (favicon, svgs, txt files, etc.)
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/", response_class=FileResponse)
def read_root():
    """Serve the static ``index.html`` as the homepage.

    FastAPI will locate the file relative to the ``static`` directory.
    """
    return static_path / "index.html"


@app.get("/health")
def health_check():
    """Simple health-check endpoint used by the test suite."""
    return JSONResponse(content={"status": "ok"})


@app.get("/api/sample")
def sample_endpoint():
    """A sample API route returning a static JSON payload."""
    return JSONResponse(content={"message": "sample response"})


def _get_owned_board_or_404(connection: Any, user_id: int, board_id: int) -> dict[str, Any]:
    """Fetch a board the current user owns, or raise 404.

    A missing board and a board owned by someone else must be
    indistinguishable from the caller's perspective - both 404.
    """
    board = get_board(connection, user_id, board_id)
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found.")
    return board


@app.get("/api/boards")
def list_boards_route(current_user: dict[str, Any] = Depends(get_current_user)):
    """List the current user's boards (metadata only, no board_data)."""
    with get_connection() as connection:
        boards = list_boards(connection, current_user["user_id"])
    return JSONResponse(content=boards)


@app.post("/api/boards")
async def create_board_route(
    request: Request, current_user: dict[str, Any] = Depends(get_current_user)
):
    """Create a new, empty board owned by the current user."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    name = payload.get("name") if isinstance(payload, dict) else None
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=400, detail="name must be a non-empty string.")

    with get_connection() as connection:
        board_id = create_board(connection, current_user["user_id"], DEFAULT_BOARD_DATA, name.strip())
        boards = list_boards(connection, current_user["user_id"])

    created = next(board for board in boards if board["id"] == board_id)
    return JSONResponse(content=created)


@app.get("/api/boards/{board_id}")
def get_board_route(board_id: int, current_user: dict[str, Any] = Depends(get_current_user)):
    """Return one board's data; 404 if missing or not owned by the current user."""
    with get_connection() as connection:
        board = _get_owned_board_or_404(connection, current_user["user_id"], board_id)
    return JSONResponse(content=board["board_data"])


@app.put("/api/boards/{board_id}")
async def put_board_route(
    board_id: int, request: Request, current_user: dict[str, Any] = Depends(get_current_user)
):
    """Replace a board's data with a validated payload."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    try:
        validate_board_data(payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    with get_connection() as connection:
        updated = update_board_data(connection, current_user["user_id"], board_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Board not found.")
        board = _get_owned_board_or_404(connection, current_user["user_id"], board_id)

    return JSONResponse(content=board["board_data"])


@app.patch("/api/boards/{board_id}")
async def patch_board_route(
    board_id: int, request: Request, current_user: dict[str, Any] = Depends(get_current_user)
):
    """Rename and/or archive/unarchive a board."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    name = payload.get("name")
    is_archived = payload.get("is_archived")

    if name is not None and (not isinstance(name, str) or not name.strip()):
        raise HTTPException(status_code=400, detail="name must be a non-empty string.")
    if is_archived is not None and not isinstance(is_archived, bool):
        raise HTTPException(status_code=400, detail="is_archived must be a boolean.")
    if name is None and is_archived is None:
        raise HTTPException(
            status_code=400, detail="At least one of name or is_archived must be provided."
        )

    with get_connection() as connection:
        updated = patch_board(
            connection,
            current_user["user_id"],
            board_id,
            name=name.strip() if name is not None else None,
            is_archived=is_archived,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Board not found.")

        boards = list_boards(connection, current_user["user_id"])

    result = next(board for board in boards if board["id"] == board_id)
    return JSONResponse(content=result)


@app.delete("/api/boards/{board_id}")
def delete_board_route(board_id: int, current_user: dict[str, Any] = Depends(get_current_user)):
    """Permanently delete a board."""
    with get_connection() as connection:
        deleted = delete_board(connection, current_user["user_id"], board_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Board not found.")
    return JSONResponse(content={"ok": True})


@app.post("/api/boards/{board_id}/chat")
async def chat_board_route(
    board_id: int, request: Request, current_user: dict[str, Any] = Depends(get_current_user)
):
    """Apply AI-generated structured operations to a board."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    message = payload.get("message") if isinstance(payload, dict) else None
    if not isinstance(message, str):
        raise HTTPException(status_code=400, detail="message must be a string.")

    try:
        with get_connection() as connection:
            user_id = current_user["user_id"]
            # Ownership must be verified before the OpenRouter call, so a
            # cross-user probe against someone else's board never burns an
            # AI request before being rejected.
            board = _get_owned_board_or_404(connection, user_id, board_id)
            board_data = board["board_data"]

            system_prompt = build_system_prompt()
            user_prompt = build_user_prompt(board_data, message)
            provider_payload = request_openrouter(system_prompt, user_prompt)
            reply, operations = parse_structured_output(provider_payload)
            execution_result = execute_operations(board_data, operations)

            if execution_result.should_persist:
                update_board_data(connection, user_id, board_id, execution_result.board)
                board = _get_owned_board_or_404(connection, user_id, board_id)

            return JSONResponse(
                content={
                    "reply": reply,
                    "board": board["board_data"],
                }
            )
    except AIServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected server error.")


# Keep this route last so API endpoints above stay authoritative.
app.mount("/", StaticFiles(directory=static_path, html=True), name="frontend")
