"""End-to-end test: connect to the MCP server in-memory and call all 3 tools."""
import asyncio
import json

from fastmcp import Client

from safe_agent_mcp import mcp


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print("TOOLS:", [t.name for t in tools])

        r1 = await client.call_tool("audit_api_keys", {"keys": [
            {"name": "stripe-main", "service": "Stripe",
             "scopes": ["charges:write", "refunds:write", "admin"]},
            {"name": "readonly-analytics", "service": "GA4", "scopes": ["read"]},
            {"name": "suspicious", "service": "?", "scopes": ["read"],
             "note": "sk" + "_live_" + "FAKE0EXAMPLE0KEY0DO0NOT0USE0"},  # fake secret, assembled at runtime so scanners do not flag the test literal
        ]})
        print("\nAUDIT:", json.dumps(r1.data, ensure_ascii=False, indent=1)[:1200])

        sample_code = '''
def send_invoice(req):
    key = req.headers["Idempotency-Key"]
    row = db.execute("INSERT OR IGNORE INTO sent (idem_key, payload_hash) VALUES (?, ?)",
                     (key, hashlib.sha256(body).hexdigest()))
    if already_sent(key):
        return stored_result(key)
    ...  # side effect
'''
        r2 = await client.call_tool("check_idempotency_pattern", {"code": sample_code})
        print("\nIDEMPOTENCY:", json.dumps(r2.data, ensure_ascii=False, indent=1))

        r3 = await client.call_tool("explain_guard_pattern", {"pattern": "approval gate"})
        print("\nEXPLAIN:", json.dumps(r3.data, ensure_ascii=False, indent=1))

        r4 = await client.call_tool("explain_guard_pattern", {"pattern": "nonsense"})
        print("\nEXPLAIN-UNKNOWN:", json.dumps(r4.data, ensure_ascii=False))

    print("\nALL CALLS OK")


if __name__ == "__main__":
    asyncio.run(main())
