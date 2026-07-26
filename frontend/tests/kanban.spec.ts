import { expect, test, type Page } from "@playwright/test";

import type { BoardData } from "@/lib/kanban";

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

const login = async (page: Page) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: /login/i }).click();
};

test("login loads board from API", async ({ page }) => {
  const board = createBoard();

  await page.route("**/api/board/user", async (route) => {
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

  await page.route("**/api/board/user", async (route) => {
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