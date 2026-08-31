# Repository Instructions

## Goal

Implement only the local MVP in [docs/mvp-spec.md](docs/mvp-spec.md).

The system must prove that tool authorization is enforced in code during discovery and invocation, and that an approved write cannot be modified or replayed.

## Scope rules

- Keep the project local and deterministic.
- Do not require an LLM, cloud account, GPU, or external service.
- Do not add a UI, Kubernetes, OAuth/OIDC, multi-tenancy, or plugin system.
- Do not create abstractions for hypothetical future implementations.
- Prefer the Python standard library, SQLite, and existing dependencies.
- Add a dependency only when the current acceptance criteria cannot be met simply without it.
- Do not create placeholder folders or documents.

## Security rules

- Treat client identity, tool names, arguments, approvals, and downstream responses as untrusted input.
- Filter tools during discovery and authorize again during invocation.
- Resolve equipment ownership from trusted server-side data, never from a caller-supplied site claim.
- Bind approval to principal, tool, canonical arguments, expiry, and single-use state.
- Consume approval only after a successful downstream write.
- Denied calls must not reach downstream servers.
- Do not log API keys, approval secrets, or unnecessary raw arguments.
- Return stable reason codes for security decisions.

## Implementation rules

- Use Python 3.12+ with type annotations.
- Use Pydantic only at trust boundaries and persisted data contracts.
- Keep policy evaluation explicit and readable; YAML plus Python is sufficient.
- Use SQLite for approvals, tickets, and audit events.
- Keep the three public tools named exactly as specified.
- Keep the default demo data deterministic.
- One implementation path is enough; do not add interfaces or factories with one implementation.

## Quality gate

Before completing a change:

1. Run formatting and static checks once configured.
2. Run the smallest relevant test, then the full suite.
3. Confirm denied requests never call the downstream fixture.
4. Update the MVP specification only when behavior intentionally changes.
5. Keep README commands truthful; do not document commands that do not work.

Every non-trivial security rule needs one runnable test that fails if the rule is removed.

## Change workflow

```text
Issue with acceptance criteria
→ small implementation plan
→ bounded code change
→ independent review
→ tests
→ human approval
```

Do not merge autonomously. Do not combine unrelated phases in one change.

## Definition of done

The MVP is done when all scenarios in `docs/mvp-spec.md` pass locally from a clean checkout and the scripted demo finishes in under three minutes.

