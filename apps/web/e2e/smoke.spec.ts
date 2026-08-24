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

const DIM_NAMES = [
  "Technical Complexity",
  "Maintainability",
  "Testing Maturity",
  "Documentation Quality",
  "Evolution Health",
  "Delivery Readiness",
  "Scalability Readiness",
  "Technical Debt Risk",
];

function stubMethodology(page: import("@playwright/test").Page) {
  return page.route("**/api/methodology", async (route) =>
    route.fulfill({
      status: 200,
      json: {
        model_version: "dna-core-1.0",
        min_coverage_for_score: 0.35,
        dimensions: DIM_NAMES.map((name, i) => ({
          key: `dim_${i}`,
          name,
          direction: i === 7 ? "lower_is_better" : "higher_is_better",
          description: `${name} description`,
          indicators: [{ key: "example_indicator", weight: 1.0, direction: "higher_is_better" }],
        })),
        coverage_labels: [
          { below: 0.35, label: "insufficient" },
          { below: 0.6, label: "low" },
          { below: 0.8, label: "moderate" },
          { below: 1.01, label: "high" },
        ],
        caveats: ["Scores are descriptive evidence-weighted signals."],
      },
    }),
  );
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
  await stubMethodology(page);
  await page.goto("/methodology");
  await expect(page.getByRole("heading", { level: 1, name: "Methodology" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Technical Complexity" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Maintainability" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Testing Maturity" })).toBeVisible();
});

test("navigation: sidebar links work", async ({ page }) => {
  await stubApi(page);
  await stubMethodology(page);
  await page.goto("/");
  await page.getByRole("link", { name: "Methodology" }).click();
  await expect(page).toHaveURL(/\/methodology/);
});

test("unknown route falls back gracefully", async ({ page }) => {
  await stubApi(page);
  const response = await page.goto("/does-not-exist");
  expect(response?.status()).toBeLessThan(500);
});