# Auru_trinity

AURA Space — an autonomous AI agent platform for business automation, customer discovery, CRM workflows, AI operations, and secure integrations. It is built with Node.js, Cloudflare Workers, OpenAI, and a modular connector architecture with human approval gates for sensitive actions.

## Development

Requires Node.js 22. Install with `npm ci`, then run `npm run format:check`, `npm run lint`, `npm run typecheck`, and `npm test`.

The core package provides a decision engine with per-action approval gates, bounded memory, validated configuration, and structured/redacted audit events. Tests use deterministic in-memory adapters and never contact external services. See [`docs/threat-model.md`](docs/threat-model.md) for security assumptions and mitigations.
