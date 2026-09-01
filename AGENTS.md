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
3. Run `make test-container` before opening or merging a pull request.
4. Confirm denied requests never call the downstream fixture.
5. Update the MVP specification only when behavior intentionally changes.
6. Keep README commands truthful; do not document commands that do not work.

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

# Engineering Rules

Apply these rules whenever creating, changing, or reviewing code. Follow existing repository conventions unless they conflict with these rules.

## 1. Keep the Happy Path Clear

- Validate inputs and preconditions at the beginning.
- Use guard clauses and early returns for failures.
- Avoid deeply nested conditionals.
- Keep the primary operation easy to read from top to bottom.

## 2. Use Domain-Specific Names

- Choose names that communicate business meaning and responsibility.
- Avoid vague names such as `data`, `item`, `result`, `value`, `handler`, or `manager`.
- Name booleans as questions or conditions, such as `isEligible` or `hasPermission`.
- Name functions after the action they perform.

## 3. Isolate External Systems

- Access external APIs, databases, file systems, queues, and SDKs through explicit boundary modules.
- Translate external data into internal domain models at the boundary.
- Do not spread vendor-specific fields or SDK types through business logic.
- Keep boundary interfaces small and easy to replace in tests.

## 4. Make Invalid States Unrepresentable

- Use types, schemas, constructors, and validation to enforce valid state.
- Represent materially different states with separate types or tagged unions.
- Do not make required state-dependent fields optional.
- Validate untrusted input once at the system boundary.

## 5. Separate Decisions from Side Effects

- Keep business rules and transformations pure whenever practical.
- Separate decisions from database writes, network requests, logging, and notifications.
- Pass required dependencies explicitly.
- Unit-test pure logic without external infrastructure.

## 6. Use Structured, Safe Errors

- Use stable, machine-readable error codes.
- Include a clear human-readable message and useful diagnostic context.
- Preserve the original error cause when wrapping failures.
- Never log passwords, tokens, secrets, personal data, or full sensitive payloads.
- Do not use vague errors such as `Something went wrong`.

## 7. Keep Changes Focused

- Each branch, commit, or pull request should have one clear responsibility.
- Do not mix features, refactoring, formatting, dependency upgrades, and unrelated fixes.
- Avoid speculative abstractions and changes not required by the current task.
- Preserve unrelated user changes already present in the working tree.

## Implementation Process

Before coding:

1. Restate the requested behavior and acceptance criteria.
2. Inspect existing patterns, tests, and boundaries.
3. Identify invalid inputs, external dependencies, and side effects.
4. Choose the smallest change that satisfies the requirement.

While coding:

1. Keep the main workflow flat and visible.
2. Use precise domain names.
3. Add abstractions only when they isolate a real boundary or remove demonstrated duplication.
4. Add or update tests with the implementation.
5. Keep unrelated changes out of the diff.

Before completion:

1. Review the diff against all seven rules.
2. Run the relevant formatter, linter, type checker, and tests.
3. Confirm failure paths and boundary behavior are tested.
4. Confirm logs and errors expose no sensitive information.
5. Remove dead code, debugging output, unnecessary comments, and unused dependencies.
6. Report what changed, what was verified, and any remaining limitations.

## Decision Priorities

When tradeoffs arise, use this order:

1. Correctness
2. Clarity
3. Testability
4. Security
5. Simplicity
6. Performance based on measured need
7. Extensibility based on a current requirement

Do not introduce frameworks, patterns, abstractions, or configuration for hypothetical future needs.