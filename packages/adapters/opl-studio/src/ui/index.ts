// SPDX-License-Identifier: OPL-1.4
// UI formatter: maps opl_studio stdout/stderr into Paperclip transcript events.
// OPL Studio is a CLI tool (not an LLM stream), so we treat each emitted line
// as a stdout/stderr event. No token-stream parsing is needed.
export function formatOplStudioLine(line: string, stream: "stdout" | "stderr"): { content: string; kind: string } {
  return { content: line, kind: stream === "stderr" ? "tool:stderr" : "tool:error" };
}
