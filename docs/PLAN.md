# High level steps for project

This plan is the execution source of truth for the MVP. It follows `AGENTS.md` constraints:

- Keep implementation simple and focused.
- Avoid over-engineering and unnecessary features.
- Prove root cause before fixes.
- Keep docs concise and practical.

## Global test and quality gates

 - Add focused unit and integration tests for changed behavior. Aim for meaningful coverage rather than enforcing a fixed percentage during every phase.
- Integration tests are required for end-to-end behavior across component/service boundaries.
- Build must pass for each phase before moving on.
- No unresolved lint/type/test failures at handoff.

## Approval gates

Before moving to the next part, pause for explicit user approval after delivering:

1. Summary of changed files
2. Commands run (tests/build)
3. Evidence that success criteria for that part are met

---

## Part 1: Plan

### Scope
Enrich this plan with detailed checklists, tests, and success criteria for all parts, and create `frontend/AGENTS.md` describing the existing frontend implementation.

### Checklist
- [ ] Expand all Parts 1-10 with concrete implementation substeps.
- [ ] Define test strategy and success criteria per part.
- [ ] Add approval gates and quality gates.
- [ ] Create `frontend/AGENTS.md` with current frontend architecture and conventions.
- [ ] Get user approval of planning artifacts.

### Tests
- [ ] N/A (documentation-only change).

### Success criteria
- [ ] `docs/PLAN.md` is explicit enough to execute without guessing.
- [ ] `frontend/AGENTS.md` accurately reflects current code, commands, and constraints.
- [ ] User approves Part 1 outputs.

---

## Part 2: Scaffolding

### Scope
Create Docker infrastructure, backend FastAPI scaffold in `backend/`, and start/stop scripts in `scripts/`. Serve a static hello-world page and expose a sample API route.

### Checklist
- [ ] Add backend app entrypoint and health/sample endpoints.
- [ ] Add Dockerfile and container wiring for frontend static assets + backend.
- [ ] Add cross-platform start/stop scripts (Linux, macOS, Windows).
- [ ] Ensure local run starts container and serves `GET /` + sample API.
- [ ] Document commands in minimal README/docs updates.

### Tests
- [ ] Backend unit tests for health/sample routes.
- [ ] Integration test that container serves static page at `/` and API route response.
- [ ] Verify build/start/stop scripts run successfully.

### Success criteria
- [ ] `docker build` succeeds.
- [ ] Running container returns hello-world page at `/`.
- [ ] Sample API route returns expected response.
- [ ] Unit test coverage for backend scaffold modules >= 80%.

---

## Part 3: Add in Frontend

### Scope
Replace hello-world static page with statically built Next.js frontend and serve Kanban board at `/`.

### Checklist
- [ ] Wire frontend build output into backend/static serving flow.
- [ ] Ensure `/` renders existing Kanban demo.
- [ ] Keep backend routes functional after integration.
- [ ] Update docs/scripts if run flow changes.

### Tests
- [ ] Frontend unit tests for key board interactions remain passing.
- [ ] Integration test that deployed stack serves Kanban UI at `/`.
- [ ] E2E smoke test for board load and core interaction.

### Success criteria
- [ ] Kanban UI is visible and interactive at `/` in containerized run.
- [ ] Unit coverage for affected frontend modules >= 80%.
- [ ] Integration/E2E pass in CI/local run path.

---

## Part 4: Add fake user sign-in experience

### Scope
Require login with hardcoded credentials (`user` / `password`) before showing board; support logout.

### Checklist
- [ ] Add login screen and simple auth state flow.
- [ ] Gate board rendering behind authenticated state.
- [ ] Add logout action to return user to login screen.
- [ ] Keep implementation intentionally minimal for MVP.

### Tests
- [ ] Unit tests for auth gate/login form behavior.
- [ ] Integration test for login success/failure flow.
- [ ] E2E: unauthenticated user sees login, authenticated user sees board, logout resets state.

### Success criteria
- [ ] Only valid dummy credentials unlock board.
- [ ] Logout reliably returns to login screen.
- [ ] Coverage for new auth modules >= 80%.

---

## Part 5: Database modeling

### Scope
Design and document SQLite schema for users + one board per user, with board data stored as JSON.

### Checklist
- [ ] Propose schema (users, boards) with constraints and indexes.
- [ ] Define JSON shape contract for board payload.
- [ ] Document migration/init strategy (create DB if missing).
- [ ] Add schema docs under `docs/` and request sign-off.

### Tests
- [ ] Unit tests for schema/model validation helpers.
- [ ] Integration test for DB initialization and basic CRUD round-trip.

### Success criteria
- [ ] Schema supports current MVP and future multi-user support.
- [ ] Documentation is approved before backend API implementation.
- [ ] Coverage for new data/model logic >= 80%.

---

## Part 6: Backend

### Scope
Implement API routes to read/update Kanban for a given user; auto-create DB if missing.

### Checklist
- [ ] Add data access layer for board read/write.
- [ ] Add API routes for fetch/update operations.
- [ ] Add input validation and clear error responses.
- [ ] Ensure DB bootstrap path runs safely on first start.

### Tests
- [ ] Backend unit tests for service/data layers.
- [ ] API integration tests for success + failure cases.
- [ ] Integration test for first-run DB creation behavior.

### Success criteria
- [ ] API correctly persists and retrieves board state.
- [ ] Error paths are deterministic and tested.
- [ ] Coverage for backend modules touched >= 80%.

---

## Part 7: Frontend + Backend

### Scope
Connect frontend board operations to backend APIs for persistence.

### Checklist
- [ ] Replace local-only board state bootstrap with API-backed load.
- [ ] Persist create/edit/move/delete actions through backend.
- [ ] Add loading/error UI states with simple UX.
- [ ] Keep board interactions responsive and stable.

### Tests
- [ ] Frontend unit tests for API integration boundaries.
- [ ] Integration tests with mocked/real backend as appropriate.
- [ ] E2E test validating persistence across page reload.

### Success criteria
- [ ] Board changes persist reliably.
- [ ] Reload shows previously saved state.
- [ ] Coverage for changed frontend modules >= 80%.

---

## Part 8: AI connectivity

### Scope
Enable backend OpenRouter connectivity and validate with a simple `2+2` prompt.

### Checklist
- [ ] Add OpenRouter client wrapper using `OPENROUTER_API_KEY`.
- [ ] Configure model `openai/gpt-oss-120b`.
- [ ] Add minimal backend route/service to test LLM response.
 - Add a reasonable request timeout. Do not add automatic retries for the MVP.

### Tests
- [ ] Unit tests for AI client wrapper (mocked HTTP responses).
- [ ] Integration test for backend AI route with mocked provider.
- [ ] Optional live connectivity smoke test (`2+2`) when key is present.

### Success criteria
- [ ] Backend can produce valid response from OpenRouter path.
- [ ] Sensitive key handling remains environment-based only.
- [ ] Coverage for AI integration modules >= 80%.

---

## Part 9: Structured AI board operation

### Scope
Send board JSON + user message + conversation history to AI, receive structured output with reply plus optional board update.

### Checklist
- [ ] Define structured output schema (assistant message + optional board patch/full state).
- [ ] Implement backend orchestration for prompt construction and schema validation.
- [ ] Apply optional board update atomically when valid.
- [ ] Persist updated board and return combined response.

### Tests
- [ ] Unit tests for schema validation and transformation logic.
- [ ] Integration tests for: reply-only, reply+update, malformed output fallback.
- [ ] Tests for conversation history inclusion and persistence behavior.

### Success criteria
- [ ] Structured outputs are validated before use.
- [ ] Invalid AI output does not corrupt board state.
- [ ] Coverage for orchestration/validation modules >= 80%.

---

## Part 10: AI sidebar in UI

### Scope
Add sidebar chat UI integrated with backend AI flow; refresh board automatically when AI update is returned.

### Checklist
- [ ] Add sidebar chat component and conversation state.
- [ ] Integrate submit flow with backend AI endpoint.
- [ ] Reflect assistant reply in chat history.
- [ ] Refresh/merge board state when AI returns update.
- [ ] Keep UX clean, simple, and aligned with color system.

### Tests
- [ ] Unit tests for sidebar state and rendering.
- [ ] Integration tests for chat submit + response + board refresh logic.
- [ ] E2E tests for full user flow: login, board interaction, AI chat update.

### Success criteria
- [ ] Sidebar supports reliable multi-turn chat.
- [ ] AI-triggered board updates appear automatically in UI.
- [ ] Coverage for new frontend sidebar modules >= 80%.

---

## Part 11: Backend auth foundation

### Scope
Add real per-user password verification and server-side sessions, purely additive: new `sessions` table,
one-time password-hash migration (upgrades the legacy sentinel hash to a real `bcrypt` hash of the current
demo password so existing logins keep working), `backend/auth.py` (hash/verify/session helpers), and
`/api/auth/signup|login|logout|me` routes. The existing `/api/board/{username}*` routes and the hardcoded
frontend login are left untouched in this Part — the app must remain fully runnable exactly as before.

### Checklist
- [ ] Add `sessions` table to `backend/db.py` schema (additive, no rebuild needed).
- [ ] Add `backend/migrations.py`: prints the resolved DB path and writes a timestamped backup
      (`pm.db.<UTC-timestamp>.bak`) only when there is an actual legacy password hash to upgrade; upgrades it
      to a real `bcrypt` hash via `UPDATE ... WHERE password_hash = <sentinel>` (idempotent by construction).
- [ ] Add `backend/auth.py`: `hash_password`/`verify_password` (bcrypt), `create_session`/`get_session_user`/
      `delete_session` (opaque `secrets.token_urlsafe(32)` token, 30-day flat expiry, no sliding renewal).
- [ ] Add `bcrypt` to `backend/requirements.txt`.
- [ ] Add routes: `POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`,
      all via httpOnly/SameSite=Lax session cookie; no CSRF token needed (SameSite=Lax already blocks
      cross-site cookie attachment on the mutating verbs used here).
- [ ] Update `docs/DB_SCHEMA.md` for the new `sessions` table and the real password-hash contract.

### Tests
- [ ] Unit: hash/verify roundtrip, wrong password rejected, two hashes of the same password differ (salt).
- [ ] Unit: session create/validate/expire (insert an expired row directly, no real sleep), tampered/garbage
      token rejected.
- [ ] Integration: signup success + duplicate-username 409; login success + wrong-password + unknown-username
      (identical response shape for the latter two, no enumeration); logout deletes the session row (replay
      same cookie afterward -> 401); `/api/auth/me` reflects session state, 401 with no/invalid cookie.
- [ ] Migration test: pre-seed the legacy sentinel hash, run migration, assert real hash + login still
      succeeds with the original demo password, backup file created, second run is a no-op (no duplicate
      backup, no re-update).

### Success criteria
- [ ] New auth endpoints work end-to-end against the real DB layer.
- [ ] Old board routes and frontend login behavior are unchanged (verified by existing test suite still
      passing unmodified).
- [ ] Migration preserves all existing user/board data; DB path and backup path are printed when it runs.
- [ ] User approves Part 11 before Part 12 begins.

---

## Part 12: Frontend auth UI

### Scope
Replace the hardcoded client-side login check with real calls to the Part 11 endpoints. Board data continues
to flow through the existing (unchanged) `/api/board/{username}` routes underneath — this Part only changes
how a user authenticates, not how boards are fetched, so the app stays fully functional throughout.

### Checklist
- [ ] `app/page.tsx`: real signup + login forms calling `/api/auth/signup` / `/api/auth/login`.
- [ ] Drop the `sessionStorage` `pm-auth-username` hack; rehydrate auth state via `GET /api/auth/me` on load.
- [ ] Logout button calls `POST /api/auth/logout`.
- [ ] Add a small profile display (current username) near the logout control.

### Tests
- [ ] Unit: `page.test.tsx` updated for signup/login against mocked `/api/auth/*`.
- [ ] E2E: signup -> land on board -> reload keeps session -> logout -> login again.

### Success criteria
- [ ] Real per-user accounts fully replace the hardcoded credential check.
- [ ] Board interactions (drag/drop, AI chat) keep working unchanged.
- [ ] User approves Part 12 before Part 13 begins.

---

## Part 13: Multi-board backend + frontend (combined)

### Scope
Add full multi-board support end-to-end in a single approval-gated Part, so the app is never left in a
broken/non-functional state between a backend change and its corresponding frontend change: `boards` table
migration (drop the one-board-per-user constraint, add `name`/`is_archived`, preserve existing board/card data
under `name = 'My Board'`), new session-scoped `/api/boards*` CRUD routes with per-request ownership checks,
and the frontend `BoardSwitcher` + `boardId`-scoped board loading that consumes them. The old
`/api/board/{username}*` routes are removed in this same Part, once the frontend no longer calls them.

### Checklist
- [ ] `backend/migrations.py`: prints DB path, timestamped backup, rebuilds `boards` (FK pragma off/on around
      the rebuild, `PRAGMA foreign_key_check`, idempotency check so repeat startups are no-ops).
- [ ] `db.py`: board CRUD scoped by `user_id` (list/create/get/update/rename/archive/delete), ownership
      enforced in the SQL itself (`WHERE id = ? AND user_id = ?`).
- [ ] Routes: `GET/POST /api/boards`, `GET/PUT/PATCH/DELETE /api/boards/{id}`, `POST /api/boards/{id}/chat`,
      all behind the Part 11 session dependency; mismatched/missing board -> 404 (never 403).
- [ ] Remove `/api/board/{username}*` routes.
- [ ] Frontend: `BoardSwitcher` (create/rename/archive/unarchive/delete/switch), `KanbanBoard` takes `boardId`,
      `lib/boardApi.ts` updated to the new endpoints. Default board on load: most recently updated
      non-archived board, else create one. Zero-board state handled as first-class UI.
- [ ] Update `docs/DB_SCHEMA.md` and strike the "one board per user" / hardcoded-login limitations in
      `AGENTS.md`.

### Tests
- [ ] Ownership isolation matrix: user A vs user B's board for every verb (`GET/PUT/PATCH/DELETE
      /api/boards/{id}`, `POST /api/boards/{id}/chat`) -> 404; every `/api/boards*` route with no cookie -> 401.
- [ ] Zero-board state: `GET /api/boards` -> `[]` cleanly, frontend renders a sane empty state.
- [ ] Migration test: pre-seed the old single-board schema, run migration, assert board/card data preserved
      with `name = 'My Board'`, idempotent second run.
- [ ] Frontend: `BoardSwitcher.test.tsx`, updated `KanbanBoard.test.tsx`; e2e covering create/switch/rename/
      archive/delete and cross-user isolation.

### Success criteria
- [ ] Users can create, rename, archive, and delete boards, and switch between them.
- [ ] Cross-user board access is impossible (verified by the isolation test matrix).
- [ ] App is fully runnable immediately after this Part lands (no interim broken state).
- [ ] User approves Part 13 before Part 14 begins.

---

## Part 14: Card detail fields

### Scope
Extend the card model with optional `label`, `dueDate`, and `assignee` fields (lowest priority of the
requested work).

### Checklist
- [ ] Extend `Card` type and `validate_board_data` for the new optional fields.
- [ ] Update card create/edit UI to capture and display them.
- [ ] Update AI `prompt_builder`/`operation_executor` so `create_card`/edits can set them.

### Tests
- [ ] Backend: validation accepts/rejects the new fields correctly; AI operation tests updated.
- [ ] Frontend: card form/display unit tests for the new fields.

### Success criteria
- [ ] New fields are optional and don't break existing boards/cards.
- [ ] User approves Part 14 before Part 15 begins.

---

## Part 15: Docs and cleanup pass

### Scope
Final sweep of `docs/PLAN.md` itself and any remaining stale references now that Parts 11-14 are complete.

### Checklist
- [ ] Re-read `CLAUDE.md`/`AGENTS.md`/`docs/DB_SCHEMA.md` for anything still describing the old single-board,
      hardcoded-login model; fix.
- [ ] Full backend + frontend test/build run.

### Success criteria
- [ ] No stale documentation describing removed behavior remains.
- [ ] Full test suite and build pass cleanly.
