"""One-time seed utility for the MVP demo board.

This script initializes the database (if needed) and replaces the board for
username "user" with the original frontend demo board data.

It does not modify boards for any other user.
"""

from __future__ import annotations

from .db import (
    create_board,
    create_user,
    get_board_by_user_id,
    get_connection,
    get_user_by_username,
    init_db,
    update_board,
)

DEMO_USERNAME = "user"
DEMO_PASSWORD_HASH = "mvp_dummy_password_hash"

DEMO_BOARD_DATA = {
    "columns": [
        {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
        {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
        {"id": "col-progress", "title": "In Progress", "cardIds": ["card-4", "card-5"]},
        {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
        {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
    ],
    "cards": {
        "card-1": {
            "id": "card-1",
            "title": "Align roadmap themes",
            "details": "Draft quarterly themes with impact statements and metrics.",
        },
        "card-2": {
            "id": "card-2",
            "title": "Gather customer signals",
            "details": "Review support tags, sales notes, and churn feedback.",
        },
        "card-3": {
            "id": "card-3",
            "title": "Prototype analytics view",
            "details": "Sketch initial dashboard layout and key drill-downs.",
        },
        "card-4": {
            "id": "card-4",
            "title": "Refine status language",
            "details": "Standardize column labels and tone across the board.",
        },
        "card-5": {
            "id": "card-5",
            "title": "Design card layout",
            "details": "Add hierarchy and spacing for scanning dense lists.",
        },
        "card-6": {
            "id": "card-6",
            "title": "QA micro-interactions",
            "details": "Verify hover, focus, and loading states.",
        },
        "card-7": {
            "id": "card-7",
            "title": "Ship marketing page",
            "details": "Final copy approved and asset pack delivered.",
        },
        "card-8": {
            "id": "card-8",
            "title": "Close onboarding sprint",
            "details": "Document release notes and share internally.",
        },
    },
}


def seed_demo_board() -> None:
    init_db()

    with get_connection() as connection:
        user = get_user_by_username(connection, DEMO_USERNAME)
        if user is None:
            user_id = create_user(connection, DEMO_USERNAME, DEMO_PASSWORD_HASH)
        else:
            user_id = int(user["id"])

        board = get_board_by_user_id(connection, user_id)
        if board is None:
            create_board(connection, user_id, DEMO_BOARD_DATA)
        else:
            update_board(connection, user_id, DEMO_BOARD_DATA)


if __name__ == "__main__":
    seed_demo_board()
    print("Seeded demo board for username 'user'.")