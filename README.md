<!-- mcp-name: io.github.naoanao/safe-agent-mcp -->

# Safe AI Agent — Guard Checks (free MCP server)

A free, read-only MCP server with three diagnostic tools for people who run
AI agents in production. Distilled from the **Safe AI Agent Pack** — the
production guard modules used by the Sage personal agent and the Growl AI
marketing SaaS.

No network calls. No writes. Inputs that look like real secrets are refused.

## Tools

| Tool | What it does |
|---|---|
| `audit_api_keys` | Flags over-privileged API keys from their permission *descriptions* (never pass key values — secret-looking entries are rejected, not stored) |
| `check_idempotency_pattern` | Scans a code snippet for the signals that actually stop duplicate execution: idempotency key, server-side store, uniqueness, short-circuit, payload binding, approval separation |
| `explain_guard_pattern` | Explains a production guard pattern — the failure it prevents and its minimal shape (`idempotency_key`, `approval_gate`, `outbox`, `key_inventory`, `circuit_breaker`, `signed_approval_link`) |

## Install & run

```bash
git clone <this repo>
cd safe-agent-mcp
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python safe_agent_mcp.py   # stdio transport
```

Claude Desktop / Cursor MCP config:

```json
{
  "mcpServers": {
    "safe-agent-guard-checks": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/safe_agent_mcp.py"]
    }
  }
}
```

## Test

```bash
.venv/bin/python test_server.py   # in-memory client; calls every tool
```

## The full pack

This free server is the diagnostic front door. The production modules —
SQLite idempotency store, `@once` decorator, approval outbox with HMAC-signed
approval links, the token-privilege inventory script, 18 regression tests and
the 100 production-traps catalog — ship in the
[Safe AI Agent Pack ($69 / team $199)](https://growl-ai.com/store/en).

## License

MIT for this free server. The paid pack has its own commercial license.

## Get the kit

- **Starter Kit ($19)** — the 24-traps checklist + guard-patterns guide bundle: https://whop.com/growl-ai/safe-ai-agent-starter-kit-guardrails-for-ai-agents
- **Full Pack ($69 / team $199)** — 100-traps catalog, working modules, sabotage-test playbook: https://growl-ai.com/store/en
- Background reading: [Idempotency Keys, Explained (dev.to)](https://dev.to/naoanao/idempotency-keys-explained-how-to-stop-your-ai-agent-from-running-things-twice-25jp)
