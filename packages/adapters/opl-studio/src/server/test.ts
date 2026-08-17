import type { AdapterEnvironmentTestContext, AdapterEnvironmentTestResult } from "@paperclipai/adapter-utils";
import { resolveOplStudioCommand } from "../index.js";

// Verify OPL Studio is installed and runnable on the host. No model/credentials
// needed (it's license tooling, not an LLM runner), but we do need Python +
// the opl_studio command resolvable.
export async function testEnvironment(
  ctx: AdapterEnvironmentTestContext,
): Promise<AdapterEnvironmentTestResult> {
  const errors: string[] = [];
  const warnings: string[] = [];
  const command = resolveOplStudioCommand(ctx.config);

  // command resolvable?
  try {
    await ctx.ensureAdapterExecutionTargetCommandInstalled(command, {
      cwd: ctx.cwd,
      timeoutSec: 15,
    });
  } catch (err) {
    errors.push(
      `OPL Studio command '${command}' is not resolvable. Install with: pip install hermes-agent (includes opl_studio) or set oplStudioCommand.`,
    );
  }

  // python available (Studio is Python stdlib)?
  try {
    await ctx.ensureAdapterExecutionTargetCommandInstalled("python3", { cwd: ctx.cwd, timeoutSec: 10 });
  } catch {
    warnings.push("python3 not found on PATH — required by OPL Studio (3.9+).");
  }

  return {
    ok: errors.length === 0,
    checks: [
      {
        name: "opl_studio_resolvable",
        ok: errors.length === 0,
        detail: `Resolved adapter type 'opl_studio' to command '${command}'.`,
      },
    ],
    warnings,
    errors,
  };
}

import type { AdapterSessionCodec } from "@paperclipai/adapter-utils";
const readNonEmptyString = (v: unknown): string | null =>
  typeof v === "string" && v.trim().length > 0 ? v.trim() : null;

// OPL Studio runs are stateless per task (license generation is deterministic
// from params), but we still thread the workspace repo + repo URL so runs can
// resume context if needed.
export const sessionCodec: AdapterSessionCodec = {
  deserialize(raw: unknown) {
    if (typeof raw !== "object" || raw === null || Array.isArray(raw)) return null;
    const record = raw as Record<string, unknown>;
    const cwd = readNonEmptyString(record.cwd) ?? readNonEmptyString(record.workdir) ?? readNonEmptyString(record.folder);
    const workspaceId = readNonEmptyString(record.workspaceId) ?? readNonEmptyString(record.workspace_id);
    const repoUrl = readNonEmptyString(record.repoUrl) ?? readNonEmptyString(record.repo_url);
    if (!cwd) return null;
    return { cwd, ...(workspaceId ? { workspaceId } : {}), ...(repoUrl ? { repoUrl } : {}) };
  },
  serialize(params: Record<string, unknown> | null) {
    if (!params) return null;
    const cwd = readNonEmptyString(params.cwd) ?? readNonEmptyString(params.workdir) ?? readNonEmptyString(params.folder);
    if (!cwd) return null;
    return { cwd, ...(params.workspaceId ? { workspaceId: params.workspaceId } : {}), ...(params.repoUrl ? { repoUrl: params.repoUrl } : {}) };
  },
  getDisplayId(params: Record<string, unknown> | null) {
    if (!params) return null;
    return readNonEmptyString(params.cwd) ?? null;
  },
};
