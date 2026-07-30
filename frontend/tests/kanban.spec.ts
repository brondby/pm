import { expect, test, type Page } from "@playwright/test";

import type { BoardData } from "@/lib/kanban";

const DEFAULT_BOARD_ID = 1;

const createBoard = (): BoardData => ({
  columns: [
    { id: "col-backlog", title: "Backlog", cardIds: ["card-1"] },
    { id: "col-discovery", title: "Discovery", cardIds: [] },
    { id: "col-progress", title: "In Progress", cardIds: [] },
    { id: "col-review", title: "Review", cardIds: [] },
    { id: "col-done", title: "Done", cardIds: [] },
  ],
  cards: {
    "card-1": {
      id: "card-1",
      title: "Initial backend card",
      details: "Seeded by mocked API",
    },
  },
});

const mockAuth = async (page: Page) => {
  // Mirrors real cookie-based session behavior: once "logged in", /api/auth/me
  // keeps reporting the session as active (e.g. across a page reload) until
  // /api/auth/logout is called.
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
  await page.route("**/api/auth/logout", async (route) => {
    isAuthenticated = false;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true }),
    });
  });
};

const mockSingleDefaultBoard = async (page: Page) => {
  await page.route("**/api/boards", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: DEFAULT_BOARD_ID,
            name: "My Board",
            is_archived: false,
            created_at: "2026-01-01T00:00:00.000Z",
            updated_at: "2026-01-01T00:00:00.000Z",
          },
        ]),
      });
      return;
    }

    await route.fallback();
  });
};

const login = async (page: Page) => {
  await mockAuth(page);
  await mockSingleDefaultBoard(page);
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: /login/i }).click();
};

test("login loads board from API", async ({ page }) => {
  const board = createBoard();

  await page.route(`**/api/boards/${DEFAULT_BOARD_ID}`, async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(board) });
      return;
    }

    await route.fallback();
  });

  await login(page);

  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.getByText("Initial backend card")).toBeVisible();
});

test("edit triggers save and refresh restores persisted board", async ({ page }) => {
  let board = createBoard();
  const putPayloads: BoardData[] = [];

  await page.route(`**/api/boards/${DEFAULT_BOARD_ID}`, async (route) => {
    const method = route.request().method();

    if (method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(board),
      });
      return;
    }

    if (method === "PUT") {
      const payload = (await route.request().postDataJSON()) as BoardData;
      putPayloads.push(payload);
      board = payload;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(board),
      });
      return;
    }

    await route.fallback();
  });

  await login(page);

  const firstColumn = page.getByTestId("column-col-backlog");
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Persisted card");
  await firstColumn.getByPlaceholder("Details").fill("Saved via PUT");
  await firstColumn.getByRole("button", { name: /add card/i }).click();

  await expect(firstColumn.getByText("Persisted card")).toBeVisible();

  await expect.poll(() => putPayloads.length).toBeGreaterThan(0);

  await page.reload();
  await expect(page.getByText("Persisted card")).toBeVisible();
});

test("creates a card with optional label, due date, and assignee, then edits and clears them", async ({ page }) => {
  let board = createBoard();
  const putPayloads: BoardData[] = [];

  await page.route(`**/api/boards/${DEFAULT_BOARD_ID}`, async (route) => {
    const method = route.request().method();

    if (method === "GET") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(board) });
      return;
    }

    if (method === "PUT") {
      const payload = (await route.request().postDataJSON()) as BoardData;
      putPayloads.push(payload);
      board = payload;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(board) });
      return;
    }

    await route.fallback();
  });

  await login(page);

  const firstColumn = page.getByTestId("column-col-backlog");
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Ship release notes");
  await firstColumn.getByRole("button", { name: /add label, due date, or assignee/i }).click();
  await firstColumn.getByLabel("Card label").fill("Urgent");
  await firstColumn.getByLabel("Due date").fill("2026-08-15");
  await firstColumn.getByLabel("Assignee").fill("Alex");
  await firstColumn.getByRole("button", { name: /add card/i }).click();

  await expect(firstColumn.getByText("Ship release notes")).toBeVisible();
  await expect(firstColumn.getByText("Urgent")).toBeVisible();
  await expect(firstColumn.getByText("Due 2026-08-15")).toBeVisible();
  await expect(firstColumn.getByText("Alex")).toBeVisible();

  await expect.poll(() => putPayloads.length).toBeGreaterThan(0);
  const createdCard = Object.values(putPayloads[putPayloads.length - 1].cards).find(
    (card) => card.title === "Ship release notes"
  );
  expect(createdCard?.label).toBe("Urgent");
  expect(createdCard?.dueDate).toBe("2026-08-15");
  expect(createdCard?.assignee).toBe("Alex");

  // Now edit the newly created card and clear its label.
  const cardId = createdCard!.id;
  const cardLocator = page.getByTestId(`card-${cardId}`);
  await cardLocator.getByRole("button", { name: /edit details/i }).click();
  await cardLocator.getByLabel("Card label").fill("");
  await cardLocator.getByRole("button", { name: /^save$/i }).click();

  await expect(cardLocator.getByText("Urgent")).toHaveCount(0);
  await expect(cardLocator.getByText("Due 2026-08-15")).toBeVisible();

  await expect.poll(() => putPayloads.length).toBeGreaterThan(1);
  const editedCard = putPayloads[putPayloads.length - 1].cards[cardId];
  expect(editedCard.label).toBeUndefined();
  expect(editedCard.dueDate).toBe("2026-08-15");
  expect(editedCard.assignee).toBe("Alex");
});
