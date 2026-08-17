import fs from "node:fs/promises";
import path from "node:path";
import {
  type AdapterExecutionContext,
  type AdapterExecutionResult,
  parseObject,
  asString,
  asNumber,
  joinPromptSections,
  renderPaperclipWakePrompt,
  resolveAdapterExecutionTargetTimeoutSec,
  readAdapterExecutionTarget,
  adapterExecutionTargetIsRemote,
  adapterExecutionTargetRemoteCwd,
  ensureAdapterExecutionTargetCommandResolvable,
  runAdapterExecutionTargetProcess,
} from "@paperclipai/adapter-utils/server-utils";
import { resolveOplStudioCommand } from "../index.js";
import { SANDBOX_INSTALL_COMMAND } from "../index.js";

// OPL Studio is a CLI tool, not an LLM runner — so it has no model/credentials
// surface. We spawn `opl_studio.py` and return its structured output.

function readNonEmptyString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}

// Prompt piped via stdin to the Studio agent. Paperclip's task body becomes the
// Studio prompt so a user can ask (in an issue): "adopt OPL into this repo,
// DOSP 36 months, commercial model paid, maintainer Acme <ops@acme.com>".
export function buildPrompt(ctx: AdapterExecutionContext): string {
  const sections: string[] = [];
  const wake = renderPaperclipWakePrompt(ctx.context.paperclipWake, { suppressIssueDescription: false });
  if (wake) sections.push(wake);
  const body = readNonEmptyString(ctx.context.task?.body) ?? readNonEmptyString(ctx.context.taskBody);
  if (body) sections.push(body);
  sections.push(
    "You are OPL Studio: a local tool that adopts the Open-Pact License into a repo.",
    "Call the `adopt-full` adapter with the repository path (the Paperclip execution workspace)",
    "and the adoption parameters extracted from the task above, then report the NOTICE,",
    "Custom LICENSE, and opl_check result.",
  );
  return joinPromptSections(sections);
}

export async function execute(ctx: AdapterExecutionContext): Promise<AdapterExecutionResult> {
  const { runId, agent, runtime, config, context, onLog, onMeta, onSpawn, authToken } = ctx;

  // 1. Ensure the command is resolvable (fail fast if Studio isn't installed).
  const command = resolveOplStudioCommand(config);
  await ensureAdapterExecutionTargetCommandResolvable(command, { ctx, log: onLog });

  // 2. Resolve timeout + execution target (Paperclip workspace sandbox).
  const timeoutSec = resolveAdapterExecutionTargetTimeoutSec(ctx, 600);
  const execTarget = readAdapterExecutionTarget(ctx);
  const executionTargetIsRemote = adapterExecutionTargetIsRemote(execTarget);
  const workspaceCwd =
    adapterExecutionTargetRemoteCwd(execTarget) ??
    asString(parseObject(context.paperclipWorkspace)?.cwd) ??
    process.cwd();

  // 3. Build the adopt-full invocation. The repo is the Paperclip workspace root.
  const repo = asString(parseObject(config).repo, workspaceCwd);
  const adoptArgs = [
    strFlag("repo", repo),
    optStr("maintainer", asString(parseObject(config).maintainer, "")),
    optStr("jurisdiction", asString(parseObject(config).jurisdiction, "United States")),
    optStr("terms_url", asString(parseObject(config).terms_url, "")),
    optFlag("commercial_model", asString(parseObject(config).commercial_model, "paid_standard_terms")),
    optFlag("opl_ai", asString(parseObject(config).opl_ai, "out")),
    optNum("abandonment", asNumber(parseObject(config).abandonment, 36)),
    optStr("dosp", asString(parseObject(config).dosp, "")),
    optFlag("derivative", asString(parseObject(config).derivative, "light_copyleft")),
    optStr("trademark", asString(parseObject(config).trademark, "")),
    optBool("confirm", !!parseObject(config).confirm),
  ].filter((a): a is string => a !== null);

  // We call the internal adopt-full adapter via the Studio's JSON API when the
  // Invoke the adopt-full adapter via its JSON harness entry point. Any
  // orchestrator (Paperclip, Claude Code, Codex, cron) can call this directly:
  //   python3 opl_adapters.py --run adopt-full --json --repo X --maintainer Y ...
  const cliArgs = ["--run", "adopt-full", "--json", ...adoptArgs];

  await onLog("stdout", `[opl-studio] running: ${command} ${cliArgs.join(" ")} in ${repo}\n`);

  const proc = await runAdapterExecutionTargetProcess(runId, execTarget, command, cliArgs, {
    cwd: repo,
    env: executionTargetIsRemote ? ctx.runtimeEnv : buildRuntimeEnv(ctx, config, authToken),
    timeoutSec,
    graceSec: asNumber(parseObject(config).graceSec, 10),
    onSpawn,
    onLog: (stream, chunk) => onLog(stream, chunk),
  });

  const ok = proc.exitCode === 0;
  return toResult(proc, ok, repo);
}

function toResult(
  proc: { exitCode: number | null; signal: string | null; timedOut: boolean; stdout: string; stderr: string },
  ok: boolean,
  repo: string,
): AdapterExecutionResult {
  if (proc.timedOut) {
    return {
      exitCode: 1,
      signal: null,
      timedOut: true,
      errorMessage: `OPL Studio timed out after the configured timeout.`,
      resultJson: { repo, ok: false, timedOut: true },
      summary: `Adopted OPL into ${repo}: timed out.`,
    };
  }
  let parsed: Record<string, unknown> | null = null;
  try {
    parsed = JSON.parse(proc.stdout) as Record<string, unknown>;
  } catch {
    parsed = null;
  }
  const err = proc.stderr.trim().split(/\r?\n/).find((l) => l.trim().length > 0);
  return {
    exitCode: ok ? 0 : (proc.exitCode ?? 1),
    signal: proc.signal,
    timedOut: false,
    errorMessage: ok ? null : (err ?? `OPL Studio exited with code ${proc.exitCode ?? -1}`),
    usage: undefined, // license tooling, not an LLM run — no token usage.
    resultJson: {
      repo,
      ok,
      ...(parsed ?? { stdout: proc.stdout, stderr: proc.stderr }),
    },
    summary: `OPL Studio adopt-full ${ok ? "complete" : "failed"} for ${repo}.`,
  };
}

// arg builders
const strFlag = (k: string, v: string | null) =>
  v && v.trim().length > 0 ? `--${k} ${JSON.stringify(v.trim())}` : null;
const optStr = (k: string, v: string) =>
  v && v.trim().length > 0 ? `--${k} ${JSON.stringify(v.trim())}` : null;
const optFlag = (k: string, v: string) => `--${k} ${JSON.stringify(v)}`;
const optNum = (k: string, v: number) => `${k}` in { k: v } && v ? `--${k} ${v}` : null;
const optBool = (k: string, v: boolean) => (v ? `--${k} true` : null);

function buildRuntimeEnv(
  ctx: AdapterExecutionContext,
  config: Record<string, unknown>,
  authToken: string | undefined,
): Record<string, string> {
  const env: Record<string, string> = {
    PAPERCLIP_API_URL: ctx.context.paperclipApiUrl ?? "",
    PAPERCLIP_RUN_ID: ctx.runId,
    PAPERCLIP_AGENT_ID: ctx.agent.id,
    PAPERCLIP_COMPANY_ID: ctx.agent.companyId,
  };
  if (authToken) env.PAPERCLIP_API_KEY = authToken;
  const cfgEnv = parseObject(config.env);
  if (cfgEnv && typeof cfgEnv === "object") {
    for (const [k, v] of Object.entries(cfgEnv)) {
      if (v !== undefined) env[String(k)] = String(v);
    }
  }
  return env;
}
