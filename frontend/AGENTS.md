# Frontend agent guide

This file describes the current frontend implementation in `frontend/` so future changes stay aligned with existing patterns.

## Purpose and current state

- Framework: Next.js (App Router) with TypeScript, statically exported (`output: "export"`) and served by the
  FastAPI backend at `/`.
- Auth: real signup/login/logout against `/api/auth/*`, session rehydrated via `GET /api/auth/me` on mount (no
  client-side credential storage).
- Boards: a user may own multiple boards; `BoardWorkspace` owns the board list and active-board selection, with
  a board switcher for create/rename/archive/delete/switch.
- Board content: columns (rename), cards (add/edit/delete, drag-and-drop within/between columns, optional
  label/due date/assignee metadata), AI chat sidebar.
- All board/board-list state is persisted via the backend (`/api/boards*`) - no local-only mode.

## Key files

- `src/app/page.tsx`
  - Login/signup gate; on mount, checks `/api/auth/me` to rehydrate session state.
  - Renders `<BoardWorkspace />` once authenticated, plus a profile/logout control.

- `src/components/BoardWorkspace.tsx`
  - Owns the board list and active-board id (`lib/boardsApi.ts`).
  - `pickDefaultBoardId` always excludes archived boards - an archived board can never become the active one.
  - Renders `BoardSwitcher` + `KanbanBoard`, or a first-class empty state (zero boards / all boards archived) -
    never auto-creates a replacement board.

- `src/components/BoardSwitcher.tsx`
  - Floating panel: select/create/rename/archive-toggle/delete (two-step confirm) boards.

- `src/components/KanbanBoard.tsx`
  - Owns one board's card/column state (`lib/boardApi.ts`), drag events (delegates to `moveCard`),
    rename/add/edit/delete card actions, and the AI chat sidebar with per-board chat history in
    `sessionStorage`.

- `src/components/KanbanColumn.tsx`
  - Column UI + droppable zone; renders cards, column title input, and `NewCardForm`.

- `src/components/KanbanCard.tsx`
  - Sortable/draggable card item; shows `CardBadges` (label/due date/assignee) and an inline "Edit details"
    form for that metadata.

- `src/components/NewCardForm.tsx`
  - Toggleable form for adding cards (title required). Label/due date/assignee are collapsed behind a
    "+ Add label, due date, or assignee" toggle so quick card creation stays a one-click flow.

- `src/components/CardBadges.tsx`
  - Shared small pill display for a card's label/due date/assignee (used by both `KanbanCard` and
    `KanbanCardPreview`).

- `src/lib/kanban.ts`
  - Domain types (`Card`, `Column`, `BoardData`, `CardMetadata`).
  - `moveCard` reorder/relocation logic, `applyCardMetadata` (set/clear label/dueDate/assignee), `createId`.

- `src/lib/authApi.ts`, `src/lib/boardsApi.ts`, `src/lib/boardApi.ts`
  - The only places that call `/api/auth/*`, `/api/boards` (list/create/rename/archive/delete), and
    `/api/boards/{id}*` (single-board read/write/chat) respectively. Each validates response shapes and maps
    failures to friendly error messages.

- `src/app/globals.css`
  - Global styles + color variables aligned with project color scheme.

## Data model and flow

- Board shape:
  - `columns: Column[]` where each column stores ordered `cardIds`
  - `cards: Record<string, Card>` keyed by card ID; `Card` has required `id`/`title`/`details` and optional
    `label`/`dueDate`/`assignee`
- Interaction flow:
  1. User action fires in a component (rename/add/edit/delete/drag/board switch)
  2. The owning component (`KanbanBoard` for card/column state, `BoardWorkspace` for board list/selection)
     updates state and calls the relevant backend route
  3. UI rerenders from updated state

## Styling conventions

- Tailwind CSS v4 utilities are used directly in components.
- CSS variables define palette tokens in `globals.css`:
  - Accent Yellow `#ecad0a`
  - Blue Primary `#209dd7`
  - Purple Secondary `#753991`
  - Dark Navy `#032147`
  - Gray Text `#888888`
- Layout and cards use rounded surfaces with light borders/shadows.

## Testing setup

- Unit/component tests: Vitest + Testing Library, one file per component/lib module (e.g.
  `src/components/KanbanBoard.test.tsx`, `src/components/BoardSwitcher.test.tsx`, `src/lib/kanban.test.ts`).
- E2E tests: Playwright (`tests/*.spec.ts`), driving a real browser against the static-exported build with the
  backend mocked via `page.route` (auth, multi-board lifecycle, card CRUD including metadata).
- Test helpers/config: `src/test/setup.ts`, `vitest.config.ts`, `playwright.config.ts`.

## Commands

Run from `frontend/`:

```bash
npm install
npm run dev
npm run lint
npm run build
npm run test:unit
npm run test:e2e
npm run test:all
```

## Change constraints for future work

- Keep implementation simple; do not add extra features outside requested scope.
- Preserve existing interaction quality (rename/add/edit/delete/drag, board switching) when extending behavior.
- Any new card field or board attribute should stay optional/unobtrusive by default - do not slow down the
  fast create-a-card or create-a-board flows.
- Keep tests updated with each behavior change, including the ownership/empty-state edge cases already covered.
