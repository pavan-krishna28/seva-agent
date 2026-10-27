"""'What needs attention first': a transparent, rule-based score computed from the same MCP tools the agent uses.

No AI here on purpose: the officer should be able to see exactly why a case is ranked where it is, and the
overview must load instantly and for free. The AI summary and recommendation come on top, per case."""
from __future__ import annotations

import asyncio
from datetime import date

from .mcp_client import McpToolbox

# Each flag has a stable code; the UI translates it (en / hi / kn).
POINTS = {"late_filing": 40, "missing_doc": 15, "doc_expired": 12, "name_mismatch": 12,
          "name_partial_match": 6, "missing_field": 8}


def level(score: int) -> str:
    return "high" if score >= 50 else "medium" if score >= 25 else "low"


async def assess(case_id: str, toolbox: McpToolbox, today: date | None = None) -> dict:
    today = today or date.today()
    case, _ = await toolbox.call("get_case", {"case_id": case_id})
    scheme, _ = await toolbox.call("get_scheme_requirements", {"scheme_id": case["scheme_id"]})
    doc_types = [d["type"] for d in scheme["required_documents"]]
    *docs, deadline = await asyncio.gather(
        *[toolbox.call("validate_document", {"case_id": case_id, "doc_type": t}) for t in doc_types],
        toolbox.call("check_deadline", {"case_id": case_id}),
    )

    flags: list[dict] = []
    for field in scheme.get("required_fields", []):
        if case["fields"].get(field) in (None, ""):
            flags.append({"code": "missing_field", "detail": field})
    for (res, _), t in zip(docs, doc_types):
        if not res.get("present"):
            flags.append({"code": "missing_doc", "detail": t})
        for issue in res.get("issues", []):
            code = {"expired": "doc_expired"}.get(issue["code"], issue["code"])
            if code in POINTS:
                flags.append({"code": code, "detail": t})
    dl, _ = deadline
    if not dl.get("within_limit", True):
        flags.append({"code": "late_filing", "detail": dl.get("rule", "")})
    waiting = max(0, (today - date.fromisoformat(case["submitted_on"])).days)
    score = sum(POINTS[f["code"]] for f in flags) + min(waiting, 20)
    return {"id": case_id, "score": score, "level": level(score), "flags": flags, "waiting_days": waiting,
            "needs_fix": bool(flags)}
