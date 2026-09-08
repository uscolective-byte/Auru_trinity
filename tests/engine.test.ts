import { describe, expect, it } from "vitest";
import { AuditLogger } from "../src/audit.js";
import { DecisionEngine } from "../src/engine.js";
import { ApprovalPolicy } from "../src/policy.js";
import {
  FixedApproval,
  FixedPlanner,
  RecordingAdapter,
  RecordingAuditSink,
} from "./adapters.js";

describe("DecisionEngine", () => {
  it("plans a task, requests approval, and performs no external write after rejection", async () => {
    const write = {
      id: "action-1",
      kind: "external_write" as const,
      description: "Update CRM",
      payload: { customer: "42", token: "must-not-leak" },
    };
    const planner = new FixedPlanner({ task: "", actions: [write] });
    const approval = new FixedApproval({
      approved: false,
      actor: "human-reviewer",
    });
    const externalService = new RecordingAdapter();
    const sink = new RecordingAuditSink();
    const engine = new DecisionEngine(
      planner,
      new ApprovalPolicy(new Set(["external_write", "send_message"])),
      approval,
      externalService,
      new AuditLogger(sink, () => new Date("2026-01-01T00:00:00Z")),
      () => "corr-integration-1",
    );

    const plan = await engine.run("Update customer 42", "alice");

    expect(plan.task).toBe("Update customer 42");
    expect(approval.requests).toEqual([write]);
    expect(externalService.executions).toEqual([]);
    expect(sink.events).toEqual([
      expect.objectContaining({
        correlationId: "corr-integration-1",
        actor: "human-reviewer",
        operation: "external_write",
        policyResult: "deny",
        executionState: "blocked",
        details: { customer: "42", token: "[REDACTED]" },
      }),
    ]);
  });

  it("executes an allowed read", async () => {
    const action = {
      id: "1",
      kind: "read" as const,
      description: "Read",
      payload: {},
    };
    const adapter = new RecordingAdapter();
    const sink = new RecordingAuditSink();
    const engine = new DecisionEngine(
      new FixedPlanner({ task: "", actions: [action] }),
      new ApprovalPolicy(new Set(["external_write"])),
      new FixedApproval({ approved: false, actor: "nobody" }),
      adapter,
      new AuditLogger(sink),
      () => "corr",
    );
    await engine.run("read", "alice");
    expect(adapter.executions).toEqual([action]);
    expect(sink.events[0]).toMatchObject({
      policyResult: "allow",
      executionState: "completed",
    });
  });

  it("rejects an empty task", async () => {
    const engine = new DecisionEngine(
      new FixedPlanner({ task: "", actions: [] }),
      new ApprovalPolicy(new Set()),
      new FixedApproval({ approved: true, actor: "user" }),
      new RecordingAdapter(),
      new AuditLogger(new RecordingAuditSink()),
    );
    await expect(engine.run(" ", "alice")).rejects.toThrow("Task is required");
  });
});
