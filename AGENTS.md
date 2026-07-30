# The Project Management MVP web app

## Business Requirements

This project is building a Project Management App. Key features:
- A user can sign in
- When signed in, the user sees a Kanban board representing their project
- The Kanban board has fixed columns that can be renamed
- The cards on the Kanban board can be moved with drag and drop, and edited
- There is an AI chat feature in a sidebar; the AI is able to create / edit / move one or more cards

## Limitations

As of Part 11/12, sign-in is real (per-user accounts, bcrypt-hashed passwords, server-side sessions) rather
than the original hardcoded MVP credential - see `docs/PLAN.md`.

As of Part 13, users may have multiple Kanban boards (create/rename/archive/delete/switch), not just one.

As of Part 14, cards may optionally carry a label, due date, and assignee, in addition to title/details.

This still runs locally only (in a Docker container) - no hosted/multi-tenant deployment story exists yet.

## Technical Decisions

- NextJS frontend
- Python FastAPI backend, including serving the static NextJS site at /
- Everything packaged into a Docker container
- Use "uv" as the package manager for python in the Docker container
- Use OpenRouter for the AI calls. An OPENROUTER_API_KEY is in .env in the project root
- Use `openai/gpt-oss-120b` as the model
- Use SQLLite local database for the database, creating a new db if it doesn't exist
- Start and Stop server scripts for Mac, PC, Linux in scripts/

## Starting Point (historical)

The project began from a pure frontend-only Kanban demo in `frontend/`, with no Docker/backend wiring yet.
Docker packaging, the FastAPI backend, and real persistence were added starting in Part 2 of `docs/PLAN.md` -
this section is kept only as a record of the initial hand-off state, not the current architecture.

## Color Scheme

- Accent Yellow: `#ecad0a` - accent lines, highlights
- Blue Primary: `#209dd7` - links, key sections
- Purple Secondary: `#753991` - submit buttons, important actions
- Dark Navy: `#032147` - main headings
- Gray Text: `#888888` - supporting text, labels

## Coding standards

1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever
4. When hitting issues, always identify root cause before trying a fix. Do not guess. Prove with evidence, then fix the root cause.

## Working documentation

All documents for planning and executing this project will be in the docs/ directory.
Please review the docs/PLAN.md document before proceeding.

Before implementing any feature:

1. Read AGENTS.md
2. Read docs/PLAN.md
3. Explain the implementation plan.
4. Wait for approval before creating or modifying files.

After implementation:

- Run tests.
- Run the build.
- Fix all errors.
- Summarize changed files.