# ADR 0001: Persist a SHA-256 audit hash chain

Status: Accepted

## Context

The local MVP must show when stored authorization decisions have been changed. Plain SQLite rows cannot demonstrate that property, while signed or externally anchored logs would add key management and infrastructure outside the MVP.

## Decision

Each audit row stores its decision fields, the previous row hash, and an SHA-256 hash of:

```text
previous_hash + "\n" + canonical_event_json
```

Canonical JSON uses UTF-8, sorted keys, compact separators, and unescaped Unicode. The first row uses 64 zeroes as its previous hash. Events store only timestamp, event type, principal ID when known, tool name when valid, decision, and reason code. API keys, raw arguments, and approval secrets are excluded.

## Consequences

The chain is deterministic and locally verifiable. Changing an event or its link causes verification to fail.

This demonstrates tamper evidence, not immutability. A database writer could recompute the chain, and deleting the tail cannot be detected without an external anchor. Signing, anchoring, retention controls, and concurrent-writer hardening belong to productionization, not this local MVP.
