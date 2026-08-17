// CLI stdout formatter for opl_studio (keep simple; the Studio emits text).
export function printOplStudioEvent(line: string): void {
  // Paperclip CLI adapters call this per stdout line. Studio output is already
  // human-readable GFM-ish text, so we pass it through.
  process.stdout.write(line.endsWith("\n") ? line : line + "\n");
}
