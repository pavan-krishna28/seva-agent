"""FastAPI app. The agent only recommends; only POST /decision changes a case's status."""
from __future__ import annotations

import os
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .agent import AgentError, run_triage
from .db import Store
from .llm import LLM, default_llm
from .mcp_client import McpToolbox

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DECISION_STATUS = {"approve": "approved", "reject": "rejected", "request_more_info": "info_requested"}


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject", "request_more_info"]
    message: str | None = None  # final message to the applicant, possibly edited by the officer
    note: str | None = None


def create_app(llm: LLM | None = None, db_path: str | None = None, toolbox: McpToolbox | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with AsyncExitStack() as stack:
            app.state.toolbox = toolbox or McpToolbox()
            await app.state.toolbox.start(stack)
            app.state.llm = llm if llm is not None else default_llm()
            app.state.store = Store(db_path or os.getenv("DB_PATH", "seva.db"))
            yield

    app = FastAPI(title="Seva Agent", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return {"ok": True, "llm_configured": app.state.llm is not None,
                "mcp_tools": [t["name"] for t in app.state.toolbox.tools]}

    @app.get("/api/cases")
    async def list_cases():
        data, err = await app.state.toolbox.call("list_open_cases", {})
        if err:
            raise HTTPException(502, str(data))
        statuses = app.state.store.statuses()
        return [c | {"status": statuses.get(c["id"], "new")} for c in data["cases"]]

    @app.get("/api/cases/{case_id}")
    async def get_case(case_id: str):
        data, err = await app.state.toolbox.call("get_case", {"case_id": case_id})
        if err:
            raise HTTPException(404, str(data))
        return data

    @app.post("/api/cases/{case_id}/analyze")
    async def analyze(case_id: str):
        if app.state.llm is None:
            raise HTTPException(503, "ANTHROPIC_API_KEY is not configured. Copy backend/.env.example to backend/.env and add your key.")
        _, err = await app.state.toolbox.call("get_case", {"case_id": case_id})
        if err:
            raise HTTPException(404, f"Unknown case {case_id}")
        try:
            result = await run_triage(case_id, app.state.llm, app.state.toolbox)
        except AgentError as e:
            raise HTTPException(502, str(e))
        app.state.store.save_triage(case_id, result)
        return app.state.store.get_triage(case_id)

    @app.get("/api/cases/{case_id}/triage")
    async def get_triage(case_id: str):
        t = app.state.store.get_triage(case_id)
        if t is None:
            raise HTTPException(404, "No triage yet for this case")
        return t | {"decisions": app.state.store.decisions(case_id)}

    @app.post("/api/cases/{case_id}/decision")
    async def decide(case_id: str, body: DecisionIn):
        t = app.state.store.get_triage(case_id)
        if t is None:
            raise HTTPException(409, "Run the analysis before deciding")
        agent_msg = t["triage"]["message_to_applicant"]
        final = body.message if body.message is not None else agent_msg
        app.state.store.record_decision(case_id, body.decision, DECISION_STATUS[body.decision], final,
                                        final != agent_msg, body.note)
        return {"case_id": case_id, "status": DECISION_STATUS[body.decision],
                "decisions": app.state.store.decisions(case_id)}

    return app


app = create_app()
