/**
 * Bridge to the tq Python CLI. All tq operations go through here.
 */

import { execSync } from "node:child_process";

let tqPath = "tq";

export function configure(path: string) {
  tqPath = path;
}

function exec(args: string): string {
  return execSync(`${tqPath} ${args}`, {
    encoding: "utf-8",
    timeout: 30_000,
  }).trim();
}

export function run(prompt: string, cwd: string): string {
  const safe = prompt.replace(/'/g, "'\\''");
  return exec(`run '${safe}' --cwd '${cwd}'`);
}

export function status(): string {
  return exec("status");
}

export function stop(sessionId: string): string {
  return exec(`stop ${sessionId}`);
}

export function markDone(sessionId: string): string {
  return exec(`_mark-done ${sessionId}`);
}

export function healthCheck(): string {
  try {
    // Check for dead sessions — status command handles reaping
    return exec("status");
  } catch {
    return "health check failed";
  }
}
