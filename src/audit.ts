import type { ExecutionState, PolicyResult } from "./types.js";

export interface AuditEvent {
  timestamp: string;
  correlationId: string;
  actor: string;
  operation: string;
  policyResult: PolicyResult;
  executionState: ExecutionState;
  details: unknown;
}

export interface AuditSink {
  write(event: Readonly<AuditEvent>): Promise<void>;
}

const SENSITIVE_KEYS = /^(authorization|api[-_]?key|password|secret|token)$/i;
const BEARER = /\bBearer\s+[A-Za-z0-9._~+/=-]+/gi;

export function redact(value: unknown): unknown {
  if (typeof value === "string")
    return value.replace(BEARER, "Bearer [REDACTED]");
  if (Array.isArray(value)) return value.map(redact);
  if (value && typeof value === "object")
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        SENSITIVE_KEYS.test(key) ? "[REDACTED]" : redact(item),
      ]),
    );
  return value;
}

export class AuditLogger {
  constructor(
    private readonly sink: AuditSink,
    private readonly now: () => Date = () => new Date(),
  ) {}

  async record(
    event: Omit<AuditEvent, "timestamp" | "details"> & { details?: unknown },
  ): Promise<void> {
    await this.sink.write({
      ...event,
      timestamp: this.now().toISOString(),
      details: redact(event.details ?? {}),
    });
  }
}
