# Frontend agent guide

This file describes the current frontend implementation in `frontend/` so future changes stay aligned with existing patterns.

## Purpose and current state

- Framework: Next.js (App Router) with TypeScript.
- UI scope today: single-page Kanban demo rendered at `/`.
- State today: fully client-side in-memory state (no backend persistence yet).
- Board behavior today:
  - Fixed 5-column layout from seeded data
  - Column rename via inline input
  - Add and remove cards
  - Drag and drop cards within and across columns

## Key files

- `src/app/page.tsx`
  - Renders `<KanbanBoard />` as the full page entry.

- `src/components/KanbanBoard.tsx`
  - Main container and state owner for board data.
  - Handles drag events and delegates move logic to `moveCard`.
  - Handles rename/add/delete card actions.

- `src/components/KanbanColumn.tsx`
  - Column UI + droppable zone.
  - Renders cards, column title input, and new-card form.

- `src/components/KanbanCard.tsx`
  - Sortable/draggable card item.

- `src/components/NewCardForm.tsx`
  - Toggleable form for adding cards (title required).

- `src/lib/kanban.ts`
  - Domain types (`Card`, `Column`, `BoardData`).
  - `initialData` seed for local board state.
  - `moveCard` reorder/relocation logic.
  - `createId` helper for new card IDs.

- `src/app/globals.css`
  - Global styles + color variables aligned with project color scheme.

## Data model and flow

- Board shape:
  - `columns: Column[]` where each column stores ordered `cardIds`
  - `cards: Record<string, Card>` keyed by card ID
- Interaction flow:
  1. User action fires in component (rename/add/delete/drag)
  2. `KanbanBoard` updates local `board` state
  3. UI rerenders from updated state

There is currently no API call layer in the frontend.

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

- Unit/component tests: Vitest + Testing Library
  - `src/components/KanbanBoard.test.tsx`
  - `src/lib/kanban.test.ts`
- E2E tests: Playwright
  - `tests/kanban.spec.ts`
- Test helpers/config:
  - `src/test/setup.ts`
  - `vitest.config.ts`
  - `playwright.config.ts`

## Commands

Run from `frontend/`:

```bash
npm install
npm run dev
npm run build
npm run test:unit
npm run test:e2e
npm run test:all
```

## Change constraints for future work

- Keep MVP behavior simple; do not add extra features outside requested scope.
- Preserve existing interaction quality (rename/add/delete/drag) when integrating backend/auth.
- Keep tests updated with each behavior change.
- Target minimum 80% unit test coverage for changed modules and include robust integration testing.
