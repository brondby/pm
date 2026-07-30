import { expect, test, type Page } from "@playwright/test";

const mockAuth = async (page: Page, options?: { signupUsername?: string }) => {
  // Mirrors real cookie-based session behavior: once "logged in", /api/auth/me
  // keeps reporting the session as active until /api/auth/logout is called.
  let isAuthenticated = false;
  let username = "user";

  await page.route("**/api/auth/me", async (route) => {
    await route.fulfill(
      isAuthenticated
        ? { status: 200, contentType: "application/json", body: JSON.stringify({ username }) }
        : { status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Not authenticated." }) }
    );
  });
  await page.route("**/api/auth/logout", async (route) => {
    isAuthenticated = false;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true }) });
  });

  if (options?.signupUsername) {
    await page.route("**/api/auth/signup", async (route) => {
      isAuthenticated = true;
      username = options.signupUsername as string;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ username }),
      });
    });
  } else {
    await page.route("**/api/auth/login", async (route) => {
      isAuthenticated = true;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ username }) });
    });
  }
};

const mockSingleDefaultBoard = async (page: Page) => {
  await page.route("**/api/boards", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 1,
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

  await page.route("**/api/boards/1", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ columns: [], cards: {} }),
      });
      return;
    }

    await route.fallback();
  });
};

test("signup creates an account and lands on the board", async ({ page }) => {
  await mockAuth(page, { signupUsername: "newperson" });
  await mockSingleDefaultBoard(page);

  await page.goto("/");
  await page.getByRole("button", { name: /create one/i }).click();
  await page.getByLabel("Username").fill("newperson");
  await page.getByLabel("Password").fill("s3cret-pass");
  await page.getByRole("button", { name: /create account/i }).click();

  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.getByText("newperson")).toBeVisible();
});

test("shows a friendly error for invalid credentials", async ({ page }) => {
  await page.route("**/api/auth/me", async (route) => {
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Not authenticated." }),
    });
  });
  await page.route("**/api/auth/login", async (route) => {
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Invalid username or password." }),
    });
  });

  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("wrong");
  await page.getByRole("button", { name: /login/i }).click();

  // Scope to the form's own alert paragraph - Next.js also renders an
  // unrelated `role="alert"` route announcer div in the live DOM.
  await expect(page.locator('p[role="alert"]')).toHaveText("Invalid username or password.");
});

test("logout returns to the sign-in screen", async ({ page }) => {
  await mockAuth(page);
  await mockSingleDefaultBoard(page);

  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: /login/i }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();

  await page.getByRole("button", { name: /logout/i }).click();
  await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();

  // A reload after logout must not silently re-authenticate.
  await page.reload();
  await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
});
