# MCP Safety Control Plane

A local reference implementation for governing discovery and invocation of state-changing MCP tools in simulated engineering workflows.

> Prompts are not an authorization boundary. Tool access must be enforced during both discovery and invocation.

## Status

The local MVP is implemented: deterministic fixtures, downstream MCP servers, identity, filtered discovery, site authorization, exact one-time SQLite approvals, tamper-evident audit events, and a scripted security demo.

## MVP

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

The demo is complete when it proves:

1. An engineer sees only authorized tools.
2. Reading assigned-site equipment succeeds.
3. Reading another site's equipment is denied.
4. Creating a maintenance ticket without approval is denied.
5. A supervisor approves the exact request once; the ticket is created and replay is denied.

## Deliberately small

- Two roles: engineer and supervisor
- Two sites
- Two downstream MCP servers
- Three tools
- One local JSON fixture file
- One SQLite database
- One command-line demo
- No paid model or cloud account

## Not in the MVP

- Browser UI
- LLM orchestration
- OAuth, OIDC, or SSO
- Kubernetes
- Multi-tenancy
- Real equipment control
- Production or compliance claims

## Local development

Clean-room validation requires Podman only:

```bash
make test-container
podman compose up --build
```

`make test-container` builds and runs the full suite in Podman without using the host Python environment.
The Compose command builds the same image and runs the end-to-end demo without persisting its SQLite database.

The image contains two stdio MCP servers:

```bash
python -m mcp_control_plane.telemetry_server
python -m mcp_control_plane.maintenance_server
```

They expose exactly three tools: `read_equipment_status`, `list_active_alarms`, and `create_maintenance_ticket`. These downstream servers intentionally do not enforce access policy; the gateway will own that boundary.

## End-to-end demo

With Python 3.12 and the project installed, the same demo runs directly:

```bash
make demo
```

It prints seven `PASS` lines covering filtered discovery, assigned-site access, cross-site denial, approval enforcement, one-time use, and audit-chain verification. Any failed check exits non-zero.

## Development

- [MVP specification](docs/mvp-spec.md)
- [Repository rules](AGENTS.md)
- [Audit hash-chain decision](docs/adr/0001-audit-hash-chain.md)

Architecture, threat-model, and productionization documents will be added only when implementation creates concrete decisions to record.

## AI-assisted development

AI tools may assist with planning, implementation, tests, documentation, and review. Architecture, security boundaries, acceptance criteria, result interpretation, and merge approval remain human-owned.
