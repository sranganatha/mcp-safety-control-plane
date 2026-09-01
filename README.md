# MCP Safety Control Plane

[![CI](https://github.com/sranganatha/mcp-safety-control-plane/actions/workflows/ci.yml/badge.svg)](https://github.com/sranganatha/mcp-safety-control-plane/actions/workflows/ci.yml)

A local reference implementation for governing high-risk MCP tool calls, demonstrated through a simulated industrial maintenance workflow.

> Prompts are not an authorization boundary. Tool access must be enforced during both discovery and invocation.

## How it works

One engineer interacts with two simulated equipment sites through an MCP gateway:

```text
MCP client
   ↓ identity
Control plane
   ├─ filters visible tools
   ├─ validates exact arguments
   ├─ enforces site access
   ├─ checks one-time approval for writes
   └─ records the decision
   ↓
Telemetry and maintenance MCP servers
```

The telemetry server represents read-only equipment status and active-alarm queries. The maintenance server represents a controlled workflow that creates maintenance tickets. These are realistic industrial boundaries, but the project does not implement or claim SECS/GEM support.

The gateway exposes `read_equipment_status`, `list_active_alarms`, and `create_maintenance_ticket`. Discovery is filtered by role, but every invocation independently rechecks identity, role, exact arguments, and equipment ownership before reaching a downstream MCP server.

## Exact request approval

The central design contribution is an approval bound to the complete intended action: requesting principal, tool name, canonical argument hash, equipment site, approver role, expiry, and unused state.

Arguments are serialized as sorted-key JSON with stable separators before hashing. Equivalent requests therefore have the same identity regardless of key order, while changing the equipment, reason, or idempotency key invalidates the approval. Approval is consumed only after the downstream write succeeds, so a transient downstream failure does not destroy authorization for an action that never completed.

Supervisor approval is a trusted, out-of-band control-plane operation and is intentionally not exposed as an MCP tool. An LLM can request an action, but it cannot approve its own request.

## Security invariants

| Threat | Enforcement point | Runnable evidence |
|---|---|---|
| Hidden-tool invocation | Invocation role policy, independent of discovery | `test_supervisor_cannot_directly_invoke_hidden_write` |
| Cross-site access | Trusted server-side equipment ownership check before dispatch | `test_denied_mcp_call_does_not_cross_downstream_boundary` |
| Approval argument modification | Canonical argument-hash comparison | `test_modified_arguments_cannot_use_existing_approval` |
| Approval replay | One-time approval consumption check | `test_approved_write_succeeds_once_through_gateway` |
| Downstream failure | Approval consumed only after successful write | `test_downstream_failure_leaves_approval_unused` |
| Audit modification | Stored hash-chain verification | `test_changed_event_fails_verification` |

## Transferable patterns

The equipment scenario is one concrete example of a general authorization pattern for high-risk agent actions, including:

- Financial transactions
- Infrastructure changes
- Healthcare workflows
- Customer-data access
- Communications and publishing
- Administrative operations

## Scope

This local MVP uses deterministic fixtures, three tools, two downstream MCP servers, and SQLite-backed approvals, tickets, and audit events. It is not a general-purpose MCP proxy, OAuth platform, production gateway, real equipment controller, or compliance-certified system.

## Local development

Clean-room validation requires Podman only:

```bash
podman info
make test-container
podman compose up --build
```

On Windows and macOS, the Podman machine must be running before these commands are used. No host Python installation is required.

## End-to-end demo

The demo exits non-zero if any security invariant fails.

For an installed development environment, it can also be run with `make demo`.

## Design references

- [MVP specification](docs/mvp-spec.md)
- [Repository rules](AGENTS.md)
- [Audit hash-chain decision](docs/adr/0001-audit-hash-chain.md)
- [MCP identity and transport decision](docs/adr/0002-mcp-identity-and-transport.md)
