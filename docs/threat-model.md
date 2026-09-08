# Threat model

## Scope and trust boundaries

The decision engine accepts untrusted user tasks and memory, creates plans, evaluates every action against policy, and invokes an external-service adapter only after authorization. Planners, connector responses, stored memory, and user content are untrusted. The policy engine and audit sink are trusted controls. Human approval is bound to one concrete action and is not reusable.

## Threats and controls

| Risk                       | Example and impact                                                                        | Required controls                                                                                                                                                       | Residual risk / verification                                                                    |
| -------------------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Prompt injection           | A task or connector response instructs the planner to ignore policy and export data.      | Treat content as data; authorize each typed action after planning; never let model text alter policy; minimize connector privileges.                                    | Novel injections can influence planning. Test adversarial inputs and monitor denied operations. |
| Secret leakage             | Credentials appear in prompts, payloads, errors, or audit logs.                           | Keep secrets out of prompts where possible; redact sensitive keys and bearer values before audit persistence; use scoped, short-lived credentials; run secret scanning. | Unrecognized secret formats require updates to redaction rules and log review.                  |
| Tool abuse                 | The agent performs destructive writes or calls a tool with attacker-controlled arguments. | Allowlist typed tools; validate arguments; require approval for external writes and messages; default to no execution when rejected.                                    | An approved action can still cause harm; approval UI must show destination and effects.         |
| Unauthorized communication | The agent sends email, chat, or data to an unintended recipient.                          | Classify outbound messages as sensitive, require explicit approval, restrict destinations and egress, and audit actor/outcome.                                          | Compromised approved destinations remain possible; monitor volume and anomalies.                |
| Memory poisoning           | Untrusted content persists as an instruction and changes later behavior.                  | Keep bounded memory, preserve provenance in production, separate facts from instructions, validate writes, and never elevate memory above policy.                       | Plausible false facts may evade validation; support review, expiry, and deletion.               |

## Audit and incident response

Every attempted action records an ISO-8601 timestamp, correlation identifier, actor, operation, policy result, execution state, and redacted details. Correlation identifiers join planning, approval, and execution records without embedding user data. Audit sinks should be append-only, access-controlled, retention-limited, and monitored for denied sensitive actions. On an incident, revoke connector credentials, block the affected operation, preserve audit records, identify correlated actions, and remove poisoned memory before restoring access.
