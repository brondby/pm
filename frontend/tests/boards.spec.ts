import { expect, test, type Page } from "@playwright/test";

type MockBoard = {
  id: number;
  name: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  board_data: { columns: unknown[]; cards: Record<string, unknown> };
};

const NOW = "2026-01-01T00:00:00.000Z";

const summary = (board: MockBoard) => ({
  id: board.id,
  name: board.name,
  is_archived: board.is_archived,
  created_at: board.created_at,
  updated_at: board.updated_at,
});

/**
 * A minimal in-memory stand-in for the real /api/boards* backend, so these
 * tests exercise real create/rename/archive/delete/switch interactions
 * through the actual UI rather than only checking static mocked responses.
 */
const mockBoardsBackend = async (page: Page, initialBoards: MockBoard[]) => {
  let boards = initialBoards;
  let nextId = Math.max(0, ...boards.map((board) => board.id)) + 1;

  // Mirrors real cookie-based session behavior: unauthenticated until
  // /api/auth/login succeeds, matching kanban.spec.ts/auth.spec.ts.
  let isAuthenticated = false;

  await page.route("**/api/auth/me", async (route) => {
    await route.fulfill(
      isAuthenticated
        ? { status: 200, contentType: "application/json", body: JSON.stringify({ username: "user" }) }
        : { status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Not authenticated." }) }
    );
  });
  await page.route("**/api/auth/login", async (route) => {
    isAuthenticated = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ username: "user" }),
    });
  });

  await page.route("**/api/boards", async (route) => {
    const method = route.request().method();

    if (method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(boards.map(summary)),
      });
      return;
    }

    if (method === "POST") {
      const payload = route.request().postDataJSON() as { name: string };
      const created: MockBoard = {
        id: nextId++,
        name: payload.name,
        is_archived: false,
        created_at: NOW,
        updated_at: NOW,
        board_data: { columns: [], cards: {} },
      };
      boards = [created, ...boards];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(summary(created)),
      });
      return;
    }

    await route.fallback();
  });

  await page.route(/\/api\/boards\/\d+$/, async (route) => {
    const match = route.request().url().match(/\/api\/boards\/(\d+)$/);
    const id = Number(match?.[1]);
    const method = route.request().method();
    const index = boards.findIndex((board) => board.id === id);

    if (index === -1) {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Board not found." }),
      });
      return;
    }

    if (method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(boards[index].board_data),
      });
      return;
    }

    if (method === "PUT") {
      const payload = route.request().postDataJSON();
      boards[index] = { ...boards[index], board_data: payload };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(payload),
      });
      return;
    }

    if (method === "PATCH") {
      const payload = route.request().postDataJSON() as { name?: string; is_archived?: boolean };
      boards[index] = { ...boards[index], ...payload };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(summary(boards[index])),
      });
      return;
    }

    if (method === "DELETE") {
      boards = boards.filter((board) => board.id !== id);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true }),
      });
      return;
    }

    await route.fallback();
  });
};

const login = async (page: Page) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: /login/i }).click();
};

test("creates a second board and switches between boards", async ({ page }) => {
  await mockBoardsBackend(page, [
    { id: 1, name: "My Board", is_archived: false, created_at: NOW, updated_at: NOW, board_data: { columns: [], cards: {} } },
  ]);

  await login(page);
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();

  // The trigger button's accessible name changes with the active board, so
  // target it structurally (direct child of the switcher) rather than by
  // name - the active board's name is ambiguous with its own list row once
  // the panel is open.
  const switcherTrigger = page.locator('[data-testid="board-switcher"] > button');

  await switcherTrigger.click();
  await page.getByPlaceholder(/new board name/i).fill("Marketing");
  await page.getByRole("button", { name: /^create$/i }).click();

  await expect(switcherTrigger).toHaveText(/marketing/i);

  // Switch back to the original board (panel stays open after creating).
  await page.getByTestId("board-switcher").getByText("My Board", { exact: true }).click();

  await expect(switcherTrigger).toHaveText(/my board/i);
});

test("renames a board", async ({ page }) => {
  await mockBoardsBackend(page, [
    { id: 1, name: "My Board", is_archived: false, created_at: NOW, updated_at: NOW, board_data: { columns: [], cards: {} } },
  ]);

  await login(page);
  const switcherTrigger = page.locator('[data-testid="board-switcher"] > button');
  await switcherTrigger.click();
  await page.getByRole("button", { name: /rename/i }).click();

  await page.getByLabel("Rename board").fill("Renamed Board");
  await page.getByRole("button", { name: /save/i }).click();

  await expect(switcherTrigger).toHaveText(/renamed board/i);
});

test("archiving the active board switches away from it, and reaching zero active boards never auto-creates a replacement", async ({ page }) => {
  await mockBoardsBackend(page, [
    { id: 1, name: "Only Board", is_archived: false, created_at: NOW, updated_at: NOW, board_data: { columns: [], cards: {} } },
  ]);

  await login(page);
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();

  await page.getByTestId("board-switcher").getByRole("button", { name: /only board/i }).click();
  await page.getByRole("button", { name: /^archive$/i }).click();

  await expect(page.getByText(/all your boards are archived/i)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toHaveCount(0);

  // Unarchiving brings it back as the active board - no board was ever auto-created.
  await page.getByRole("button", { name: /unarchive/i }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
});

test("deleting a board requires confirmation and reaches a first-class empty state", async ({ page }) => {
  await mockBoardsBackend(page, [
    { id: 1, name: "Only Board", is_archived: false, created_at: NOW, updated_at: NOW, board_data: { columns: [], cards: {} } },
  ]);

  await login(page);
  await page.getByTestId("board-switcher").getByRole("button", { name: /only board/i }).click();
  await page.getByRole("button", { name: /^delete$/i }).click();

  // First click must only arm the confirmation, not delete immediately.
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();

  await page.getByRole("button", { name: /confirm\?/i }).click();

  await expect(page.getByText(/don't have any boards yet/i)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toHaveCount(0);
});
