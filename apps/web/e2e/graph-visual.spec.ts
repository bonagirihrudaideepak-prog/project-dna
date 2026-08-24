import { test } from "@playwright/test";

// Throwaway visual probe: renders /graph with realistic stub data and saves a
// screenshot so layout/legibility can be verified by eye.
test("graph visual probe", async ({ page }) => {
  await page.route("**/api/v1/auth/me", (r) =>
    r.fulfill({ status: 200, json: { id: "u1", login: "octocat", display_name: "Octo Cat", avatar_url: null, github_connected: true } })
  );
  const project = {
    id: "p1", full_name: "acme/service-app", owner: "acme", name: "service-app",
    default_branch: "main", visibility: "public", description: "demo", is_fixture: false,
    latest_snapshot: { id: "s9", status: "COMPLETED", captured_at: new Date().toISOString() },
  };
  await page.route("**/api/v1/projects", (r) => r.fulfill({ status: 200, json: [project] }));
  await page.route("**/api/v1/projects/p1/snapshots**", (r) =>
    r.fulfill({ status: 200, json: [{ id: "s9", project_id: "p1", commit_sha: "abc", analyzer_version: "v", score_model_version: "m", status: "COMPLETED", captured_at: new Date().toISOString(), warning_json: {}, limits_json: {} }] })
  );

  const N = (key: string, type: string, label: string) => ({ key, node_type: type, label, entity_type: type, entity_id: key, metadata_json: {} });
  const nodes = [
    N("proj", "project", "acme/service-app"),
    N("snap", "snapshot", "Snapshot 9f31c2ab"),
    N("r1", "release", "v1.0.0 initial stable"),
    N("e1", "event", "fix: payment retry storm on timeouts"),
    N("e2", "event", "feat: webhook ingestion pipeline"),
    N("d1", "decision", "Adopt PostgreSQL SKIP LOCKED queue"),
    N("x1", "experiment", "Tried Prisma ORM (rolled back)"),
    N("c1", "component", "billing"),
    N("c2", "component", "auth"),
    N("o1", "outcome", "Latency p99 improved 40%"),
    N("r2", "release", "v1.4.0 auth overhaul"),
    N("x2", "experiment", "Redis caching PoC"),
    N("d2", "decision", "Pydantic v2 migration"),
    N("e3", "event", "chore: dependency bumps Q3"),
  ];
  const E = (source: string, target: string, edge_type = "produced") => ({
    source, target, edge_type, provenance: "observed", confidence: 0.9, evidence_json: {},
  });
  const edges = [
    E("proj", "snap"), E("snap", "r1"), E("e1", "d1", "informed"), E("x1", "d1", "informed"),
    E("d1", "r2"), E("e2", "c2", "touches"), E("c1", "o1"), E("r1", "x1", "tried"),
    E("r2", "x2", "evaluated"), E("x2", "d2", "informed"), E("d2", "snap"), E("e3", "c1", "touches"),
  ];
  await page.route("**/api/v1/snapshots/s9/graph*", (r) =>
    r.fulfill({ status: 200, json: { nodes, edges, focus: null } })
  );

  await page.goto("/graph?project=p1");
  await page.waitForTimeout(2500);
  await page.screenshot({ path: "test-results/graph-visual.png", fullPage: true });

  // Click a decision node to capture the inspect bar too
  await page.locator("canvas").first().click({ position: { x: 400, y: 300 } });
  await page.waitForTimeout(600);
  await page.screenshot({ path: "test-results/graph-clicked.png", fullPage: true });
});
