import { test, expect } from "@playwright/test";

function stubApi(page: import("@playwright/test").Page) {
  return page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/auth/me")) {
      return route.fulfill({ status: 401, json: { error: { code: "UNAUTHENTICATED", message: "no session", retryable: false } } });
    }
    if (url.pathname.endsWith("/projects")) {
      return route.fulfill({
        status: 200,
        json: [
          {
            id: "11111111-1111-1111-1111-111111111111",
            full_name: "octocat/hello-world",
            owner: "octocat",
            name: "hello-world",
            default_branch: "main",
            visibility: "public",
            is_fixture: false,
            latest_snapshot: null,
            latest_scores: {},
          },
        ],
      });
    }
    return route.fulfill({ status: 404, json: { error: { code: "NOT_FOUND", message: "not stubbed", retryable: false } } });
  });
}

test("landing page renders hero and quick start", async ({ page }) => {
  await stubApi(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Project DNA");
  await expect(page.getByText("Software archaeology & project intelligence platform")).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Quick Start" })).toBeVisible();
});

test("methodology page renders the 8 dimensions", async ({ page }) => {
  await stubApi(page);
  await page.goto("/methodology");
  await expect(page.getByRole("heading", { level: 1, name: "Methodology" })).toBeVisible();
  await expect(page.getByText("Technical Complexity")).toBeVisible();
  await expect(page.getByText("Maintainability")).toBeVisible();
  await expect(page.getByText("Testing Maturity")).toBeVisible();
});

test("navigation: sidebar links work", async ({ page }) => {
  await stubApi(page);
  await page.goto("/");
  await page.getByRole("link", { name: "Methodology" }).click();
  await expect(page).toHaveURL(/\/methodology/);
});

test("unknown route falls back gracefully", async ({ page }) => {
  await stubApi(page);
  const response = await page.goto("/does-not-exist");
  expect(response?.status()).toBeLessThan(500);
});