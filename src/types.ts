export type ActionKind = "read" | "external_write" | "send_message";

export interface PlannedAction {
  id: string;
  kind: ActionKind;
  description: string;
  payload: Readonly<Record<string, unknown>>;
}

export interface Plan {
  task: string;
  actions: readonly PlannedAction[];
}

export type PolicyResult = "allow" | "approval_required" | "deny";
export type ExecutionState = "not_started" | "blocked" | "completed" | "failed";

export interface ApprovalDecision {
  approved: boolean;
  actor: string;
}
