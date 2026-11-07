---
title: "fix: MCP endpoint answers 421 on the public hostnames"
type: fix
status: active
date: 2026-11-07
---

# fix: MCP endpoint answers 421 on the public hostnames

## Problem

On 2026-11-04 the MCP mount fix (PR #25) moved `POST /mcp` on PROD from 405 to
421 Misdirected Request. The route now reaches the MCP SDK, but the SDK rejects
the request's `Host` header.

Cause: `folio_mcp.server.mcp` is a `FastMCP` built with the default
`host="127.0.0.1"`. For a loopback host, `mcp` 1.27 auto-enables DNS-rebinding
protection with `allowed_hosts` limited to `127.0.0.1:*`, `localhost:*` and
`[::1]:*`. Caddy forwards `Host: folio.openlegalstandard.org` (and
`soli.openlegalstandard.org`), so every public MCP request fails validation.

## Approach

folio-api owns the deployment, so it owns the host allowlist. Before calling
`streamable_http_app()`, folio-api sets `folio_mcp_server.settings.transport_security`
to a `TransportSecuritySettings` that keeps DNS-rebinding protection **on** and
allows:

- the loopback hosts the SDK allows by default (local dev and the container
  health check keep working);
- the public hostnames, read from `config["api"]["mcp_allowed_hosts"]`, which
  defaults to `["folio.openlegalstandard.org", "soli.openlegalstandard.org"]`
  so PROD needs no config change;
- matching `https://` origins for those hosts, plus loopback origins.

Keeping protection on (rather than disabling it) preserves the SDK's defense
against browser-driven DNS rebinding while admitting the real public names.

Review follow-ups (2026-11-07): the default list also carries the DEV preview,
`folio-api.dev.openlegalstandard.org`, which answered 421 too. Portless loopback
names (`localhost`, `127.0.0.1`, `[::1]`) are admitted because the dev Caddy serves
port 80, so clients omit the port.

Deliberate limit: a browser page served from any other origin (for example a hosted
MCP inspector) gets 403 "Invalid Origin header", even though the REST API's CORS
allows `*`. That origin check is the DNS-rebinding defense. Hosted connectors and
CLI clients send no Origin header and are unaffected.

## Verification

- A test drives the real app: `POST /mcp` with `Host: folio.openlegalstandard.org`
  and an MCP `initialize` body no longer returns 421; an unlisted host such as
  `evil.example` still returns 421.
- Full folio-api test suite passes.
- After deploy: `curl -X POST https://folio.openlegalstandard.org/mcp` with an
  `initialize` body returns a JSON-RPC result, not 421; `/info/health` 200.

## Rollback

Retag the pre-deploy image and recreate the container, as in the 2026-11-04
receipt.
