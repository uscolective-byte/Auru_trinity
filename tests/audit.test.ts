import { describe, expect, it } from "vitest";
import { AuditLogger, redact } from "../src/audit.js";
import { RecordingAuditSink } from "./adapters.js";

describe("audit", () => {
  it("recursively redacts named secrets and bearer credentials", () => {
    expect(
      redact({ token: "abc", nested: [{ password: "p" }, "Bearer abc.def"] }),
    ).toEqual({
      token: "[REDACTED]",
      nested: [{ password: "[REDACTED]" }, "Bearer [REDACTED]"],
    });
  });

  it("writes a structured and redacted event", async () => {
    const sink = new RecordingAuditSink();
    const logger = new AuditLogger(
      sink,
      () => new Date("2026-01-02T03:04:05.000Z"),
    );
    await logger.record({
      correlationId: "corr-1",
      actor: "alice",
      operation: "external_write",
      policyResult: "allow",
      executionState: "completed",
      details: { apiKey: "secret" },
    });
    expect(sink.events[0]).toEqual({
      timestamp: "2026-01-02T03:04:05.000Z",
      correlationId: "corr-1",
      actor: "alice",
      operation: "external_write",
      policyResult: "allow",
      executionState: "completed",
      details: { apiKey: "[REDACTED]" },
    });
  });
});
