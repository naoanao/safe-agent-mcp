# Installing safe-agent-mcp

safe-agent-mcp is a free, read-only MCP server that runs three diagnostic
tools for AI agents: `audit_api_keys`, `check_idempotency_pattern`, and
`explain_guard_pattern`. It makes no network calls and writes nothing.

## Requirements

- Python 3.10 or newer
- An MCP client (Cline, Claude Desktop, Claude Code, Gemini CLI, etc.)
- No API keys are required. The server never asks for, stores, or transmits
  secrets; `audit_api_keys` works from permission *descriptions* only and
  refuses secret-looking values.

## Option A — install from PyPI (recommended)

```bash
pip install safe-agent-mcp
```

Run it:

```bash
python3 -m safe_agent_mcp
# or, using the console script:
safe-agent-mcp
```

## Option B — run from source

```bash
git clone https://github.com/naoanao/safe-agent-mcp.git
cd safe-agent-mcp
pip install -r requirements.txt
python3 safe_agent_mcp.py
```

## Client configuration (stdio)

```json
{
  "mcpServers": {
    "safe-agent-mcp": {
      "command": "python3",
      "args": ["-m", "safe_agent_mcp"]
    }
  }
}
```

For Cline, add the same block under `cline_mcp_settings.json`.

## Verify the installation

Call any tool, for example `explain_guard_pattern` with
`pattern_name: "idempotency_key"`. You should receive a short explanation
of the pattern. A self-test is also included in the repository:

```bash
python3 test_server.py
```

## Troubleshooting

- **`ModuleNotFoundError: safe_agent_mcp`** — reinstall into the same
  Python environment your MCP client uses (`pip install safe-agent-mcp`),
  or point the client at the cloned `safe_agent_mcp.py` path instead.
- **Server starts but no tools appear** — make sure the client is using
  stdio transport and that the command exits only when the client closes;
  check the client's MCP log for a Python traceback.
- **Live demo** — the three tools also run in your browser at
  https://naoanao.github.io/safe-agent-mcp/ if you want to preview the
  outputs before installing.
