# MVP Specification

## 1. Purpose

Prove one claim:

> An MCP client cannot discover or invoke a tool unless server-side policy permits the exact action, and a state-changing action requires a matching one-time approval.

## 2. Actors and fixtures

### Principals

| ID | Role | Assigned site |
|---|---|---|
| `eng-a` | Engineer | `site-a` |
| `sup-a` | Supervisor | `site-a` |

Identity is supplied through development API keys stored in local fixture configuration. This is not production authentication.

### Equipment

| ID | Site | State |
|---|---|---|
| `etch-101` | `site-a` | Elevated temperature and active warning |
| `etch-201` | `site-b` | Normal |

Equipment-to-site ownership is trusted server-side data.

### Tools

| Tool | Risk | Rule |
|---|---:|---|
| `read_equipment_status` | Low | Engineer or supervisor; assigned site only |
| `list_active_alarms` | Low | Engineer or supervisor; assigned site only |
| `create_maintenance_ticket` | High | Engineer; assigned site; exact supervisor approval required |

## 3. End-to-end flow

### Discovery

1. Client supplies an API key.
2. Gateway resolves the principal.
3. Gateway evaluates each registered tool against the principal's role.
4. Gateway returns only permitted tools.
5. Gateway records the discovery decision without secrets.

### Read invocation

1. Client calls a visible read tool with `equipment_id`.
2. Gateway validates the request schema.
3. Gateway resolves the equipment site from trusted configuration.
4. Gateway rechecks role and site policy.
5. Allowed calls reach the telemetry MCP server; denied calls do not.
6. Gateway records the result.

### Approved write

1. Engineer requests `create_maintenance_ticket`.
2. Gateway validates role, site, and arguments.
3. Gateway denies the call with `APPROVAL_REQUIRED`.
4. Supervisor approves the canonical request.
5. Gateway stores an expiring approval bound to principal, tool, and argument hash.
6. Engineer retries the exact call with the approval identifier.
7. Gateway executes the maintenance tool.
8. Gateway consumes the approval after successful execution.
9. Reuse or argument modification is denied.

## 4. Approval contract

An approval is valid only when all values match:

- Requesting principal ID
- Tool name
- Canonical argument hash
- Equipment site
- Approver role
- Unexpired timestamp
- Unused status

Canonical arguments use sorted-key JSON with stable separators before hashing.

Approval must remain unused if the downstream write fails.

## 5. Required reason codes

| Code | Meaning |
|---|---|
| `IDENTITY_REQUIRED` | No credential supplied |
| `IDENTITY_INVALID` | Credential is unknown |
| `TOOL_NOT_AUTHORIZED` | Role cannot invoke the tool |
| `ARGUMENTS_INVALID` | Request does not match the tool schema |
| `EQUIPMENT_NOT_FOUND` | Equipment ID is unknown |
| `CROSS_SITE_ACCESS` | Equipment is outside the principal's assigned site |
| `APPROVAL_REQUIRED` | Valid approval was not supplied |
| `APPROVAL_MISMATCH` | Approval does not match the exact request |
| `APPROVAL_EXPIRED` | Approval is no longer valid |
| `APPROVAL_ALREADY_USED` | Approval was previously consumed |
| `DOWNSTREAM_FAILURE` | Authorized downstream execution failed |

## 6. Persistence

Use one local SQLite database containing only:

- Approvals
- Maintenance tickets
- Audit events

Fixture principals and equipment may remain in YAML configuration.

Audit events form a hash chain using normalized event data plus the previous event hash. This demonstrates tamper evidence; it is not an immutable production audit system.

## 7. Acceptance scenarios

### Identity and discovery

- [ ] Missing API key is rejected with `IDENTITY_REQUIRED`.
- [ ] Unknown API key is rejected with `IDENTITY_INVALID`.
- [ ] `eng-a` discovers the two read tools and the approved-write capability defined by policy.
- [ ] A fabricated or hidden tool name cannot bypass invocation authorization.

### Site authorization

- [ ] `eng-a` reads `etch-101` successfully.
- [ ] `eng-a` cannot read `etch-201` and receives `CROSS_SITE_ACCESS`.
- [ ] Cross-site denial occurs before the telemetry server is called.

### Approval safety

- [ ] Ticket creation without approval returns `APPROVAL_REQUIRED`.
- [ ] Approval for `etch-101` cannot authorize `etch-201`.
- [ ] Approval cannot authorize modified ticket arguments.
- [ ] Expired approval returns `APPROVAL_EXPIRED`.
- [ ] Successful ticket creation consumes approval.
- [ ] Reusing consumed approval returns `APPROVAL_ALREADY_USED`.
- [ ] Downstream failure does not consume approval.

### Auditability

- [ ] Every invocation attempt produces an audit event.
- [ ] Audit events contain decision and reason code.
- [ ] Audit events do not contain API keys.
- [ ] Audit-chain verification passes for intact events.
- [ ] Audit-chain verification fails after stored event mutation.

## 8. Implementation slices

Implement and verify one slice at a time:

1. Project tooling and deterministic fixture loading
2. Three downstream MCP tools
3. Identity and filtered discovery
4. Invocation and site authorization
5. Exact one-time approval
6. Audit hash chain
7. Security scenarios and scripted demo

Do not start a later slice until the current slice has one runnable check.

## 9. Completion check

The MVP is complete when:

- All acceptance scenarios pass without an LLM or network access.
- `docker compose up --build`, `make test`, and `make demo` work from a clean checkout.
- The demo completes in under three minutes.
- The README accurately describes implemented behavior and limitations.

