import type { Plugin } from "@opencode-ai/plugin";

/**
 * Guardrails for project-dna.
 *
 * - PreToolUse equivalent: block edits to protected paths (.env, secrets) and
 *   edits that would rewrite an *applied* migration (allows creating new ones).
 * - PostToolUse equivalent: after a file edit, run ruff (api) and tsc (web)
 *   and append any failures to the tool result so the model fixes them.
 *
 * Small by design: each check is a few lines and failures are actionable.
 */

const EDIT_TOOLS = new Set(["edit", "write"]);

// .env files and anything named like a secret. Migrations are handled
// separately below so new migration files can still be created.
const PROTECTED_PATTERNS: RegExp[] = [
  /(^|[\\/])\.env(\..*)?$/i,
  /(^|[\\/])[^\\/]*secret[^\\/]*$/i,
];

// Applied migrations live in migrations/versions/. We never hand-edit them
// (CLAUDE.md hard rule 5); new ones are created fresh, so the check is an
// "edit only" block, not a "write/create" block.
const MIGRATION_DIR_RE = /(^|[\\/])migrations[\\/]versions[\\/]/i;

export default (async ({ $ }) => {
  async function runChecks(apiRoot: string, webRoot: string): Promise<string> {
    const results: string[] = [];
    if (apiRoot) {
      try {
        const res = await $`python -m ruff check app tests --output-format=concise`.cwd(apiRoot);
        const out = res.stdout?.trim();
        if (out) results.push(`[api] ruff:\n${out}`);
      } catch (err: unknown) {
        const e = err as { stderr?: string; stdout?: string };
        results.push(`[api] ruff FAILED:\n${e.stderr || e.stdout || String(err)}`);
      }
    }
    if (webRoot) {
      try {
        const res = await $`npx tsc --noEmit`.cwd(webRoot);
        const out = res.stdout?.trim();
        if (out) results.push(`[web] tsc:\n${out}`);
      } catch (err: unknown) {
        const e = err as { stderr?: string; stdout?: string };
        results.push(`[web] tsc FAILED:\n${e.stderr || e.stdout || String(err)}`);
      }
    }
    return results.join("\n\n");
  }

  return {
    "tool.execute.before": async (input, output) => {
      if (!EDIT_TOOLS.has(input.tool)) return;
      const filePath = String(output.args?.filePath ?? output.args?.path ?? "");
      if (!filePath) return;
      const normalized = filePath.replace(/\\/g, "/");
      for (const pattern of PROTECTED_PATTERNS) {
        if (pattern.test(normalized)) {
          throw new Error(
            `Guardrail: "${filePath}" is a protected path (.env/secrets). ` +
              `Do not edit or commit it; use the correct secret mechanism.`,
          );
        }
      }
      if (
        MIGRATION_DIR_RE.test(normalized) &&
        /\.py$/.test(normalized) &&
        input.tool === "edit"
      ) {
        throw new Error(
          `Guardrail: "${filePath}" is an existing migration file. ` +
            `Applied migrations are additive and reviewed (CLAUDE.md rule 5); ` +
            `do not hand-edit them. Create a new migration instead.`,
        );
      }
    },
    "tool.execute.after": async (input, output) => {
      if (!EDIT_TOOLS.has(input.tool)) return;
      // Let the edit land before linting.
      await new Promise((r) => setTimeout(r, 300));
      const feedback = await runChecks("apps/api", "apps/web");
      if (!feedback) return;
      output.output = `${output.output || ""}\n\n--- guardrails ---\n${feedback}`;
    },
  };
}) satisfies Plugin;