/**
 * tq OpenClaw Plugin — Claude Code sessions in tmux
 *
 * Registers 3 tools (tq_run, tq_status, tq_stop), 1 background service
 * (health checker), and 1 hook (session context injection).
 */

import * as tq from "./tq-bridge.js";

export default {
  id: "tq",
  name: "tq — Claude Code Sessions",
  description: "Spawn and manage Claude Code sessions in tmux",
  kind: "tools",

  register(api: any) {
    const config = api.pluginConfig ?? {};
    const tqPath = config.tqPath || "tq";
    const defaultCwd = config.defaultCwd || "~";

    tq.configure(tqPath);

    // ── Tool: tq_run ──────────────────────────────────────────────────
    api.registerTool(
      () => ({
        name: "tq_run",
        description:
          "Spawn a Claude Code session in tmux with a prompt. Returns the session ID.",
        inputSchema: {
          type: "object",
          properties: {
            prompt: {
              type: "string",
              description: "The prompt for Claude Code to execute",
            },
            cwd: {
              type: "string",
              description: "Working directory for the session",
            },
          },
          required: ["prompt"],
        },
        execute: async ({ prompt, cwd }: { prompt: string; cwd?: string }) => {
          const result = tq.run(prompt, cwd || defaultCwd);
          return { content: [{ type: "text", text: result }] };
        },
      }),
      { name: "tq_run" },
    );

    // ── Tool: tq_status ───────────────────────────────────────────────
    api.registerTool(
      () => ({
        name: "tq_status",
        description: "List all tq sessions with their status (running/done/pending)",
        inputSchema: { type: "object", properties: {} },
        execute: async () => {
          const result = tq.status();
          return { content: [{ type: "text", text: result || "No sessions." }] };
        },
      }),
      { name: "tq_status" },
    );

    // ── Tool: tq_stop ─────────────────────────────────────────────────
    api.registerTool(
      () => ({
        name: "tq_stop",
        description: "Stop a running Claude Code session by ID",
        inputSchema: {
          type: "object",
          properties: {
            session_id: {
              type: "string",
              description: "The session ID to stop",
            },
          },
          required: ["session_id"],
        },
        execute: async ({ session_id }: { session_id: string }) => {
          const result = tq.stop(session_id);
          return { content: [{ type: "text", text: result }] };
        },
      }),
      { name: "tq_stop" },
    );

    // ── Service: health check ─────────────────────────────────────────
    api.registerService({
      name: "tq-health",
      interval: 30_000,
      execute: async () => {
        tq.healthCheck();
      },
    });

    // ── Hook: inject session context ──────────────────────────────────
    api.on("before_agent_start", () => {
      try {
        const sessions = tq.status();
        if (sessions && sessions !== "No sessions.") {
          return { prependContext: `Active tq sessions:\n${sessions}` };
        }
      } catch {
        // Non-fatal — don't block agent start
      }
      return {};
    });
  },
};
