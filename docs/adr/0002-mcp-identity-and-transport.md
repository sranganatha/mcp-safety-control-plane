# ADR 0002: Carry demo identity in MCP request metadata over stdio

Status: Accepted

## Context

The governed gateway must filter `tools/list` and reauthorize `tools/call` for the same client identity. Putting the development API key in every tool schema would expose an authentication concern as business input, while process-global identity would not be request-scoped. Adding HTTP authentication would expand this local MVP into deployment infrastructure.

The gateway must also prove that downstream execution crosses an MCP client/server boundary rather than importing tool functions.

## Decision

Clients place the development API key in request `_meta` under `io.github.sranganatha.mcp-safety-control-plane/api-key`. The gateway reads it for both discovery and invocation, never returns or audits it, and treats a missing or non-string value as missing identity.

The local gateway uses the installed MCP client with stdio subprocess transports for telemetry and maintenance. This exercises MCP request handling across process boundaries while keeping the demo deterministic and network-free.

## Consequences

Discovery can vary safely per request and credentials stay out of public tool schemas. Tests and the demo can prove the complete local MCP path without another dependency.

The metadata key and fixture API keys are development contracts, not production authentication. A deployed service must replace them with transport authentication such as verified OAuth tokens and must manage long-lived downstream sessions when measurements justify it.
