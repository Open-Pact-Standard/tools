// SPDX-License-Identifier: OPL-1.4
/**
 * OPL Studio adapter for Paperclip.
 *
 * Dispatch the Open-Pact License Studio as a managed agent: Paperclip hands
 * a task, the adapter spawns the local OPL Studio CLI against Paperclip's
 * execution workspace, streams stdout, and returns a structured
 * AdapterExecutionResult carrying the assembled NOTICE + LICENSE + opl_check
 * outcome as resultJson.
 */

import type { AdapterRuntimeCommandSpec, ServerAdapterModule } from "@paperclipai/adapter-utils";

export const type = "opl_studio";
export const label = "OPL Studio";

// OPL Studio has no provider/model surface — it is a license tooling adapter,
// not an LLM runner. Paperclip should not offer model selection.
export const models: { id: string; label: string }[] = [];

// OPL Studio is distributed via its GitHub repo. Install from source:
//   pip install "git+https://github.com/Open-Pact-Standard/tools.git"
// (it is NOT on PyPI as `hermes-agent` — that was a copy/paste mistake).
export const SANDBOX_INSTALL_COMMAND = 'pip install "git+https://github.com/Open-Pact-Standard/tools.git"';

export function resolveOplStudioCommand(config: Record<string, unknown>): string {
  const command =
    typeof config.oplStudioCommand === "string" && config.oplStudioCommand.trim().length > 0
      ? config.oplStudioCommand.trim()
      : "opl_studio";
  return command;
}

function getRuntimeCommandSpec(config: Record<string, unknown>): AdapterRuntimeCommandSpec {
  const command = resolveOplStudioCommand(config);
  return { command, detectCommand: command, installCommand: null };
}

export { testEnvironment, sessionCodec, getConfigSchema, execute } from "./server/index.js";
export { printOplStudioEvent } from "./cli/index.js";

export function createServerAdapter(): ServerAdapterModule {
  return {
    type,
    execute,
    testEnvironment,
    sessionCodec,
    models,
    supportsLocalAgentJwt: true,
    instructionsPathKey: "instructionsFilePath",
    getRuntimeCommandSpec,
    getConfigSchema,
    agentConfigurationDoc,
  };
}

export const agentConfigurationDoc = `# OPL Studio

Adapter: \`${type}\`

Drives the Open-Pact License Studio against the Paperclip execution workspace.
On each heartbeat, Paperclip hands a task; the adapter spawns \`opl_studio.py\`
(with the OPL tooling CLI) against the live workspace, writes/checks NOTICE +
SPDX headers, and reports the assembled license + compliance result.

## Prerequisites
- OPL Studio on PATH (\`opl_studio\`) or set \`oplStudioCommand\` to its absolute path.
- Python 3.9+ (Studio is stdlib-only, no pip deps).
- The repo to license lives in the Paperclip execution workspace.

## Core fields
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| oplStudioCommand | string | opl_studio | Path to the opl_studio CLI entry point. |
| repo | string | (workspace cwd) | Absolute repo path the license is applied to. Defaults to the Paperclip execution workspace. |
| maintainer | string | | Maintainer "Name <email>" written into NOTICE. |
| jurisdiction | string | United States | Governing jurisdiction declared in NOTICE (any — you write it). |
| terms_url | string | | HTTPS Standard Terms URL publishing commercial-use pricing. |
| commercial_model | string | paid_standard_terms | paid_standard_terms | free_for_all | personal_only |
| opl_ai | string | out | opted out (ai training allowed) or in |
| abandonment | number | 36 | Months of silence before the Work auto-converts to Apache-2.0. |
| dosp | string | | DOSP period in months; blank = no scheduled conversion. |
| confirm | boolean | false | Set true to write NOTICE + SPDX into the repo. False = preview only. |
| timeoutSec | number | 600 | Run timeout in seconds. |
| extraArgs | string[] | [] | Additional CLI args forwarded to opl_studio.py. |

## Prompt template variables
- \`{{repo}}\` — the target repo path.
- \`{{task}}\` — the Paperclip task body (issue title + description).
`;

export { createServerAdapter as createOplStudioServerAdapter };
