"""FastAPI application serving the exported frontend and API routes.

Routes:

* ``GET /`` – serves the exported Next.js Kanban app.
* ``GET /health`` – health-check JSON response.
* ``GET /api/sample`` – a simple JSON payload.
* ``GET /api/board/{username}`` – returns a user's board, auto-creating user/board.
* ``PUT /api/board/{username}`` – replaces a user's board with validated payload.
* ``POST /api/board/{username}/chat`` – applies AI-generated structured board operations.

Static frontend assets are served from ``backend/static``.
"""

from __future__ import annotations

import pathlib
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .ai.openrouter_ai import AIServiceError, parse_structured_output, request_openrouter
from .ai.operation_executor import execute_operations
from .ai.prompt_builder import build_system_prompt, build_user_prompt
from .db import (
    create_board,
    create_user,
    get_board_by_user_id,
    get_connection,
    get_user_by_username,
    init_db,
    update_board,
    validate_board_data,
)

app = FastAPI()

static_path = pathlib.Path(__file__).parent / "static"
next_static_path = static_path / "_next"

DEFAULT_BOARD_DATA = {"columns": [], "cards": {}}
DEFAULT_PASSWORD_HASH = "mvp_dummy_password_hash"


def _normalize_username(username: str) -> str:
    normalized = username.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="username must be a non-empty string.")
    return normalized


def _ensure_user_and_board(connection: Any, username: str) -> tuple[int, dict[str, Any]]:
    user = get_user_by_username(connection, username)

    if user is None:
        user_id = create_user(connection, username, DEFAULT_PASSWORD_HASH)
        create_board(connection, user_id, DEFAULT_BOARD_DATA)
        board = get_board_by_user_id(connection, user_id)
        return user_id, board["board_data"]

    user_id = int(user["id"])
    board = get_board_by_user_id(connection, user_id)

    if board is None:
        create_board(connection, user_id, DEFAULT_BOARD_DATA)
        board = get_board_by_user_id(connection, user_id)

    return user_id, board["board_data"]


@app.on_event("startup")
def startup_event() -> None:
    """Ensure database and tables exist on application startup."""
    init_db()


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


@app.get("/api/board/{username}")
def get_board(username: str):
    """Return board for ``username``, auto-creating user and default board if missing."""
    normalized_username = _normalize_username(username)

    try:
        with get_connection() as connection:
            _, board_data = _ensure_user_and_board(connection, normalized_username)
            return JSONResponse(content=board_data)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected server error.")


@app.put("/api/board/{username}")
async def put_board(username: str, request: Request):
    """Replace board for ``username`` with validated board JSON payload."""
    normalized_username = _normalize_username(username)

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    try:
        validate_board_data(payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    try:
        with get_connection() as connection:
            user_id, _ = _ensure_user_and_board(connection, normalized_username)
            update_board(connection, user_id, payload)
            board = get_board_by_user_id(connection, user_id)
            return JSONResponse(content=board["board_data"])
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected server error.")


@app.post("/api/board/{username}/chat")
async def chat_board(username: str, request: Request):
    """Apply AI-generated structured operations to a user's board."""
    normalized_username = _normalize_username(username)

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    message = payload.get("message") if isinstance(payload, dict) else None
    if not isinstance(message, str):
        raise HTTPException(status_code=400, detail="message must be a string.")

    try:
        with get_connection() as connection:
            user_id, board_data = _ensure_user_and_board(connection, normalized_username)

            system_prompt = build_system_prompt()
            user_prompt = build_user_prompt(board_data, message)
            provider_payload = request_openrouter(system_prompt, user_prompt)
            reply, operations = parse_structured_output(provider_payload)
            execution_result = execute_operations(board_data, operations)

            if execution_result.should_persist:
                update_board(connection, user_id, execution_result.board)

            board = get_board_by_user_id(connection, user_id)
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
