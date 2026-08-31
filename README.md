# MCP Safety Control Plane

A local reference implementation for governing discovery and invocation of state-changing MCP tools in simulated engineering workflows.

> Prompts are not an authorization boundary. Tool access must be enforced during both discovery and invocation.

## Status

Phase 1 in progress: deterministic principals and equipment fixtures load and validate locally.

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
- One YAML policy file
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
```

`make test-container` builds and runs the full suite in Podman without using the host Python environment.

## Final verification target

The finished repository will support a clean-checkout workflow equivalent to:

```bash
docker compose up --build
make demo
make test
```

Docker Compose and `make demo` are not implemented yet.

## Development

- [MVP specification](docs/mvp-spec.md)
- [Repository rules](AGENTS.md)

Architecture, threat-model, and productionization documents will be added only when implementation creates concrete decisions to record.

## AI-assisted development

AI tools may assist with planning, implementation, tests, documentation, and review. Architecture, security boundaries, acceptance criteria, result interpretation, and merge approval remain human-owned.
