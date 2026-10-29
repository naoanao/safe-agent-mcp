"""Safe AI Agent — free read-only MCP server (v0).

Three diagnostic tools distilled from the Safe AI Agent Pack:
  1. audit_api_keys           - flag over-privileged API keys from their
                                *permission descriptions* (never key values).
  2. check_idempotency_pattern - scan a code snippet for the signals that
                                actually stop duplicate execution.
  3. explain_guard_pattern    - explain a production guard pattern and the
                                failure it prevents.

Read-only: no network calls, no writes, no secrets accepted.
Run:  fastmcp run safe_agent_mcp.py  (or: python safe_agent_mcp.py)
"""

from __future__ import annotations

import re
from typing import Any

from fastmcp import FastMCP

mcp = FastMCP("Safe AI Agent Guard Checks")

# ---------------------------------------------------------------------------
# 1. API key privilege audit
# ---------------------------------------------------------------------------

_SECRET_LIKE = re.compile(r"^[A-Za-z0-9_\-./+=]{24,}$")
_DANGER_SCOPES = {
    "admin": "full administrative access",
    "administrator": "full administrative access",
    "*": "wildcard scope (everything)",
    "all": "unscoped 'all' permission",
    "root": "root-level access",
    "superuser": "superuser access",
}
_WRITE_WORDS = ("write", "create", "update", "post", "send", "modify")
_DELETE_WORDS = ("delete", "destroy", "remove", "drop", "purge")
_MONEY_WORDS = ("billing", "payment", "charge", "payout", "refund", "transfer")


def _looks_like_secret(value: str) -> bool:
    v = value.strip()
    return len(v) >= 24 and bool(_SECRET_LIKE.match(v)) and " " not in v


@mcp.tool
def audit_api_keys(keys: list[dict[str, Any]]) -> dict[str, Any]:
    """Audit API keys for over-privilege using permission *descriptions* only.

    Pass entries like {"name": "stripe-main", "service": "Stripe",
    "scopes": ["charges:write", "refunds:write"]}. NEVER pass actual key
    values — entries that look like secrets are rejected, not stored.
    Returns a per-key risk level with reasons and a summary count.
    """
    results: list[dict[str, Any]] = []
    rejected: list[str] = []

    for entry in keys:
        name = str(entry.get("name", "(unnamed)"))
        # Guard: refuse anything that looks like a real credential value.
        flat = " ".join(str(v) for v in entry.values() if not isinstance(v, (list, dict)))
        if any(_looks_like_secret(tok) for tok in flat.split()):
            rejected.append(name)
            continue

        scopes_raw = entry.get("scopes", entry.get("permissions", []))
        if isinstance(scopes_raw, str):
            scopes = [s.strip() for s in re.split(r"[,\s]+", scopes_raw) if s.strip()]
        else:
            scopes = [str(s) for s in scopes_raw]
        scope_text = " ".join(scopes).lower()

        reasons: list[str] = []
        score = 0
        for word, why in _DANGER_SCOPES.items():
            if re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", scope_text) or scope_text.strip() == word:
                reasons.append(f"dangerous scope '{word}': {why}")
                score += 3
        has_write = any(w in scope_text for w in _WRITE_WORDS)
        has_delete = any(w in scope_text for w in _DELETE_WORDS)
        has_money = any(w in scope_text for w in _MONEY_WORDS)
        if has_write and has_delete:
            reasons.append("combines write and delete — an agent loop can destroy what it creates")
            score += 2
        if has_money:
            reasons.append("touches money movement — keep behind a human approval gate")
            score += 2
        if len(scopes) > 8:
            reasons.append(f"broad scope list ({len(scopes)} scopes) — split into per-task keys")
            score += 1
        if not scopes:
            reasons.append("no scopes declared — privilege is unknown, treat as unverified")
            score += 1

        level = "high" if score >= 4 else "medium" if score >= 2 else "low"
        results.append(
            {"name": name, "service": entry.get("service"), "risk": level,
             "score": score, "scopes_checked": scopes, "reasons": reasons}
        )

    return {
        "audited": len(results),
        "rejected_looked_like_secrets": rejected,
        "high_risk": sum(1 for r in results if r["risk"] == "high"),
        "results": results,
        "note": "Audit is heuristic, based on declared scopes only. "
                "Full key-inventory script ships in the Safe AI Agent Pack ($69 / team $199).",
    }


# ---------------------------------------------------------------------------
# 2. Idempotency pattern check
# ---------------------------------------------------------------------------

_SIGNALS: list[tuple[str, str, str]] = [
    ("idempotency_key", r"idempotency|idem[-_ ]?key", "requests carry an idempotency key"),
    ("server_side_store", r"sqlite|database|\bdb\b|redis|INSERT\s+OR\s+IGNORE|ON\s+CONFLICT", "keys are stored server-side (not just in memory)"),
    ("unique_constraint", r"unique|PRIMARY\s+KEY|IntegrityError", "uniqueness is enforced, duplicates raise instead of running twice"),
    ("duplicate_short_circuit", r"already|exists|seen|dedup|duplicate", "a seen key short-circuits before the side effect runs"),
    ("payload_binding", r"hashlib|sha256|fingerprint|payload.{0,20}hash", "key is bound to the payload, so a reused key with a different body is caught"),
    ("approval_separation", r"approv|outbox|pending", "dangerous actions are separated from execution by approval/outbox"),
]


@mcp.tool
def check_idempotency_pattern(code: str) -> dict[str, Any]:
    """Check a code snippet for the signals that stop duplicate execution.

    Paste the function that performs the side effect (sending, charging,
    writing). Returns which guard signals are present, which are missing,
    and a plain verdict. Read-only static check — the code is not executed.
    """
    found, missing = [], []
    for signal, pattern, why in _SIGNALS:
        (found if re.search(pattern, code, re.IGNORECASE) else missing).append(
            {"signal": signal, "why_it_matters": why}
        )
    score = len(found)
    verdict = (
        "strong" if score >= 5 else
        "partial — the happy path is guarded, the retry path probably is not" if score >= 3 else
        "weak — a retried request can run the side effect twice"
    )
    return {"signals_found": found, "signals_missing": missing,
            "found_count": score, "of": len(_SIGNALS), "verdict": verdict}


# ---------------------------------------------------------------------------
# 3. Guard pattern explanations
# ---------------------------------------------------------------------------

_PATTERNS: dict[str, dict[str, str]] = {
    "idempotency_key": {
        "prevents": "The same email/payment/record being created twice when a request is retried.",
        "how": "Client generates one key per logical operation; server stores it with a unique constraint and returns the first result for repeats.",
        "minimal_shape": "key = uuid per operation; INSERT (key, result) with UNIQUE(key); on conflict, return stored result without re-running.",
    },
    "approval_gate": {
        "prevents": "An agent executing a dangerous or irreversible action with no human in the loop.",
        "how": "Action is recorded as a pending proposal; execution only happens after an explicit human approval, ideally via a signed link/token.",
        "minimal_shape": "propose(action) -> pending row; approve(token) verifies HMAC signature + expiry, then and only then executes.",
    },
    "outbox": {
        "prevents": "Lost or half-sent outbound actions, and sends that happen before approval.",
        "how": "Nothing is sent directly. Actions are written to an outbox table first; a dispatcher sends only approved rows and marks them sent.",
        "minimal_shape": "outbox(id, payload, status[pending|approved|sent]); dispatcher sends status=approved exactly once (see idempotency_key).",
    },
    "key_inventory": {
        "prevents": "Over-privileged API keys quietly giving an agent (or an attacker) far more power than its task needs.",
        "how": "Periodically list every key, its scopes and its owner; split broad keys into per-task keys; delete unused ones.",
        "minimal_shape": "Start with audit_api_keys in this server; the full inventory script ships in the Safe AI Agent Pack.",
    },
    "circuit_breaker": {
        "prevents": "Infinite tool loops and runaway API bills ($50+ from one stuck agent is a real, common accident).",
        "how": "Hard caps on iterations, per-run spend and repeats of the same call; tripping the cap stops the run and alerts a human.",
        "minimal_shape": "max_steps + max_cost counters checked before every tool call; same-call repeat counter that aborts at N.",
    },
    "signed_approval_link": {
        "prevents": "Forged or replayed approvals (anyone with the URL pressing 'approve').",
        "how": "Approval links carry an HMAC signature over action id + expiry; the server verifies before executing.",
        "minimal_shape": "token = HMAC(secret, f'{action_id}:{expires_at}'); verify signature and expiry on click; single-use.",
    },
}


@mcp.tool
def explain_guard_pattern(pattern: str) -> dict[str, Any]:
    """Explain one production guard pattern: what failure it prevents and its minimal shape.

    Known patterns: idempotency_key, approval_gate, outbox, key_inventory,
    circuit_breaker, signed_approval_link.
    """
    key = pattern.strip().lower().replace(" ", "_").replace("-", "_")
    if key not in _PATTERNS:
        return {"known": False, "available_patterns": sorted(_PATTERNS)}
    return {"known": True, "pattern": key, **_PATTERNS[key],
            "note": "Working code, tests and the 100 production traps catalog ship in the Safe AI Agent Pack ($69 / team $199)."}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
