import { randomUUID } from "node:crypto";
import type { AuditLogger } from "./audit.js";
import type { ApprovalPolicy } from "./policy.js";
import type { ApprovalDecision, Plan, PlannedAction } from "./types.js";

export interface Planner {
  createPlan(task: string): Promise<Plan>;
}

export interface ActionAdapter {
  execute(action: PlannedAction): Promise<void>;
}

export interface ApprovalProvider {
  request(action: PlannedAction): Promise<ApprovalDecision>;
}

export class DecisionEngine {
  constructor(
    private readonly planner: Planner,
    private readonly policy: ApprovalPolicy,
    private readonly approval: ApprovalProvider,
    private readonly adapter: ActionAdapter,
    private readonly audit: AuditLogger,
    private readonly correlationId: () => string = randomUUID,
  ) {}

  async run(task: string, actor: string): Promise<Plan> {
    if (!task.trim()) throw new Error("Task is required");
    const plan = await this.planner.createPlan(task);
    const correlationId = this.correlationId();
    for (const action of plan.actions) {
      let result = this.policy.evaluate(action.kind);
      let approvalActor = actor;
      if (result === "approval_required") {
        const decision = await this.approval.request(action);
        approvalActor = decision.actor;
        result = this.policy.evaluate(action.kind, decision);
      }
      if (result !== "allow") {
        await this.audit.record({
          correlationId,
          actor: approvalActor,
          operation: action.kind,
          policyResult: result,
          executionState: "blocked",
          details: action.payload,
        });
        continue;
      }
      await this.adapter.execute(action);
      await this.audit.record({
        correlationId,
        actor,
        operation: action.kind,
        policyResult: result,
        executionState: "completed",
        details: action.payload,
      });
    }
    return plan;
  }
}
