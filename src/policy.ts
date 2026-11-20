import type { ActionKind, ApprovalDecision, PolicyResult } from "./types.js";

export class ApprovalPolicy {
  constructor(private readonly sensitive: ReadonlySet<ActionKind>) {}

  evaluate(kind: ActionKind, decision?: ApprovalDecision): PolicyResult {
    if (!this.sensitive.has(kind)) return "allow";
    if (!decision) return "approval_required";
    return decision.approved ? "allow" : "deny";
  }
}
