// SPDX-License-Identifier: OPL-1.4
// The OPL Studio adapter needs no remote runtime; it shells out to the local
// opl_studio CLI. This is kept for parity with the other CLI adapters'
// exported surface (and for the env test hook).
export { execute } from "./execute.js";

import type { AdapterConfigSchema } from "@paperclipai/adapter-utils";
export function getConfigSchema(): AdapterConfigSchema {
  return {
    fields: [
      {
        key: "oplStudioCommand",
        label: "OPL Studio command",
        type: "text",
        default: "opl_studio",
        hint: "Path to the opl_studio CLI entry point. Defaults to 'opl_studio' on PATH.",
      },
      {
        key: "repo",
        label: "Repository path",
        type: "text",
        hint: "Absolute repo path NOTICE/SPDX are applied to. Defaults to the Paperclip workspace cwd.",
      },
      {
        key: "maintainer",
        label: "Maintainer",
        type: "text",
        hint: 'e.g. "Jane Doe <jane@example.com>"',
      },
      {
        key: "jurisdiction",
        label: "Governing Jurisdiction",
        type: "text",
        default: "United States",
        hint: "Any jurisdiction — you write it. OPL §9.4 covers all.",
      },
      {
        key: "terms_url",
        label: "Standard Terms URL",
        type: "text",
        hint: "HTTPS page publishing commercial-use pricing.",
      },
      {
        key: "commercial_model",
        label: "Commercial model",
        type: "select",
        default: "paid_standard_terms",
        options: [
          { value: "paid_standard_terms", label: "Paid (Standard Terms)" },
          { value: "free_for_all", label: "Free for all" },
          { value: "personal_only", label: "Personal use only" },
        ],
      },
      {
        key: "opl_ai",
        label: "OPL-AI",
        type: "select",
        default: "out",
        options: [
          { value: "out", label: "Opted out (AI training allowed)" },
          { value: "in", label: "Opted in (AI training restricted)" },
        ],
      },
      {
        key: "abandonment",
        label: "Abandonment (months)",
        type: "number",
        default: 36,
        hint: "Months of silence before the Work auto-converts to Apache-2.0.",
      },
      {
        key: "dosp",
        label: "DOSP period (months)",
        type: "text",
        hint: "Blank = no scheduled conversion to Apache-2.0.",
      },
      {
        key: "derivative",
        label: "Derivative notice",
        type: "select",
        default: "light_copyleft",
        options: [
          { value: "light_copyleft", label: "Light copyleft" },
          { value: "off", label: "Off" },
        ],
      },
      {
        key: "trademark",
        label: "Trademark notice",
        type: "text",
      },
      {
        key: "confirm",
        label: "Write into repo",
        type: "boolean",
        default: false,
        hint: "True writes NOTICE + SPDX in place. False = preview only.",
      },
      {
        key: "timeoutSec",
        label: "Timeout (seconds)",
        type: "number",
        default: 600,
      },
    ],
  };
}
