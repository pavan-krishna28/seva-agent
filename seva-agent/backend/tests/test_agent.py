"""Tests run the real agent loop against the real MCP server (stdio subprocess).
Only the LLM is scripted, so no API key or network is needed."""
import functools
import inspect
from contextlib import AsyncExitStack

import pytest
from fastapi.testclient import TestClient

from app.agent import AgentError, run_triage
from app.main import create_app
from app.mcp_client import McpToolbox
from mcp_server import server as srv


def tu(id_, name, **inp):
    return {"type": "tool_use", "id": id_, "name": name, "input": inp}


GOOD_TRIAGE = dict(
    summary="Photo missing and bank name is abbreviated.",
    missing_items=[{"item": "crop_loss_photo", "why": "Required by scheme"}],
    risks=[{"issue": "Bank name differs", "evidence": "Ramesh G vs Ramesh Gowda"}],
    recommended_action="request_more_info",
    reason="Applicant can fix both quickly.",
    message_to_applicant="ದಯವಿಟ್ಟು ಬೆಳೆ ಹಾನಿಯ ಫೋಟೋ ಮತ್ತು ಬ್ಯಾಂಕ್ ಪಾಸ್‌ಬುಕ್ ತನ್ನಿ.",
    confidence="high",
)


class ScriptedLLM:
    model = "scripted"

    def __init__(self, script):
        self.script = list(script)
        self.seen = []

    async def create(self, system, messages, tools):
        self.seen.append((system, [m for m in messages], [t["name"] for t in tools]))
        content = self.script.pop(0) if self.script else [tu("loop", "list_open_cases")]
        return {"stop_reason": "tool_use", "content": content}


def happy_script(case="C-1001", scheme="crop_loss_claim"):
    return [
        [tu("a1", "get_case", case_id=case)],
        [
            tu("b1", "get_scheme_requirements", scheme_id=scheme),
            tu("b2", "validate_document", case_id=case, doc_type="bank_passbook"),
            tu("b3", "validate_document", case_id=case, doc_type="crop_loss_photo"),
            tu("b4", "check_deadline", case_id=case),
        ],
        [tu("c1", "submit_triage", **GOOD_TRIAGE)],
    ]


def with_toolbox(fn):
    """Open the MCP session inside the test's own task (anyio cancel scopes
    can't be exited from a different task, so an async fixture won't work)."""
    @functools.wraps(fn)
    async def wrapper():
        async with AsyncExitStack() as stack:
            tb = McpToolbox()
            await tb.start(stack)
            await fn(tb)

    wrapper.__signature__ = inspect.Signature()
    return wrapper


# ---------- agent loop ----------

@with_toolbox
async def test_full_triage_over_real_mcp(toolbox):
    llm = ScriptedLLM(happy_script())
    out = await run_triage("C-1001", llm, toolbox)
    assert out["triage"]["recommended_action"] == "request_more_info"
    assert out["steps"] == 3
    names = [t["tool"] for t in out["trace"]]
    assert names == ["get_case", "get_scheme_requirements", "validate_document", "validate_document", "check_deadline", "submit_triage"]
    assert all(t["source"] == "mcp" for t in out["trace"][:-1])
    assert out["trace"][-1]["source"] == "local"
    # the model really received MCP output on its next turn
    tool_results = llm.seen[1][1][-1]["content"]
    assert "Hosahalli" in tool_results[0]["content"]
    # tools offered to the model = MCP tools + local submit tool
    assert "submit_triage" in llm.seen[0][2] and "validate_document" in llm.seen[0][2]


@with_toolbox
async def test_invalid_submission_is_bounced_then_accepted(toolbox):
    bad = {k: v for k, v in GOOD_TRIAGE.items() if k != "message_to_applicant"}
    llm = ScriptedLLM([[tu("s1", "submit_triage", **bad)], [tu("s2", "submit_triage", **GOOD_TRIAGE)]])
    out = await run_triage("C-1001", llm, toolbox)
    assert out["trace"][0]["is_error"] is True
    assert "message_to_applicant" in out["trace"][0]["output"]
    assert out["trace"][1]["is_error"] is False


@with_toolbox
async def test_tool_errors_are_returned_to_model_not_raised(toolbox):
    llm = ScriptedLLM([
        [tu("e1", "get_case", case_id="NOPE"), tu("e2", "does_not_exist")],
        [tu("e3", "submit_triage", **GOOD_TRIAGE)],
    ])
    out = await run_triage("C-1001", llm, toolbox)
    assert out["trace"][0]["is_error"] and "Unknown case_id" in out["trace"][0]["output"]
    assert out["trace"][1]["is_error"] and "Unknown tool" in out["trace"][1]["output"]
    assert out["triage"]["confidence"] == "high"


@with_toolbox
async def test_step_cap_raises(toolbox):
    with pytest.raises(AgentError):
        await run_triage("C-1001", ScriptedLLM([]), toolbox, max_steps=3)


# ---------- MCP tool logic on the planted case issues ----------

def test_clean_case_has_no_issues():
    for doc in ["aadhaar", "income_certificate", "marksheet", "bank_passbook", "admission_letter"]:
        assert srv.validate_document("C-1004", doc)["issues"] == []
    assert srv.check_deadline("C-1004")["within_limit"] is True


def test_planted_problems_are_detected():
    assert srv.validate_document("C-1001", "bank_passbook")["issues"][0]["code"] == "name_partial_match"
    assert srv.validate_document("C-1001", "crop_loss_photo")["issues"][0]["code"] == "missing"
    assert srv.check_deadline("C-1001")["within_limit"] is True
    late = srv.check_deadline("C-1002")
    assert late["within_limit"] is False and late["days_elapsed"] == 13
    assert srv.validate_document("C-1003", "income_certificate")["issues"][0]["code"] == "expired"
    assert srv.validate_document("C-1003", "marksheet")["issues"][0]["code"] == "missing"
    assert srv.validate_document("C-1005", "address_proof")["issues"][0]["code"] == "name_mismatch"


@pytest.mark.parametrize("a,b,expected", [
    ("Ramesh Gowda", "ramesh  gowda", "exact"),
    ("Ramesh Gowda", "Ramesh G", "partial"),
    ("Sunita Devi", "Sunita Kumari", "mismatch"),
])
def test_name_match(a, b, expected):
    assert srv.name_match(a, b) == expected


# ---------- HTTP API: agent recommends, human decides ----------

def test_api_flow_human_decides(tmp_path):
    app = create_app(llm=ScriptedLLM(happy_script()), db_path=str(tmp_path / "t.db"))
    with TestClient(app) as c:
        assert c.get("/api/health").json()["llm_configured"] is True
        cases = c.get("/api/cases").json()
        assert len(cases) == 6 and all(x["status"] == "new" for x in cases)

        # cannot decide before the agent has analysed
        assert c.post("/api/cases/C-1001/decision", json={"decision": "approve"}).status_code == 409

        r = c.post("/api/cases/C-1001/analyze")
        assert r.status_code == 200 and r.json()["status"] == "awaiting_review"

        # the agent alone never changes the outcome
        assert {x["id"]: x["status"] for x in c.get("/api/cases").json()}["C-1001"] == "awaiting_review"

        d = c.post("/api/cases/C-1001/decision", json={"decision": "request_more_info", "message": "Edited by officer", "note": "called applicant"})
        assert d.json()["status"] == "info_requested"
        audit = d.json()["decisions"][0]
        assert audit["message_edited"] is True and audit["final_message"] == "Edited by officer"

        t = c.get("/api/cases/C-1001/triage").json()
        assert t["status"] == "info_requested" and len(t["decisions"]) == 1


def test_api_without_key_returns_503(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    app = create_app(llm=None, db_path=str(tmp_path / "t.db"))
    with TestClient(app) as c:
        assert c.get("/api/health").json()["llm_configured"] is False
        r = c.post("/api/cases/C-1001/analyze")
        assert r.status_code == 503 and "ANTHROPIC_API_KEY" in r.json()["detail"]
        assert c.post("/api/cases/NOPE/analyze").status_code in (404, 503)
