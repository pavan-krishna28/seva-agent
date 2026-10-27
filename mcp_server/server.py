"""MCP server exposing case-file tools to the triage agent.

Run standalone (stdio):  python mcp_server/server.py
The backend spawns it as a subprocess and talks to it over MCP.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DATA = Path(__file__).parent / "data"
mcp = FastMCP("seva-cases")


def _load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _case(case_id: str) -> dict:
    for c in _load("cases.json"):
        if c["id"] == case_id:
            return c
    raise ValueError(f"Unknown case_id '{case_id}'")


def _scheme(scheme_id: str) -> dict:
    schemes = _load("schemes.json")
    if scheme_id not in schemes:
        raise ValueError(f"Unknown scheme_id '{scheme_id}'. Known: {sorted(schemes)}")
    return schemes[scheme_id]


def _tokens(name: str) -> list[str]:
    return re.sub(r"[^a-z\s]", "", name.lower()).split()


def name_match(a: str, b: str) -> str:
    """'exact', 'partial' (initial/abbreviation) or 'mismatch'."""
    ta, tb = _tokens(a), _tokens(b)
    if ta == tb:
        return "exact"
    short, long_ = sorted([ta, tb], key=len)
    if short and all(any(t2.startswith(t1) or t1.startswith(t2) for t2 in long_) for t1 in short):
        return "partial"
    return "mismatch"


@mcp.tool()
def list_open_cases() -> dict:
    """List all cases waiting for review, with scheme and applicant language."""
    return {
        "cases": [
            {
                "id": c["id"],
                "scheme_id": c["scheme_id"],
                "applicant_name": c["applicant"]["name"],
                "language": c["applicant"]["language"],
                "submitted_on": c["submitted_on"],
            }
            for c in _load("cases.json")
        ]
    }


@mcp.tool()
def get_case(case_id: str) -> dict:
    """Get the full case file: applicant, language, scheme, form fields, attached documents."""
    return _case(case_id)


@mcp.tool()
def get_scheme_requirements(scheme_id: str) -> dict:
    """Get what a scheme requires: mandatory fields, mandatory documents, deadline rules."""
    return _scheme(scheme_id)


@mcp.tool()
def validate_document(case_id: str, doc_type: str) -> dict:
    """Check one attached document: is it present, does the name match the applicant, is it expired on the submission date."""
    case = _case(case_id)
    submitted = date.fromisoformat(case["submitted_on"])
    doc = next((d for d in case["documents"] if d["type"] == doc_type), None)
    if doc is None or not doc.get("present"):
        return {"doc_type": doc_type, "present": False, "issues": [{"code": "missing", "detail": f"{doc_type} not attached"}]}
    issues = []
    if doc.get("name_on_doc"):
        m = name_match(case["applicant"]["name"], doc["name_on_doc"])
        if m == "partial":
            issues.append({"code": "name_partial_match", "detail": f"Applicant '{case['applicant']['name']}' vs document '{doc['name_on_doc']}'"})
        elif m == "mismatch":
            issues.append({"code": "name_mismatch", "detail": f"Applicant '{case['applicant']['name']}' vs document '{doc['name_on_doc']}'"})
    if doc.get("expires_on") and date.fromisoformat(doc["expires_on"]) < submitted:
        issues.append({"code": "expired", "detail": f"Expired on {doc['expires_on']}, submitted {case['submitted_on']}"})
    return {"doc_type": doc_type, "present": True, "name_on_doc": doc.get("name_on_doc"), "issues": issues}


@mcp.tool()
def check_deadline(case_id: str) -> dict:
    """Check whether the case was submitted within the scheme's filing window or before its deadline."""
    case = _case(case_id)
    scheme = _scheme(case["scheme_id"])
    submitted = date.fromisoformat(case["submitted_on"])
    if scheme.get("claim_window_days") and case.get("incident_date"):
        days = (submitted - date.fromisoformat(case["incident_date"])).days
        return {"rule": f"{scheme['claim_window_days']} days from incident", "days_elapsed": days, "within_limit": days <= scheme["claim_window_days"]}
    if scheme.get("deadline"):
        return {"rule": f"deadline {scheme['deadline']}", "within_limit": submitted <= date.fromisoformat(scheme["deadline"])}
    return {"rule": "no time limit for this scheme", "within_limit": True}


if __name__ == "__main__":
    mcp.run()
