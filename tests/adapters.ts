import type { AuditEvent, AuditSink } from "../src/audit.js";
import type {
  ActionAdapter,
  ApprovalProvider,
  Planner,
} from "../src/engine.js";
import type { ApprovalDecision, Plan, PlannedAction } from "../src/types.js";

export class FixedPlanner implements Planner {
  constructor(private readonly plan: Plan) {}
  async createPlan(task: string): Promise<Plan> {
    return Promise.resolve({ ...this.plan, task });
  }
}

export class FixedApproval implements ApprovalProvider {
  requests: PlannedAction[] = [];
  constructor(private readonly decision: ApprovalDecision) {}
  async request(action: PlannedAction): Promise<ApprovalDecision> {
    this.requests.push(action);
    return Promise.resolve(this.decision);
  }
}

export class RecordingAdapter implements ActionAdapter {
  executions: PlannedAction[] = [];
  async execute(action: PlannedAction): Promise<void> {
    this.executions.push(action);
    return Promise.resolve();
  }
}

export class RecordingAuditSink implements AuditSink {
  events: AuditEvent[] = [];
  async write(event: Readonly<AuditEvent>): Promise<void> {
    this.events.push(structuredClone(event));
    return Promise.resolve();
  }
}
