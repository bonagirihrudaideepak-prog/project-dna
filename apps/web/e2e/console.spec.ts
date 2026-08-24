import { test, expect } from "@playwright/test";

const ROUTES = [
  "/",
  "/landing",
  "/auth",
  "/login",
  "/projects",
  "/dna",
  "/timeline",
  "/compare",
  "/decisions",
  "/experiments",
  "/exports",
  "/graph",
  "/methodology",
  "/definitely-not-a-route",
];

function stubAnonymousApi(page: import("@playwright/test").Page) {
  return page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/auth/me")) {
      return route.fulfill({ status: 401, json: { error: { code: "UNAUTHENTICATED", message: "no session", retryable: false } } });
    }
    if (url.pathname.endsWith("/api/methodology")) {
      return route.fulfill({ status: 200, json: { model_version: "dna-core-1.0", dimensions: [], coverage_labels: [], min_coverage_for_score: 0.35, caveats: [] } });
    }
    return route.fulfill({ status: 401, json: { error: { code: "UNAUTHENTICATED", message: "no session", retryable: false } } });
  });
}

test("no uncaught errors or app-level console errors across all routes", async ({ page }) => {
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];

  page.on("pageerror", (err) => pageErrors.push(`${err.name}: ${err.message}`));
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    // The browser itself logs failed network lines for the expected signed-out
    // 401 probes; those are handled by the app and are not app errors.
    if (/Failed to load resource.*\b40[134]\b/.test(text)) return;
    consoleErrors.push(text);
  });

  await stubAnonymousApi(page);
  for (const route of ROUTES) {
    await page.goto(route);
    // Give lazy chunks + queries a beat to settle before moving on.
    await page.waitForTimeout(150);
  }

  expect(pageErrors, `uncaught exceptions:\n${pageErrors.join("\n")}`).toEqual([]);
  expect(consoleErrors, `console errors:\n${consoleErrors.join("\n")}`).toEqual([]);
});
